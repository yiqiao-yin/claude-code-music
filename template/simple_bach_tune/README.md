# Recreating "simple bach tune": MIDI, MP3, and MP4

This document is the full recipe to regenerate `simple_bach_tune.mid`,
`simple_bach_tune.mp3`, and `simple_bach_tune_visualizer.mp4` from scratch. It
follows the pipeline in [`../instructions.md`](../instructions.md): symbolic
composition, numerical synthesis, frame-by-frame rendering. No AI audio or video
generation.

> **Folder naming.** Every other bundle is `<name>_bundle`; this one is plain
> `simple_bach_tune` because that is the folder name that was asked for.

**The brief it was built from:** a simple Bach tune, clear and rhythmic, with
drums in the background. The requested figure —

```
C4 E4 G4 C5 E5 G4 C5 E5      then the same from D4, then from B3, then home to C4
```

— is the opening figure of Bach's Prelude in C, BWV 846, and the requested root
motion C → D → B → C is that prelude's first four bars.

## 0. Environment

| Component | Version used |
|---|---|
| Python | 3.10.12 |
| numpy | 2.2.6 |
| scipy | 1.15.3 |
| Pillow | 12.2.0 |
| midiutil | 1.2.1 |
| ffmpeg | 7.0.2 (libx264 + aac + libmp3lame) |

```bash
pip install numpy scipy pillow midiutil imageio-ffmpeg
```

Reproducibility notes:

- The MIDI file is fully deterministic. Same script, same bytes.
- One seeded RNG in the audio, `default_rng(3)`, used for the harpsichord quill
  noise and the drums; `default_rng(7)` for video particles.
- Verify the **PCM sample data**, not the WAV container:

```python
import hashlib
from scipy.io import wavfile
sr, a = wavfile.read("assets/simple_bach_tune.wav")
print(hashlib.md5(a.tobytes()).hexdigest())   # e25804ac215141591fd5251b58858d48
```

File MD5s from the original run, for reference only:

```
10d343b77304e6722b3663e75d1d5294  simple_bach_tune.mid
f1225556141ab4f8ecfbb9ba5b31cdfd  simple_bach_tune.wav
09a2602ef815cc813a1a19801373d007  simple_bach_tune.mp3
218b17a752772c8dbc06ac476c0e39e3  simple_bach_tune_visualizer.mp4
```

## 1. Musical specification

Everything below is hard-coded in `scripts/01_make_music.py`.

**Global**

- Key: C major, and it never leaves. Every note in the piece is a white key.
- Tempo: 72 BPM, 4/4
- Form: 16 bars = 53.33 s, plus a 4 s tail = **57.33 s** total
- Sample rate for synthesis: 44,100 Hz, mono, 16-bit PCM

**The figure.** One five-note cell per bar, ascending — root, 3rd, 5th, octave,
10th. The figure indexes into it as `[0, 1, 2, 3, 4, 2, 3, 4]`, and the whole
eight-note group is played **twice per bar in 16th notes**, sixteen notes to the
bar. That doubling is Bach's; the eight-note group alone would be eighth notes and
would not move.

```python
FIGURE = [0, 1, 2, 3, 4, 2, 3, 4]
STEPS_PER_BAR = 16
STEP = 0.25            # beats per 16th
```

Velocities accent the shape: 74 at the head of each group, 66 on the other beats,
58 elsewhere.

**Harmony.** Four 4-bar phrases. The requested four bars open it; the rest is
three descending-fifths chains, which is how Bach keeps a single figure moving.

