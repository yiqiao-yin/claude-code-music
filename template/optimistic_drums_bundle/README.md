# Recreating "optimistic drums": MIDI, MP3, and MP4

This document is the full recipe to regenerate `optimistic_drums.mid`,
`optimistic_drums.mp3`, and `optimistic_drums_visualizer.mp4` from scratch. It
follows the same pipeline as [`../moody_drums_bundle`](../moody_drums_bundle/README.md):
symbolic composition, numerical synthesis, frame-by-frame rendering. No AI audio
or video generation anywhere.

The piece starts in **G major** and lifts to **C major** two thirds of the way
through. Everything downstream — the drums, the palette, the visualizer — is
built around that one moment.

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
pip install numpy scipy pillow midiutil
# ffmpeg from your package manager, or:
pip install imageio-ffmpeg      # scripts fall back to this static binary
```

Reproducibility notes:

- The MIDI file is fully deterministic. Same script, same bytes.
- The WAV uses two seeded RNGs (`default_rng(3)` for drum noise, `default_rng(7)`
  for video particles). The **PCM sample data** is reproducible; the WAV *file*
  MD5 is not, because scipy versions differ in which optional RIFF chunks they
  write. Verify the samples, not the container:

```python
import hashlib
from scipy.io import wavfile
sr, a = wavfile.read("assets/optimistic_drums.wav")
print(hashlib.md5(a.tobytes()).hexdigest())   # 0bc5f0b09f43ccf57b50f9326a05a374
```

- MP3 and MP4 bytes will differ across ffmpeg builds. The audible and visible
  content will not.

File MD5s from the original run, for reference only:

```
07ae67caf0b14b5f3c7d42f11cdd35c9  optimistic_drums.mid
07029d39168224c119cc17fad65e517d  optimistic_drums.wav
7c3af1fcc499d17489d0691d1ee0bff1  optimistic_drums.mp3
d07df0a474dfe53981b14314369b5069  optimistic_drums_visualizer.mp4
```

## 1. Musical specification

Everything below is hard-coded in `scripts/01_make_music.py`.

**Global**

- Key: G major for bars 1–16, C major for bars 17–24 (the whole cycle transposed
  up a perfect fourth, `+5` semitones)
- Tempo: 104 BPM, 4/4
- Form: an 8-bar cycle played three times = 24 bars = 96 beats = 55.38 s, plus a
  4 s tail = 59.38 s total
- Sample rate for synthesis: 44,100 Hz, mono, 16-bit PCM
- Modulation lands at bar 17 = **36.92 s**

**Chord progression** (one bar each, MIDI note numbers)

Sections 1 and 2 — G major:

| Bar | Chord | Voicing (MIDI) | Function |
|---|---|---|---|
| 1 | Gmaj9 | 55 59 62 66 69 | I |
| 2 | Em7 | 52 55 59 62 | vi |
| 3 | Cmaj7 | 48 52 55 59 | IV |
| 4 | D6/9 | 50 54 57 59 64 | V |
| 5 | Gmaj9 | 55 59 62 66 69 | I |
| 6 | Bm7 | 50 54 57 59 | iii |
| 7 | Am7 | 57 60 64 67 | ii |
| 8 | D7 | 50 54 57 60 | V7 |

Section 3 — C major, every voicing `+5`: Cmaj9, Am7, Fmaj7, G6/9, Cmaj9, Em7,
Dm7, G7.

Chord notes are staggered by 0.08 beats per voice (strum feel) in the MIDI and by
0.06 s per voice in the synth. Velocities descend 62, 58, 54, 50, 46 from the
lowest voice up.

**Bass** (MIDI note numbers, one per bar)

- G sections: 43 40 36 38 43 47 45 38
- C section: 36 45 41 43 36 40 38 43 — deliberately re-voiced rather than
  transposed, so the lift does not drag the bass into a muddy register

Root held 2.5 beats at velocity 70, then the fifth (root + 7) for 1 beat starting
at beat 3 at velocity 55.

**Melody** as (start beat, MIDI note, length in beats), played once per 32-beat
section, transposed `+5` in section 3:

```
(0, 74, 1) (1, 76, 1) (2, 79, 2)
(4, 78, 1.5) (5.5, 76, 0.5) (6, 74, 2)
(8, 71, 1) (9, 74, 1) (10, 76, 2)
(12, 78, 1) (13, 79, 1) (14, 81, 2)
(16, 79, 1) (17, 78, 1) (18, 76, 2)
(20, 74, 1) (21, 76, 1) (22, 79, 2)
(24, 81, 1.5) (25.5, 79, 0.5) (26, 78, 2)
(28, 76, 1) (29, 74, 1) (30, 71, 2)
```

Note lengths are multiplied by 0.95 in the MIDI for slight detachment. Velocity 80.
The line is built from rising three-note cells, the opposite of the moody
template's descending sighs.

**Drums** (General MIDI channel 10, enters at bar 3, `DRUM_START_BAR = 2`, runs
through bar 24)

- Kick (note 36): beats 0, 1.5, 2.5 of each bar, velocity 100 — the extra hit on
  the "and" of 2 is what makes it drive rather than brood
- Snare (note 38): beats 1 and 3, velocity 85
- Closed hat (note 42): every eighth note, velocity 62 on downbeats, 40 on offbeats
- Fill: every 4th bar (`bar % 4 == 3`), two extra snare hits at beats 3.5 and 3.75,
  velocities 70 and 80
- Open hat (note 46): downbeat of bars 3, 9 and 17, velocity 90 — a crash
  substitute marking each section, including the modulation

## 2. MIDI file

Library: `midiutil.MIDIFile(4)`, four tracks. Identical layout to the moody bundle.

| Track | Channel | Program | Content |
|---|---|---|---|
| 0 Pad | 0 | 0 (Acoustic Grand) | chords |
| 1 Bass | 1 | 32 (Acoustic Bass) | bass line |
| 2 Lead | 2 | 73 (Flute) | melody |
| 3 Drums | 9 | n/a | drum hits |

Tempo event 104 BPM at tick 0. Written with `mid.writeFile(open(path, "wb"))`.

## 3. Audio synthesis (WAV)

All voices are built directly in numpy at 44.1 kHz.

**Helpers**

- `env(n, a, d, s, r)`: linear ADSR envelope over `n` samples. Segment lengths are
  clamped to `n` — see [§7](#7-what-changed-from-the-moody-template).
- `lowpass(x, cutoff)`: 2nd-order Butterworth via `scipy.signal.butter` + `lfilter`.
- `f_of(n) = 440 * 2 ** ((n - 69) / 12)`.

**Pad voice** (per chord note): three detuned copies at -0.4, 0, +0.4 cents, each a
5-harmonic additive "soft saw" with amplitude `1 / h ** 1.6`. ADSR (0.5, 0.4, 0.7,
0.8). Low-passed at **2200 Hz**. Gain 0.05. Duration one bar plus 1.0 s. Faster
attack and a higher cutoff than the moody pad (0.9 s / 1400 Hz) so the chords
speak on the beat instead of swelling in behind it.

**Bass voice**: sine plus 0.3 x second harmonic. ADSR (0.02, 0.3, 0.6, 0.4). Root
gain 0.35 for 2.6 beats; fifth gain 0.22 for 1.1 beats at beat 3.

**Lead voice**: sine plus 0.15 x third harmonic, with 5 Hz vibrato of depth 0.4
percent ramping in over 0.6 s. ADSR (0.06, 0.3, 0.75, 0.4). Gain 0.28. Duration
note length plus 0.4 s.

**Drums** (RNG seeded with 3)

- Kick (0.45 s): sine sweeping `150 * exp(-18 t) + 45` Hz (integrated to phase with
  cumsum), amplitude `exp(-7 t)`, plus a white-noise click scaled by
  `0.3 * exp(-400 t)`. Gain 0.9.
- Snare (0.3 s): white noise with `exp(-16 t)` envelope, band-passed 1500–7000 Hz,
  times 0.8, plus a 190 Hz sine with `exp(-28 t)` times 0.6. Gain 0.45. Fill hits
  use 0.2 s duration and gains 0.30 and 0.38.
- Closed hat (0.09 s): white noise with `exp(-60 t)`, high-passed at 7000 Hz. Gain
  0.16 on downbeats, 0.09 on offbeats.
- Open hat (0.45 s): white noise with `exp(-7 t)`, high-passed at 6000 Hz. Gain 0.13.

**Mix and reverb**

1. Sum pad, bass and lead into `out`.
2. Reverb `out` only: four feedback-free delay taps at **61, 89, 127, 211 ms** with
   gains 0.26, 0.20, 0.15, 0.11, each low-passed at 4500 Hz, summed onto the dry
   signal. Shorter and brighter than the moody bundle's 97/151/233/389 ms — a long
   tail at 104 BPM smears the backbeat.
3. Sum drums separately into `drums`, then `out = reverb(out) + drums * 0.8`
   (drums stay dry).
4. Normalize to peak 1 / 1.05, apply a 3 s linear fade-out, write int16 WAV with
   `scipy.io.wavfile.write`.

Measured on the committed asset: peak 0.952, overall RMS 0.178.

## 4. MP3

Script 01 now runs the transcode itself, so there is no manual step:

```bash
ffmpeg -y -i optimistic_drums.wav -b:a 192k optimistic_drums.mp3
```

## 5. Structure handoff

Script 01 also writes `structure.json` at the bundle root:

```json
{
  "bpm": 104,
  "bars": 24,
  "beats_per_bar": 4,
  "duration_sec": 59.38,
  "section_starts_sec": [0.0, 18.46, 36.92],
  "modulation_sec": 36.92,
  "title": "optimistic (with drums)  |  G major -> C major, 104 BPM"
}
```

The video script reads it. That is the only way the visualizer knows where the key
change is — it is a structural event, not something the onset detector could find.

## 6. Video (`scripts/02_make_video.py`)

**Format**: 1280x720, 24 fps, H.264 (`libx264`, `yuv420p`, CRF 20, preset medium),
AAC 192k audio, `-shortest`. Frame count `N = ceil(duration * 24) = 1426`. Frames
are generated as RGB numpy arrays and piped as `rawvideo` into ffmpeg's stdin; no
intermediate image files.

**Audio analysis, computed once before rendering**

- `hop = 44100 // 24 = 1837` samples per frame.
- `rms[i]`: RMS of samples `[i*hop, (i+1)*hop)`, normalized to max 1, then smoothed
  with `rms[i] = max(rms[i], 0.9 * rms[i-1])`.
