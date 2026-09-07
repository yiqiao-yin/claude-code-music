# How to build a new music-video bundle

This file is the spec for creating another folder like
[`moody_drums_bundle`](moody_drums_bundle/) or
[`optimistic_drums_bundle`](optimistic_drums_bundle/). It is written to be read
by Claude Code *and* by a human.

**The deal:** the framework never changes — same folder layout, same two scripts,
same asset set, same pipeline (notes → code → audio → analysis → frames → video).
The *music* should change a lot. Section 3 is the menu of things to change;
section 2 is the list of things not to.

**To use it:** point Claude Code at this file and say what you want. Claude asks
you the questions in section 1, fills the gaps with defaults, builds the bundle,
verifies it with section 5, and reports back.

> Claude: ask the section-1 questions in **one batch**, at most six of them, and
> only the ones the request left genuinely open. Do not ask about anything that
> has a default in section 3 unless the answer would change the whole piece.
> State your assumptions in your first reply, then build the whole thing without
> stopping. Do not ship a bundle that has not passed section 5.

---

## 1. The brief — what I need from you

### 1.1 The three that matter

Nothing sensible can be defaulted for these.

1. **Mood or genre, in your own words.** One sentence is plenty. "Nocturnal jazz,
   smoky, brushes not sticks." "Driving and mechanical, like a train at night."
   "Pastoral, sunrise over a field." This drives every other choice.
2. **Key and mode** — or say "you pick" and I'll choose one that fits the mood.
   Modes are the cheapest way to get a genuinely different colour: Dorian is not
   minor, Lydian is not major. See §3.2.
3. **Does the harmony go anywhere?** Static loop, one key change, a gradual
   darkening, a false ending? The optimistic bundle's whole identity is the
   G→C lift at bar 17. Say "just loop it" if you want a loop.

### 1.2 The ones with defaults — override if you care

| Question | Default if you don't say |
|---|---|
| **Tempo and feel** | Derived from mood: brooding 60–75, reflective 76–95, upbeat 96–120, driving 121–140 |
| **Length** | ~60 s, matching both existing bundles |
| **Meter** | 4/4 |
| **Drums?** | Yes. Say "no drums" for something ambient — the framework handles it, the visualizer just gets quieter |
| **Lead instrument character** | A voice from the §3.5 menu chosen to fit the mood |
| **Video palette** | Derived from mood — cold purples for dark, warm golds for bright, etc. |
| **Caption text** | `"<name>  |  <key>, <bpm> BPM"` |
| **Folder / file naming** | `template/<name>_bundle/`, assets named `<name>.*` |

### 1.3 Copy-paste answer block

If you'd rather not be interviewed, fill this in and hand it over:

```
mood:        
key/mode:    
harmonic arc:
tempo:       
length:      
meter:       
drums:       
lead sound:  
palette:     
name:        
notes:       
```

### 1.4 Things you never need to tell me

Register and voicing choices, exact chord spellings, reverb tap times, particle
counts, envelope times, FFT settings, ffmpeg flags. Those are mine unless you
have an opinion.

---

## 2. The invariant framework — do not change this

### 2.1 Layout

```
template/<name>_bundle/
├── README.md              # the full recipe, per §6
├── structure.json         # written by 01, read by 02
├── scripts/
│   ├── 01_make_music.py   # composition + synthesis + MP3 + structure.json
│   └── 02_make_video.py   # analysis + frame rendering + mux
└── assets/
    ├── <name>.mid
    ├── <name>.wav
    ├── <name>.mp3
    └── <name>_visualizer.mp4
```

Exactly four files in `assets/`. `structure.json` lives at the bundle root — it
is a build artifact, not a deliverable.

### 2.2 The pipeline

Notes as data → MIDI → numpy synthesis → WAV → MP3 → per-frame analysis of that
same WAV → Pillow frames → ffmpeg. **No AI audio or video generation, ever.** No
sample libraries. Every sound is arithmetic; every frame is drawn.

### 2.3 Script 01 contract

- Paths: `OUT = Path(__file__).resolve().parent.parent / "assets"`, `OUT.mkdir(parents=True, exist_ok=True)`.
  Never hard-code an absolute path.
- ffmpeg: `shutil.which("ffmpeg")` falling back to `imageio_ffmpeg.get_ffmpeg_exe()`.
- Musical material lives in **module-level constants at the top** — `CHORDS`,
  `BASS`, `MELODY`, drum pattern lists — so the README can quote them and a human
  can edit them without reading the synthesis code.