| Bar | Chord | Cell (MIDI) | Notes | Phrase |
|---|---|---|---|---|
| 1 | C | 60 64 67 72 76 | C4 E4 G4 C5 E5 | statement |
| 2 | Dm | 62 65 69 74 77 | D4 F4 A4 D5 F5 | |
| 3 | G/B | 59 62 67 71 74 | B3 D4 G4 B4 D5 | |
| 4 | C | 60 64 67 72 76 | C4 E4 G4 C5 E5 | |
| 5 | Am | 57 60 64 69 72 | A3 C4 E4 A4 C5 | first chain |
| 6 | Dm | 62 65 69 74 77 | D4 F4 A4 D5 F5 | A → D → G → C |
| 7 | G | 55 59 62 67 71 | G3 B3 D4 G4 B4 | |
| 8 | C | 60 64 67 72 76 | C4 E4 G4 C5 E5 | |
| 9 | F | 53 57 60 65 69 | F3 A3 C4 F4 A4 | second chain |
| 10 | B° | 59 62 65 71 74 | B3 D4 F4 B4 D5 | F → B → E → A |
| 11 | Em | 52 55 59 64 67 | E3 G3 B3 E4 G4 | the low point |
| 12 | Am | 57 60 64 69 72 | A3 C4 E4 A4 C5 | |
| 13 | Dm | 62 65 69 74 77 | D4 F4 A4 D5 F5 | cadence |
| 14 | G7 | 55 59 62 65 71 | G3 B3 D4 F4 B4 | D → G → C |
| 15 | C | 60 64 67 72 76 | C4 E4 G4 C5 E5 | |
| 16 | C | 60 64 67 72 76 | C4 E4 G4 C5 E5 | |

Root motion: **C D G C | A D G C | F B E A | D G C C** — three descending-fifths
chains (A-D-G-C, F-B-E-A, D-G-C) inside a sixteen-bar arch that dips to its lowest
register at bar 11 and climbs home.

**Bar 3 is G/B, not G7/B.** The requested figure from B3 gives B-D-G — a
first-inversion G *triad*, with no seventh. Rather than force an F into the
five-note shape, the seventh is held back until bar 14, so the only true G7 in the
piece is the one that resolves the final cadence. Bar 10's B° and bar 3's G/B are
the two inversions; both take B as their bass, which is what the voicing is for.

**Continuo:** the root of each chord an octave below the cell,
`BASS = [c[0] - 12 for c in CELLS]`, range MIDI 40–50. Held 3.8 beats per bar at
velocity 68 — a sustained bass line, not the root-plus-fifth pattern the other
bundles use.

**Upper voice:** one held note per bar entering at bar 5, alternating between the
fifth and the root of each chord. It forms a stepwise descent and then climbs home:

```
bar   5   6   7   8   9  10  11  12  13  14  15  16
note  E5  D5  D5  C5  C5  B4  B4  A4  A4  B4  C5  E5
```

Each note is a chord tone of its own bar and is tied across the change to the next,
which is the chain-of-suspensions shape a Bach chorale line has.

**Drums** — a light pulse, staged so it never fights the counterpoint.

- Shaker (note 70): every 8th note, from **bar 3**, velocity 54 / 38
- Kick (note 36): beats 0 and 2, from **bar 5**, velocity 82
- Rim (note 37): beats 1 and 3, from bar 5, velocity 68
- Fill: two extra rim hits at beats 3.5 and 3.75 of every 4th bar, marking each phrase

The first phrase is therefore unaccompanied except for the shaker's last two bars,
and the kit arrives with the first descending-fifths chain at 13.3 s.

## 2. MIDI file

`midiutil.MIDIFile(4)`, four tracks, standard channel layout.

| Track | Channel | Program | Content |
|---|---|---|---|
| 0 Harpsichord | 0 | 6 (Harpsichord) | the figure |
| 1 Continuo | 1 | 42 (Cello) | bass line |
| 2 Upper voice | 2 | 40 (Violin) | held melody |
| 3 Drums | 9 | n/a | shaker, kick, rim |

Tempo event 72 BPM at tick 0.

## 3. Audio synthesis (WAV)

Helpers are the canonical ones from `instructions.md` §2.7 — `f_of`, `env` with
clamped segments, `lowpass`, `place`, `rng_d`.

