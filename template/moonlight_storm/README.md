# Recreating "moonlight storm": MIDI, MP3, and MP4

Full recipe to regenerate the assets from scratch, following the pipeline in
[`../instructions.md`](../instructions.md). No AI audio or video generation.

**The brief:** *"sound like Beethoven's Moonlight sonata"* — then, from the
three questions: the **first movement into the third**, **swelling and receding**,
**dying away** at the end.

That combination is a shape Beethoven did not write. The storm of the finale
arrives and then **dissolves** instead of resolving — the first movement's ending
grafted onto the third movement's climax. So this is original music built from the
sonata's devices, not a transcription of it. The repo composes; it does not
transcribe.

## 0. The devices borrowed

| Device | What it does here |
|---|---|
| **Relentless broken-chord figuration** | the entire texture, never stopping, from bar 1 to bar 28 |
| **C♯ minor** | its actual key, with the raised leading tone in every dominant |
| **The sustain pedal** | Beethoven's marking is *senza sordino* — no dampers. Notes ring 3.4 s regardless of written length and pile into each other. That blur **is** the sound. |
| **A dotted melody on repeated notes** | sits above the ripple, mostly static, which is what makes it feel suspended rather than going anywhere |

## 1. Environment and reproducibility

Python 3.10.12 · numpy 2.2.6 · scipy 1.15.3 · Pillow 12.2.0 · midiutil 1.2.1 ·
ffmpeg 7.0.2

```bash
pip install numpy scipy pillow midiutil imageio-ffmpeg
```

Verify the **PCM sample data**, not the WAV container:

```python
import hashlib
from scipy.io import wavfile
sr, a = wavfile.read("assets/moonlight_storm.wav")   # shape (n, 2)
print(hashlib.md5(a.tobytes()).hexdigest())   # 4ac66b89a4eff6e15e6eebcc231f5fe0
```

File MD5s from the original run, for reference only:

```
e79b882c707bab0b92e76c8459f65da1  moonlight_storm.mid
3ff478bb03fb8b0c5b1fa651891fcd12  moonlight_storm.wav
f42fb6830270b375ed7bd4e74aa76217  moonlight_storm.mp3
5b83b0c5bf068dda6b309f956530cece  moonlight_storm_visualizer.mp4
```

## 2. Musical specification

- Key: **C♯ minor**. Pitch classes used: C♯ D♯ E F♯ G♯ A, plus **B♯ (= C natural)**
  as the leading tone in G♯7. Note there is no B natural anywhere — the piece is
  strictly harmonic minor, which is what gives the dominant its pull.
- Tempo: 72 BPM, 4/4 — **one tempo throughout**
- Form: 28 bars = 93.3 s, plus a 5 s tail = **98.33 s**
- **Stereo**, 44.1 kHz, 16-bit

### One tempo, three densities

The finale's *presto agitato* feeling is reached **without a tempo change**. Only
the note count accelerates:

| Texture | Notes per bar | Figure | Used in |
|---|---|---|---|
| `trip` | 12 | three notes rising, four times a bar | hushed, dying away |
| `sext` | 24 | four notes, reaching an octave above the root | gathering, receding |
| `storm` | 32 | eight notes rocketing through two octaves | the storm |

At 72 BPM that is 3.6, 7.2 and 9.6 notes per second. The ear reads the last as
frantic even though the pulse never moves — and keeping one tempo means the
`bar_sec` in `structure.json` stays valid for the whole piece, which every
downstream check depends on.

### Form

| Bars | Section | Texture | Dynamic |
|---|---|---|---|
| 1–6 | Hushed | triplets, no melody | 0.30 |
| 7–12 | The melody enters | triplets + dotted line | 0.42 → 0.50 |
| 13–16 | Gathering | sextuplets, melody in octaves | 0.58 → 0.92 |
| 17–22 | **The storm** | 32nds + hammered chords | **1.05 → 1.15** |
| 23–26 | Receding | sextuplets → triplets | 0.80 → 0.36 |
| 27–28 | Dying away | triplets | 0.26 → 0.18 |