- 4-track MIDI via `midiutil.MIDIFile(4)`: Pad ch0, Bass ch1, Lead ch2, Drums ch9.
  Program changes on tracks 0–2. Track roles can be renamed for a different
  arrangement, but keep it to four tracks on those channels.
- Synthesis at `SR = 44100`, mono, written as int16.
- Seeded RNG for any noise: `np.random.default_rng(3)` for drums. Do not use
  unseeded randomness anywhere.
- Master chain, in this order: sum melodic voices → reverb the melodic sum only →
  add dry drums at 0.8 → normalize to `peak / 1.05` → 3 s linear fade-out.
- Transcode the MP3 in-script at 192k.
- Write `structure.json` last.

### 2.4 Script 02 contract

- Reads `assets/<name>.wav` and `../structure.json`. Never re-derives BPM or bar
  positions from constants copied out of script 01.
- 1280×720, 24 fps, `N = ceil(duration * 24)` frames, `hop = SR // FPS`.
- Analysis, one FFT pass per frame (2048-point, Hann) feeding **both** the
  spectrum and the onset detector:
  - `rms[i]`, normalized, smoothed `max(rms[i], 0.9 * rms[i-1])`
  - `spec[i, b]`, 32 log bands 40–4000 Hz, `log1p(x*20)`, normalized, smoothed 0.85
  - onsets from low-band (40–120 Hz) spectral flux, threshold = 9-frame moving
    average × 1.6 + 2% of max flux; `pulse[i] = 1.0` on onset else `0.78 * pulse[i-1]`
- Scene elements, all of them present: background gradient, blurred central orb
  sized by `rms` and `pulse`, kick ring, 32-line spectrum ring, drifting
  particles (`default_rng(7)`), bottom waveform strip, caption fading in/out over
  3 s. Their *colours, motion and extras* are yours to change; the element list is not.
- Frames piped as `rawvideo` into ffmpeg. No intermediate PNGs.
- Encode: `libx264`, `yuv420p`, CRF 20, preset medium, AAC 192k, `-shortest`.

### 2.5 `structure.json` schema

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

`modulation_sec` may be `null` for a piece that stays in one key. Add extra keys
freely (`drop_sec`, `build_start_sec`, `section_labels`) — the video script is
the only consumer. **Any musical event the visualizer should react to but the
onset detector cannot find belongs in this file.**

### 2.6 Environment

```bash
pip install numpy scipy pillow midiutil imageio-ffmpeg
```

No system ffmpeg required.

---

## 3. What varies — the knob reference

This is where a new bundle earns its existence. Changing only the key and tempo
gets you a remix, not a new piece. **Aim to change at least one thing from every
subsection below.**

### 3.1 Structure, tempo, meter

Total seconds `= bars * beats_per_bar * 60 / bpm + tail`. Tail is 4 s.

| | moody | optimistic |
|---|---|---|
| Form | 8-bar cycle × 2 = 16 bars | 8-bar cycle × 3 = 24 bars |
| BPM | 68 | 104 |
| Length | 60.5 s | 59.4 s |

Other shapes worth using: 4-bar cycle × 6 for something hypnotic; a 12-bar blues;
16-bar through-composed with no repeat; an AABA with a contrasting B section;
3/4 or 6/8 for lilt; 5/4 or 7/8 for unease. Meter is `BEATS_PER_BAR` plus a
matching drum pattern — nothing else in the framework assumes 4.

Represent the form as a `SECTIONS` list of `(chords, bass, melody_transpose)`
tuples, as the optimistic bundle does. It makes key changes and section swaps a
one-line edit.

### 3.2 Harmony

Mode is the cheapest source of a genuinely new colour. Same root, very different
feeling:

| Mode | Character | Signature chord move |
|---|---|---|
| Ionian (major) | bright, settled | I – IV – V |
| Dorian | minor but hopeful, jazzy | i – IV (major IV over minor) |
| Phrygian | dark, Spanish, tense | i – ♭II |
| Lydian | floating, wondrous, filmic | I – II (major II) |
| Mixolydian | rootsy, warm, unresolved | I – ♭VII |
| Aeolian (natural minor) | plainly sad | i – ♭VI – ♭VII |
| Harmonic minor | dramatic, ornate | i – V7 (raised 7th) |