**`harpsichord(freq, dur=0.9)`** — the whole piece rests on this voice. Twelve
harmonics rolling off slowly at `1 / h ** 0.75` (bright, plucked-string), amplitude
normalized, an exponential body decay `exp(-3.2 t)`, plus a noise burst at
`exp(-250 t) * 0.18` standing in for the quill. Envelope (0.002, 0.02, 0.9, 0.15).
Harmonics above `0.9 * Nyquist` are skipped. Cached by pitch — the figure repeats
the same handful of notes 256 times. Gain 0.30 / 0.26 / 0.22 by beat position.

**`continuo(freq, dur)`** — six harmonics at `1 / h ** 1.2`, low-passed 1300 Hz,
envelope (0.06, 0.3, 0.7, 0.5). Gain 0.30.

**`viol(freq, dur)`** — eight harmonics at `1 / h ** 1.1`, low-passed 2600 Hz,
envelope (0.15, 0.35, 0.75, 0.6), with a 0.3 percent 4.5 Hz vibrato easing in over
0.8 s. Gain 0.17. **The vibrato integrates frequency to phase with `cumsum`** —
see §7, this is not a stylistic detail.

**Drums** (RNG seeded with 3)

- `kick_soft` (0.4 s): sine sweeping `120 * exp(-20t) + 44` Hz, amplitude
  `exp(-9t)`, no click. Gain 0.45.
- `rim` (0.06 s): 400 Hz sine at `exp(-90t)` plus noise at `exp(-300t) * 0.4`.
  Gain 0.30, fills 0.20 and 0.28.
- `shaker` (0.07 s): noise at `exp(-80t)`, high-passed 9000 Hz. Gain 0.085 / 0.05.

**Mix and reverb**

1. Sum harpsichord, continuo and upper voice into `out`.
2. Reverb `out` only: taps at **89, 137, 211, 331 ms**, gains 0.28, 0.22, 0.17,
   0.12, each low-passed at **4000 Hz**. A stone room — longer than morning
   forest, shorter than moody's cathedral. The longest tap stays well under one
   beat (833 ms) so the 16th notes never smear into each other.
3. Sum drums separately, then `out = reverb(out) + drums * 0.8`.
4. Normalize to peak 1 / 1.05, 3 s linear fade-out, int16 WAV.

Measured on the committed asset: **peak 0.952, overall RMS 0.205**.

## 4. MP3

Script 01 runs the transcode itself:

```bash
ffmpeg -y -i simple_bach_tune.wav -b:a 192k simple_bach_tune.mp3
```

## 5. Structure handoff

`structure.json` at the bundle root carries the usual fields plus `chords`,
`bar_sec` and `drums_in_sec`, all of which the visualizer reads:

```json
{
  "bpm": 72, "bars": 16, "beats_per_bar": 4,
  "duration_sec": 57.33,
  "section_starts_sec": [0.0, 13.33, 26.67, 40.0],
  "section_keys": ["C major", "C major", "C major", "C major"],
  "chords": ["C", "Dm", "G/B", "C", "Am", "Dm", "G", "C",
             "F", "Bdim", "Em", "Am", "Dm", "G7", "C", "C"],
  "bar_sec": 3.333,
  "drums_in_sec": 13.33,
  "modulation_sec": null,
  "title": "simple bach tune  |  C major, 72 BPM"
}
```

## 6. Video (`scripts/02_make_video.py`)

**Format**: 1280×720, 24 fps, H.264 (CRF 20, preset medium), AAC 192k,
`-shortest`. `N = ceil(57.33 * 24) = 1376` frames piped as `rawvideo`.

**Analysis** — identical to the other bundles: `hop = 1837`; per-frame RMS
normalized and smoothed at 0.9; 32 log bands 40–4000 Hz, `log1p(x*20)`, smoothed
0.85; low-band spectral flux against a 9-frame moving average × 1.6 + 2% of max,
`pulse` decaying at 0.78. One FFT pass feeds both. This run detected **56 onsets**
against 24 notated kicks (2 per bar over bars 5–16).

**Frame composition**