A **6.4 : 1** written dynamic range. That is the piece.

### Harmony

```
C#m C#m A   A   F#m G#7        hushed
C#m A   F#m G#7 C#m C#m        the melody enters
A   F#m G#7 C#m                gathering
C#m G#7 C#m A   F#m G#7        the storm
C#m A   F#m G#7                receding
C#m C#m                        dying away
```

| Chord | Voicing | Notes |
|---|---|---|
| C♯m | 61 64 68 | C♯4 E4 G♯4 |
| A | 57 61 64 | A3 C♯4 E4 |
| F♯m | 54 57 61 | F♯3 A3 C♯4 |
| G♯7 | 56 60 63 | G♯3 **B♯3** D♯4 |

The melody leans on G♯ over the A chord — a major seventh, making it Amaj7. That
is deliberate and is the sound of this idiom, so the verification treats A as
Amaj7 rather than a bare triad.

Left hand is bare octaves, root − 24 and root − 12, range MIDI 30–49 (F♯1 to C♯3).

### The melody

Dotted quarter, eighth, half — mostly on repeated notes:

```
bar   7    8    9    10   11   12
      G#5  A5   F#5  G#5  C#6  G#5     ... then the same shape doubled in
                                        octaves for the gathering, and thinning
                                        to single held notes as it recedes
```

## 3. MIDI file

`midiutil.MIDIFile(4)`, all piano, channels 0–3: figuration, left-hand octaves,
melody, hammered chords.

> **The written note lengths and the synthesized ones deliberately disagree.**
> MIDI durations are short (0.7 of a step) because midiutil cannot serialize
> overlapping same-pitch notes on one channel and the figure repeats every pitch
> several times a bar. The pedal lives in the synthesis, where notes ring 3.4 s
> regardless. The MIDI is the score; the WAV is the performance.

## 4. Audio synthesis

**`piano(freq, dur, bright)`** — two refinements over
`mozart_sonata_allegro`'s fortepiano.

**Inharmonicity varies with pitch.** A piano's stiffness coefficient B is not
constant: bass strings are long and flexible, treble strings short and stiff, so
the treble stretches far more. Modelled as B rising from 0.00008 to 0.0013 across
the compass. Mozart's version used one fixed value; this is closer to a real
instrument, and it matters here because the deep pedalled bass is exposed.

**The pedal.** Decay is roughly half as fast, and nothing is damped at note-off.
Every note rings its full 3.4 s and piles into the next. With 648 notes over 98
seconds, the accumulation is the texture.

Fourteen partials, amplitude `1/h^(1.5 − 0.3·bright)`, higher partials decaying
faster, plus a low-passed hammer thump.

**Stereo** panned by pitch, equal power. Measured L/R correlation **0.663**.

**Reverb**: five taps at 89, 149, 241, 379, 557 ms, low-passed 3400 Hz. A pedalled
piano is already a blur; the room only extends it. At 72 BPM a beat is 833 ms, so
the longest tap sits inside one.

## 5. Video

Stereo summed to mono for analysis; both channels drawn in the waveform.
`pulse` from the downbeat — continuous figuration saturates the onset detector,
as established in `mozart_sonata_allegro`.

**The harmonic bloom** is the new scene element. Every note flies outward from the
centre at an angle set by its **pitch class**, fading over exactly the 3.4 s the
pedal lets it ring. Because angle encodes pitch class, each chord shows as a
distinct set of arms and a chord change visibly rotates the whole figure. Density
is the texture: sparse at the start, a dense burst at the storm, almost nothing at
the end. It is the pedal made visible.

Notes are drawn as **streaks, not dots** — the first render used dots and they
were invisible against the orb glow. A tail in the direction of travel reads as
motion and survives the background.

## 6. What this bundle taught the framework

### The RMS floor assumes constant loudness

