# Recreating "music box waltz": MIDI, MP3, and MP4

This document is the full recipe to regenerate `music_box_waltz.mid`,
`music_box_waltz.mp3`, and `music_box_waltz_visualizer.mp4` from scratch. It
follows the pipeline in [`../instructions.md`](../instructions.md): symbolic
composition, numerical synthesis, frame-by-frame rendering. No AI audio or video
generation.

**The brief it was built from** was an 8-bar melody in 3/4, supplied note by note
in `NOTE:BEATS` form, with the instruction to make it a waltz and add drums:

```
E4:1.5 F4:0.5 E4:1  |  G4:2 G4:1  |  D4:1.5 E4:0.5 D4:1  |  F4:2 F4:1
C4:2 D4:1           |  E4:2 F4:1  |  E4:2 G4:0.5 F4:0.5  |  E4:2 D4:1
```

Every bar sums to exactly 3. The tune is reproduced here unaltered; the key,
harmony, form, orchestration and drums were chosen to fit it.

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

Reproducibility: the MIDI is deterministic; `default_rng(3)` seeds the strike
noise and percussion, `default_rng(7)` the video particles. Verify the **PCM
sample data**, not the WAV container:

```python
import hashlib
from scipy.io import wavfile
sr, a = wavfile.read("assets/music_box_waltz.wav")
print(hashlib.md5(a.tobytes()).hexdigest())   # 3582eac1473e5d5e538ca86581283ce6
```

File MD5s from the original run, for reference only:

```
0f48337e3d0effc7fedd13151cc3310d  music_box_waltz.mid
0d47df5f62352e569da20507f9e99f32  music_box_waltz.wav
cec617fbaa6023ccf25b5a0ef64a0e9d  music_box_waltz.mp3
63dbb8d0b754bfb7b962895d46b84773  music_box_waltz_visualizer.mp4
```

## 1. Musical specification

**Global**

- Key: **D Dorian**. See below — this was a choice, not a reading.
- Tempo: 132 BPM, **3/4**. The first bundle in the repo that is not in 4/4.
- Form: 40 bars = 54.55 s, plus a 4 s tail = **58.55 s** total
- Sample rate for synthesis: 44,100 Hz, mono, 16-bit PCM

### Why D Dorian

The melody uses only **C D E F G**. There is no B anywhere, and no B♭ — so the
sixth degree is simply absent, and *the melody cannot tell you whether it is
major, natural minor or Dorian.* The harmony decides.

Two facts pushed the choice:

- **The tune ends on D4.** Harmonised in C major that final D is a hanging
  second; in D Dorian it is the tonic, and the phrase lands.
- Dorian's signature is the **raised sixth** — a B natural — which arrives in the
  G major chord of bar 2. That one chord is what separates this from plain D
  minor, and it is why the piece sounds wistful rather than sad.

Measured on the finished audio: B natural registers at 0.062 of the total chroma
and B♭ at 0.039. The B♭ reading is an artifact of the music box's deliberately
inharmonic partials, not a played note.

### The melody, as supplied

| Bar | Notes | Beats |
|---|---|---|
| 1 | E4 F4 E4 | 1.5 + 0.5 + 1 |
| 2 | G4 G4 | 2 + 1 |
| 3 | D4 E4 D4 | 1.5 + 0.5 + 1 |
| 4 | F4 F4 | 2 + 1 |
| 5 | C4 D4 | 2 + 1 |
| 6 | E4 F4 | 2 + 1 |
| 7 | E4 G4 F4 | 2 + 0.5 + 0.5 |
| 8 | E4 D4 | 2 + 1 |

Bars 1–2 and 3–4 are the same shape a step apart — a real sequence — so the
harmony sequences with it.

### Harmony

| Bar | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Chord | Dm | **G** | Am | F | C | Dm | C | Dm |