- `spec[i, b]`: 2048-sample Hann-windowed FFT starting at `i*hop`, mean magnitude in
  32 log-spaced bands from 40 Hz to 4000 Hz (`np.geomspace`), then `log1p(x * 20)`,
  normalized, smoothed with decay 0.85.
- Kick onsets: `low[i]` = mean FFT magnitude in 40–120 Hz.
  `flux = max(low - roll(low, 1), 0)`. Threshold = 9-frame moving average of flux
  times 1.6, plus 2 percent of max flux. `onsets = flux > threshold`. `pulse[i]` =
  1.0 on an onset, else `0.78 * pulse[i-1]`. This run detected **160 onsets**
  (3 kicks per bar over 22 bars = 66 notated hits; the detector also fires on
  snares and the busier hat pattern).
- The spectrum and the onset detector share **one** FFT pass.

**Key-change envelopes**

- `lift[i] = clip((t - 36.92) / 1.5, 0, 1)` — permanent palette shift
- `bloom[i] = exp(-(t - 36.92) * 1.1)` for `t >= 36.92`, else 0 — one-off flash

**Frame composition, for frame i at time t = i / 24**

1. Background: vertical gradient interpolated by `lift` between
   `R = 16 + 30g, G = 12 + 20g, B = 24 + 14g` (G major) and
   `R = 26 + 44g, G = 22 + 34g, B = 20 + 18g` (C major), where `g = y / H`, plus
   `4 * sin(0.35 t)` breathing and `30 * bloom` on all channels.
