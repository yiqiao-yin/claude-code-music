# Recreating "church passacaglia": MIDI, MP3, and MP4

This document is the full recipe to regenerate `church_passacaglia.mid`,
`church_passacaglia.mp3`, and `church_passacaglia_visualizer.mp4` from scratch. It
follows the pipeline in [`../instructions.md`](../instructions.md): symbolic
composition, numerical synthesis, frame-by-frame rendering. No AI audio or video
generation.

**The brief it was built from** was deliberately vague — *"baroque style music
like Bach, typically played by harpsichord, in church or something"* — from
someone with no music training and no way to write notes down. It is the clearest
example in the repo of a §1.0 type-A brief, and of what the three questions are
for.

## 0. How a vague brief became this piece

The sentence already answered more than it looks. Genre, instrument family and
space were all given; only three things were genuinely open, and each was asked
with concrete options rather than as a theory question.

| Asked | Options offered | Chosen |
|---|---|---|
| Which baroque? | solemn and devotional / joyful and dancing / driving and dramatic | **solemn and devotional** |
| Harpsichord or organ? | organ / harpsichord / both | **church organ** |
| How does it move? | a repeating bass decorated / voices entering one at a time / slow then fast | **a repeating bass** |

Two things were decided without asking and stated as assumptions:

- **No percussion.** Baroque church music has none, and a kit would fight
  everything else. This is the repo's first drumless bundle.
- **Organ over harpsichord**, gently flagged: the brief said harpsichord *and*
  church, and those are different instruments. A harpsichord is a chamber
  instrument that cannot sustain; "in church" means an organ. The user chose.

## 0b. Environment and reproducibility

| Component | Version used |
|---|---|
| Python | 3.10.12 · numpy 2.2.6 · scipy 1.15.3 · Pillow 12.2.0 · midiutil 1.2.1 · ffmpeg 7.0.2 |

```bash
pip install numpy scipy pillow midiutil imageio-ffmpeg
```

One seeded RNG, `default_rng(3)`, for the pipe chiff; `default_rng(7)` for video
particles. Verify the **PCM sample data**, not the WAV container:

```python
import hashlib
from scipy.io import wavfile
sr, a = wavfile.read("assets/church_passacaglia.wav")
print(hashlib.md5(a.tobytes()).hexdigest())   # 0831ecd6b164c5dccd6f893744f20690
```

File MD5s from the original run, for reference only:

```
9f7faab27f9348a471e1d6713f046e8c  church_passacaglia.mid
fef6fa617a747c0ed6d90afef947a9da  church_passacaglia.wav
66db00e3b0343bad548c4cedd5cbb4ab  church_passacaglia.mp3
ee110517e87b733c183b60331641e9ca  church_passacaglia_visualizer.mp4
```

## 1. Musical specification

**Global**

- Key: **E Phrygian**
- Tempo: 80 BPM, 3/4
- Form: an 8-bar ground played five times = 40 bars = 90 s, plus a 4 s tail =
  **94 s** total
- Sample rate for synthesis: 44,100 Hz, mono, 16-bit PCM

### Why E Phrygian

A passacaglia is built on a *ground* — a short bass line repeated unchanged for
the whole piece. The classic ground, used everywhere from Purcell to Bach, is the
**descending tetrachord**: down four steps from the tonic. From E that is
**E – D – C – B**.

That descent is what Phrygian is made of. Phrygian is also literally one of the
church modes, which suits the brief. And the mode's fingerprint — the flat second,
**F natural**, falling to E — becomes the cadence that ends every one of the five
passes. Nothing else in the repo has used a mode other than major, minor or Dorian.

Measured on the finished audio: F natural registers at **0.162** of the total
chroma against F♯ at **0.013**. The mode is unambiguous.

### The ground

Eight bars, one chord each, never varied.