`Dm → G` is the Dorian move, and it is the only place the B natural appears.
`C → Dm` closing the phrase is the ♭VII–i modal cadence. Bar 1 puts the melody's
E over Dm as a ninth and bar 8 resolves that same E down to D — a 9–8 suspension
opening and closing the tune.

Accompaniment voicings sit in MIDI 48–60, under the melody without crowding it:

| Chord | Voicing | Bass |
|---|---|---|
| Dm | D3 F3 A3 | D2 |
| G | D3 G3 B3 | G2 |
| Am | E3 A3 C4 | A2 |
| F | C3 F3 A3 | F2 |
| C | E3 G3 C4 | C2 |

**The waltz figure** is the classic oom-pah-pah: bass alone on beat 1 (0.9 beats),
the three-note chord on beats 2 and 3 (0.8 beats each), voices staggered 0.02
beats apart.

### Form

| Bars | Section | |
|---|---|---|
| 1–4 | Intro | music box picks out Dm and G, one note per beat; no drums |
| 5–12 | Theme | the tune as written |
| 13–20 | Theme with drums | the brushed kit enters |
| 21–28 | Variation | the tune an octave up, with an accordion counter-line |
| 29–36 | Theme returns | back at written pitch |
| 37–40 | Coda | the last two bars again, then D held for two bars |

The coda's chords are C – Dm – G – Dm, so the held D is first the fifth of G and
then the tonic.

### Drums

A light waltz kit, entering at bar 13.

- **Shaker** on all three beats from bar 1, accented on beat 1
- **Felt kick** on beat 1 from bar 13
- **Brush** on beats 2 and 3 from bar 13 — the pah-pah, doubled by the drums
- **Triangle** on the downbeat of each of the six sections

## 2. MIDI file

`midiutil.MIDIFile(4)`, four tracks, standard channel layout.

| Track | Channel | Program | Content |
|---|---|---|---|
| 0 Accordion | 0 | 21 (Accordion) | the pah-pah chords |
| 1 Bass | 1 | 32 (Acoustic Bass) | the oom, plus the counter-line |
| 2 Music box | 2 | 10 (Music Box) | the melody |
| 3 Drums | 9 | n/a | shaker 70, kick 36, brush 38, triangle 81 |

Tempo event 132 BPM at tick 0.

## 3. Audio synthesis (WAV)

Helpers are the canonical ones from `instructions.md` §2.7.

**`music_box(freq, dur)`** — a struck metal bar is *inharmonic*: its modes sit
near ratios **1.00, 2.76, 5.40, 8.93**, not at whole-number harmonics. Amplitudes
1.00, 0.42, 0.20, 0.10, and each mode decays faster than the last
(`exp(-t * (2.6 + ratio * 1.1))`), which is what makes the attack shimmer and the
tail settle to a pure tone. Plus a `exp(-320t)` strike click. Cached by pitch.
Gain 0.34. This ratio set is what separates a music box from the FM bell in
`morning_forest_bundle` — that one is harmonic, this one is not.

**`accordion(freq, dur)`** — two copies detuned ±0.6 cents, eight harmonics at
`1 / h ** 1.15`, low-passed 3000 Hz, with a shallow 6 percent 5.5 Hz tremolo.
Envelope (0.05, 0.12, 0.8, 0.18). Gain 0.075.

> The tremolo is applied to **amplitude**, so it sidesteps the phase-modulation
> trap in `instructions.md` §7 entirely.

**`waltz_bass(freq, dur)`** — sine plus 0.35 second and 0.12 third harmonic,
low-passed 1100 Hz, envelope (0.01, 0.15, 0.55, 0.25). Gain 0.30.

**Percussion** (RNG seeded with 3)

- `kick_felt` (0.35 s): sine sweeping `100 exp(-24t) + 45` Hz under `exp(-11t)`,
  no click — a felt mallet, not a beater. Gain 0.50.
