# Recreating "morning forest": MIDI, MP3, and MP4

This document is the full recipe to regenerate `morning_forest.mid`,
`morning_forest.mp3`, and `morning_forest_visualizer.mp4` from scratch. It follows
the pipeline in [`../instructions.md`](../instructions.md): symbolic composition,
numerical synthesis, frame-by-frame rendering. No AI audio or video generation.

**The brief it was built from:** *"happy and clear and full of hope… crisp and
clean just like walking into forest in the morning breathing clean air with this
refreshing sensation."* Key: C major on the C–G–Am axis. Harmonic arc: *"go up
and down then go up more and then back down."*

That arc is the piece. Five 8-bar sections stepping **C → D → C → E → C**, each
modulation prepared by the dominant of the key it's about to enter.

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
- Two seeded RNGs: `default_rng(3)` for drum noise and the Karplus-Strong
  excitation, `default_rng(7)` for video particles.
- Verify the **PCM sample data**, not the WAV container — scipy versions differ
  in which optional RIFF chunks they write:

```python
import hashlib
from scipy.io import wavfile
sr, a = wavfile.read("assets/morning_forest.wav")
print(hashlib.md5(a.tobytes()).hexdigest())   # 9f83c777739225035a957a7c5bc187ee
```

File MD5s from the original run, for reference only:

```
db0fa4ca42b36397f9dc9cfa886e2afd  morning_forest.mid
d1f34f6519d805b6569bfc99d1237ad6  morning_forest.wav
94c016bd7771a0c016a3ef863f28fe7d  morning_forest.mp3
cc61aa9b826b3b566f0acb7e6d83fc3b  morning_forest_visualizer.mp4
```

## 1. Musical specification

Everything below is hard-coded in `scripts/01_make_music.py`.

**Global**

- Key: C major, arching to D, back to C, up to E, and home to C
- Tempo: 112 BPM, 4/4 — a walking pace
- Form: an 8-bar cycle played five times = 40 bars = 85.71 s, plus a 4 s tail =
  **89.71 s** total
- Sample rate for synthesis: 44,100 Hz, mono, 16-bit PCM

**The arch**

| Section | Bars | Start | Transpose | Key | Role |
|---|---|---|---|---|---|
| 1 | 1–8 | 0.00 s | +0 | C major | home, entering |
| 2 | 9–16 | 17.14 s | +2 | D major | up |
| 3 | 17–24 | 34.29 s | +0 | C major | and down |
| 4 | 25–32 | 51.43 s | +4 | E major | up more — the peak |
| 5 | 33–40 | 68.57 s | +0 | C major | back down, resolving |

Sharp-ward rather than flat-ward: D and E both add sharps, which brightens each
step. Modulating to F or B♭ would have gone *up* in pitch while going *down* in
brightness, which is the opposite of the brief.

**Chord progression** — the base cycle, in C. Voicings are open, sit high
(MIDI 50–74) and contain no low thirds; that is what makes them read as "clear"
rather than "warm".

| Bar | Chord | Voicing (MIDI) | Notes | Function |
|---|---|---|---|---|
| 1 | Cmaj9 | 60 64 67 71 74 | C E G B D | I |
| 2 | G6/9 | 55 59 64 69 | G B E A | V |
| 3 | Am7 | 57 60 64 67 | A C E G | vi |
| 4 | Fmaj7(♯11) | 53 57 60 64 71 | F A C E B | IV |
| 5 | Cmaj9 | 60 64 67 71 74 | C E G B D | I |
| 6 | G6/9 | 55 59 64 69 | G B E A | V |
| 7 | Dm9 | 50 53 57 60 64 | D F A C E | ii |
| 8 | *pivot* | see below | | V7 of the next key |

The ♯11 on the F chord — a B, entirely diatomic to C — is the single brightest
sound in the piece. It's the sunlight-through-leaves chord.

**Pivots.** Bar 8 of each section is replaced by an absolute (untransposed)
dominant seventh leading into the next key, so the arch steps rather than jumps:

