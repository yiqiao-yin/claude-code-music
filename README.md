# claude-code-music

Music generation using Claude Code.

Every piece here — the notes, the sound, the video — is generated from plain
Python. Symbolic composition to MIDI, numerical synthesis in numpy, audio-reactive
video drawn frame by frame with Pillow. **No AI audio or video models, no sample
libraries.** Every sound is arithmetic; every frame is drawn.

You describe what you want — a mood in a sentence, or the actual notes — and the
result is a finished music video.

## The bundles

| | Key | Tempo | Form | Character |
|---|---|---|---|---|
| [`moody_drums_bundle`](template/moody_drums_bundle/) | A minor | 68 BPM | 16 bars, 60.5 s | Brooding. Half-time kit, descending melody, cathedral reverb. |
| [`optimistic_drums_bundle`](template/optimistic_drums_bundle/) | G → C | 104 BPM | 24 bars, 59.4 s | Uplift. One key change at bar 17, warm sunrise palette. |
| [`morning_forest_bundle`](template/morning_forest_bundle/) | C → D → C → E → C | 112 BPM | 40 bars, 89.7 s | Crisp and hopeful. A harmonic arch, arpeggio, god-rays. |
| [`simple_bach_tune`](template/simple_bach_tune/) | C major | 72 BPM | 16 bars, 57.3 s | Baroque. The Prelude in C figure in 16ths, harpsichord, all white keys. |
| [`avenger_beginning_song`](template/avenger_beginning_song/) | E minor | 88 BPM | 32 bars, 91.3 s | Heroic fanfare. Power chords, brass, orchestral percussion, no kit. |
| [`music_box_waltz`](template/music_box_waltz/) | D dorian | 132 BPM | 40 bars, 58.6 s | Waltz in **3/4**. Inharmonic music box, accordion oom-pah-pah. |
| [`church_passacaglia`](template/church_passacaglia/) | E phrygian | 80 BPM | 40 bars, 94.0 s | Baroque, pipe organ, **no percussion**. A ground bass, five times. |
| [`mozart_sonata_allegro`](template/mozart_sonata_allegro/) | C minor | 138 BPM | 48 bars, 87.5 s | Classical piano, sonata form, Alberti bass. **Stereo.** |

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

### `avenger_beginning_song`

A heroic fanfare in E minor, built from a two-handed keyboard layout supplied note
by note: left hand on power chords with no third (E+B, D+A, C+G), right hand on
triads with the melody on top. One chord per bar at 88 BPM, each hit heavily
accented and left to ring into silence. The written material is stated, restated
with a sub-octave under every chord, then resolved by a four-bar descending run.

Voiced for additive brass with a pitch scoop and breath transient, a darker low
brass with a sine sub, and a horn doubling the melody. Percussion is orchestral
only — pitched timpani tuned to each left-hand root, taiko on the downbeats, and
cymbal swells that land on each section change. No drum kit and no backbeat.

The visualizer draws a scrolling piano roll of the actual score with the two hands
in different colours, over a palette that warms from steel to gold at the
restatement.

It also ships **4× and 8× renders** (`make_4x.py`, `make_8x.py`) — 22.8 s and
11.4 s. These are true tempo changes at 352 and 704 BPM, re-synthesized with the
pitch untouched, not playback speed-ups: resampling would have raised everything
two or three octaves, and time-stretching would have smeared the brass attacks.

### `music_box_waltz`

A wistful waltz built on an 8-bar melody supplied note by note in 3/4. The tune
uses only C D E F G — no sixth degree at all — so the melody alone cannot say
whether it is major, minor or modal, and the harmony gets to decide. Harmonised
in **D Dorian**: the tune ends on D, which becomes the tonic rather than a hanging
second, and the G major chord supplies the raised sixth that makes it Dorian.

The melody is played by an inharmonic struck-bar voice — a real music box's modes
sit near 1.00, 2.76, 5.40 and 8.93, not at whole-number harmonics — over a detuned
accordion playing oom-pah-pah and a light brushed waltz kit. The visualizer runs
three beat markers orbiting the centre, one full turn per bar, so you can count
1-2-3 off the screen.