`instructions.md` §5.1 says RMS below 0.08 is "thin". This piece measures
**0.0639** — and is correct. A 6.4:1 written dynamic range means peak
normalization is set by the storm, leaving everything else genuinely quiet. That
is the entire point of the piece.

| Section | RMS |
|---|---|
| Hushed | 0.029 |
| The melody enters | 0.048 |
| Gathering | 0.087 |
| **The storm** | **0.097** |
| Receding | 0.059 |
| Dying away | 0.020 |

**For a piece with real dynamics, check per-section RMS and require the loudest
section to be in band**, not the whole-piece average. Whole-piece RMS is only
meaningful when loudness is roughly constant, which was true of the first eight
bundles and is not true here.

### A new check: are the written dynamics actually audible?

If a bundle writes dynamics, verify they came out. Correlate the per-bar written
dynamic against the per-bar measured RMS:

```
correlation 0.923      quietest bar 28 (0.14)      loudest bar 18 (1.00)
```

The swell is real, not merely notated. This is now a §5 verification step for any
bundle carrying a `dynamics` array.

### A fourth way the chroma check lies

The "Dying away" section reports a **D**, a note in no chord and in no scale used.
The note log holds only C C♯ D♯ E F♯ G♯ A, and the reading survives excluding the
fade tail, so it is not noise floor.

It is the **11th partial of the pedalled low G♯**. The 11th harmonic sits a
tritone above its fundamental — G♯ + tritone = D — and lands at 574 Hz, 40 cents
flat of D5, which rounds to D. A deep bass note held for 3.4 seconds with
inharmonic stretch sprays energy across pitch classes nobody played.

So the blind-spot list is now four: bright timbres (5th and 7th partials), swept
and inharmonic percussion, too wide an analysis band, and now **deep sustained
bass with inharmonic partials**. The general lesson has not changed: a flagged
pitch is a hypothesis. Check the note log first.

## 7. What's different from the other bundles

| | Eight others | **moonlight storm** |
|---|---|---|
| Acceleration | tempo, or none | **note density at one tempo** |
| Note damping | notes end when written | **nothing is damped — 3.4 s pedal ring** |
| Dynamic range | roughly flat | **6.4 : 1, verified at r = 0.923** |
| Inharmonicity | none, fixed, or one coefficient | **varies with pitch across the compass** |
| MIDI vs audio | the same durations | **deliberately different — score vs performance** |
| Scene element | rays, rings, roll, orbit, journey | **the harmonic bloom** |

## 8. Run order

```bash
cd scripts
python3 01_make_music.py      # ~5 s
python3 02_make_video.py      # ~105 s
```

## 9. Verification results

- Every figuration, octave and melody note checked against its chord before
  synthesis: **no problems**
- Duration 98.33 s, peak 0.952
- **Stereo**: 2 channels, L/R correlation 0.663; the mp4's audio stream reads stereo
- Whole-piece RMS 0.064 — below the standard floor, correctly, see §6. Loudest
  section 0.097.
- **Written dynamics vs measured loudness: r = 0.923**
- Five of six sections fully diatonic; the sixth flags a D traced to an
  inharmonic partial, not a played note
- Frames inspected at 8 s, 30 s, 45 s, 63 s and 92 s

```
Hushed               A:0.213 F#:0.143 C#:0.140 E:0.128 G#:0.107   in key
The melody enters    G#:0.215 F#:0.179 C#:0.156 A:0.085 C:0.076   in key
Gathering            G#:0.308 F#:0.180 C#:0.134 A:0.067 C:0.060   in key
The storm            A:0.194 G#:0.152 C#:0.150 E:0.101 F#:0.094   in key
Receding             F#:0.219 A:0.178 G#:0.163 C#:0.118 E:0.084   in key
Dying away           C#:0.302 G#:0.202 E:0.128 D:0.062 B:0.058    D = partial, see §6
```

The "Dying away" section leading on C♯ at 0.302, with G♯ and E behind it, is the
tonic triad settling — the piece landing where it started, three times quieter.