| Section | Bar 8 | Voicing | Bass | Resolves to |
|---|---|---|---|---|
| 1 | A7 | 57 61 64 67 | 45 | D major |
| 2 | G7 | 55 59 62 65 | 43 | C major |
| 3 | B7 | 59 63 66 69 | 47 | E major |
| 4 | G7 | 55 59 62 65 | 43 | C major |
| 5 | Cmaj9 | 60 64 67 71 74 | 36 | — lands home |

Chord notes are staggered 0.05 beats per voice in the MIDI, 0.04 s in the synth.
Velocities descend 46, 43, 40, 37, 34 — the sustained pad is a bed, not the
foreground.

**Arpeggio.** Over each chord, eight 8th notes running up and back down through
the voicing, an octave above it: `tones = [n + 12 for n in chord]`, index sequence
`[0,1,…,len-1,len-2,…,1]` truncated to 8. Note length 0.45 beats, velocities 58 on
downbeats and 44 off. This is the "crisp" — the sustained pad alone would have
been another moody-bundle wash.

> The +12 is not only register. The pad and the arp share MIDI track 0 / channel
> 0, and midiutil cannot serialize two overlapping notes of the same pitch on one
> channel. No voicing in this piece contains a note 12 semitones below another,
> so the octave offset guarantees no collision. See §7.

**Bass** (one per bar, base cycle): 36 43 45 41 36 43 38 43 — C G A F C G D G.
Transposed with the section; the E-major section reaches 49 (C♯3), which is high
for a bass and deliberately so at the peak. Root held 2.5 beats at velocity 70,
then the fifth (root + 7) for 1 beat at beat 3, velocity 55.

**Melody** as (start beat, MIDI note, length in beats). Note it covers only beats
0–28 of each 32-beat section:

```
(0, 76, 1.5) (1.5, 79, 0.5) (2, 84, 2)
(4, 83, 1) (5, 81, 1) (6, 79, 2)
(8, 76, 1) (9, 81, 1) (10, 79, 2)
(12, 77, 1.5) (13.5, 76, 0.5) (14, 74, 2)
(16, 72, 1) (17, 76, 1) (18, 79, 2)
(20, 79, 1) (21, 83, 1) (22, 86, 2)
(24, 84, 1.5) (25.5, 81, 0.5) (26, 79, 2)
```

**The last bar of every section is a rest.** That silence does three jobs: it is
the breath in "breathing clean air", it lets the pivot chord be heard as the hinge
it is, and it sidesteps the problem that a C-natural melody sitting over an A7 or
B7 pivot would clash. Transposed with the section; range 72–90.

**Drums** — a light kit, no snare in the ordinary sense.

- Shaker (note 70, 0.09 s): every 8th note, **from bar 1**, velocity 58 on
  downbeats and 40 off. It is the only thing playing at the very start.
- Kick (note 36): beats 0 and 2, **from bar 5**, velocity 88 — a footstep pulse,
  not a backbeat
- Rim (note 37): beats 1 and 3, from bar 5, velocity 72
- Brush snare (note 38): beats 1 and 3, **only in section 4**, velocity 70 — the
  kit fills out for the peak and empties again
- Fill: every 8th bar, two extra rim hits at beats 3.5 and 3.75, velocities 60 and 76

## 2. MIDI file

`midiutil.MIDIFile(4)`, four tracks, standard channel layout.

| Track | Channel | Program | Content |
|---|---|---|---|
| 0 Pad+Arp | 0 | 11 (Vibraphone) | sustained chords *and* the arpeggio |
| 1 Bass | 1 | 32 (Acoustic Bass) | bass line |
| 2 Lead | 2 | 9 (Glockenspiel) | melody |
| 3 Drums | 9 | n/a | shaker, kick, rim, brush |

Tempo event 112 BPM at tick 0.

## 3. Audio synthesis (WAV)

**Helpers** — `f_of(n) = 440 * 2 ** ((n - 69) / 12)`; `env(n, a, d, s, r)` linear
ADSR with segments clamped to `n`; `lowpass(x, cutoff)` 2nd-order Butterworth.

**`pluck(freq, dur)`** — Karplus-Strong, the arpeggio voice. A length-`SR/freq`
buffer of seeded white noise, averaged pairwise with a 0.996 decay factor,
normalized, low-passed at 5000 Hz, and enveloped `(0.001, 0.05, 0.8, dur/2)`.
Cached per (pitch, duration): the loop is pure Python and the arpeggio repeats
the same pitches hundreds of times. Gain 0.075 on downbeats, 0.055 off.

