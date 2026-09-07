# Recreating "avenger beginning song": MIDI, MP3, and MP4

This document is the full recipe to regenerate `avenger_beginning_song.mid`,
`avenger_beginning_song.mp3`, and `avenger_beginning_song_visualizer.mp4` from
scratch. It follows the pipeline in [`../instructions.md`](../instructions.md):
symbolic composition, numerical synthesis, frame-by-frame rendering. No AI audio
or video generation.

**The brief it was built from** was a complete two-handed keyboard layout, given
note by note: left hand on low power chords with no third (E+B, D+A, C+G), right
hand on triads with the melody on top, in three sections — Opening Fanfare,
Build-Up, Climax — followed by a descending run over a bass line. The Silvestri
voicing, with the instruction to play the left hand with heavy accents and short
pauses for orchestral percussion impact.

Every pitch in this bundle comes from that brief. What was added was rhythm,
form and orchestration, none of which the brief specified.

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
- One seeded RNG in the audio, `default_rng(3)`, for the brass breath transient
  and all percussion; `default_rng(7)` for video particles.
- Verify the **PCM sample data**, not the WAV container:

```python
import hashlib
from scipy.io import wavfile
sr, a = wavfile.read("assets/avenger_beginning_song.wav")
print(hashlib.md5(a.tobytes()).hexdigest())   # c37c320e75a0208f1d5b33c815942aa3
```

File MD5s from the original run, for reference only:

```
3435223f9d644eb441264fbd3a577f07  avenger_beginning_song.mid
9250bbb2d98d5eb60094a5ddd6a169cd  avenger_beginning_song.wav
59bf870fbfb9fcbb9e2c6cac07834fca  avenger_beginning_song.mp3
daa864f96cbb60d16efdc8fd01164cdd  avenger_beginning_song_visualizer.mp4
```

## 1. Musical specification

Everything below is hard-coded in `scripts/01_make_music.py`.

**Global**

- Key: E minor. Pitch classes used across the whole piece: **C D D♯ E F♯ G A B** —
  E natural minor plus the D♯ that the B major chord contributes, which is the
  harmonic-minor dominant.
- Tempo: 88 BPM, 4/4
- Form: 32 bars = 87.27 s, plus a 4 s tail = **91.27 s** total
- Sample rate for synthesis: 44,100 Hz, mono, 16-bit PCM

**Rhythm.** One chord per bar. Both hands hit on beat 1 and are left to ring
about 3.2 beats, so roughly a beat of silence separates every chord — the "heavy
accents and short pauses" the brief asked for. The three pickup bars put their
single B3 on beat 3, where it functions as a lead-in to the next downbeat rather
than as a bar of its own.

**Form.** The brief's material is 18 chord events. Played once at this tempo that
is about 50 s, so it is stated, restated, and then resolved:

| Bars | Section | |
|---|---|---|
| 1–4 | Opening Fanfare | as written |
| 5–9 | The Build-Up | as written |
| 10–14 | The Climax | as written |
| 15–18 | Fanfare (restated) | sub-octave added under every chord |
| 19–23 | Build-Up (restated) | percussion at full weight |
| 24–28 | Climax (restated) | |
| 29–32 | Descending run | once, as the ending |

The descending run resolves the whole piece, so it is played after the
restatement rather than at the end of each pass. This works because bar 14 ends
on Am/D, whose D bass leads straight back to E minor for bar 15.

**The score, bar by bar.** Left hand is always root + fifth, no third.

| Bar | Label | Left hand | Right hand | Melody |
|---|---|---|---|---|
| 1 | E (pickup) | E2 B2 | B3 *(beat 3)* | |
| 2 | Em | E2 B2 | E4 G4 B4 | |
| 3 | Em/G | E2 B2 | G4 B4 E5 | |
| 4 | D | D2 A2 | D4 F♯4 A4 | |
| 5 | E (pickup) | E2 B2 | B3 *(beat 3)* | |
| 6 | Em | E2 B2 | E4 G4 B4 | |
| 7 | Em/G | E2 B2 | G4 B4 E5 | |
| 8 | Am/C | A2 E3 | C4 E4 A4 | |
| 9 | B/D♯ | B2 F♯3 | D♯4 F♯4 B4 | |
| 10 | E (pickup) | E2 B2 | B3 *(beat 3)* | |
| 11 | Em | E2 B2 | E4 G4 B4 | |
| 12 | Em/G | E2 B2 | G4 B4 E5 | |
| 13 | Cmaj7 (peak) | C3 G3 | G4 C5 E5 | **B5** |
| 14 | Am/D | D2 A2 | A4 C5 E5 | **A5** |

