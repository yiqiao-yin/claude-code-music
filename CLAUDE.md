# CLAUDE.md

Guidance for Claude Code working in this repo.

## What this repo is

A collection of self-contained music-video "bundles". Each one generates a piece
of music and an audio-reactive video for it **entirely from code** — symbolic
composition to MIDI, numerical synthesis in numpy, frame-by-frame rendering with
Pillow, muxed by ffmpeg.

**No AI audio or video generation. No sample libraries.** Every sound is
arithmetic; every frame is drawn. This is not a style preference — it is the
point of the project. If a task seems to call for generating audio or video with
a model, it is the wrong task for this repo.

## The one rule

**Before creating or modifying a bundle, read
[`template/instructions.md`](template/instructions.md) in full.** It is the spec:
the three questions to ask the user, the parts of the framework that must not
change, the menu of what should, the build procedure, and the verification a
bundle has to pass before you call it done.

Do not reconstruct that guidance from this file or from memory. Read it.

The short version of what it says:

- When someone asks for a new music video and hasn't answered the three questions
  in §1.1 — **mood, key/mode, harmonic arc** — stop and ask, all in one batch,
  offering the concrete options listed there. Everything else has a default.
- **Copy the nearest existing bundle's scripts and edit them.** Never write the
  two scripts fresh from the contracts; that produces something that works and
  quietly drifts, which defeats the shared framework.
- Verify with §5 before reporting success. Running without an exception is not
  verification.

## Layout

```
template/
├── instructions.md              the spec — read this first
├── moody_drums_bundle/          A minor, 68 BPM, 16 bars. The original.
├── optimistic_drums_bundle/     G → C, 104 BPM, 24 bars. The clean baseline.
├── morning_forest_bundle/       C → D → C → E → C, 112 BPM, 40 bars.
├── simple_bach_tune/            C major, 72 BPM, 16 bars. Baroque, 16th notes.
├── avenger_beginning_song/      E minor, 88 BPM, 32 bars. Heroic fanfare.
└── music_box_waltz/             D dorian, 132 BPM, 40 bars. 3/4 waltz.
```

Every bundle has the same shape:

```
<name>_bundle/
├── README.md          the full recipe — detailed enough to rebuild from alone
├── structure.json     written by script 01, read by script 02
├── scripts/01_make_music.py    composition → MIDI → WAV → MP3 → structure.json
├── scripts/02_make_video.py    analysis → frames → MP4
└── assets/            <name>.mid, .wav, .mp3, <name>_visualizer.mp4
```

Which to copy when building a new one:

- **`optimistic_drums_bundle`** — the clean baseline. Script-relative paths,
  in-script MP3, `structure.json` handoff, single FFT pass. Default choice.
- **`morning_forest_bundle`** — copy this if the piece has more than two
  sections, an arpeggio, or non-default synth voices.
- **`simple_bach_tune`** — copy this for anything on a 16th-note grid.
- **`avenger_beginning_song`** — copy this for brass or orchestral percussion, or
  when the visualizer should draw the score itself; it is the only bundle that
  exports every note into `structure.json`. It also carries the speed-variant
  machinery (`make_4x.py` / `make_8x.py`).
- **`music_box_waltz`** — copy this for anything not in 4/4, for a modal
  harmonisation, or for inharmonic struck-bar voices.
- **`moody_drums_bundle`** — the original. Paths and ffmpeg are now handled like
  the others, but it still has no `structure.json`, so its script 02 hard-codes
  its own caption. Prefer one of the three above.

## Environment

```bash
pip install numpy scipy pillow midiutil imageio-ffmpeg
```

No system ffmpeg needed — scripts resolve it via `shutil.which("ffmpeg")` falling
back to `imageio_ffmpeg.get_ffmpeg_exe()`. Do not add a hard dependency on a
system ffmpeg; this machine has none.

## Running

```bash
cd template/<name>_bundle/scripts
python3 01_make_music.py     # ~5-10 s
python3 02_make_video.py     # ~1.3 s of render per second of music
```

Both write to `../assets/`. Paths resolve relative to the script — never
hard-code an absolute output path.

## Conventions that are easy to get wrong

- **`.wav` files stay in git.** They are large and regenerable, and keeping them
  is a deliberate decision. Do not propose pruning them to save repo size.
- **Verify PCM data, not the WAV file.** `hashlib.md5(a.tobytes())` after
  `wavfile.read`. File-level MD5s differ across scipy versions over optional RIFF
  chunks while the samples are bit-identical — a bundle README's file MD5s are
  reference only.
- **midiutil cannot serialize two overlapping notes of the same pitch on one
  channel.** It dies with `IndexError: pop from empty list` inside
  `deInterleaveNotes`, and the traceback blames midiutil, not your music. Bites
  when one track carries two simultaneous parts.
- **Seeded RNG everywhere** — `default_rng(3)` for audio noise, `default_rng(7)`
  for video particles. Never unseeded.
- **Vibrato must integrate frequency to phase** with `np.cumsum`, never
  `sin(2*pi * freq * vib * t)`. The latter modulates phase, and the pitch error
  grows with note length — an intended ±7 cents measured −719/+490 cents on a 3 s
  note. Fixed in all four bundles; don't reintroduce it.
- **The chroma check misreads bright timbres and swept percussion.** The fifth
  harmonic of a note is a major third two octaves up and the seventh is a minor
  seventh, so rich voices put unplayed pitch classes into the analysis; pitch-swept
  or inharmonic drums do the same. Narrow to ~70–1200 Hz, check per bar, and
  re-render without percussion before believing a failure.
- **The 5× onset rule assumes the kick is alone in 40–120 Hz.** If the bass parts
  sit in that band too, count every low note attack in the denominator, not just
  the kicks.
- **A melody that transposes with its section** must be checked against every
  section's chords, including any untransposed pivot chords.
- After building a bundle, **send the user the `.mp4`**. They asked for a music
  video; a commit is not one.

## Git

Public repo, `main` branch, pushes to
`github.com/yiqiao-yin/claude-code-music`. Commit and push when the user asks,
or as the last step of the build procedure in `instructions.md` §4.