Beyond mode, things that change the harmonic feel more than a transposition does:

- **Voicing register.** Both existing bundles keep pads in MIDI 48–74. Drop to
  36–55 for something heavy and close, or lift to 64–84 for something glassy.
- **Chord density.** Triads are open and folk-like; 7ths are smooth; 9ths and
  6/9s are lush; quartal stacks (`[n, n+5, n+10]`) are modern and ambiguous.
- **Harmonic rhythm.** Both bundles use one chord per bar. Two per bar drives;
  one chord per two bars floats; one chord for the entire piece is a drone.
- **Pedal tones.** Hold one bass note under changing chords for tension.
- **Chromatic motion.** A descending chromatic bass line under static upper voices.

Keep the strum stagger (0.08 beats per voice in MIDI, 0.06 s in synth) or change
it deliberately — 0 for a hard block-chord attack, 0.15+ for a harp roll.

### 3.3 Melody

The two bundles are deliberate opposites and show the mechanism:

- **moody**: descending cells, long notes (2–3 beats), narrow range, lands on
  chord tones — sounds like sighing
- **optimistic**: rising three-note cells, short notes (1–2 beats), reaches a high
  peak at bar 4 of each half — sounds like lifting

Other levers: **rhythmic density** (one note per bar = spacious; sixteenths =
busy), **syncopation** (start notes on off-beats), **range** (an octave feels
folk-like, two octaves feels virtuosic), **repetition** (an exact repeated motif
is a hook; never repeating is ambient), **call and response** (a phrase, a bar of
silence, an answer), and **tension notes** — landing on the 9th or 11th instead of
a chord tone is the single fastest way to sound unresolved.

Write it as `(start_beat, midi_note, length_beats)` tuples and verify every note
against the chord under it before you synthesize.

### 3.4 Drums

The pattern *is* the genre. Beats are 0-indexed within the bar.

| Feel | Kick | Snare | Hats |
|---|---|---|---|
| Half-time (moody) | 0, 2.5 | 1, 3 | 8ths |
| Backbeat (optimistic) | 0, 1.5, 2.5 | 1, 3 | 8ths |
| Four-on-the-floor | 0, 1, 2, 3 | 1, 3 | 8ths, offbeat open hats |
| Broken / breakbeat | 0, 0.75, 2.5 | 1, 3 | 16ths, ghosted |
| Waltz (3/4) | 0 | 1, 2 | 3 quarters |
| Brushes / jazz | 0, 2 | soft on 1, 3 | ride on 0, 1.5, 2, 3.5 |
| None | — | — | — |

Also vary: **entry point** (both bundles start drums at bar 3 — try bar 1, or
halfway, or dropping out for a section), **fills** (every 4th bar in both — try
every 8th, or a big one only before a section change), **swing** (offset every
odd 8th by +0.06 beats), **ghost notes** (velocity 25–35 snares on the "e" and
"a"), and **section dynamics** (scale all drum gains by 0.6 in a verse, 1.0 in a
chorus).

Drum synthesis is also a knob, not a fixture:

```python
def kick_808(dur=0.9):                      # long, tuned, hip-hop
    n = int(dur*SR); t = np.arange(n)/SR
    f = 90*np.exp(-t*12) + 38
    return np.sin(2*np.pi*np.cumsum(f)/SR) * np.exp(-t*2.2)

def snare_brush(dur=0.45):                  # soft, jazzy
    n = int(dur*SR); t = np.arange(n)/SR
    b, a = butter(2, [900/(SR/2), 4500/(SR/2)], btype="band")
    return lfilter(b, a, rng_d.standard_normal(n)*np.exp(-t*7)) * 0.9

def rim(dur=0.06):                          # dry click
    n = int(dur*SR); t = np.arange(n)/SR
    return np.sin(2*np.pi*400*t)*np.exp(-t*90) + rng_d.standard_normal(n)*np.exp(-t*300)*0.4

def shaker(dur=0.07):                       # tight, dry
    n = int(dur*SR); t = np.arange(n)/SR
    b, a = butter(2, 9000/(SR/2), btype="high")
    return lfilter(b, a, rng_d.standard_normal(n)*np.exp(-t*80))

def tom(freq, dur=0.35):
    n = int(dur*SR); t = np.arange(n)/SR
    f = freq*np.exp(-t*6) + freq*0.7
    return np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*8)
```

