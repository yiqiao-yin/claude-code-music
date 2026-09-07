# claude-code-music

Music generation using Claude Code.

A playground for making music with an AI coding agent — symbolic composition,
numerical synthesis, and audio-reactive video, all generated from plain Python.
No AI audio or video models involved; every note and every frame comes from code.

## Structure

```
.
├── README.md
└── template/
    ├── moody_drums_bundle/
    └── optimistic_drums_bundle/
        ├── README.md      # full recipe to regenerate the track from scratch
        ├── structure.json # bar/section map, handed from script 01 to script 02
        ├── scripts/
        │   ├── 01_make_music.py   # MIDI + WAV synthesis + MP3
        │   └── 02_make_video.py   # audio-reactive visualizer
        └── assets/
            ├── optimistic_drums.mid
            ├── optimistic_drums.wav
            ├── optimistic_drums.mp3
            └── optimistic_drums_visualizer.mp4
```

## Templates

### `moody_drums_bundle`

A 16-bar piece in A minor at 68 BPM — pad, bass, sparse flute-ish melody, and a
half-time drum kit entering at bar 3 — plus a 1280x720 visualizer driven by RMS,
a 32-band log spectrum, and a low-band onset detector. The original template.

```bash
cd template/moody_drums_bundle/scripts
python3 01_make_music.py                  # -> moody_drums.mid, moody_drums.wav
ffmpeg -y -i moody_drums.wav -b:a 192k moody_drums.mp3
python3 02_make_video.py                  # -> moody_drums_visualizer.mp4
```

Output paths are hard-coded to `/mnt/user-data/outputs/` at the top of each
script — edit them for your machine.

### `optimistic_drums_bundle`

Same pipeline, brighter genre: 24 bars at 104 BPM that start in **G major** and
lift to **C major** at bar 17. The visualizer runs a warm sunrise palette and
blooms at the modulation. Built as a reproducibility test of the moody template;
the fixes it produced are listed in
[its README §7](template/optimistic_drums_bundle/README.md#7-what-changed-from-the-moody-template).

```bash
pip install numpy scipy pillow midiutil imageio-ffmpeg

cd template/optimistic_drums_bundle/scripts
python3 01_make_music.py       # -> ../assets/{mid,wav,mp3}, ../structure.json
python3 02_make_video.py       # -> ../assets/optimistic_drums_visualizer.mp4
```

No path editing needed; ffmpeg is located automatically.

## Adding a template

Each template is a self-contained folder under `template/` with a `README.md`
describing the recipe, a `scripts/` folder, and an `assets/` folder holding the
rendered output. The README should be detailed enough that the piece can be
regenerated from the document alone.
