#!/usr/bin/env python3
import sys
import collections
import collections.abc
import argparse
import pathlib

# Monkey patch collections to provide backwards-compatible collections.Sequence.
# pymp4 relies on an older version of construct which doesn't support newer
# Python versions.
setattr(collections, "Sequence", collections.abc.Sequence)

# Importing pymp4, which will import construct, should be done after the
# monkeypatch.
from pymp4.parser import MP4, Box

# Duration of the track, in seconds, above which the track will be considered to
# have a broken timestamp.
INVALID_TRACK_DURATION_THRESHOLD_SEC = 10_000
# Sample delta value of an entry in the STTS that will be considered invalid.
INVALID_STTS_DELTA_THRESHOLD = 100_000


def main():
    parser = argparse.ArgumentParser(
        prog="mp4fixts",
        description="Attempt fixing corrupted duration timestamps of an MP4 file.",
    )
    parser.add_argument("filename", help="input MP4 file")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("-o", "--output", help="output filename", type=str)
    g.add_argument(
        "--output-prefix",
        help="append a prefix to the filename of the input file",
        type=str,
    )
    g.add_argument(
        "-i", "--in-place", help="replace the existing file", action="store_true"
    )
    args = parser.parse_args()

    input_file = args.filename
    output_file = ""
    if hasattr(args, "output"):
        output_file = args.output
    if getattr(args, "in_place", False):
        output_file = input_file
    if getattr(args, "output_prefix", None) is not None:
        output_file = pathlib.Path(input_file)
        output_file = output_file.with_stem(
            output_file.stem + args.output_prefix
        ).resolve()

    mp4: MP4
    with open(input_file, "rb") as f:
        b = f.read()
        mp4 = MP4.parse(b)

    ftyp = next(filter(lambda x: x.type == b"ftyp", mp4))
    if ftyp.major_brand == b"isom":
        print(
            "pymp4 cannot handle this file, but it's probably fine as it did not come from the broken phone."
        )
        exit(0)

    moov = next(filter(lambda x: x.type == b"moov", mp4))
    mvhd = next(filter(lambda x: x.type == b"mvhd", moov.children))
    print("MVHD timescale:", mvhd.timescale, "duration:", mvhd.duration)

    # Try fixing up all broken tracks
    for trak in filter(lambda x: x.type == b"trak", moov.children):
        tkhd = next(filter(lambda x: x.type == b"tkhd", trak.children))
        mdia = next(filter(lambda x: x.type == b"mdia", trak.children))
        mdhd = next(filter(lambda x: x.type == b"mdhd", mdia.children))
        track_seconds = int(mdhd.duration / mdhd.timescale)
        if track_seconds < INVALID_TRACK_DURATION_THRESHOLD_SEC:
            print(
                f"Skipping track at offset {trak.offset} as it appears to have correct timestamp"
            )
            continue
        print(
            f"Found broken track at offset {trak.offset} with duration of {track_seconds}s"
        )
        print("TKHD duration:", tkhd.duration)
        print("MDHD timescale:", mdhd.timescale, "duration:", mdhd.duration)

        minf = next(filter(lambda x: x.type == b"minf", mdia.children))
        stbl = next(filter(lambda x: x.type == b"stbl", minf.children))
        stts = next(filter(lambda x: x.type == b"stts", stbl.children))
        for idx, entry in enumerate(stts.entries):
            if entry.sample_delta > INVALID_STTS_DELTA_THRESHOLD:
                print(
                    f"STTS Entry {idx} invalid: sample delta is {entry.sample_delta}, correcting"
                )
                # Use sample delta of the following entry to fix up the broken one.
                entry.sample_delta = stts.entries[idx + 1].sample_delta

        stts_duration = 0
        for entry in stts.entries:
            stts_duration += entry.sample_delta * entry.sample_count
        stts_duration_sec = float(stts_duration) / mdhd.timescale
        tkhd_new_duration = int(stts_duration_sec * mvhd.timescale)
        print(
            f"STTS calculated duration: {stts_duration} @ {mdhd.timescale} ({stts_duration_sec}s)"
        )
        print(
            f"Updating MDHD duration: {mdhd.duration} ({mdhd.duration / mdhd.timescale}s) => {stts_duration}"
        )
        print(
            f"Updating TKHD duration: {tkhd.duration} ({tkhd.duration / mvhd.timescale}s) => {tkhd_new_duration}"
        )
        mdhd.duration = stts_duration
        # TKHD duration is specified with respect to the MVHD timescale.
        tkhd.duration = tkhd_new_duration

    # Establish base duration from the fixed up tracks and modify mvhd accordingly.
    # This should match the longest track.
    longest_duration_track = 0.0
    for trak in filter(lambda x: x.type == b"trak", moov.children):
        tkhd = next(filter(lambda x: x.type == b"tkhd", trak.children))
        mdia = next(filter(lambda x: x.type == b"mdia", trak.children))
        mdhd = next(filter(lambda x: x.type == b"mdhd", mdia.children))

        duration = float(tkhd.duration) / mvhd.timescale
        longest_duration_track = max(longest_duration_track, tkhd.duration)
        print(f"Track at offset {trak.offset} duration: {tkhd.duration} ({duration}s)")

    print(f"Updating MVHD duration: {mvhd.duration} => {longest_duration_track}")
    mvhd.duration = longest_duration_track

    with open(output_file, "wb") as f:
        f.write(MP4.build(mp4))


if __name__ == "__main__":
    main()