### 3.5 Synth voices

The biggest single lever on how a bundle *sounds*, and the most under-used.
Swap at least one voice for every new bundle.

All of these are drop-in replacements for `pad_voice` / `lead_voice` / `bass_voice`
and assume the `env`, `lowpass` and `rng_d` helpers from the existing scripts.
They return **unnormalized** signals — measured peaks range from 0.9 (`sub_bass`)
to 4.0 (`pluck`) — so balance is set entirely by the `gain` argument at the
`place()` call. Start a new voice at gain 0.1 and adjust against §5.1.

```python
def pluck(freq, dur):                       # Karplus-Strong — guitar/harp/koto
    n = int(dur*SR); L = max(2, int(SR/freq))
    buf = rng_d.standard_normal(L); out_ = np.zeros(n)
    for i in range(n):
        out_[i] = buf[i % L]
        buf[i % L] = 0.5*(buf[i % L] + buf[(i+1) % L]) * 0.996
    return out_ * env(n, 0.001, 0.05, 0.8, dur*0.5)

def fm_bell(freq, dur, ratio=3.5, index=6):  # bell, mallet, electric piano
    n = int(dur*SR); t = np.arange(n)/SR
    mod = np.sin(2*np.pi*freq*ratio*t) * index * np.exp(-t*4)
    return np.sin(2*np.pi*freq*t + mod) * np.exp(-t*3)

def organ(freq, dur):                        # drawbar — church, gospel, prog
    n = int(dur*SR); t = np.arange(n)/SR
    sig = sum(np.sin(2*np.pi*freq*h*t)*g for h, g in ((1,1),(2,.6),(3,.4),(4,.3),(6,.2),(8,.15)))
    return sig * env(n, 0.03, 0.05, 0.95, 0.08)

def breath_lead(freq, dur):                  # airy flute / voice-like
    n = int(dur*SR); t = np.arange(n)/SR
    b, a = butter(2, [freq*0.8/(SR/2), min(freq*4, SR/2-1)/(SR/2)], btype="band")
    air = lfilter(b, a, rng_d.standard_normal(n)) * 0.25
    return (np.sin(2*np.pi*freq*t) + air) * env(n, 0.12, 0.2, 0.8, 0.4)

def sub_bass(freq, dur, drive=1.6):          # deep, round, modern
    n = int(dur*SR); t = np.arange(n)/SR
    return np.tanh(np.sin(2*np.pi*freq*t) * drive) * env(n, 0.01, 0.2, 0.7, 0.3)

def sweep_pad(freq, dur, f0=400, f1=3000):   # filter opening over the note
    n = int(dur*SR); t = np.arange(n)/SR
    sig = sum(np.sin(2*np.pi*freq*h*t)/h**1.4 for h in range(1, 8))
    cut = np.linspace(f0, f1, n)             # crude but effective: blend two filters
    lo, hi = lowpass(sig, f0), lowpass(sig, f1)
    m = (cut - f0) / (f1 - f0)
    return (lo*(1-m) + hi*m) * env(n, 0.6, 0.5, 0.7, 1.0)
```

Also: **arpeggiate** instead of sustaining (same chord, one note per 8th or 16th,
using `pluck`); **detune amount** (0.4 cents is subtle, 8 cents is a chorused
wash); **octave doubling**; **tremolo** (`* (0.7 + 0.3*np.sin(2*np.pi*5*t))`);
**stereo** — both bundles are mono, and going stereo (two output buffers, pan
voices, write shape `(n, 2)`) is a legitimate framework extension.

### 3.6 Mix and space

Reverb taps set the room. The moody bundle uses long taps (97/151/233/389 ms,
lowpass 3500) for a cathedral; the optimistic one short taps (61/89/127/211 ms,
lowpass 4500) so the backbeat stays tight.

Rule of thumb: **the longest tap should be shorter than one beat.** At 68 BPM a
beat is 882 ms so 389 is fine; at 140 BPM a beat is 429 ms and a 389 ms tap turns
the mix to mud. Scale taps with tempo. Darken the lowpass (2000 Hz) for distance,
brighten it (6000 Hz) for presence. For a dry, in-your-face genre, skip reverb
entirely and just add a single 40 ms slapback.

Also worth varying: drum-to-melodic balance (the `drums * 0.8`), whether drums get
any reverb at all, fade-out length, and whether the piece fades or ends cold.

