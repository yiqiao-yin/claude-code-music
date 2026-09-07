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
    └── moody_drums_bundle/
        ├── README.md      # full recipe to regenerate the track from scratch
        ├── scripts/
        │   ├── 01_make_music.py   # writes the MIDI + synthesizes the WAV
        │   └── 02_make_video.py   # renders the audio-reactive visualizer
        └── assets/
            ├── moody_drums.mid
            ├── moody_drums.wav
            ├── moody_drums.mp3
            └── moody_drums_visualizer.mp4
```

## Templates

### `moody_drums_bundle`

A 16-bar piece in A minor at 68 BPM — pad, bass, sparse flute-ish melody, and a
half-time drum kit entering at bar 3 — plus a 1280x720 visualizer driven by RMS,
a 32-band log spectrum, and a low-band onset detector.

```bash
pip install numpy scipy pillow midiutil   # plus ffmpeg from your package manager

cd template/moody_drums_bundle/scripts
python3 01_make_music.py                  # -> moody_drums.mid, moody_drums.wav
ffmpeg -y -i moody_drums.wav -b:a 192k moody_drums.mp3
python3 02_make_video.py                  # -> moody_drums_visualizer.mp4
```

Output paths are set at the top of each script — edit them for your machine.
See [`template/moody_drums_bundle/README.md`](template/moody_drums_bundle/README.md)
for the exact musical spec, synthesis parameters, and render settings.

## Adding a template

Each template is a self-contained folder under `template/` with a `README.md`
describing the recipe, a `scripts/` folder, and an `assets/` folder holding the
rendered output.