Bars 15–28 repeat this with a sub-octave added: the left hand gains root − 12
where that stays at or above MIDI 26, and each right-hand chord gains its own
lowest note an octave down. "Fuller" here means thickening *downward*; stacking
higher would have thinned the sound rather than weighted it.

The descending run, bars 29–32:

| Bar | Left hand | Right hand |
|---|---|---|
| 29 | C2 G2 | G4 *(beat 1)*, F♯4 *(beat 3)* |
| 30 | A1 E2 | E4 |
| 31 | D2 A2 | D4 |
| 32 | E1 E2 | E4 G4 B4 E5 — the full smash |

The melody line across those four bars is a stepwise descent G–F♯–E–D resolving
onto the final E minor chord.

**Percussion.** Orchestral only — no kit, no backbeat. The percussion doubles the
chord hits rather than keeping time.

- **Timpani** on every downbeat, tuned to the pitch class of the left-hand root
  placed in MIDI 36–47: E→40, D→38, A→45, B→47, C→36.
- **Taiko** on every downbeat, plus an answering hit on beat 3 of restatement
  bars that have no pickup.
- **Cymbal swell** into each of the seven section boundaries, placed about a
  second early so the swell *lands* on the downbeat.

## 2. MIDI file

`midiutil.MIDIFile(4)`, four tracks, standard channel layout.

| Track | Channel | Program | Content |
|---|---|---|---|
| 0 Brass (RH) | 0 | 61 (Brass Section) | right-hand chords |
| 1 Low Brass (LH) | 1 | 58 (Tuba) | left-hand power chords |
| 2 Horn melody | 2 | 60 (French Horn) | B5, A5, and the descending run |
| 3 Percussion | 9 | n/a | taiko 41, timpani 45, cymbal 49 |

Tempo event 88 BPM at tick 0. Note that channel 9 is unpitched in General MIDI,
so the MIDI file loses the timpani's tuning; only the synthesized audio has it.

## 3. Audio synthesis (WAV)

Helpers are the canonical ones from `instructions.md` §2.7.

**`brass(freq, dur, bite)`** — ten harmonics at `1 / h ** 0.9`, normalized, with
two things that stop an additive stack sounding like an organ: a short upward
pitch scoop of 3.5 percent decaying at `exp(-55t)`, and a breath transient of
filtered noise at `exp(-90t)`. The filter also opens on the attack — the output
crossfades from a 4200 Hz low-pass to a 1500 Hz one at `exp(-6t)`, which is what
gives each hit its edge. Envelope (0.035, 0.18, 0.72, 0.45). Gains 0.095–0.105,
0.085 for pickups.

> The scoop integrates frequency to phase with `cumsum`. Scaling `t` inside the
> sine would bend the entire note instead of just its onset — the same bug
> documented in `instructions.md` §7.

**`low_brass(freq, dur)`** — eight harmonics at `1 / h ** 1.05`, low-passed
1900 Hz, plus a bare sine at 0.55 for sub weight. Envelope (0.018, 0.22, 0.78,
0.5). Gain 0.14, 0.16 in the restatement.

**`horn(freq, dur)`** — six harmonics at `1 / h ** 1.35`, a gentler 2 percent
scoop, low-passed 2600 Hz. Envelope (0.06, 0.25, 0.8, 0.5). Gain 0.20.

**Percussion** (RNG seeded with 3)

- `timpani(freq)` (1.1 s): the fundamental starts 10 percent sharp and relaxes
  at `exp(-22t)`, as a real drumhead does. Body is `sin(ph) + 0.4 sin(2.1 ph)` —
  the 2.1 ratio is deliberately inharmonic — under `exp(-4.2t)`, plus a filtered
  skin transient. Gains 0.36 / 0.42.
- `taiko()` (1.0 s): sine sweeping `95 exp(-14t) + 46` Hz under `exp(-5t)`, plus
  a low-passed noise thwack. Gains 0.50 / 0.60.
- `cymbal()` (2.2 s): high-passed noise with a squared ramp *up* over the first
  45 percent and an exponential decay after — a swell, not a crash. Gain 0.16.

**Mix and reverb**

1. Sum brass, low brass and horn into `out`.
2. Reverb `out` only: taps at **113, 179, 271, 421 ms**, gains 0.34, 0.28, 0.22,
   0.16, each low-passed at **3200 Hz**. The largest hall of the five bundles,
   which is what an orchestral fanfare wants; the longest tap still sits under one
   beat (682 ms) so successive hits stay separate.
