# Recreating "moody drums": MIDI, MP3, and MP4

This document is the full recipe to regenerate `moody_drums.mid`, `moody_drums.mp3`, and `moody_drums_visualizer.mp4` from scratch. Nothing in the pipeline uses AI audio or video generation; everything is symbolic composition plus numerical synthesis plus frame-by-frame rendering.

## 0. Environment

| Component | Version used |
|---|---|
| Python | 3.12.3 |
| numpy | 2.4.4 |
| scipy | 1.17.1 |
| Pillow | 12.1.1 |
| midiutil | 1.2.1 |
| ffmpeg | 6.1.1 (with libx264 and aac) |

```bash
pip install numpy scipy pillow midiutil
# ffmpeg from your package manager (apt, brew, choco)
```

Reproducibility notes:

- The MIDI file is fully deterministic. Same script, same bytes.
- The WAV/MP3 use two seeded RNGs (`default_rng(3)` for drum noise, `default_rng(7)` for video particles). Output is bit-identical on the same numpy version; across numpy versions the RNG stream is stable but floating point ordering can differ in the last bits.
- MP3 and MP4 bytes will differ across ffmpeg builds. The audible and visible content will not.

Reference MD5s from the original run:

```
c1acedc3306d3ded2fe234558ca2d5e6  moody_drums.mid
4afb91f3aea51e02dd4100e6ae9e51ff  moody_drums.wav
1c402bc690342be15d7df1ba9a707363  moody_drums.mp3
602e3e18f66a08a9cbb43e417a563d33  moody_drums_visualizer.mp4
```

## 1. Musical specification

Everything below is hard-coded in `scripts/01_make_music.py`.

**Global**