- `brush` (0.22 s): noise band-passed 1200–6000 Hz under `exp(-18t)`. Gain 0.22.
- `shaker` (0.06 s): noise high-passed 9000 Hz under `exp(-95t)`. Gains 0.075 / 0.045.
- `triangle` (1.4 s): the same inharmonic-bar model as the music box, pitched at
  2100 Hz and left to ring. Gain 0.10.

**Mix and reverb**

1. Sum music box, accordion and bass into `out`.
2. Reverb `out` only: taps at **67, 101, 151, 239 ms**, gains 0.26, 0.21, 0.16,
   0.12, low-passed at **5200 Hz**. A small bright room — a music box on a shelf.
   At 132 BPM a beat is 455 ms, so the longest tap stays inside one beat and the
   oom-pah-pah keeps its edges.
3. Sum drums separately, then `out = reverb(out) + drums * 0.8`.
4. Normalize to peak 1 / 1.05, 3 s linear fade-out, int16 WAV.

Measured: **peak 0.952, overall RMS 0.138**.

## 4. MP3

Script 01 runs the transcode itself, at 192k.

## 5. Structure handoff

`structure.json` carries the usual fields plus `beat_sec`, `section_labels`,
`chords`, `drums_in_sec` and `variation_sec`. `beat_sec` is new and matters here:
the visualizer needs the beat, not just the bar, to animate the meter.

## 6. Video (`scripts/02_make_video.py`)

**Format**: 1280×720, 24 fps, CRF 20, AAC 192k. `N = ceil(58.55 * 24) = 1406`
frames. Analysis is identical to the other bundles, one FFT pass feeding both the
spectrum and the onset detector.

**Frame composition**

1. Background: warm antique gradient `R = 26 + 26g, G = 18 + 18g, B = 20 + 14g`,
   lightening downward like aged paper, plus bloom, warmth and lift terms.
2. Orb at (640, 310), radius `54 + 58*rms + 30*pulse + 22*bloom`, base colour
   (224, 168, 126) warming when the drums enter and tinting cooler through the
   octave-up variation. Blurred 30, added.
3. Onset ring and a wide section ring at each of the six boundaries.
4. Spectrum ring: 32 lines in dusty rose (214, 156, 168).
5. **The waltz orbit.** Three markers on a ring of radius 250, at angle
   `-π/2 + 2π(b/3 − in_bar)`. The whole ring turns once per bar, so each marker
   passes the top exactly as its beat begins; the marker whose beat is current is
   enlarged, shrinking across the beat, and beat 1 is brighter than 2 and 3. This
   is the repo's first 3/4 piece and the orbit is what makes the meter visible —
   you can count 1-2-3 off the screen.
6. Dust motes: 230 particles, the slowest drift of any bundle.
7. Waveform strip, then section name, chord, bar and **beat** readout top-left.

## 7. What's different from the other bundles

| | moody | optimistic | morning forest | simple bach | avenger | **music box waltz** |
|---|---|---|---|---|---|---|
| Meter | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | **3/4** |
| Mode | minor | major | major | major | minor | **Dorian** |
| Tempo | 68 | 104 | 112 | 72 | 88 | **132** |
| Length | 60.5 s | 59.4 s | 89.7 s | 57.3 s | 91.3 s | **58.6 s** |
| Lead voice | sine + 3rd | sine + 3rd | FM bell | harpsichord | brass | **inharmonic struck bar** |
| Accompaniment | pad | pad | arpeggio | 16th figure | block chords | **oom-pah-pah** |
| Reverb | 97–389, lp 3500 | 61–211, lp 4500 | 53–181, lp 6000 | 89–331, lp 4000 | 113–421, lp 3200 | **67–239, lp 5200** |
| Extra scene element | — | — | god-rays | bar tick ring | two-hand score | **three-beat orbit** |

This bundle takes the two axes `instructions.md` §8 listed as untouched: it is the
first in a meter other than 4/4, and the first in a genuine church mode.

