# How to build a new music-video bundle

This file is the spec for creating another folder like
[`moody_drums_bundle`](moody_drums_bundle/),
[`optimistic_drums_bundle`](optimistic_drums_bundle/) or
[`morning_forest_bundle`](morning_forest_bundle/). It is written to be read by
Claude Code *and* by a human.

**The deal:** the framework never changes — same folder layout, same two scripts,
same asset set, same pipeline (notes → code → audio → analysis → frames → video).
The *music* should change a lot. Section 3 is the menu of things to change;
section 2 is the list of things not to.

**To use it:** point Claude Code at this file and say what you want — even just
"create a new music video." Claude asks you the three questions in §1.1, fills
every other gap with a default, builds the bundle, verifies it against §5, and
reports back.

> **Claude — read this before doing anything else.**
>
> When someone asks for a new music video, a new bundle, or another track, and
> has not already answered the three questions in §1.1: **stop and ask them.**
> Ask all of the unanswered ones in a single batch, never one at a time. Offer
> the concrete options listed under each question rather than an open prompt —
> most people cannot answer "what mode do you want?" cold, but they can pick from
> a list, and they will happily correct a suggestion.
>
> Rules for that exchange:
> - Ask **only** the §1.1 questions. Everything in §1.2 has a default; do not ask
>   about it unless the answer would change the whole piece.
> - Three questions is the target. Six is the absolute ceiling, and you should
>   never need it.
> - "You pick" is a valid answer to any of them. Take it, choose something that
>   fits the mood, and say what you chose and why.
> - If the request already contains the answers ("upbeat funk in E dorian, just
>   loop it"), ask nothing and start building.
>
> Then: restate the full spec including every default you assumed, build the
> whole bundle without stopping, and do not ship anything that has not passed
> §5. If §5 fails, fix it and re-run §5 — do not report a bundle as working on
> the strength of the code having executed.

---

## 1. The brief — what I need from you

### 1.1 The three that matter

Nothing sensible can be defaulted for these three. Everything else in §1.2 has a
default, so in practice this is the whole interview.

---

#### Question 1 — What mood or genre? One sentence in your own words.

This cascades into every other choice: tempo, mode, drum pattern, synth voices,
even the video palette. Be evocative rather than technical; "like rain on a bus
window at night" tells me more than "melancholy."

Examples that would each produce a very different bundle:

| If you say | It would lead to |
|---|---|
| "Nocturnal jazz, smoky bar, brushes not sticks" | ~80 BPM, Dorian, brush snare, walking bass, dim amber palette |
| "Driving and mechanical, like a train at night" | ~128 BPM, Phrygian, four-on-the-floor, sub bass, cold monochrome |
| "Pastoral, sunrise over a field" | ~92 BPM, Lydian, no drums or very soft ones, plucked strings, warm greens |
| "Anxious, something is about to go wrong" | ~110 BPM, harmonic minor, 7/8, rim clicks, near-black with red |
| "Weightless, floating, half asleep" | ~64 BPM, Lydian, no drums, filter-sweep pads, soft rose |
| "Triumphant, the end of a long climb" | ~118 BPM, Ionian, big backbeat, organ, gold |
| "Playful and mischievous, a cartoon chase" | ~140 BPM, Mixolydian, breakbeat, FM bells, saturated primaries |
| "Grief, but calm about it" | ~58 BPM, Aeolian, no drums until late, breathy lead, grey-blue |

Or just describe a scene, a film, a time of day, a weather. Anything concrete.

---

#### Question 2 — What key and mode? Or say "you pick."

**Mode matters far more than key.** Dorian, Lydian and Phrygian on the same root
are three genuinely different pieces; C minor and D minor are the same piece
shifted. If you only answer half of this, answer the mode half.

| Mode | Sounds like | Try it for |
|---|---|---|
| **Ionian** (major) | bright, settled, resolved | triumph, warmth, children's-book optimism |
| **Dorian** | minor but hopeful, cool, jazzy | jazz, funk, wistful-but-moving |
| **Phrygian** | dark, Spanish, tense | menace, drive, unease |
| **Lydian** | floating, wondrous, unresolved-upward | wonder, dreams, film scores |
| **Mixolydian** | rootsy, warm, bluesy | folk, rock, the open road |
| **Aeolian** (natural minor) | plainly sad | straightforward melancholy |
| **Harmonic minor** | dramatic, ornate, Eastern | drama, ornament, gothic |

Key mostly affects register and colour: lower keys (C, D, E♭) sit heavier and
darker, higher ones (G, A, B♭) sit brighter and lighter. Pick one you like the
sound of, or let me choose. (§3.2 has the same table with the chord moves that
make each mode audible — that's the implementation side of this answer.)

Valid answers: "D dorian" · "something bright" · "same key as the moody one but
major" · "you pick, but darker than the optimistic one" · "you pick."

---

#### Question 3 — Does the harmony go anywhere, or does it just loop?

The single biggest driver of whether a 60-second piece holds attention. The
optimistic bundle's entire identity is one event: the G→C lift at bar 17. The
moody bundle deliberately has none — it broods in one place, which is the point.

| Answer | What happens |
|---|---|
| **"Just loop it"** | One 8-bar cycle repeated. Hypnotic, ambient, background-music-safe. What moody does. |
| **"One key change, lifting"** | Modulate up a fourth or a whole step partway through. Uplift. What optimistic does. |
| **"One key change, dropping"** | Modulate down, or major → parallel minor. The floor falls out. |
| **"Gradual darkening"** | Same key, but voicings descend, chords sour, drums thin out. Slow dread. |
| **"Build and release"** | Sparse → full → sudden drop to near-silence → return. Dance-music shape. |
| **"Two contrasting sections"** | AABA. B in a different mode or register, then home. Song-like. |
| **"False ending"** | Everything stops around 45 s, then one last phrase. Unsettling or tender. |
| **"You pick"** | I'll choose something that fits the mood and tell you where the event lands. |

Whatever you pick, the timestamp of the event goes into `structure.json` and the
video reacts to it — see §2.5 and §3.7. A structural event the visualizer ignores
is a wasted one.

### 1.2 The ones with defaults — override if you care

| Question | Default if you don't say |
|---|---|
| **Tempo and feel** | Derived from mood: brooding 55–75, reflective 76–95, upbeat 96–120, driving 121–145 |
| **Length** | ~60 s. Go longer only when the form needs it — the five-section arch in `morning_forest_bundle` justifies its 90 s |
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

### 1.4 What the exchange looks like

The shortest useful version, start to finish:

> **You:** create a new music video
>
> **Claude:** Three questions before I start — everything else I'll default.
> 1. Mood or genre, in your own words? (e.g. "nocturnal jazz, smoky", "driving
>    and mechanical", "pastoral sunrise" — or describe a scene)
> 2. Key and mode, or "you pick"? Mode matters most: Dorian is cool and jazzy,
>    Lydian floats, Phrygian is dark and tense.
> 3. Does the harmony go anywhere — just loop, one key change, a build and
>    release, a gradual darkening? Or "you pick"?
>
> **You:** rainy city at 2am. you pick the key. gradual darkening
>
> **Claude:** Building `template/rain_city_bundle`. D Dorian at 76 BPM — cool
> rather than self-pitying, which suits 2am better than a plain minor. 24 bars,
> ~63 s, 4/4. Voicings descend a register per section and the drums thin out to
> just rim clicks by the last eight bars. Karplus-Strong pluck lead, brushed
> snare, long reverb. Palette: wet asphalt blue-grey, dim sodium-orange orb,
> particles falling instead of rising. Defaults everywhere else. Starting now.

Note what Claude did *not* ask about: tempo, length, meter, drum feel, lead
sound, palette, naming. All of those were derived from four words of mood and
stated as assumptions, which you can correct after hearing it.

### 1.5 Things you never need to tell me

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
- Musical material lives in **module-level constants at the top** — chords, bass,
  melody, drum pattern lists — so the README can quote them and a human can edit
  them without reading the synthesis code. Names follow the shape of the piece:
  `CHORDS`/`BASS`/`MELODY` for a single-key piece, `BASE`/`ARCH`/`SECTIONS` plus a
  `section(i)` builder when the form transposes.
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
  "section_keys": ["G major", "G major", "C major"],
  "modulation_sec": 36.92,
  "title": "optimistic (with drums)  |  G major -> C major, 104 BPM"
}
```

Every field above is required except `modulation_sec`, which may be `null` for a
piece that stays in one key — or for a piece with several changes, where
`section_starts_sec` carries the information instead. `section_keys` is not read
by the video script, but the §5.2 verification uses it to label its own output;
without it you are eyeballing unlabelled numbers.

Add extra keys freely (`section_transpose`, `peak_sec`, `drop_sec`,
`build_start_sec`) — the video script is the only consumer. **Any musical event
the visualizer should react to but the onset detector cannot find belongs in this
file.**

### 2.6 Environment

```bash
pip install numpy scipy pillow midiutil imageio-ffmpeg
```

No system ffmpeg required.

### 2.7 Canonical helpers

Identical in every bundle. Copy them verbatim; the §3.5 voice menu and the §3.4
drum menu both assume these exact definitions exist.

```python
import shutil
from pathlib import Path
import numpy as np
from scipy.signal import butter, lfilter

SR = 44100
OUT = Path(__file__).resolve().parent.parent / "assets"
OUT.mkdir(parents=True, exist_ok=True)


def ffmpeg_exe():
    """System ffmpeg if present, else the static binary from imageio-ffmpeg."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    from imageio_ffmpeg import get_ffmpeg_exe
    return get_ffmpeg_exe()


def f_of(n):
    """MIDI note number -> frequency in Hz."""
    return 440.0 * 2 ** ((n - 69) / 12)


def env(n_samp, a, d, s, r):
    """Linear ADSR over n_samp samples. Segment lengths are clamped so a note
    shorter than attack + decay + release cannot wrap around and click."""
    e = np.ones(n_samp) * s
    a_n = min(int(a * SR), n_samp)
    d_n = min(int(d * SR), n_samp - a_n)
    r_n = min(int(r * SR), n_samp)
    if a_n:
        e[:a_n] = np.linspace(0, 1, a_n)
    if d_n:
        e[a_n:a_n + d_n] = np.linspace(1, s, d_n)
    if r_n:
        e[-r_n:] *= np.linspace(1, 0, r_n)
    return e


def lowpass(x, cutoff, order=2):
    b, a = butter(order, cutoff / (SR / 2))
    return lfilter(b, a, x)


def place(buf, sig, start_sec, gain):
    """Mix sig into buf at start_sec, truncating at the end of the buffer."""
    s = int(start_sec * SR)
    e = min(s + len(sig), len(buf))
    buf[s:e] += sig[: e - s] * gain


rng_d = np.random.default_rng(3)     # every noise-based voice draws from this
```

The reverb is per-bundle rather than canonical — the tap times are a musical
choice (§3.6) — but the shape is always the same: feedback-free taps, each
low-passed, summed onto the dry signal, applied to the melodic sum only.

```python
def reverb(x):
    y = x.copy()
    for d_ms, g in ((61, 0.26), (89, 0.20), (127, 0.15), (211, 0.11)):
        d = int(d_ms / 1000 * SR)
        buf = np.zeros_like(x)
        buf[d:] = x[:-d]
        y += lowpass(buf, 4500) * g
    return y
```

---

## 3. What varies — the knob reference

This is where a new bundle earns its existence. Changing only the key and tempo
gets you a remix, not a new piece. **Aim to change at least one thing from every
subsection below.**

### 3.1 Structure, tempo, meter

Total seconds `= bars * beats_per_bar * 60 / bpm + tail`. Tail is 4 s.

| | moody | optimistic | morning forest |
|---|---|---|---|
| Form | 8-bar cycle × 2 = 16 bars | 8-bar cycle × 3 = 24 bars | 8-bar cycle × 5 = 40 bars |
| BPM | 68 | 104 | 112 |
| Length | 60.5 s | 59.4 s | 89.7 s |

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

Also vary: **entry point** (moody and optimistic both start drums at bar 3;
morning forest stages it, shaker from bar 1 and the pulse from bar 5 — try bar 1, or
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
**stereo** — every bundle so far is mono, and going stereo (two output buffers, pan
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

**Step 0, and this is not optional: do not write either script from scratch.**
Copy the scripts from the existing bundle closest to what you're building and
edit them. `optimistic_drums_bundle` is the clean baseline — script-relative
paths, in-script MP3, `structure.json` handoff, single FFT pass.
`morning_forest_bundle` is the one to copy if the piece has more than two
sections, an arpeggio, or alternative synth voices. `moody_drums_bundle` is the
original and still has hard-coded paths; copy from it only for reference.

Writing fresh from the §2 contracts produces something that *works* and quietly
drifts — different helper names, a different envelope shape, a reimplemented
reverb. The framework staying identical across bundles is the entire point of
this repo. Read the source you're copying before you edit it.

Then:

1. **Collect the brief.** Ask the §1.1 questions in one batch. Restate the full
   spec back, including every default you're assuming, before writing code.
2. **Write the material first.** Chords, bass, melody, drum pattern as constants.
   Then check, on paper, before running anything:
   - every melody note against the chord under it — **in every section**, not just
     the untransposed one. If a section's bar 8 is a pivot chord that does not
     transpose with the rest, the melody over it is the most likely wrong note in
     the piece.
   - every bass note is the root of its chord (or a deliberate pedal/inversion)
   - every part's register is sane for the voice you picked, and bass lines are
     re-voiced by hand rather than transposed
   - no two simultaneous parts on the same MIDI channel ever share a pitch (§7)
3. **Write `scripts/01_make_music.py`.** Run it. Check §5.1.
4. **Write `scripts/02_make_video.py`.** Run it — budget ~1.3 s of render per
   second of music, so a 90 s piece takes about 2 minutes.
5. **Verify** with §5, all of it, including looking at the extracted frames.
6. **Write `README.md`** to the §6 outline, with the real measured numbers from
   step 5 — never numbers you expected to get.
7. **Update the repo README** and the §8 comparison table in this file.
8. **Commit and push.**
9. **Send the user the `.mp4`.** They asked for a music video; a git commit is not
   one. Deliver the file, and say where the structural events land in
   minutes:seconds so they know what to listen for.

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

Run it from the bundle root. The windows come from `structure.json`, so it works
unchanged for any number of sections:

```bash
python3 -c "
import json, numpy as np
from scipy.io import wavfile
name = 'NAME'
st = json.load(open('structure.json'))
sr, a = wavfile.read('assets/%s.wav' % name); a = a.astype(np.float32)/32767
names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def chroma(seg):
    mag = np.abs(np.fft.rfft(seg*np.hanning(len(seg)))); f = np.fft.rfftfreq(len(seg), 1/sr)
    ok = (f>60)&(f<2000); pc = np.zeros(12)
    np.add.at(pc, np.round(69+12*np.log2(np.maximum(f[ok],1e-9)/440)).astype(int)%12, mag[ok])
    return pc/pc.sum()
starts = st['section_starts_sec'] + [st['duration_sec'] - 4]
keys = st.get('section_keys', ['?'] * (len(starts)-1))
for i in range(len(starts)-1):
    s, e = starts[i] + 2, starts[i+1] - 1          # trim the modulation edges
    c = chroma(a[int(s*sr):int(e*sr)])
    top = np.argsort(c)[::-1][:5]
    print('%-2d %-10s %s' % (i+1, keys[i], ' '.join('%s:%.3f'%(names[j], c[j]) for j in top)))
"
```

Read the output against three rules:

- **The tonic ranks first or second.** Second is common and fine — a cycle that
  leans on its dominant will put the fifth on top.
- **Every pitch class in the top five is diatonic to that section's key.** This is
  the rule that actually catches bugs. An F♯ in a C major section means a
  transposition went somewhere it shouldn't.
- **If the piece modulates, the sections differ.** Identical chroma across a
  claimed key change means the transposition never happened.

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

The same shape all three existing bundles use. The test: **someone with no access to the
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
9. Verification results   the actual §5 numbers — duration, peak, RMS, onset
                          count, the per-section chroma output, and which frame
                          timestamps you looked at
10. LLM regeneration prompt  one paragraph that would reproduce the piece
```

---

## 7. Pitfalls, learned the hard way

- **midiutil cannot serialize two overlapping notes of the same pitch on the same
  channel.** `writeFile` dies with `IndexError: pop from empty list` inside
  `deInterleaveNotes`, and the traceback points at midiutil, not at your music.
  It bites whenever one track carries two simultaneous parts — a sustained pad
  plus an arpeggio, a melody plus its own harmony. Fixes, in order of preference:
  put the second part an octave away so the pitch sets cannot intersect (what
  `morning_forest_bundle` does), or shorten note durations so nothing overlaps.
  Check for it at step 2 of §4, not by waiting for the crash.
- **Keep the `.wav` files in git.** They are large and they are regenerable, and
  deleting them is still the wrong call — the WAV is part of the bundle's
  structure, and the repo is meant to hold the finished artifacts, not just a
  recipe for them. Do not propose pruning them to save space.
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

| | `moody_drums_bundle` | `optimistic_drums_bundle` | `morning_forest_bundle` |
|---|---|---|---|
| Key | A minor | G major → C major at bar 17 | C → D → C → E → C |
| Tempo | 68 BPM | 104 BPM | 112 BPM |
| Form | 8-bar × 2 = 16 bars, 60.5 s | 8-bar × 3 = 24 bars, 59.4 s | 8-bar × 5 = 40 bars, 89.7 s |
| Melody | descending, long notes | rising cells, short notes | rising, rests the last bar of each section |
| Foreground | sustained pad | sustained pad | 8th-note Karplus-Strong arpeggio |
| Lead voice | sine + 3rd harmonic | sine + 3rd harmonic | FM bell + sine core |
| Pad | attack 0.9 s, lp 1400 Hz | attack 0.5 s, lp 2200 Hz | filter opens 500 → 3200 Hz |
| Bass | sine + 2nd harmonic | sine + 2nd harmonic | tanh-saturated |
| Drums | half-time, from bar 3 | backbeat + push, open-hat marks | shaker/kick/rim/brush, staged entry |
| Reverb | 97/151/233/389 ms, lp 3500 | 61/89/127/211 ms, lp 4500 | 53/79/113/181 ms, lp 6000 |
| Palette | indigo, violet orb, lavender ring | dusk→gold, amber orb, teal ring | forest green, gold sun, green ring |
| Gradient | brightens downward | brightens downward | brightens **upward** |
| Structural events | 0 | 1 | 4 |
| Paths | hard-coded `/mnt/user-data/outputs/` | script-relative ✅ | script-relative ✅ |
| MP3 step | manual shell command | in-script ✅ | in-script ✅ |

A fourth bundle should differ from **all three** — the axes still untouched are
meter (everything so far is 4/4), a drumless piece, a genuinely modal colour
(nothing yet uses Dorian, Phrygian, Lydian or harmonic minor), swing, and stereo.
