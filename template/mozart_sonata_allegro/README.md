# Recreating "mozart sonata allegro": MIDI, MP3, and MP4

This document is the full recipe to regenerate `mozart_sonata_allegro.mid`,
`mozart_sonata_allegro.mp3`, and `mozart_sonata_allegro_visualizer.mp4` from
scratch. It follows the pipeline in [`../instructions.md`](../instructions.md).
No AI audio or video generation.

**The brief:** *"music that sounds like Mozart — basically start from Bach style
but add a little variation, one of those conventional Mozart piano sonatas."*
From someone with no formal music training, immediately after
`church_passacaglia`.

**This is the repo's first stereo bundle.**

## 0. From Bach to Mozart, concretely

The brief's own framing — Bach plus variation — is the right one, and the
difference is four specific things, all of which are implemented here:

| | Baroque (`simple_bach_tune`, `church_passacaglia`) | Classical (this) |
|---|---|---|
| **Texture** | every voice equally busy, continuously | one singing line over simple accompaniment |
| **Phrasing** | one line spun onward indefinitely | balanced 4-bar units, with actual rests |
| **Accompaniment** | counterpoint, or a walking ground | the **Alberti bass** — low, high, middle, high |
| **Dynamics** | none possible; a harpsichord cannot play louder | every bar carries a gain, and the contrast is structural |

That last row is not a stylistic note. A harpsichord physically cannot play
louder or softer — plucking is plucking. That limitation is *why the piano
replaced it*, and it is why `DYN` exists in this script and in no earlier one.

## 1. Environment and reproducibility

Python 3.10.12 · numpy 2.2.6 · scipy 1.15.3 · Pillow 12.2.0 · midiutil 1.2.1 ·
ffmpeg 7.0.2

```bash
pip install numpy scipy pillow midiutil imageio-ffmpeg
```

`default_rng(3)` seeds the hammer thump, `default_rng(7)` the video particles.
Verify the **PCM sample data**, not the WAV container:

```python
import hashlib
from scipy.io import wavfile
sr, a = wavfile.read("assets/mozart_sonata_allegro.wav")   # shape (n, 2)
print(hashlib.md5(a.tobytes()).hexdigest())   # 09cc548fb6d00533c643da0d5288bf3b
```

File MD5s from the original run, for reference only:

```
5a2343b8ea7667a45203172f9764cf1d  mozart_sonata_allegro.mid
9eaf2e749fd6c8ad070e5da03db13b80  mozart_sonata_allegro.wav
9e1929d82ceab4200e97c3bd0c337f09  mozart_sonata_allegro.mp3
bd7620f9737cdc4d57b0aee82b6599d0  mozart_sonata_allegro_visualizer.mp4
```

## 2. Musical specification

- Key: **C minor**, with the harmonic-minor leading tone (B♮) in every dominant
- Tempo: 138 BPM, 4/4 — an Allegro
- Form: 48 bars = 83.5 s, plus a 4 s tail = **87.48 s**
- **Stereo**, 44.1 kHz, 16-bit

Pitch classes across the whole piece: **C D E♭ F G A♭ B♭** plus **B♮**. The seven
of C natural minor plus the leading tone — which is also, exactly, the note set of
E♭ major, because E♭ is C minor's relative major. That is what makes the modulation
work without a single accidental changing.

### Sonata form

The reason this form was chosen: it is the only one in the repo that *argues*.

| Bars | Section | Key |
|---|---|---|
| 1–8 | First subject | C minor |
| 9–12 | Transition | modulating |
| 13–20 | Second subject | **E♭ major** |
| 21–32 | Development | wandering |
| 33–40 | Recapitulation, first subject | C minor |
| 41–46 | **Second subject again** | **C minor** |
| 47–48 | Coda | C minor |

