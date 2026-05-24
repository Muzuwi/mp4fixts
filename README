# mp4fixts

This is a small Python script that attempts to fix corrupted MP4 timestamps.
This script utilizes the [`pymp4`](https://github.com/beardypig/pymp4) library.

The script fixes one particular corruption case where an underflow occurs during calculation of the very first sample delta in the `stts` atom, which leads to wildly incorrect duration values, confusing most media players and transcoders.

This won't fix other classes of corruption!
In this particular case the file contents are still correct, other than the invalid sample delta which poisons all duration fields of the video track, making the file unplayable.

There are alternative ways of fixing this case (for example: by extracting the raw h264/audio streams from the container file and remuxing them manually), but the goal of this project was to learn a bit about the MP4 format.
This script leaves the entire MP4 file structure as is, and only modifies the corrupted fields.

# Identifying if your file is affected

One way you can tell that your file is affected by this is running `ffprobe path-to-file.mp4`, which will report wildly incorrect duration for the video file, as well as insanely low framerate:

```
Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'VID_20190305_214653.mp4':
  Metadata:
    major_brand     : mp42
    minor_version   : 0
    compatible_brands: isommp42
    creation_time   : 2019-03-05T20:47:32.000000Z
    com.android.version: 8.1.0
    com.android.manufacturer: Samsung
    com.android.model: SM-J710F
  Duration: 11:42:41.71, start: 0.000000, bitrate: 15 kb/s
  Stream #0:0[0x1](eng): Video: h264 (Baseline) (avc1 / 0x31637661), yuv420p(tv, bt709, progressive), 2048x1152, 15 kb/s, SAR 1:1 DAR 16:9, 0.03 fps, 30 tbr, 90k tbn (default)
```

Running `mp4dump --verbosity 3 path-to-file.mp4 | less` will show a similarly corrupted `stts` entry:
```
          [stts] size=12+1524
            entry_count = 190
            entries:
              (       0) sample_count = 1, sample_duration = 3791181956
```

The media file is also unplayable due to this length and ends up having a single frame playing for `T - T_real_duration`.
Seeking sometimes shows different frames, but at durations this long it will probably be hard to seek to the timestamp where the actual video contents begin.

# What this script does

This script fixes up tracks containing corrupted entries in the `stts` atom by replacing entries exceeding a certain threshold with sane values.
Afterwards, `tkhd`/`mvhd`/`mdhd` atoms are updated based on the actual computed time of the track instead of the corrupted time.

While I did attempt to only modify files which are actually corrupted and leave ones without corruption unaffected, you should make a backup just in case.

# How to use

Install `pymp4`, either using your system's package manager, or via venv:
```sh
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

To run:
```sh
python3 ./mp4fixts.py path-to-file.mp4
```
By default, the fixed file is written to `output_fixed.mp4`.

To change the output file path:
```sh
python3 ./mp4fixts.py path-to-file.mp4 --output path-to-output
```

To append a suffix to the input file name:
```sh
python3 ./mp4fixts.py path-to-file.mp4 --output-suffix _fixed
```
This will output the file in `path-to-file_fixed.mp4`

To replace the original file:
```sh
python3 ./mp4fixts.py path-to-file.mp4 --in-place
```

# License

This project is licensed under the [Apache-2.0 license](./LICENSE).