The interesting decision was harmonic. A melody with a missing scale degree is not
under-specified — it is an *opportunity*, because the harmony gets to choose what
the tune means. The same eight bars over C major would be a bright, slightly
unresolved folk song; over D Dorian they become wistful and land on home. Nothing
in the melody had to change.

## 8. Run order

```bash
cd scripts
python3 01_make_music.py      # -> ../assets/{mid,wav,mp3} and ../structure.json
python3 02_make_video.py      # -> ../assets/music_box_waltz_visualizer.mp4
```

About 2 s for the audio and 71 s for the video.

## 9. Verification results

Per [`../instructions.md`](../instructions.md) §5, on the committed assets:

- All eight supplied bars sum to exactly 3 beats; checked before synthesis
- Duration 58.55 s, matching `structure.json`
- Peak 0.952, RMS 0.138 — both inside the target bands
- 67 onsets detected against 76 genuine low-band attacks (40 bass, 28 kick,
  8 counter-line) — **0.9×**, i.e. slightly *under*, which is right for a piece
  whose bass notes are soft and the kick is felt-mallet
- **The chord root is among the top three low-band pitch classes in 40/40 bars**
- Per-section chroma, 70–1200 Hz, all six fully diatonic to D Dorian:

```
Intro                    G:0.185 D:0.177 A:0.131 B:0.109 F:0.097
Theme                    F:0.150 D:0.131 C:0.127 E:0.119 A:0.113
Theme with drums         F:0.143 D:0.124 C:0.124 E:0.115 A:0.112
Variation, an octave up  F:0.161 C:0.153 D:0.134 E:0.128 A:0.103
Theme returns            F:0.142 D:0.124 C:0.124 E:0.114 A:0.112
Coda                     D:0.201 G:0.155 A:0.119 B:0.092 F:0.085
```

The coda leading on D is the piece landing on its tonic. B natural appears in the
Intro and Coda top-fives, which is the Dorian sixth doing its job.

- Video 58.55 s, both streams present; frames extracted at 8.00 s, 8.15 s, 8.30 s
  (three points inside one bar), 30 s and 52 s and inspected. The orbit advances
  correctly and the beat readout matches the marker position.

## 10. Prompt to regenerate the whole thing from an LLM

> Write two Python scripts. Script 1 composes a 40-bar waltz in 3/4 at 132 BPM in
> D Dorian. The 8-bar melody is E4:1.5 F4:0.5 E4:1 | G4:2 G4:1 | D4:1.5 E4:0.5
> D4:1 | F4:2 F4:1 | C4:2 D4:1 | E4:2 F4:1 | E4:2 G4:0.5 F4:0.5 | E4:2 D4:1,
> harmonised Dm G Am F C Dm C Dm — the G major supplies the Dorian raised sixth
> and C–Dm is the modal cadence. Accompany it oom-pah-pah: bass alone on beat 1,
> a three-note chord in MIDI 48–60 on beats 2 and 3. Form: a 4-bar intro, the
> theme, the theme with drums, the theme an octave up with a counter-line, the
> theme again, and a 4-bar coda ending on a held D. Synthesize the melody with an
> inharmonic struck-bar voice using mode ratios 1.00, 2.76, 5.40 and 8.93 with
> faster decay on the higher modes, the chords with a detuned reedy accordion with
> amplitude tremolo, and the bass with a soft low sine stack. Drums are a light
> waltz kit: shaker on all three beats, felt kick on 1 and brush on 2 and 3 from
> the third section, triangle on each section downbeat. Short bright multi-tap
> reverb on the pitched parts only. Write a 4-track MIDI with midiutil, transcode
> to MP3, and emit a JSON file with bar and beat durations. Script 2 reads the WAV
> and that JSON and renders a 1280×720 24 fps visualizer in warm antique tones
> with three beat markers orbiting the centre, one full turn per bar, the current
> beat enlarged.

The exact parameter values in sections 1, 3 and 6 are what make the output match
rather than merely resemble.