The whole point is that **the second subject is heard twice in different keys** —
bright in E♭ at bar 13, dark in C minor at bar 41. Same contour, same rhythm,
opposite colour. Everything else in the form exists to make that reconciliation
land. In a minor-key sonata the second subject goes to the *relative major*, not
the dominant; that is why E♭ and not G.

### Harmony

```
Cm  G7  Cm  G7  Cm  G7  Fm  G7        first subject
Cm  Ab  Bb7 Eb                         transition, arriving in E flat
Eb  Bb7 Eb  Ab  Fm  Bb7 Eb  Eb         second subject
Cm  Fm  Bb7 Eb  Ab  Ddim G7  Cm  Ab  Fm  G7  G7    development
Cm  G7  Cm  G7  Cm  G7  Fm  G7        recapitulation
Cm  G7  Cm  Fm  Ddim G7                second subject, now at home
Cm  Cm                                 coda
```

The development's first seven bars are a **descending-fifths sequence** —
Cm–Fm–B♭7–E♭–A♭–D°–G7 — with the opening arpeggio transposed onto each chord in
turn. Bars 29–32 fragment it down to two notes, then one, over a dominant pedal:
the standard way a Classical development builds pressure before the return.

**G7 is voiced B–D–F**, first inversion, putting the leading tone in the bass.
That B♮ is essential — C minor's own seventh is B♭, and without raising it there
is no pull back to the tonic.

### The Alberti bass

`[0, 2, 1, 2]` — low, high, middle, high — through a three-note voicing, twice per
bar, eight eighth notes. Left hand voicings sit in MIDI 44–60:

| Cm | G7 | Fm | Ab | Bb7 | Eb | Ddim |
|---|---|---|---|---|---|---|
| C3 E♭3 G3 | B2 D3 F3 | F3 A♭3 C4 | A♭2 C3 E♭3 | B♭2 D3 F3 | E♭3 G3 B♭3 | D3 F3 A♭3 |

### Dynamics

A per-bar multiplier applied to every voice, and exported in `structure.json` so
the visualizer can use it too:

| Section | Dynamic |
|---|---|
| First subject | forte, easing back into the bar-4 rest |
| Transition | crescendo 0.78 → 1.05 |
| Second subject | **piano, 0.66** — the classic contrast |
| Development | a twelve-bar build, 0.72 → 1.12 |
| Recapitulation | forte again |
| Second subject at home | 0.70 → 1.00, growing this time |
| Coda | 1.10 |

## 3. MIDI file

`midiutil.MIDIFile(4)`, all four tracks on acoustic grand (program 0), channels
0–3. There is no percussion, so channel 9 is unused.

| Track | Content |
|---|---|
| 0 | left hand — the Alberti figure |
| 2 | right hand — the melody |
| 1, 3 | reserved for hand extensions; unused in this piece |

## 4. Audio synthesis

**`fortepiano(freq, dur, bright)`** is the only voice. Three details matter.

**Inharmonicity.** A piano string is stiff, not an ideal string, so its overtones
are stretched sharp:

```
f_n  =  n · f0 · sqrt(1 + B · n²)          B = 0.0004
```

Without that stretch an additive stack sounds like an organ. With it, it sounds
struck. Note how this differs from `music_box_waltz`, which uses **fixed**
inharmonic ratios (1.00, 2.76, 5.40, 8.93): a struck *bar* has genuinely
non-harmonic modes, while a struck *string* has harmonics that drift
progressively sharper. Different physics, different formula, different sound.

**Partial-dependent decay.** Higher partials die faster
(`exp(-t · base · (1 + 0.22h))`), which is why a piano note gets darker as it
rings rather than just quieter.

**Pitch-dependent decay.** `base_decay = 1.6 + 5.5 · clip((f − 130)/900)`. Low
strings ring on; the top of the keyboard is nearly percussive. This is a real
property of the instrument and the thing most synthesized pianos miss.

Plus a low-passed noise thump at `exp(-130t)` — the wooden part of the hammer.