1. Background: vertical gradient `R = 16 + 26g, G = 19 + 18g, B = 32 + 6g` — cool
   slate above, candle warmth below. Plus `18 * bloom`, and `(6, 3, 0) * warmth`
   where `warmth` ramps over 3 s once the kit enters.
2. Orb: four concentric ellipses at (640, 316.8), radius
   `58 + 62*rms + 34*pulse + 20*bloom`, scaled 2.3, 1.6, 1.15, 1.0, base colour
   (225, 178, 100) warming to (243, 190, 100). Blurred 30, added.
3. Kick ring at `pulse > 0.05`; phrase ring at `bloom > 0.02`, firing at each of
   the three phrase boundaries.
4. Spectrum ring: 32 lines, cool ivory (196, 206, 232) against the gold orb.
5. **Sixteen bar ticks** at radius 268, one per bar of the piece. The current bar's
   tick is long and bright and shrinks across the bar; bars already played stay dim
   warm; bars to come are dim cool. A longer inner tick every four bars marks the
   phrases. This is the piece's strict sixteen-bar structure drawn directly.
6. Dust motes: 240 particles, `default_rng(7)`, slower than any other bundle
   (`y -= 0.20 z`) — hanging in candlelight rather than rising.
7. Waveform strip, 2-hop window, at y = 630.
8. Chord readout: the current chord name at 38 px and `bar n / 16` beneath it, in
   the **top-left corner**. It began under the orb and was moved — see §7.
9. Title caption bottom-left, fading over 3 s.

## 7. What's different, and what went wrong

| | moody | optimistic | morning forest | **simple bach tune** |
|---|---|---|---|---|
| Key | A minor | G → C | C→D→C→E→C | **C major throughout** |
| Tempo | 68 | 104 | 112 | **72** |
| Bars / length | 16 / 60.5 s | 24 / 59.4 s | 40 / 89.7 s | **16 / 57.3 s** |
| Note grid | 8ths | 8ths | 8ths | **16ths** |
| Main voice | additive pad | additive pad | Karplus-Strong | **additive harpsichord** |
| Bass | sine + 2nd | sine + 2nd | tanh-saturated | **6-harmonic bowed, held** |
| Kit | kick/snare/hat | + open hat | shaker/kick/rim/brush | **shaker/kick/rim only** |
| Reverb | 97–389 ms, lp 3500 | 61–211, lp 4500 | 53–181, lp 6000 | **89–331, lp 4000** |
| Extra scene element | — | — | god-rays | **16-bar tick ring, chord readout** |
| Accidentals used | — | F♯, G♯ | F♯, G♯ | **none — all white keys** |

Three things this build turned up.

**A real vibrato bug, in this bundle and in two older ones.** The §5.2 chroma check
flagged accidentals in a piece that has none. Per-bar analysis narrowed it to bars
5–16, and an A/B render — one without drums, one without the upper voice — showed
the drums were innocent and the upper voice was not. The cause:

```python
vib = 1 + 0.003 * np.sin(2 * np.pi * 4.5 * t) * np.minimum(t / 0.8, 1)
sig = np.sin(2 * np.pi * freq * h * vib * t)     # WRONG
```

Multiplying `t` by `vib` inside the sine modulates *phase*, not frequency. The
instantaneous frequency is `f * (vib + t * dvib/dt)`, so the deviation grows
linearly with time and a long note wanders further and further off pitch. Measured
with a Hilbert transform on the shipped `moody_drums_bundle` voice, which uses the
identical construction: **±7 cents intended, 14.4 semitones of swing on a 1 s note
and 23.6 semitones on a 3 s note.** The fix is to integrate:

```python
for h in range(1, 9):
    phase = 2 * np.pi * np.cumsum(freq * h * vib) / SR
    sig += np.sin(phase) / h ** 1.1
```

This bundle is fixed. `moody_drums_bundle` and `optimistic_drums_bundle` still
carry it; fixing them would change their audio and invalidate their recorded
checksums, so it is left as a decision rather than done silently.