The repo's first piece in a meter other than 4/4, and its first in a church mode.

### `church_passacaglia`

Built from a deliberately vague brief — *"baroque style music like Bach, typically
played by harpsichord, in church or something"* — by someone who couldn't write
notes down. Three questions with concrete options turned it into a piece; it is
the clearest worked example of how the interview is meant to go.

An 8-bar ground bass in **E Phrygian**, repeated five times without variation
while the music above it accumulates: pedal alone, then chords, then a melody,
then running figuration, then full organ. The mode follows from the form — a
passacaglia's classic ground is a descending tetrachord, and that descent *is*
Phrygian.

Everything is one pipe-organ voice under four registrations built from real stop
lists, with no decay, a breathy chiff on each attack, and a per-pipe detune. **No
percussion at all** — which broke the visualizer's onset detector and taught the
framework that a drumless piece has to take its pulse from the score instead.

### `mozart_sonata_allegro`

The follow-up to the passacaglia, from the brief *"like Bach but Mozart — one of
those conventional piano sonatas."* A quick opening movement, in C minor, in
**sonata form** — the only form in the repo that argues rather than repeats. Its
second subject is heard in E♭ major at bar 13 and again in C minor at bar 41:
same tune, once bright and once dark, and everything else exists to make that
reconciliation land.

Four things separate Classical from Baroque and all four are here: one singing
line over an **Alberti bass** instead of equal voices, four-bar phrases that
breathe, and **written dynamics** — which a harpsichord physically cannot play,
and which is why the piano replaced it.

The **first stereo bundle**, panned by pitch. The fortepiano models real string
inharmonicity (`fₙ = n·f₀·√(1+Bn²)`) with decay depending on both partial number
and pitch. The visualizer plots the harmony's distance from home, so you can watch
sonata form leave and come back.

## Making a new one

Point Claude Code at [`template/instructions.md`](template/instructions.md) and
say what you want — even just "create a new music video." It asks a short batch of
questions, defaults everything else, builds the bundle, verifies it, and hands you
the `.mp4`.

**Which questions depends on what you brought.**

### If you have a mood but no notes

Three questions, because nothing sensible can be guessed for them:

1. **Mood or genre, in your own words.** One sentence. "Nocturnal jazz, smoky bar,
   brushes not sticks." "Driving and mechanical, like a train at night."
2. **Key and mode** — or "you pick." Mode matters more than key: Dorian, Lydian
   and Phrygian on the same root are three different pieces.
3. **Does the harmony go anywhere?** Just loop, one key change, a gradual
   darkening, a build and release, a false ending?

### If you have the notes

Write them as `NOTE:BEATS`, one bar per line, and make each line add up to a bar:

```
E4:1.5 F4:0.5 E4:1        <- 3 beats: a bar of 3/4
G4:2 G4:1                 <- 3
```

`E4` on its own means one beat; `R:1` is a rest; `[E4 G4 B4]:2` is a chord. That
last rule — every line sums to a bar — catches your own typos before anyone else
sees them, and it's how the meter gets settled without discussion. This is how
`music_box_waltz` was written.

If you give pitches but no rhythm, the questions become rhythm, form and
orchestration instead — that's how `avenger_beginning_song` was built, from a
two-handed keyboard layout with no durations at all.

### What else is in there

`instructions.md` holds the invariant framework contract, a menu of what should
vary between bundles (modes, meters, 11 drop-in synth voices, drum feels, reverb,
palettes), patterns for growing short material into a full piece, how to render
speed variants without wrecking the pitch, the build procedure, and the
verification every bundle has to pass. It grows with each piece — every bundle so
far has taught it at least one thing.

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
    ├── avenger_beginning_song/
    ├── music_box_waltz/
    ├── church_passacaglia/
    ├── mozart_sonata_allegro/
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