### 3.7 Video

Palette should follow the music, not a template. Set a background gradient, an
orb base colour, a spectrum-ring colour that *contrasts* with the background
(cold ring on warm bg, warm ring on cold bg), and a particle tint.

| Mood | Background | Orb | Ring |
|---|---|---|---|
| moody | deep indigo | violet | lavender |
| optimistic | warm dusk → gold | amber → gold | teal |
| tense | near-black, slight green | pale grey-green | red |
| dreamy | soft rose-grey | pink-white | pale cyan |
| aquatic | deep teal | cyan | white-green |
| nocturnal jazz | warm brown-black | dim amber | dusty blue |

Reactivity beyond the required elements: shake the orb centre on onsets; rotate
the spectrum ring faster in busier sections; make particles fall instead of rise
for something heavy; a horizon line; a second orb for a call-and-response melody;
strobe the background on a four-on-the-floor kick. Drive any section-scale
behaviour from `structure.json`, exactly as the optimistic bundle drives its
`lift` and `bloom` envelopes from `modulation_sec`.

---

## 4. Build procedure

1. **Collect the brief.** Ask the §1.1 questions in one batch. Restate the full
   spec back, including every default you're assuming, before writing code.
2. **Write the material first.** Chords, bass, melody, drum pattern as constants.
   Check every melody note against its chord. Check every bass note is the root of
   its chord. Check registers are in range for the voices you picked.
3. **Write `scripts/01_make_music.py`** to the §2.3 contract. Run it. Listen to
   the numbers: §5.1.
4. **Write `scripts/02_make_video.py`** to the §2.4 contract. Run it (~75 s for a
   60 s piece).
5. **Verify** with §5, all of it.
6. **Write `README.md`** to the §6 outline, with the real measured numbers from
   step 5 — never numbers you expected to get.
7. **Update the repo README** with the new bundle.
8. **Commit and push.**

---

## 5. Verification — do all of it before claiming it works

### 5.1 Audio

```bash
python3 -c "
import numpy as np; from scipy.io import wavfile
sr,a = wavfile.read('assets/NAME.wav'); a = a.astype(np.float32)/32767
print('dur %.2fs  peak %.3f  rms %.4f' % (len(a)/sr, np.abs(a).max(), np.sqrt((a**2).mean())))
"
```

- Duration within 0.1 s of `structure.json`'s `duration_sec`
- Peak 0.90–0.96 (the `/1.05` normalize should land here; higher means a bug)
- RMS 0.10–0.25 — below 0.08 is thin, above 0.30 is squashed
- No clipping: `np.abs(a).max() < 1.0`

### 5.2 The key is what you say it is

Do not skip this. It catches transposition errors, wrong voicings, and melodies
that are in a different key from their chords.

```bash
python3 -c "
import numpy as np; from scipy.io import wavfile
sr,a = wavfile.read('assets/NAME.wav'); a = a.astype(np.float32)/32767
names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def chroma(seg):
    mag = np.abs(np.fft.rfft(seg*np.hanning(len(seg)))); f = np.fft.rfftfreq(len(seg), 1/sr)
    ok = (f>60)&(f<2000); pc = np.zeros(12)
    np.add.at(pc, np.round(69+12*np.log2(np.maximum(f[ok],1e-9)/440)).astype(int)%12, mag[ok])
    return pc/pc.sum()
for lbl, s, e in [('section 1', 5, 30), ('section 2', 38, 55)]:
    c = chroma(a[int(s*sr):int(e*sr)])
    print(lbl, ' '.join('%s:%.3f'%(names[i], c[i]) for i in np.argsort(c)[::-1][:5]))
"
```

The tonic should rank first or second. Notes outside the mode should not appear
in the top five. If there's a key change, the two sections must differ.

### 5.3 Video

```bash
FF=$(python3 -c "import imageio_ffmpeg as f;print(f.get_ffmpeg_exe())")
"$FF" -hide_banner -i assets/NAME_visualizer.mp4 2>&1 | grep -E 'Duration|Stream'
for T in 8 30 50; do "$FF" -y -loglevel error -ss $T -i assets/NAME_visualizer.mp4 \
  -frames:v 1 /tmp/frame_$T.png; done
```