3. Sum percussion separately, then `out = reverb(out) + drums * 0.8`.
4. Normalize to peak 1 / 1.05, 3 s linear fade-out, int16 WAV.

Measured: **peak 0.952, overall RMS 0.132**. The RMS is the lowest of the five
bundles by design — roughly a quarter of the piece is silence between hits.

## 4. MP3

Script 01 runs the transcode itself, at 192k.

## 5. Structure handoff

`structure.json` carries the usual fields plus `section_labels`, `chords`,
`peak_sec`, and — new in this bundle — **`notes`**: every synthesized note as
`[start_sec, dur_sec, midi, track]`, 173 of them. The visualizer draws the score
from it.

## 6. Video (`scripts/02_make_video.py`)

**Format**: 1280×720, 24 fps, H.264 (CRF 20, preset medium), AAC 192k,
`-shortest`. `N = ceil(91.27 * 24) = 2191` frames piped as `rawvideo`.

**Analysis** — identical to the other bundles: `hop = 1837`; RMS normalized and
smoothed at 0.9; 32 log bands 40–4000 Hz; low-band spectral flux with `pulse`
decaying at 0.78. One FFT pass feeds both.

**Frame composition**

1. Background: cold steel gradient `R = 10 + 20g, G = 14 + 20g, B = 24 + 22g`,
   darkest at the top, plus `26 * bloom`, `30 * peak_glow`, and a warm shift
   `(5,2,0) * weight` where `weight` ramps over 4 s from the restatement.
2. Impact core at (640, 223): radius `40 + 46*rms + 78*pulse + 30*bloom + 26*peak`.
   Note the weighting — `pulse` counts nearly twice what `rms` does, because this
   music is hits separated by silence and a level-driven orb would barely move.
   Colour runs steel blue (150, 178, 235) → gold (255, 214, 140) with `weight`,
   and to near-white at the peak. Blurred 32, added.
3. Shockwave on each hit, and a wide section ring at each of the seven boundaries.
4. Spectrum ring: 32 lines, blue cooling to gold across the restatement.
5. Embers: 260 particles rising faster than any other bundle's.
6. **The score, scrolling.** A piano roll in a band from y = 452 to 598, pitch
   MIDI 24–90 mapped bottom to top, with the playhead at x = 470 so most of the
   band shows what is *coming*. Window is 2 s behind and 6 s ahead. Notes are
   coloured by track — **gold for the right hand, blue for the left, white for the
   horn melody** — dim while pending, bright with a white outline while sounding.
   The brief was a two-handed layout, so the visualizer draws both hands.
7. Waveform strip at y = 642.
8. Section name at 30 px top-left, with chord and bar beneath it; title bottom-left.

## 7. What's different from the other bundles

| | moody | optimistic | morning forest | simple bach | **avenger** |
|---|---|---|---|---|---|
| Key | A minor | G → C | C→D→C→E→C | C major | **E minor (+D♯)** |
| Tempo | 68 | 104 | 112 | 72 | **88** |
| Bars / length | 16 / 60.5 s | 24 / 59.4 s | 40 / 89.7 s | 16 / 57.3 s | **32 / 91.3 s** |
| Texture | sustained pad | sustained pad | arpeggio | 16th figure | **block hits with silence** |
| Main voice | additive pad | additive pad | Karplus-Strong | harpsichord | **scooped brass** |
| Bass | sine + 2nd | sine + 2nd | tanh sat. | bowed, held | **8-harmonic + sine sub** |
| Percussion | kick/snare/hat | + open hat | shaker kit | shaker/kick/rim | **timpani/taiko/cymbal, no kit** |
| Reverb | 97–389, lp 3500 | 61–211, lp 4500 | 53–181, lp 6000 | 89–331, lp 4000 | **113–421, lp 3200** |
| RMS | 0.175 | 0.176 | 0.145 | 0.205 | **0.132** |
| Extra scene element | — | — | god-rays | bar tick ring | **scrolling two-hand score** |

Two things this build turned up.

**The 5× onset rule needs a better denominator.** `instructions.md` §5.3 says
detected onsets more than 5× the notated kick count means the threshold is too
low. This piece detected **285 onsets against 32 bar hits — 8.9×** — and nothing
was wrong. The rule silently assumes the kick is the only thing in the 40–120 Hz
detection band. Here the left hand *is* power chords at E1, A1, C2 and D2, so
every bass attack legitimately registers. Against the honest denominator — 95
note attacks below MIDI 60 plus 81 percussion hits = 176 — the ratio is **1.6×**,
entirely normal.