| Bar | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Chord | Em | Dm | C | G/B | C | G/B | **F** | Em |
| Bass | E2 | D2 | C2 | B1 | C2 | B1 | F2 | E2 |
| Voicing | E3 G3 B3 | D3 F3 A3 | C3 E3 G3 | D3 G3 B3 | C3 E3 G3 | D3 G3 B3 | C3 F3 A3 | B2 E3 G3 |

Root motion **E D C B C B F E**: the descending tetrachord, a rocking C–B, then
the Phrygian ♭II–i cadence.

**Bar 4 is G major in first inversion, not B diminished.** The triad on the fifth
degree of Phrygian is B–D–F, a diminished chord, and the fifth above B (F♯) is
outside the mode — so there is no usable chord there. Using G/B keeps the bass
note the ground wants while giving the ear a consonance. This is the standard
modal solution, not a dodge.

### The melody

Enters in pass 3. One line, mostly one note per bar, all chord tones:

```
bar   1    2       3    4       5    6    7    8
      B4   A4 F4   G4   G4 D4   E4   D4   F4   E4
```

It descends B–A–G–G–E–D, lifts to F and falls to E. That last move is the
Phrygian cadence sung rather than merely played.

### The figuration

Enters in pass 4. Six eighth notes per bar running through the chord an octave
above it, pattern `[0,1,2,0,1,2]`.

> The figuration shares MIDI channel 0 with the chords. That is safe here because
> no voicing contains a note twelve semitones below another, so `chord + 12` can
> never collide with the chord itself — the midiutil trap in `instructions.md` §7
> is avoided by construction, and it was checked before synthesis.

### The five passes

| Pass | Bars | What is added |
|---|---|---|
| 1 | 1–8 | pedal alone, stating the ground |
| 2 | 9–16 | sustained chords |
| 3 | 17–24 | the melody |
| 4 | 25–32 | running figuration |
| 5 | 33–40 | full organ registration, melody doubled at the octave |

Nothing is ever taken away and the harmony never changes. All the motion is
accumulation — which is what a passacaglia is.

## 2. MIDI file

`midiutil.MIDIFile(4)`, four tracks, all on church organ (program 19).

| Track | Channel | Content |
|---|---|---|
| 0 Organ manual | 0 | chords, and the figuration an octave above them |
| 1 Organ pedal | 1 | the ground bass |
| 2 Organ melody | 2 | the melody, doubled at the octave in pass 5 |
| 3 Organ figuration | 3 | the running eighths |

> Channel 3 rather than the usual channel 9. Channel 9 is percussion in General
> MIDI and this piece has none, so the fourth track carries a fourth organ part
> instead. `instructions.md` §2.3 allows the roles to be renamed; this is that.

## 3. Audio synthesis (WAV)

Helpers are the canonical ones from `instructions.md` §2.7.

**`organ_pipe(freq, dur, ranks, chiff)`** is the only voice in the piece. A rank
list is `(harmonic multiple, amplitude)` pairs, which is exactly how organ stops
work: 16′ sounds an octave below the written note, 8′ at pitch, 4′ an octave up,
2⅔′ a twelfth, 2′ two octaves, and a mixture adds the ranks above that.

Three things separate it from a plain additive stack, and all three are what make
it read as an organ rather than a synthesizer:

1. **No decay.** Wind keeps blowing, so the tone sustains flat until the key is
   released. Sustain sits at 0.97, attack is a slow 85 ms.
2. **Chiff** — the breathy transient as a pipe speaks before the tone settles.
   Band-passed noise between 1.5× and 5× the fundamental, gone in about 80 ms.
3. **Per-pipe detune.** No two pipes in a real rank are perfectly in tune. Each
   rank is offset by up to ±0.06 percent, derived deterministically from the rank
   number so the result stays reproducible.

Four registrations:

| Stop | Ranks | Used for |
|---|---|---|
| `REG_PEDAL` | 16′ 8′ 4′ (0.5, 1, 2) | the ground bass |
| `REG_PRINCIPAL` | 8′ 4′ 2⅔′ 2′ | chords in passes 2–4, and the figuration |
| `REG_FULL` | 8′ 4′ 2⅔′ 2′ + mixture (6, 8) | chords in pass 5 |
| `REG_FLUTE` | 8′ 4′, quiet | the melody |

**Mix and reverb**

1. Everything sums into one buffer. There is no separate percussion bus, because
   there is no percussion — so unusually, the *entire* mix goes through the room.
2. Reverb: **six** taps rather than the usual four, at 109, 173, 251, 367, 487 and
   631 ms with gains 0.30, 0.26, 0.22, 0.19, 0.15, 0.11, each low-passed at
   **2600 Hz**. Density is what makes a reverb sound like a room rather than an
   echo, and this is the darkest and longest of any bundle. At 80 BPM a beat is
   750 ms, so the longest tap still lands inside one beat — even a cathedral has
   to stay legible.
3. Normalize to peak 1 / 1.05, 3.5 s fade-out, int16 WAV.

Measured: **peak 0.952, overall RMS 0.182**.

## 4. MP3

Script 01 runs the transcode itself, at 192k.

## 5. Structure handoff

`structure.json` adds `ground_bars`, `passes` and — new, and load-bearing —
**`has_drums: false`**. See §7.

## 6. Video (`scripts/02_make_video.py`)

**Format**: 1280×720, 24 fps, CRF 20, AAC 192k. `N = ceil(94 * 24) = 2256` frames.

**Frame composition**

1. Background: cold stone gradient, a little warmer low down where the candles are,
   brightening through the piece as the organ fills.
2. Orb at (640, 317), radius `46 + 82*rms + 26*build + 18*pulse + 20*bloom`. Note
   how little weight `pulse` carries here compared with every other bundle — see §7.
3. Onset ring and a wide ring at each of the five pass boundaries.
4. Spectrum ring: stained glass, cold blue warming to amber as the registration
   grows.
5. **The ground, as accumulating rings.** One ring per pass, each with eight ticks
   for the eight bars of the ground. The current ring is brighter and its current
   bar brightest; rings already walked stay on screen, dim. By the last pass there
   are five concentric rings — the same circle, walked again with more on top,
   which is a passacaglia drawn rather than described.
6. Dust motes, the slowest of any bundle.
7. Waveform strip; pass name, chord, pass number and ground-bar position top-left.

## 7. What this bundle taught the framework

**The onset detector is useless on a drumless piece, and the framework assumed it
was not.**

`instructions.md` §2.4 requires a "kick ring sized by `pulse`" as a mandatory
scene element, and every previous bundle drove its orb largely from `pulse`. That
silently assumes a percussive transient exists to detect. Organ pipes speak slowly
and never stop, so there is nothing for spectral flux to catch — it fires on
noise-floor drift instead. Measured on the first render:

```
onsets detected  585  across 2256 frames  = 26% of frames
pulse > 0.05     on 98% of frames
notated pedal entries: 40                 -> 14.6x
```

The impact ring was lit essentially all the time: pure visual noise carrying no
information.

The fix is not a better threshold. **When there is no percussion, the musical
event is not in the audio's transients — it is in the score.** Here the event is
the chord change on every downbeat, which `structure.json` knows about and the
waveform does not advertise. So the visualizer branches on `has_drums`:

```python
if struct.get("has_drums", True):
    pulse = ...   # spectral flux, as before
else:
    pulse = np.exp(-(t_all % BAR_SEC) * 2.8)     # from the downbeat
```

The orb was also rebalanced — `82*rms` against `18*pulse`, roughly the inverse of
every other bundle — because loudness and the slow swell are what actually move in
this music.

Both are now in `instructions.md` §2.4 and §3.8, and `has_drums` is in the
schema.

## 8. What's different from the other bundles

