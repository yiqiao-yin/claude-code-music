# CLAUDE.md

Guidance for Claude Code working in this repo.

## What this repo is

Seven self-contained music-video "bundles", each generating a piece of music and an
audio-reactive video for it **entirely from code** — symbolic composition to MIDI,
numerical synthesis in numpy, frame-by-frame rendering with Pillow, muxed by
ffmpeg.

**No AI audio or video generation. No sample libraries.** Every sound is
arithmetic; every frame is drawn. This is not a style preference — it is the point
of the project. If a task seems to call for generating audio or video with a
model, it is the wrong task for this repo.

The work has two halves, and both matter:

1. **The pieces.** Six of them, deliberately unalike — see the table below.
2. **The method.** [`template/instructions.md`](template/instructions.md) is the
   accumulated spec: how to take a brief, what must stay fixed, what should vary,
   how to verify, and every trap found so far. It grows with each bundle. Adding a
   piece without adding what it taught is half the job.

## The one rule

**Before creating or modifying a bundle, read
[`template/instructions.md`](template/instructions.md) in full.** Do not
reconstruct it from this file or from memory.

The short version:

- **Triage the brief first (§1.0).** It arrives as a mood, as notes without
  timing, or as a complete score — and each needs *different* questions. Asking
  "what mood, what key, what arc?" of someone who just wrote out a two-handed
  keyboard score is tone-deaf.
- **Copy the nearest existing bundle's scripts and edit them.** Never write the
  two scripts fresh from the contracts; that produces something that works and
  quietly drifts, which defeats the shared framework.
- **Verify with §5 before reporting success.** Running without an exception is not
  verification.

## What exists

| Bundle | Meter | Key / mode | Tempo | Length | Distinguishing feature |
|---|---|---|---|---|---|
| `moody_drums_bundle` | 4/4 | A minor | 68 | 60.5 s | The original. Half-time kit, cathedral reverb. |
| `optimistic_drums_bundle` | 4/4 | G → C | 104 | 59.4 s | One key change. The clean baseline to copy. |
| `morning_forest_bundle` | 4/4 | C→D→C→E→C | 112 | 89.7 s | Harmonic arch, Karplus-Strong arpeggio, god-rays. |
| `simple_bach_tune` | 4/4 | C major | 72 | 57.3 s | 16th-note figure, harpsichord, all white keys. |
| `avenger_beginning_song` | 4/4 | E minor | 88 | 91.3 s | Two-hand score, brass, orchestral percussion, 4×/8× variants. |
| `music_box_waltz` | **3/4** | **D Dorian** | 132 | 58.6 s | Inharmonic struck bar, oom-pah-pah, three-beat orbit. |
| `church_passacaglia` | 3/4 | **E Phrygian** | 80 | 94.0 s | Pipe organ, **no percussion**, a ground bass five times over. |

Still untouched, for an eighth: swing, stereo, an odd meter (5/4, 7/8), and the
modes Lydian and Mixolydian.

## Layout

```
template/
├── instructions.md              the spec — read this first
├── moody_drums_bundle/
├── optimistic_drums_bundle/
├── morning_forest_bundle/
├── simple_bach_tune/
├── avenger_beginning_song/
├── music_box_waltz/
└── church_passacaglia/
```

Every bundle has the same shape:

```
<name>/
├── README.md          the full recipe — detailed enough to rebuild from alone
├── structure.json     written by script 01, read by script 02
├── scripts/01_make_music.py    composition → MIDI → WAV → MP3 → structure.json
├── scripts/02_make_video.py    analysis → frames → MP4
└── assets/            <name>.mid, .wav, .mp3, <name>_visualizer.mp4
```

Which to copy when starting a new one:

- **`optimistic_drums_bundle`** — the clean baseline. Default choice.
- **`morning_forest_bundle`** — more than two sections, an arpeggio, or
  alternative synth voices.
- **`simple_bach_tune`** — anything on a 16th-note grid.
- **`avenger_beginning_song`** — brass or orchestral percussion, a user-supplied
  two-hand score, a visualizer that draws the notes themselves (it is the only
  bundle exporting every note into `structure.json`), or speed variants
  (`make_4x.py` / `make_8x.py`).