**`sweep_pad(freq, dur)`** — the bed. Two copies detuned ±0.3 cents, each a
7-harmonic additive saw with amplitude `1/h**1.4`; the output crossfades linearly
from a 500 Hz low-pass to a 3200 Hz one across the note, so the filter opens as
the chord sustains. ADSR (0.7, 0.5, 0.65, 1.0). Gain **0.025** — felt, not heard.

**`bell_lead(freq, dur)`** — the melody. A 2-operator FM strike (modulator at 3×
carrier, index 4 decaying at `exp(-5t)`, whole thing decaying at `exp(-1.8t)`)
summed at 0.7 with a plain sine core at 0.5 enveloped (0.02, 0.25, 0.5, 0.35).
The FM gives a crisp glassy onset; the sine core lets 2-beat notes still sing.
Gain 0.30.

**`bass_voice(freq, dur)`** — `tanh(sin(2πft) * 1.3)` plus 0.18 × second harmonic,
ADSR (0.02, 0.25, 0.6, 0.35). The soft saturation rounds the bottom without
adding mud. Gains 0.32 root, 0.20 fifth.

**Drums** (RNG seeded with 3)

- `kick_soft` (0.4 s): sine sweeping `120 * exp(-20t) + 44` Hz, amplitude
  `exp(-9t)`, no noise click. Gain 0.55.
- `rim` (0.06 s): 400 Hz sine at `exp(-90t)` plus noise at `exp(-300t)` × 0.4.
  Gain 0.35 (0.22 and 0.32 for fills).
- `shaker` (0.07 s): noise at `exp(-80t)`, high-passed 9000 Hz. Gain 0.10 / 0.055.
- `snare_brush` (0.45 s): noise at `exp(-7t)`, band-passed 900–4500 Hz, × 0.9.
  Gain 0.22, section 4 only.

**Mix and reverb**

1. Sum pad, arpeggio, bass and lead into `out`.
2. Reverb `out` only: four feedback-free taps at **53, 79, 113, 181 ms** with gains
   0.22, 0.18, 0.14, 0.10, each low-passed at **6000 Hz**, summed onto the dry
   signal. An open clearing, not a cathedral — and the longest tap is well under
   one beat (536 ms), so the arpeggio stays articulate. The 6000 Hz cutoff is the
   brightest of the three bundles, which is most of the "clean air".
3. Sum drums separately, then `out = reverb(out) + drums * 0.8` (drums stay dry).
4. Normalize to peak 1 / 1.05, apply a 3 s linear fade-out, write int16 WAV.

Measured on the committed asset: **peak 0.952, overall RMS 0.145**.

## 4. MP3

Script 01 runs the transcode itself:

```bash
ffmpeg -y -i morning_forest.wav -b:a 192k morning_forest.mp3
```

## 5. Structure handoff

Script 01 writes `structure.json` at the bundle root:

```json
{
  "bpm": 112,
  "bars": 40,
  "beats_per_bar": 4,
  "duration_sec": 89.71,
  "section_starts_sec": [0.0, 17.14, 34.29, 51.43, 68.57],
  "section_transpose": [0, 2, 0, 4, 0],
  "section_keys": ["C major", "D major", "C major", "E major", "C major"],
  "modulation_sec": null,
  "peak_sec": 51.43,
  "title": "morning forest  |  C major, arch to E and back, 112 BPM"
}
```

`modulation_sec` is `null` because there isn't one modulation, there are four.
`section_transpose` is what the visualizer actually reads — it turns the arch
into a brightness envelope.

## 6. Video (`scripts/02_make_video.py`)

**Format**: 1280×720, 24 fps, H.264 (`libx264`, `yuv420p`, CRF 20, preset medium),
AAC 192k, `-shortest`. `N = ceil(89.71 * 24) = 2154` frames, piped as `rawvideo`
into ffmpeg's stdin.

