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
    ├── instructions.md     # how to build a new bundle — read this first
    ├── moody_drums_bundle/
    ├── optimistic_drums_bundle/
    └── morning_forest_bundle/
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

### `morning_forest_bundle`

40 bars at 112 BPM. The harmony arches **C → D → C → E → C** across five 8-bar
sections, each modulation prepared by the dominant of the key it enters. Built
from the brief *"happy and clear and full of hope… crisp and clean, like walking
into a forest in the morning."*

Crispness comes from an 8th-note Karplus-Strong arpeggio in place of a sustained
pad, an FM-bell lead, and the brightest reverb of the three bundles. The kit is
shaker, soft kick, rim and brush — no ordinary snare. The visualizer inverts the
gradient (light above, understory below), adds precomputed god-rays, and
brightens the whole scene in step with the arch.

```bash
cd template/morning_forest_bundle/scripts
python3 01_make_music.py       # -> ../assets/{mid,wav,mp3}, ../structure.json
python3 02_make_video.py       # -> ../assets/morning_forest_visualizer.mp4
```

## Adding a template

Read [`template/instructions.md`](template/instructions.md). It is the spec for
building a new bundle: the questions to answer up front, the parts of the
framework that must stay fixed, a menu of everything that should change, and the
verification steps a bundle has to pass. Hand it to Claude Code with a one-line
brief ("nocturnal jazz in D dorian, brushes, no key change") and it has enough to
go on.

The mechanics:

Each template is a self-contained folder under `template/` with a `README.md`
describing the recipe, a `scripts/` folder, and an `assets/` folder holding the
rendered output. The README should be detailed enough that the piece can be
regenerated from the document alone.