2. Orb glow: four concentric filled ellipses at (640, 316.8) with radius
   `r = 70 + 70 * rms + 45 * pulse + 25 * bloom`, scaled by 2.2, 1.6, 1.15, 1.0.
   Base colour interpolates from amber (210, 130, 45) to gold (255, 195, 90) by
   `lift`. Drawn on a black layer, Gaussian-blurred radius 28, added to the
   background.
3. Kick ring: if `pulse > 0.05`, an outline ellipse of radius
   `r + 40 + 260 * (1 - pulse)`, width 3, colour (255, 235, 195), alpha `200 * pulse`.
4. Modulation ring: if `bloom > 0.02`, one large outline ellipse of radius
   `r + 60 + 900 * (1 - bloom)`, width 5, colour (255, 250, 235), alpha `220 * bloom`.
5. Spectrum ring: 32 teal lines from radius `r + 30` to `r + 55 + 110 * spec[b]`,
   angle `-pi/2 + 2 pi b / 32 + 0.08 t`, width 4, colour
   `(90 + 60*lift, 220 + 20*lift, 200 + 30*lift)`, alpha `90 + 140*spec[b] + 40*bloom`.
6. Particles: 260 points, seeded with 7, uniform initial positions, depth `z` in
   [0.3, 1]. Each frame `x += 0.25 z sin(phase + 0.3 t)`,
   `y -= (0.35 + 0.35 * lift) z`, wrapped. Radius `1.2 + 2.5 z`, alpha
   `40 + 150 * twinkle * z + 50 * bloom` with `twinkle = 0.5 + 0.5 sin(1.7 t + phase)`.