- Key: A minor (natural minor for melody and chords, one borrowed G# in the E7 chord from A harmonic minor)
- Tempo: 68 BPM, 4/4
- Form: an 8-bar chord cycle played twice = 16 bars = 64 beats = 56.47 s, plus a 4 s tail = 60.47 s total
- Sample rate for synthesis: 44,100 Hz, mono, 16-bit PCM

**Chord progression** (one bar each, MIDI note numbers, repeated twice)

| Bar | Chord | Voicing (MIDI) | Function |
|---|---|---|---|
| 1 | Am9 | 57 60 64 67 71 | i |
| 2 | Fmaj7 | 53 57 60 64 | VI |
| 3 | Cmaj7 | 48 52 55 59 | III |
| 4 | Em7 | 52 55 59 62 | v |
| 5 | Am9 | 57 60 64 67 71 | i |
| 6 | Fmaj7 | 53 57 60 64 | VI |
| 7 | Dm7 | 50 53 57 60 | iv |
| 8 | E7 | 52 56 59 62 | V |

Chord notes are staggered by 0.08 beats per voice (strum feel) in the MIDI, and by 0.06 s per voice in the synth. Velocities descend 62, 58, 54, 50, 46 from lowest voice up.

**Bass** (MIDI note numbers, one per bar): 45 41 36 40 45 41 38 40. Root held 2.5 beats at velocity 70, then the fifth (root + 7) for 1 beat starting at beat 3 at velocity 55.

**Melody** as (start beat, MIDI note, length in beats), played once per 32-beat half:

```
(0, 76, 3) (3, 72, 1)
(4, 74, 2) (6, 72, 1.5) (7.5, 71, 0.5)
(8, 72, 2) (10, 67, 2)
(12, 71, 3) (15, 69, 1)
(16, 76, 2) (18, 79, 1) (19, 77, 1)
(20, 76, 2) (22, 72, 2)
(24, 74, 1.5) (25.5, 72, 1.5) (27, 69, 1)
(28, 68, 3) (31, 71, 1)
```

Note lengths are multiplied by 0.95 in the MIDI for a slight detachment. Velocity 80.

**Drums** (General MIDI channel 10, enters at bar 3, index `DRUM_START_BAR = 2`, runs through bar 16)

- Kick (note 36): beats 0 and 2.5 of each bar, velocity 100
- Snare (note 38): beats 1 and 3, velocity 85
- Closed hat (note 42): every eighth note, velocity 60 on downbeats and 38 on offbeats
- Fill: every 4th bar (bar index `% 4 == 3`), two extra snare hits at beats 3.5 and 3.75, velocities 70 and 80

## 2. MIDI file

Library: `midiutil.MIDIFile(4)`, four tracks.

| Track | Channel | Program | Content |
|---|---|---|---|
| 0 Pad | 0 | 0 (Acoustic Grand) | chords |
| 1 Bass | 1 | 32 (Acoustic Bass) | bass line |
| 2 Lead | 2 | 73 (Flute) | melody |
| 3 Drums | 9 | n/a | drum hits |

Tempo event 68 BPM at tick 0. Written with `mid.writeFile(open(path, "wb"))`.

## 3. Audio synthesis (WAV)

All voices are built directly in numpy at 44.1 kHz.

**Helpers**

- `env(n, a, d, s, r)`: linear ADSR envelope over `n` samples with attack, decay, sustain level, release in seconds.
- `lowpass(x, cutoff)`: 2nd-order Butterworth via `scipy.signal.butter` + `lfilter`.
- `f_of(n) = 440 * 2 ** ((n - 69) / 12)`.

**Pad voice** (per chord note): three detuned copies at -0.4, 0, +0.4 cents, each a 5-harmonic additive "soft saw" with amplitude `1 / h ** 1.6`. ADSR (0.9, 0.5, 0.7, 1.2). Low-passed at 1400 Hz. Gain 0.05. Duration one bar plus 1.0 s.

**Bass voice**: sine plus 0.3 x second harmonic. ADSR (0.02, 0.3, 0.6, 0.4). Root gain 0.35 for 2.6 beats; fifth gain 0.22 for 1.1 beats at beat 3.

**Lead voice**: sine plus 0.15 x third harmonic, with 5 Hz vibrato of depth 0.4 percent that ramps in over 0.6 s. ADSR (0.08, 0.3, 0.75, 0.5). Gain 0.28. Duration note length plus 0.4 s.

**Drums** (RNG seeded with 3)

- Kick (0.45 s): sine whose frequency sweeps `150 * exp(-18 t) + 45` Hz (integrated to phase with cumsum), amplitude `exp(-7 t)`, plus white noise click scaled by `0.3 * exp(-400 t)`. Gain 0.9.
- Snare (0.3 s): white noise with `exp(-16 t)` envelope, band-passed 1500 to 7000 Hz, times 0.8, plus a 190 Hz sine with `exp(-28 t)` times 0.6. Gain 0.45. Fill hits use 0.2 s duration and gains 0.30 and 0.38.
- Hat (0.09 s): white noise with `exp(-60 t)` envelope, high-passed at 7000 Hz. Gain 0.16 on downbeats, 0.09 on offbeats.

**Mix and reverb**

1. Sum pad, bass, and lead into `out`.
2. Reverb `out` only: four feedback-free delay taps at 97, 151, 233, 389 ms with gains 0.32, 0.26, 0.20, 0.15, each low-passed at 3500 Hz, summed onto the dry signal.
3. Sum drums separately into `drums`, then `out = reverb(out) + drums * 0.8` (drums stay dry).
4. Normalize to peak 1 / 1.05, apply a 3 s linear fade-out, write int16 WAV with `scipy.io.wavfile.write`.

## 4. MP3

```bash
ffmpeg -y -i moody_drums.wav -b:a 192k moody_drums.mp3
```

## 5. Video (`scripts/02_make_video.py`)

**Format**: 1280x720, 24 fps, H.264 (`libx264`, `yuv420p`, CRF 20, preset medium), AAC 192k audio, `-shortest`. Frame count `N = ceil(duration * 24) = 1452`. Frames are generated as RGB numpy arrays and piped as `rawvideo` into ffmpeg's stdin; no intermediate image files.

**Audio analysis, computed once before rendering**

- `hop = 44100 // 24 = 1837` samples per frame.
- `rms[i]`: RMS of samples `[i*hop, (i+1)*hop)`, normalized to max 1, then smoothed with `rms[i] = max(rms[i], 0.9 * rms[i-1])`.
- `spec[i, b]`: 2048-sample Hann-windowed FFT starting at `i*hop`, mean magnitude in 32 log-spaced bands from 40 Hz to 4000 Hz (`np.geomspace`), then `log1p(x * 20)`, normalized, smoothed with decay 0.85.
- Kick onsets: `low[i]` = mean FFT magnitude in 40 to 120 Hz. `flux = max(low - roll(low, 1), 0)`. Threshold = 9-frame moving average of flux times 1.6, plus 2 percent of max flux. `onsets = flux > threshold`. `pulse[i]` = 1.0 on an onset, else `0.78 * pulse[i-1]`. The original run detected 90 onsets.

**Frame composition, for frame i at time t = i / 24**

1. Background: static vertical gradient, R = 8 + 14g, G = 6 + 8g, B = 20 + 30g where g = y / H, plus `6 * sin(0.25 t)` on blue.
2. Orb glow: four concentric filled ellipses centered at (640, 316.8) with radius `r = 70 + 70 * rms + 45 * pulse` scaled by 2.2, 1.6, 1.15, 1.0 and colors scaled from (60, 40, 150), drawn on a black layer, Gaussian-blurred with radius 28, added to the background.
3. Kick ring: if `pulse > 0.05`, an outline ellipse of radius `r + 40 + 260 * (1 - pulse)`, width 3, color (230, 200, 255) with alpha `200 * pulse`.
4. Spectrum ring: 32 lines from radius `r + 30` to `r + 55 + 110 * spec[b]`, angle `-pi/2 + 2 pi b / 32 + 0.05 t`, width 4, color (170, 150, 255) with alpha `90 + 140 * spec[b]`.
5. Particles: 220 points, seeded with 7, initial uniform positions, depth `z` in [0.3, 1]. Each frame `x += 0.25 z sin(phase + 0.3 t)`, `y -= 0.35 z`, wrapped. Radius `1.2 + 2.5 z`, alpha `40 + 150 * twinkle * z` with `twinkle = 0.5 + 0.5 sin(1.7 t + phase)`.
6. Waveform strip: raw samples for a 2-hop window drawn as a polyline from x = 80 to x = 1200, centered at y = 630, amplitude 45 px, every 8th sample, color (150, 130, 220, 120).
7. Caption at (80, 660): `moody (with drums)  |  A minor, 68 BPM`, alpha fading in over the first 3 s and out over the last 3 s.

## 6. Run order

```bash
cd scripts
python3 01_make_music.py      # writes moody_drums.mid and moody_drums.wav
ffmpeg -y -i moody_drums.wav -b:a 192k moody_drums.mp3
python3 02_make_video.py      # reads moody_drums.wav, writes moody_drums_visualizer.mp4
```

The scripts write to `/mnt/user-data/outputs/` by default; change the paths at the top of each file for your own machine.

## 7. Prompt to regenerate the whole thing from an LLM

If you want to hand this to a model instead of running the scripts:

> Write two Python scripts. Script 1 composes a 16-bar piece in A minor at 68 BPM (progression Am9 Fmaj7 Cmaj7 Em7 Am9 Fmaj7 Dm7 E7, twice) with a pad, bass on chord roots and fifths, a sparse melody, and a half-time drum pattern entering at bar 3 (kick on 1 and the and of 2, snare on 2 and 4, eighth-note hats, a two-hit snare fill every fourth bar). Write it as a 4-track MIDI with midiutil, and also synthesize it to a 44.1 kHz WAV in numpy using additive/subtractive voices, synthesized kick/snare/hat, and a multi-tap delay reverb on the melodic parts only. Script 2 reads the WAV, computes per-frame RMS, a 32-band log spectrum, and a low-band spectral-flux onset detector, and renders a 1280x720 24 fps visualizer (glowing orb sized by loudness and onsets, spectrum ring, drifting particles, waveform strip) by piping raw frames into ffmpeg with the WAV muxed as AAC.

The exact parameter values in sections 1, 3, and 5 are what make the output match rather than merely resemble.