**A percussion artifact in the chroma check.** The descending run reported an A♯
in a piece with no A♯ anywhere. The note log confirms only A B C D E F♯ G are
written there. Rendering the section without percussion removes the A♯ completely
and leaves `D E A B G`. It comes from the taiko's frequency chirp and the
timpani's deliberately inharmonic 2.1× partial, both of which are unpitched by
design. This is a third variant of the §5.2 blind spot: after harmonically rich
timbres and 5th/7th partials, **swept and inharmonic percussion also puts
pitch classes into the chroma that nobody played.**

## 8. Run order

```bash
cd scripts
python3 01_make_music.py      # -> ../assets/{mid,wav,mp3} and ../structure.json
python3 02_make_video.py      # -> ../assets/avenger_beginning_song_visualizer.mp4
```

About 4 s for the audio and 95 s for the video.

## 9. Verification results

Per [`../instructions.md`](../instructions.md) §5, on the committed assets:

- Duration 91.27 s, matching `structure.json`
- Peak 0.952, RMS 0.132 — both inside the target bands
- 285 detected onsets against 176 genuine low-band attacks: 1.6×
- **Every bar's left-hand root is among the top three low-band pitch classes: 32/32**
- Per-section chroma, 70–1200 Hz:

```
Opening Fanfare        B:0.247 E:0.133 D:0.093 C:0.089 A:0.081   all in E minor
The Build-Up           B:0.207 E:0.178 A:0.100 F#:0.085 C:0.083   all in E minor
The Climax             B:0.246 G:0.160 C:0.120 E:0.106 D:0.069   all in E minor
Fanfare (restated)     B:0.231 E:0.151 D:0.107 G:0.084 C:0.080   all in E minor
Build-Up (restated)    B:0.190 E:0.182 A:0.107 G:0.083 C:0.082   all in E minor
Climax (restated)      B:0.217 G:0.170 C:0.125 E:0.122 D:0.071   all in E minor
Descending run         D:0.225 A:0.147 E:0.145 B:0.085 A#:0.070   percussion artifact, see §7
```

B ranking first throughout is expected: it is the fifth of the tonic power chord,
present in nearly every bar in both hands.

- Video 91.27 s, both streams present; frames extracted at 6 s, 27 s, 71 s and
  85 s and inspected. The piano roll tracks the score, the palette turns from
  steel to gold at the restatement, and the Cmaj7 peak at 70.9 s is the brightest
  frame in the piece.

## 10. Prompt to regenerate the whole thing from an LLM

> Write two Python scripts. Script 1 composes a 32-bar piece in E minor at 88 BPM
> from a two-handed keyboard layout: the left hand plays power chords with no
> third and the right hand plays triads, one chord per bar, both hitting on beat 1
> and ringing about 3.2 beats so silence separates every chord. The 14-bar
> arrangement is E2+B2 with a B3 pickup on beat 3, then Em (E4 G4 B4), Em/G
> (G4 B4 E5), D (D2+A2 / D4 F♯4 A4); the same four again but ending Am/C (A2+E3 /
> C4 E4 A4) and B/D♯ (B2+F♯3 / D♯4 F♯4 B4); then the same three again ending
> Cmaj7 (C3+G3 / G4 C5 E5, melody B5) and Am/D (D2+A2 / A4 C5 E5, melody A5).
> Play that twice, the second time adding a sub-octave under the left hand and
> under each right-hand chord, then finish with a four-bar descending run:
> C2+G2 under G4–F♯4, A1+E2 under E4, D2+A2 under D4, and E1+E2 under a full
> E4 G4 B4 E5. Synthesize the right hand with an additive brass voice using ten
> harmonics, a short upward pitch scoop and a breath transient, the left hand with
> a darker eight-harmonic voice plus a sine sub, and the melody with a rounder
> horn. Percussion is orchestral only — pitched timpani tuned to each left-hand
> root, taiko on the downbeats, and a cymbal swell placed early so it lands on
> each section change. Apply a long dark multi-tap reverb to the pitched parts
> only. Write a 4-track MIDI with midiutil, transcode to MP3, and emit a JSON file
> listing every note as [start, duration, midi, track]. Script 2 reads the WAV and
> that JSON and renders a 1280×720 24 fps visualizer in cold steel warming to
> gold, with an impact core driven mainly by onset rather than level, and a
> scrolling piano roll of the score with the two hands in different colours.

The exact parameter values in sections 1, 3 and 6 are what make the output match
rather than merely resemble.