**The chroma check has a blind spot for bright timbres.** Even after the fix, the
phrase-level §5.2 output still shows an F♯ in phrases 1 and 3. It is not a played
note: the fifth harmonic of any pitch is a major third two octaves up, so a
harmonically rich voice puts the major third of whatever it plays into the chroma —
D's fifth harmonic lands on F♯. Restricting the analysis band to roughly 70–1200 Hz,
where fundamentals dominate, removes it entirely and gives a clean result. Verified
per bar: **all 16 bars have their exact chord tones as the top three pitch classes.**

**Text over the orb is unreadable.** The chord readout started under the orb and
vanished into the glow whenever the orb was at full size. Moved to the top-left
corner, where the background is darkest.

## 8. Run order

```bash
cd scripts
python3 01_make_music.py      # -> ../assets/{mid,wav,mp3} and ../structure.json
python3 02_make_video.py      # -> ../assets/simple_bach_tune_visualizer.mp4
```

About 1.5 s for the audio and 1 minute for the video.

## 9. Verification results

Per [`../instructions.md`](../instructions.md) §5, on the committed assets:

- Duration 57.33 s, matching `structure.json`
- Peak 0.952, RMS 0.205 — both inside the target bands
- 56 detected onsets against 24 notated kicks (2.3×, within the expected range)
- Per-bar chroma, 70–1200 Hz, top three pitch classes against the chord:

```
bar  1 C     want C E G    top3 C G E      bar  9 F     want F A C    top3 F C A
bar  2 Dm    want D F A    top3 D A F      bar 10 Bdim  want B D F    top3 B D F
bar  3 G/B   want G B D    top3 B D G      bar 11 Em    want E G B    top3 B E G
bar  4 C     want C E G    top3 C G E      bar 12 Am    want A C E    top3 A C E
bar  5 Am    want A C E    top3 A E C      bar 13 Dm    want D F A    top3 D A F
bar  6 Dm    want D F A    top3 D A F      bar 14 G7    want G B D F  top3 B G D
bar  7 G     want G B D    top3 D G B      bar 15 C     want C E G    top3 C G E
bar  8 C     want C E G    top3 C G E      bar 16 C     want C E G    top3 C E G

mismatched bars: none
```

- Video 57.33 s, both streams present; frames extracted at 6 s, 14 s, 30 s and
  44 s and inspected. The bar tick advances correctly, the chord readout matches
  the table above, and the phrase ring fires at 13.3 s, 26.7 s and 40.0 s.

## 10. Prompt to regenerate the whole thing from an LLM

> Write two Python scripts. Script 1 composes a 16-bar piece in C major at 72 BPM
> using the figure from Bach's Prelude in C: one five-note ascending broken chord
> per bar (root, 3rd, 5th, octave, 10th), indexed as [0,1,2,3,4,2,3,4] and played
> twice per bar in 16th notes. Harmony: C Dm G/B C, then three descending-fifths
> chains — Am Dm G C, F B° Em Am, Dm G7 C C — all white keys, never leaving C
> major. Add a held continuo on each chord root an octave below the cell, and a
> sustained upper voice from bar 5 alternating between the fifth and root of each
> chord to make a stepwise descent that climbs home. Drums: shaker on 8ths from
> bar 3, soft kick on 1 and 3 and rim on 2 and 4 from bar 5, two rim hits closing
> every fourth bar. Synthesize the figure with a bright twelve-harmonic
> plucked-string voice with a noise quill, the continuo and upper voice additively,
> and apply a short bright multi-tap reverb to the melodic parts only. Any vibrato
> must integrate frequency to phase with cumsum. Write a 4-track MIDI with
> midiutil, transcode to MP3, and emit a JSON file with the chord name of every
> bar. Script 2 reads the WAV and that JSON and renders a 1280×720 24 fps
> visualizer in a candlelit palette — cool slate above, warm below, gold orb,
> ivory spectrum ring, slow dust motes — with a ring of sixteen ticks marking the
> bars and the current bar lit, and the current chord name in the top-left corner.

The exact parameter values in sections 1, 3 and 6 are what make the output match
rather than merely resemble.