Fourteen partials, amplitude `1/h^(1.45 − 0.25·bright)`, so the melody
(`bright=1.0`) is more brilliant than the accompaniment (`bright=0.7`) — as it
would be under a real player's hands.

### Stereo

The first stereo bundle. Pan is derived from pitch:

```python
pan = clip((midi - 46) / 44, 0.10, 0.90)      # 0 = left, 1 = right
L, R = cos(pan·π/2), sin(pan·π/2)             # equal power
```

Low notes left, high notes right — how a piano actually reaches a listener. Both
channels go through the reverb independently.

Measured on the committed asset: **L RMS 0.140, R RMS 0.106, inter-channel
correlation 0.589.** A correlation near 1.0 would mean duplicated mono; 0.59 is a
genuinely stereo image.

### Mix and reverb

Four taps at **41, 67, 103, 163 ms**, gains 0.22, 0.17, 0.13, 0.09, low-passed at
5600 Hz, applied per channel. A salon, not a church — the shortest and brightest
reverb in the repo, because Classical music was written for rooms with furniture
in them. At 138 BPM a beat is 435 ms, so the longest tap stays well inside one.

Measured: **peak 0.952, RMS 0.110.**

## 5. Video

1280×720, 24 fps, 2100 frames. Analysis sums the stereo pair to mono — an FFT of
two interleaved channels is not meaningful — but the waveform strip draws **both**
channels so the panning is visible on screen.

**The tonal journey** is the new scene element: a plot of how far the harmony has
travelled from the home key, across the width of the frame. `section_distance` in
`structure.json` gives home = 0 and fully away = 1, smoothed over 1.6 s. The
travelled path is bright, the road ahead is faint, and section boundaries are
ticked. Sonata form is a journey out and back, so the visualizer draws exactly
that: the line climbs for the second subject, stays high through the development,
and drops home at the recapitulation and never leaves again.

The orb is sized by `rms`, `pulse`, *and the score's own dynamics* — so the
twelve-bar crescendo through the development is visible, not merely audible.

## 6. What this bundle taught the framework

**The `has_drums` rule from `church_passacaglia` was too narrow.**

That bundle established: no drums means the onset detector fires on noise, so take
`pulse` from the score. This piece is *also* drumless — and the detector fails
again, but for the **opposite reason**:

| | `church_passacaglia` | `mozart_sonata_allegro` |
|---|---|---|
| Transients | none — organ pipes never stop | one every 217 ms — the Alberti bass |
| Detector behaviour | fires on noise-floor drift | **saturates** |
| Onsets | 585 / 2256 frames | 244 / 2100 frames |
| Ring lit | 98% of frames | 88% of frames |

Starving and saturating look identical on screen. So the real question was never
"are there drums" — it is **"does the audio contain discrete, *separated*
transients?"** Three cases:

- **None** (sustained organ, pads, strings) → the detector finds noise.
- **Continuous** (any eighth- or sixteenth-note ostinato) → the detector saturates.
- **Discrete and separated** (a drum kit) → the detector works. This is the only
  case the framework originally assumed.

`structure.json` now carries **`pulse_source: "onsets" | "downbeat"`**, which
states the answer explicitly instead of inferring it from `has_drums`.

**Stereo is now available.** `instructions.md` §2.3 said mono; it now permits
either, with the rules that video analysis sums to mono and `channels` goes in
`structure.json`. Every existing mono bundle stays valid.

## 7. What's different from the other bundles

| | Seven others | **mozart sonata allegro** |
|---|---|---|
| Channels | mono | **stereo** |
| Dynamics | fixed gain per part | **per-bar, in the score and exported** |
| Form | loop, arch, ground, or through-composed | **sonata form — a theme reconciled in two keys** |
| Inharmonicity | none, or fixed ratios | **progressive string stretch** |
| Decay | uniform per voice | **depends on both partial number and pitch** |
| `pulse` from | onsets, or the downbeat | **the downbeat, for saturation not starvation** |
| Scene element | rays, rings, score, orbit | **the tonal journey plot** |