**Audio analysis** — identical to the other bundles: `hop = 1837`; per-frame RMS
normalized and smoothed at 0.9; 32 log-spaced bands 40–4000 Hz, `log1p(x*20)`,
smoothed at 0.85; low-band (40–120 Hz) spectral flux against a 9-frame moving
average × 1.6 + 2% of max, with `pulse` decaying at 0.78. One FFT pass feeds both.
This run detected **164 onsets** against 72 notated kicks — the rim, brush and
shaker leak into the low band.

**Arch envelopes**

- `height[i]`: a step function of `section_transpose / 4`, box-smoothed over 1.5 s.
  Runs 0 → 0.5 → 0 → 1 → 0 and drives every colour in the scene.
- `bloom[i]`: `exp(-(t - start) * 1.3)` from each of the four section boundaries,
  combined with `maximum`.

**Frame composition, for frame i at time t = i / 24**

1. Background: vertical gradient interpolated by `height` between
   top (58, 72, 54) → bottom (10, 18, 13) and top (108, 112, 74) → bottom
   (18, 30, 20). **Light above, understory below** — the reverse of the other two
   bundles, which brighten downward.
2. God-rays: six diagonal polygons from above, Gaussian-blurred radius 45,
   multiplied by `clip(1.25 - y/H, 0, 1)` so they fade toward the floor. Computed
   **once** before the loop and added per frame scaled by
   `0.55 + 0.45 * rms + 0.5 * bloom`; the geometry never changes, so the blur is
   paid for once rather than 2154 times.
3. `+ 22 * bloom` on all channels — a flash at each section change.
4. Sun orb: four concentric ellipses at (640, 316.8), radius
   `r = 62 + 66*rms + 40*pulse + 22*bloom`, scaled 2.3, 1.6, 1.15, 1.0. Base
   colour interpolates (190, 170, 90) → (245, 235, 165) by `height`. Blurred 30,
   added.
5. Kick ring: if `pulse > 0.05`, outline radius `r + 40 + 250*(1 - pulse)`, width 3,
   colour (235, 245, 205), alpha `180 * pulse`.
6. Section ring: if `bloom > 0.02`, outline radius `r + 60 + 880*(1 - bloom)`,
   width 5, colour (255, 255, 235), alpha `210 * bloom`. Fires four times.
7. Spectrum ring: 32 lines from `r + 28` to `r + 50 + 105*spec[b]`, angle
   `-π/2 + 2πb/32 + 0.06t`, width 4, green
   `(120 + 40*height, 225 + 20*height, 130 + 30*height)`, alpha
   `95 + 135*spec[b] + 40*bloom`.
8. Pollen: 300 points, `default_rng(7)`, depth `z` in [0.3, 1].
   `x += 0.22 z sin(phase + 0.25t)`, `y -= (0.22 + 0.14*height) z`, wrapped. Radius
   `1.1 + 2.3z`, colour (255, 248, 205), alpha `35 + 145*twinkle*z + 45*bloom`
   with `twinkle = 0.5 + 0.5 sin(1.4t + phase)`. Slower than the other bundles —
   motes hanging in a sunbeam, not sparks rising.
9. Waveform strip: 2-hop window, x from 80 to 1200, centred y = 630, amplitude
   45 px, every 8th sample, colour (205, 235, 175, 125).
10. Caption at (80, 660) from `structure.json`, fading in and out over 3 s.

## 7. What's different from the other bundles

| | moody | optimistic | **morning forest** |
|---|---|---|---|
| Key | A minor | G → C | **C → D → C → E → C** |
| Tempo | 68 | 104 | **112** |
| Bars / length | 16 / 60.5 s | 24 / 59.4 s | **40 / 89.7 s** |
| Foreground texture | sustained pad | sustained pad | **8th-note arpeggio** |
| Lead voice | sine + 3rd harmonic | sine + 3rd harmonic | **FM bell + sine core** |
| Pad | static low-pass | static low-pass | **filter opens across the note** |
| Bass | sine + 2nd harmonic | sine + 2nd harmonic | **tanh-saturated** |
| Kit | kick/snare/hat | kick/snare/hat + open hat | **kick/rim/shaker/brush** |
| Reverb | 97–389 ms, lp 3500 | 61–211 ms, lp 4500 | **53–181 ms, lp 6000** |
| Gradient | brightens downward | brightens downward | **brightens upward** |
| Extra scene element | — | — | **precomputed god-rays** |
| Structural events | 0 | 1 | **4** |