| | Six others | **church passacaglia** |
|---|---|---|
| Percussion | every one has some | **none at all** |
| Mode | major, minor, Dorian | **Phrygian** |
| Voices | 2–4 distinct instruments | **one voice, four registrations** |
| Harmony | changes, or modulates | **eight bars, never varied, five times** |
| Reverb taps | 4 | **6**, and the darkest at 2600 Hz |
| Dry bus | drums bypass the reverb | **nothing is dry** |
| `pulse` source | onset detector | **the downbeat, from the score** |
| Extra scene element | god-rays, tick ring, score, orbit | **accumulating rings, one per pass** |

## 9. Run order

```bash
cd scripts
python3 01_make_music.py      # -> ../assets/{mid,wav,mp3} and ../structure.json
python3 02_make_video.py      # -> ../assets/church_passacaglia_visualizer.mp4
```

About 2 s for the audio and 100 s for the video.

## 10. Verification results

Per [`../instructions.md`](../instructions.md) §5, on the committed assets:

- Every chord tone, bass note and melody note checked against its chord before
  synthesis: no problems, and all seven pitch classes diatonic to E Phrygian
- Duration 94.00 s, matching `structure.json`
- Peak 0.952, RMS 0.182 — both inside the target bands
- **The ground-bass note is among the top three low-band pitch classes in 40/40 bars**
- F natural 0.162 against F♯ 0.013 — Phrygian, not natural minor
- Per-pass chroma, 70–1200 Hz, all five fully diatonic:

```
The ground, alone      D:0.239 C:0.236 F:0.220 B:0.165 E:0.067
Chords enter           D:0.187 B:0.180 C:0.141 E:0.133 G:0.132
The melody enters      D:0.244 E:0.209 G:0.185 F:0.112 B:0.093
Figuration enters      D:0.241 E:0.194 G:0.176 B:0.108 F:0.103
Full organ             D:0.248 E:0.205 G:0.175 F:0.110 B:0.096
```

D ranking first throughout is the ground bass doing its work — D and C are two of
the four tetrachord steps and each sounds for a full bar of every pass.

- Video 94.00 s, both streams present; frames extracted at 10 s, 55 s and 88 s and
  inspected. One ring at pass 1, five by pass 5, and the spectrum ring warms from
  blue to gold as the registration grows.

## 11. Prompt to regenerate the whole thing from an LLM

> Write two Python scripts. Script 1 composes a passacaglia in E Phrygian, 3/4 at
> 80 BPM: an 8-bar ground of Em Dm C G/B C G/B F Em over the bass E2 D2 C2 B1 C2
> B1 F2 E2 — a descending tetrachord and the Phrygian flat-II cadence — repeated
> five times without variation. Use G major in first inversion on the B, since the
> triad on Phrygian's fifth degree is diminished. Pass 1 is pedal alone; pass 2
> adds sustained chords; pass 3 a slow melody B4 A4-F4 G4 G4-D4 E4 D4 F4 E4; pass
> 4 six running eighths per bar through the chord an octave up; pass 5 full
> registration with the melody doubled. There is no percussion. Synthesize
> everything with one pipe-organ voice taking a rank list of (harmonic multiple,
> amplitude) — 16′ 8′ 4′ for the pedal, 8′ 4′ 2⅔′ 2′ for the principal, plus a
> mixture for full — with no decay, a band-passed noise chiff on the attack, and a
> deterministic per-rank detune. Run the whole mix through a six-tap reverb
> low-passed at 2600 Hz. Write a 4-track MIDI, transcode to MP3, and emit a JSON
> file including has_drums false. Script 2 reads the WAV and that JSON and renders
> a 1280×720 24 fps visualizer in stone and candlelight, taking its pulse from the
> downbeat rather than the onset detector because there is no percussion to
> detect, and drawing the ground as accumulating concentric rings — one per pass,
> eight ticks each, earlier rings kept on screen.

The exact parameter values in sections 1, 3 and 6 are what make the output match
rather than merely resemble.