Then **actually look at the extracted frames.** Check: video duration matches the
audio; both streams present; the orb isn't clipped off-screen or filling the
frame; the caption is legible; the spectrum ring reads against the background; if
there's a structural event, extract a frame at that timestamp and confirm it's
visible.

Also sanity-check the printed onset count against the notated kick count
(`kicks_per_bar * drum_bars`). Detected will exceed notated — snares and hats leak
into the low band — but 5× notated means the threshold is too low.

### 5.4 Reproducibility

Re-run script 01 and compare **PCM data**, not the file:

```python
import hashlib; from scipy.io import wavfile
sr, a = wavfile.read("assets/NAME.wav"); print(hashlib.md5(a.tobytes()).hexdigest())
```

Record that hash in the README. Do not record file-level MD5s as the verification
method — see §7.

---

## 6. The bundle README outline

Same shape both existing bundles use. The test: **someone with no access to the
scripts should be able to rebuild the piece from the README alone.**

```
# Recreating "<name>": MIDI, MP3, and MP4
0. Environment            versions table, install line, reproducibility notes,
                          PCM-data checksum
1. Musical specification  key, tempo, form, duration; chord table with voicings
                          and functions; bass; melody tuples; drum pattern with
                          velocities. Every number hard-coded in script 01.
2. MIDI file              track/channel/program table
3. Audio synthesis        each voice's exact parameters; drum synthesis; mix and
                          reverb chain in order; measured peak and RMS
4. MP3                    the transcode
5. Structure handoff      the structure.json contents and what reads them
6. Video                  format; analysis parameters; frame composition as a
                          numbered list, one entry per drawn element
7. What's different       what this bundle changes vs. the others, and why —
                          this is the section that makes the folder worth having
8. Run order              the two commands and rough timings
9. LLM regeneration prompt  one paragraph that would reproduce the piece
```

---

## 7. Pitfalls, learned the hard way

- **Never hard-code output paths.** `moody_drums_bundle` writes to
  `/mnt/user-data/outputs/` and cannot run anywhere else unedited.
- **Never require system ffmpeg.** Use the `shutil.which` → `imageio_ffmpeg`
  fallback; some machines have no ffmpeg and no way to install one.
- **WAV file MD5s are not a reproducibility check.** Re-running the moody script
  on a different scipy produced 100% identical PCM samples but a different file
  hash — that scipy writes 5,766 bytes of extra RIFF chunk. Hash `a.tobytes()`.
- **Don't duplicate musical constants across the two scripts.** That's what
  `structure.json` is for.
- **Clamp ADSR segments.** `env()` must handle `attack + decay + release > duration`
  or short notes wrap around and click.
- **One FFT pass per frame.** Computing the spectrum and the onset detector
  separately doubles the slowest stage for nothing.
- **Long reverb at fast tempo is mud.** Longest tap < one beat.
- **Check the melody against the harmony before synthesizing.** A wrong note is
  cheap to fix in a tuple list and expensive to find by ear in a 60 s render.
- **Bass register doesn't survive transposition.** Transposing the optimistic
  chords up a fourth was right; transposing its bass up a fourth would have put
  the roots at C3–E3. Re-voice bass lines by hand.
- **Don't repeat a palette.** Two bundles with the same violet orb look like a
  bug, not a series.

---

## 8. Reference: what exists so far

| | `moody_drums_bundle` | `optimistic_drums_bundle` |
|---|---|---|
| Key | A minor | G major → C major at bar 17 |
| Tempo | 68 BPM | 104 BPM |
| Form | 8-bar cycle × 2 = 16 bars, 60.5 s | 8-bar cycle × 3 = 24 bars, 59.4 s |
| Melody | descending, long notes | rising cells, short notes |
| Drums | half-time, from bar 3 | backbeat + push, open-hat section marks |
| Pad | attack 0.9 s, lowpass 1400 Hz | attack 0.5 s, lowpass 2200 Hz |
| Reverb | 97/151/233/389 ms, lp 3500 | 61/89/127/211 ms, lp 4500 |
| Palette | deep indigo, violet orb, lavender ring | warm dusk→gold, amber orb, teal ring |
| Structural trick | none | palette lift + bloom ring at the modulation |
| Paths | hard-coded `/mnt/user-data/outputs/` | script-relative ✅ |
| MP3 step | manual shell command | in-script ✅ |

A third bundle should differ from **both** of these — ideally in mode, meter,
lead voice and drum feel at once, not just in key.
