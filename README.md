# claude-code-music

Music generation using Claude Code.

Every piece here — the notes, the sound, the video — is generated from plain
Python. Symbolic composition to MIDI, numerical synthesis in numpy, audio-reactive
video drawn frame by frame with Pillow. **No AI audio or video models, no sample
libraries.** Every sound is arithmetic; every frame is drawn.

You describe a mood in a sentence; the result is a finished music video.

## The bundles

| | Key | Tempo | Form | Character |
|---|---|---|---|---|
| [`moody_drums_bundle`](template/moody_drums_bundle/) | A minor | 68 BPM | 16 bars, 60.5 s | Brooding. Half-time kit, descending melody, cathedral reverb. |
| [`optimistic_drums_bundle`](template/optimistic_drums_bundle/) | G → C | 104 BPM | 24 bars, 59.4 s | Uplift. One key change at bar 17, warm sunrise palette. |
| [`morning_forest_bundle`](template/morning_forest_bundle/) | C → D → C → E → C | 112 BPM | 40 bars, 89.7 s | Crisp and hopeful. A harmonic arch, arpeggio, god-rays. |
| [`simple_bach_tune`](template/simple_bach_tune/) | C major | 72 BPM | 16 bars, 57.3 s | Baroque. The Prelude in C figure in 16ths, harpsichord, all white keys. |

### `moody_drums_bundle`

The original. A minor at 68 BPM — pad, bass, a sparse flute-ish melody, and a
half-time drum kit entering at bar 3 — plus a 1280×720 visualizer driven by RMS,
a 32-band log spectrum, and a low-band onset detector.

Originally it hard-coded its output paths and needed a system ffmpeg; both were
converted to match the other bundles when its lead voice was fixed. It is still
the only bundle without a `structure.json`.

### `optimistic_drums_bundle`

Same pipeline, brighter genre: 24 bars that start in **G major** and lift to
**C major** at bar 17. The visualizer runs a warm sunrise palette and blooms at
the modulation.

Built as a reproducibility test of the moody template — the MIDI regenerated
byte-identical and the WAV regenerated with 100% identical PCM samples on a
different Python/numpy/scipy stack. The fixes that came out of it (script-relative
paths, ffmpeg fallback, in-script MP3, the `structure.json` handoff) are listed in
[its README §7](template/optimistic_drums_bundle/README.md#7-what-changed-from-the-moody-template).

### `morning_forest_bundle`

40 bars whose harmony arches **C → D → C → E → C** across five 8-bar sections,
each modulation prepared by the dominant of the key it enters. Built from the
brief *"happy and clear and full of hope… crisp and clean, like walking into a
forest in the morning."*

The crispness is an 8th-note Karplus-Strong arpeggio in place of a sustained pad,
an FM-bell lead over a sine core, and the brightest, shortest reverb of the three.
The kit is shaker, soft kick, rim and brush — no ordinary snare. The visualizer
inverts the gradient (light above, understory below), adds precomputed god-rays,
and brightens the whole scene in step with the arch.

### `simple_bach_tune`

The opening figure of Bach's Prelude in C, BWV 846 — a five-note broken chord per
bar, played twice a bar in 16th notes — over sixteen bars that open with
`C Dm G/B C` and then walk home through three descending-fifths chains. Not a note
outside C major: the whole piece is white keys.

A twelve-harmonic additive harpsichord with a noise quill carries the figure, over
a held bowed continuo, with an upper voice entering at bar 5 that descends by step
and climbs home. The drums are a light pulse staged in behind the counterpoint —
shaker from bar 3, soft kick and rim from bar 5. The visualizer runs a candlelit
palette and draws the sixteen-bar structure as a ring of ticks with the current
bar lit, plus a live chord readout.

Its folder is `simple_bach_tune`, not `..._bundle`, because that is the name that
was asked for.

## Making a new one

Point Claude Code at [`template/instructions.md`](template/instructions.md) and
say what you want — even just "create a new music video." It will ask you three
questions, default everything else, build the bundle, verify it, and hand you
the `.mp4`.

The three questions, because nothing sensible can be guessed for them:

1. **Mood or genre, in your own words.** One sentence. "Nocturnal jazz, smoky bar,
   brushes not sticks." "Driving and mechanical, like a train at night."
2. **Key and mode** — or "you pick." Mode matters more than key: Dorian, Lydian
   and Phrygian on the same root are three different pieces.
3. **Does the harmony go anywhere?** Just loop, one key change, a gradual
   darkening, a build and release, a false ending?

`instructions.md` also holds the invariant framework contract, a menu of what
should vary between bundles (modes, forms, 11 drop-in synth voices, drum feels,
reverb, palettes), the build procedure, and the verification a bundle must pass.

## Running a bundle

```bash
pip install numpy scipy pillow midiutil imageio-ffmpeg

cd template/<name>_bundle/scripts
python3 01_make_music.py     # -> ../assets/{mid,wav,mp3}, ../structure.json
python3 02_make_video.py     # -> ../assets/<name>_visualizer.mp4
```

No system ffmpeg required — the scripts fall back to the static binary bundled
with `imageio-ffmpeg`. Expect a few seconds for the audio and roughly 1.3 s of
render per second of music for the video.

## Layout

```
.
├── CLAUDE.md                       guidance for Claude Code
├── README.md
└── template/
    ├── instructions.md             the spec for building a new bundle
    ├── moody_drums_bundle/
    ├── optimistic_drums_bundle/
    ├── simple_bach_tune/
    └── morning_forest_bundle/
        ├── README.md               full recipe, detailed enough to rebuild from alone
        ├── structure.json          bar/section map, script 01 → script 02
        ├── scripts/
        │   ├── 01_make_music.py    composition → MIDI → WAV → MP3
        │   └── 02_make_video.py    analysis → frames → MP4
        └── assets/
            ├── morning_forest.mid
            ├── morning_forest.wav
            ├── morning_forest.mp3
            └── morning_forest_visualizer.mp4
```

Every bundle is self-contained and follows this shape. Each `README.md` is written
so the piece could be rebuilt from the document alone, without the scripts.

## Reproducibility

The MIDI is deterministic. The audio is deterministic down to the sample — but
check the **PCM data**, not the WAV file:

```python
import hashlib
from scipy.io import wavfile
sr, a = wavfile.read("assets/<name>.wav")
print(hashlib.md5(a.tobytes()).hexdigest())
```

WAV file-level MD5s differ across scipy versions over optional RIFF chunks while
the samples stay bit-identical, so the file hashes recorded in each bundle README
are reference only. MP3 and MP4 bytes vary with the ffmpeg build; the audible and
visible content does not.