7. Waveform strip: raw samples for a 2-hop window as a polyline from x = 80 to
   x = 1200, centred at y = 630, amplitude 45 px, every 8th sample, colour
   (255, 205, 150, 130).
8. Caption at (80, 660), text taken from `structure.json`, alpha fading in over the
   first 3 s and out over the last 3 s.

## 7. What changed from the moody template

This bundle was built to test whether `moody_drums_bundle` is actually
reproducible. It is — with one caveat — and the differences below are the fixes
that came out of the exercise.

| Change | Why |
|---|---|
| Output paths resolve as `Path(__file__).parent.parent / "assets"` | The moody scripts hard-code `/mnt/user-data/outputs/`, so they fail on any other machine until you edit them. |
| ffmpeg located via `shutil.which`, falling back to `imageio-ffmpeg` | No system ffmpeg needed; `pip install imageio-ffmpeg` is enough. |
| MP3 transcode folded into script 01 | The moody recipe has a manual shell step between the two scripts that is easy to skip. |
| `structure.json` written by 01, read by 02 | Lets the visualizer react to musical structure (the key change) without duplicating BPM and bar constants in two files. |
| `env()` clamps its segment lengths | The moody `env()` assumes `attack + decay + release < duration`; for a short enough note the slices overlap and the envelope wraps. Nothing in the moody piece is short enough to trigger it, but the drum fills come close. |
| One FFT pass in script 02 instead of two | The moody video script computes the same 2048-point FFT twice per frame, once for the spectrum and once for the onset detector. |
| Verification uses a PCM-data checksum | See below. |

**The reproducibility caveat.** Re-running `moody_drums_bundle/scripts/01_make_music.py`
on Python 3.10 / numpy 2.2.6 / scipy 1.15.3 — a different stack from the one its
README documents — produced:

- `moody_drums.mid`: **byte-identical** to the committed asset ✅
- `moody_drums.wav`: **100% identical PCM samples**, max sample difference 0 ✅,
  but a different file MD5 ❌ — the committed file carries 5,766 bytes of extra
  RIFF chunk that this scipy version does not write.

So the synthesis is deterministic across versions, more so than its README claims;
the file-level MD5s just are not a valid way to check it. Checksum the sample
array instead.

## 8. Run order

```bash
cd scripts
python3 01_make_music.py      # -> ../assets/{mid,wav,mp3} and ../structure.json
python3 02_make_video.py      # -> ../assets/optimistic_drums_visualizer.mp4
```

Roughly 4 s for the audio and 75 s for the video on a laptop core.

## 9. Prompt to regenerate the whole thing from an LLM

> Write two Python scripts. Script 1 composes a 24-bar piece at 104 BPM: an 8-bar
> cycle (Gmaj9 Em7 Cmaj7 D6/9 Gmaj9 Bm7 Am7 D7) played twice in G major, then a
> third time transposed up a fourth to C major, with a pad, bass on chord roots and
> fifths, a rising sparse melody, and an upbeat drum pattern entering at bar 3
> (kick on 1, the and of 2, and 3; snare on 2 and 4; eighth-note hats; a two-hit
> snare fill every fourth bar; an open hat marking each 8-bar section). Write it as
> a 4-track MIDI with midiutil, synthesize it to a 44.1 kHz WAV in numpy using
> additive/subtractive voices, synthesized kick/snare/hat, and a short multi-tap
> delay reverb on the melodic parts only, transcode to MP3, and emit a JSON file
> recording the bar positions of each section. Script 2 reads the WAV and that
> JSON, computes per-frame RMS, a 32-band log spectrum, and a low-band
> spectral-flux onset detector, and renders a 1280x720 24 fps visualizer with a
> warm sunrise palette (glowing orb sized by loudness and onsets, teal spectrum
> ring, drifting particles, waveform strip) that shifts palette and fires an
> expanding ring at the moment of the key change, piping raw frames into ffmpeg
> with the WAV muxed as AAC.

The exact parameter values in sections 1, 3 and 6 are what make the output match
rather than merely resemble.