Two things learned building this one:

**midiutil cannot serialize overlapping same-pitch notes on one channel.** The
first version put the arpeggio on the pad's own pitches and `writeFile` died with
`IndexError: pop from empty list` deep inside `deInterleaveNotes`. Moving the arp
up an octave fixed it and improved the register besides. Any future bundle that
puts two simultaneous parts on one MIDI channel needs to guarantee they never
share a pitch.

**A melody that transposes with its section needs its cadence bar checked against
the un-transposed pivot.** The melody's original final phrase resolved to C, which
is fine over G7 and actively wrong over A7 and B7. Making the last bar a rest was
the better fix — it solved the clash and gave the piece its breath at the same time.

## 8. Run order

```bash
cd scripts
python3 01_make_music.py      # -> ../assets/{mid,wav,mp3} and ../structure.json
python3 02_make_video.py      # -> ../assets/morning_forest_visualizer.mp4
```

About 7 s for the audio (the Karplus-Strong loop dominates) and 2 min for the
video, on a laptop core.

## 9. Verification results

Per [`../instructions.md`](../instructions.md) §5, on the committed assets:

- Duration 89.71 s, matching `structure.json`
- Peak 0.952, RMS 0.145 — both inside the target bands
- Chroma per section, tonic ranked and top five pitch classes:

```
S1 C major   C rank#2 | G:0.174 C:0.155 E:0.132 F:0.119 D:0.108
S2 D major   D rank#1 | D:0.173 A:0.138 F#:0.129 G:0.128 E:0.123
S3 C major   C rank#2 | G:0.167 C:0.157 E:0.136 F:0.130 D:0.105
S4 E major   E rank#1 | E:0.166 B:0.149 G#:0.144 A:0.112 F#:0.100
S5 C major   C rank#2 | G:0.173 C:0.152 E:0.132 F:0.123 D:0.113
```

Every section's top five is fully diatonic to its own key; the F♯ appears only in
the D section, the G♯ and B only in the E section. The C sections rank G first
because G6/9 occurs three times per cycle — the tonic ranking second is expected
and within the §5.2 criterion.

- Video 89.71 s, both streams present; frames extracted at 8 s, 34.5 s, 52 s,
  55 s and 80 s and inspected. The arch is visible: cool dim green at 8 s,
  section ring mid-expansion at 34.5 s, near-white sun at the E-major peak,
  returned to cool green at 80 s.

## 10. Prompt to regenerate the whole thing from an LLM

> Write two Python scripts. Script 1 composes a 40-bar piece at 112 BPM in C
> major: an 8-bar cycle (Cmaj9 G6/9 Am7 Fmaj7♯11 Cmaj9 G6/9 Dm9, with bar 8 a
> pivot dominant) played five times and transposed 0, +2, 0, +4, 0 semitones so
> the harmony arches C–D–C–E–C, where bar 8 of each section is replaced by the
> absolute dominant seventh of the next key. Voice the chords open and high with
> no low thirds. Over each chord run an eight-step 8th-note arpeggio an octave
> above the voicing, synthesized with Karplus-Strong. Add a saturated sine bass on
> roots and fifths, a rising melody on an FM-bell voice that rests for the last bar
> of every section, and a light kit — shaker from bar 1, soft kick on 1 and 3 plus
> rim on 2 and 4 from bar 5, brush snare only in the peak section. Write a 4-track
> MIDI with midiutil, synthesize to a 44.1 kHz WAV in numpy with a short bright
> multi-tap reverb on the melodic parts only, transcode to MP3, and emit a JSON
> file recording each section's start time and transpose. Script 2 reads the WAV
> and that JSON and renders a 1280×720 24 fps visualizer with a forest palette —
> light above and dark understory below, precomputed god-rays scaled by loudness,
> a gold sun orb sized by RMS and kick onsets, a green spectrum ring, slow rising
> pollen — where the whole palette brightens with the section transpose and an
> expanding ring fires at each key change.

The exact parameter values in sections 1, 3 and 6 are what make the output match
rather than merely resemble.