## 8. Run order

```bash
cd scripts
python3 01_make_music.py      # -> ../assets/{mid,wav,mp3} and ../structure.json
python3 02_make_video.py      # -> ../assets/mozart_sonata_allegro_visualizer.mp4
```

About 3 s for the audio and 94 s for the video.

## 9. Verification results

- All 48 bars sum to exactly 4 beats, and **every strong-beat melody note is a
  chord tone** — checked before synthesis
- Duration 87.48 s, peak 0.952, RMS 0.110 — all inside the target bands
- **Stereo confirmed**: 2 channels, L 0.140 / R 0.106, correlation 0.589
- 46 of 48 bars have at least two of their top three pitch classes as chord tones
- All seven sections diatonic to C minor / E♭ major:

```
First subject                    C:0.183 D:0.155 G:0.140 D#:0.110 B:0.101
Transition                       A#:0.168 C:0.144 G#:0.133 D:0.123 F:0.110
Second subject, in E flat        C:0.153 G#:0.149 A#:0.137 F:0.119 G:0.102
Development                      D:0.143 G#:0.136 C:0.127 B:0.116 F:0.105
Recapitulation                   C:0.183 D:0.155 G:0.140 D#:0.110 B:0.101
Second subject, now in C minor   C:0.190 G:0.139 G#:0.136 F:0.123 D#:0.095
Coda                             C:0.300 D#:0.182 G:0.166 D:0.063 B:0.056
```

The exposition's second subject leans on B♭/A♭/E♭ — E♭ major's own notes — while
the same music at bar 41 leans on C. That difference is the form working, measured.
The coda is 30% C, 18% E♭, 17% G: a C minor triad, landed on.

- Video 87.48 s, both streams present and the audio stream reads **stereo**.
  Frames inspected at 6 s, 26 s, 45 s and 78 s: the journey line climbs at the
  second subject, holds through the development, and returns home at the
  recapitulation.

## 10. Prompt to regenerate the whole thing from an LLM

> Write two Python scripts. Script 1 composes a 48-bar Classical sonata-form
> allegro in C minor, 4/4 at 138 BPM, for solo piano. Harmony: Cm G7 Cm G7 Cm G7
> Fm G7 for the first subject; Cm Ab Bb7 Eb to modulate; Eb Bb7 Eb Ab Fm Bb7 Eb Eb
> for a lyrical second subject in E flat major; a development of Cm Fm Bb7 Eb Ab
> Ddim G7 Cm Ab Fm G7 G7 with the opening arpeggio transposed onto each chord and
> fragmenting to two notes then one over a dominant pedal; then the first subject
> again unchanged, then the second subject rewritten in C minor, then a two-bar
> coda. Voice G7 as B-D-F so the leading tone is in the bass. Accompany throughout
> with an Alberti bass — low, high, middle, high — twice per bar in eighth notes.
> Give every bar a dynamic multiplier: forte for the first subject, crescendo
> through the transition, piano for the second subject, a twelve-bar build through
> the development. Synthesize with a fortepiano voice using progressive string
> inharmonicity f_n = n·f0·sqrt(1 + 0.0004·n²), decay that is faster for higher
> partials and for higher pitches, and a low-passed hammer thump. Output
> **stereo**, panning by pitch with equal-power law. Short bright four-tap reverb
> per channel. Write a 4-track MIDI, transcode to MP3, and emit JSON including the
> per-bar dynamics and each section's distance from the home key. Script 2 reads
> the WAV and that JSON, sums to mono for analysis but draws both channels in the
> waveform, takes its pulse from the downbeat because a continuous Alberti bass
> saturates the onset detector, and draws the harmony's distance from home as a
> journey plot across the frame.

The exact parameter values in sections 2, 4 and 5 are what make the output match
rather than merely resemble.