- **`music_box_waltz`** — anything not in 4/4, a modal harmonisation, or
  inharmonic struck-bar voices.
- **`church_passacaglia`** — a **drumless** piece (its visualizer takes `pulse`
  from the downbeat, not the onset detector), organ or any sustained voice, or
  variations over a fixed ground.
- **`moody_drums_bundle`** — the original. Still the only bundle with no
  `structure.json`, so its script 02 hard-codes its own caption. Prefer the others.

## Environment

```bash
pip install numpy scipy pillow midiutil imageio-ffmpeg
```

No system ffmpeg needed — scripts resolve it via `shutil.which("ffmpeg")` falling
back to `imageio_ffmpeg.get_ffmpeg_exe()`. Do not add a hard dependency on a
system ffmpeg; this machine has none.

## Running

```bash
cd template/<name>/scripts
python3 01_make_music.py     # a few seconds
python3 02_make_video.py     # ~1.3 s of render per second of music
```

Both write to `../assets/`. Paths resolve relative to the script — never hard-code
an absolute output path.

## Conventions that are easy to get wrong

**On the music**

- **Never silently "fix" a note the user supplied.** If a pitch looks wrong, flag
  it and ask, or keep the notes and correct the label. Reproducing the brief
  exactly is the job.
- **A melody missing a scale degree is an opportunity.** `music_box_waltz`'s tune
  has no sixth, so the harmony chose the mode. Look at where the melody *ends*.
- **midiutil cannot serialize two overlapping notes of the same pitch on one
  channel.** It dies with `IndexError: pop from empty list` inside
  `deInterleaveNotes`, blaming midiutil rather than your music.
- **Vibrato and pitch scoops must integrate frequency to phase** with `np.cumsum`,
  never `sin(2*pi * freq * vib * t)`. The latter modulates phase and the error
  grows with note length — an intended ±7 cents measured −719/+490 cents on a 3 s
  note. Fixed everywhere; don't reintroduce it.
- **The longest reverb tap must be shorter than one beat.** Scale tap times with
  tempo.

**On verification**

- **Run the per-bar chroma test before the section one.** It localises problems
  instead of averaging them away, and it is what found the vibrato bug.
- **A flagged pitch is a hypothesis, not a verdict.** Bright timbres, swept drums
  and inharmonic percussion all put unplayed notes into the chroma. Narrow to
  70–1200 Hz, check the note list, then **re-render with one part muted at a time.**
- **The onset-count rule needs the right denominator** — every attack in the
  40–120 Hz band, not just kicks. A piece whose bass is power chords at E1 measured
  8.9× against kicks and 1.6× against the honest count, with nothing wrong.
- **Verify PCM data, not the WAV file.** `hashlib.md5(a.tobytes())` after
  `wavfile.read`; file MD5s differ across scipy versions over optional RIFF chunks.
- **Seeded RNG everywhere** — `default_rng(3)` for audio, `default_rng(7)` for
  video particles. Never unseeded.
- **A drumless piece breaks the onset detector.** With no transient it fires on
  noise-floor drift — 585 hits across 2256 frames in `church_passacaglia`, leaving
  the impact ring lit 98% of the time. Set `has_drums: false` and take `pulse`
  from the downbeat instead. General rule: when the audio has no transient, the
  event lives in the score.

**On the repo**

- **`.wav` files stay in git.** Large and regenerable, and keeping them is a
  deliberate decision. Do not propose pruning them to save space.
- **Speed variants are re-synthesized, never post-processed.** Scale the tempo up
  and every absolute time constant down (`instructions.md` §3.6). Resampling
  raises pitch; time-stretching smears attacks.
- After building a bundle, **send the user the `.mp4`**. They asked for a music
  video; a commit is not one.
- **Feed what you learned back into `instructions.md`.** Every bundle so far has
  produced at least one framework-level lesson. That file is the real deliverable.

## Git

Public repo, `main` branch, pushes to
`github.com/yiqiao-yin/claude-code-music`. Commit and push when the user asks, or
as the last step of the build procedure in `instructions.md` §4.
