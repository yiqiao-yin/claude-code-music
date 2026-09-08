"""Compose and synthesize "moonlight storm".

Same framework as the other bundles. No AI audio anywhere.

The brief was "sound like Beethoven's Moonlight sonata", then: the first movement
*into* the third, swelling and receding, dying away at the end. That combination
is a shape Beethoven did not write — the storm of the finale arriving and then
**dissolving** instead of resolving — so this is original music built from the
sonata's devices rather than a transcription of it.

The devices:

  * **relentless broken-chord figuration**, never stopping, which is the entire
    texture of the first movement
  * **C sharp minor**, its actual key, with the raised leading tone in dominants
  * **the sustain pedal.** Beethoven's marking is *senza sordino* — no dampers,
    pedal held down. Notes ring far past their written length and pile into each
    other. That blur is the sound, not an artifact.
  * a **dotted melody** sitting above the ripple, mostly on repeated notes

Form: 28 bars of 4/4 at 72 BPM. One tempo throughout: the acceleration comes from
note density, not from speeding up, which is how the finale's *presto agitato*
feeling is reached without a tempo change.

  bars  1-6   Hushed              triplets alone, pianissimo
  bars  7-12  The melody enters   triplets + the dotted line
  bars 13-16  Gathering           sextuplets, melody doubled in octaves
  bars 17-22  The storm           32nds rocketing up, hammered chords   <- peak
  bars 23-26  Receding            back down through sextuplets
  bars 27-28  Dying away          triplets, pianississimo, the last chord rings
"""

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from midiutil import MIDIFile
from scipy.io import wavfile
from scipy.signal import butter, lfilter

BPM = 72
BEAT = 60.0 / BPM
SR = 44100
BEATS_PER_BAR = 4

OUT = Path(__file__).resolve().parent.parent / "assets"
OUT.mkdir(parents=True, exist_ok=True)


def ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    from imageio_ffmpeg import get_ffmpeg_exe
    return get_ffmpeg_exe()


# ---------------- Musical material ----------------
# C sharp minor: C# D# E F# G# A B, plus B# (= C natural) as the leading tone in
# the dominant. G#7 is what makes it minor rather than modal.
VOICING = {
    "C#m": [61, 64, 68],   # C#4 E4  G#4
    "A":   [57, 61, 64],   # A3  C#4 E4
    "F#m": [54, 57, 61],   # F#3 A3  C#4
    "G#7": [56, 60, 63],   # G#3 B#3 D#4
}
# The melody leans on the major seventh over A, which is the sound of this idiom,
# so A is verified as Amaj7 rather than a bare triad.
TONES = {"C#m": "C# E G#", "A": "A C# E G#", "F#m": "F# A C#", "G#7": "G# C D# F#"}

HARMONY = [
    "C#m", "C#m", "A", "A", "F#m", "G#7",              # hushed
    "C#m", "A", "F#m", "G#7", "C#m", "C#m",            # the melody enters
    "A", "F#m", "G#7", "C#m",                          # gathering
    "C#m", "G#7", "C#m", "A", "F#m", "G#7",            # the storm
    "C#m", "A", "F#m", "G#7",                          # receding
    "C#m", "C#m",                                      # dying away
]
BARS = len(HARMONY)

# Texture per bar. The only thing that accelerates is the note count.
TEXTURE = (["trip"] * 12) + (["sext"] * 4) + (["storm"] * 6) + \
          (["sext"] * 2) + (["trip"] * 4)
assert len(TEXTURE) == BARS

STEPS = {"trip": 12, "sext": 24, "storm": 32}


def figure(chord, texture):
    """The broken-chord figure for one bar, as a list of MIDI notes."""
    v = VOICING[chord]
    if texture == "trip":
        # three notes rising, four times a bar — the first movement's texture
        return [v[j % 3] for j in range(12)]
    if texture == "sext":
        # four notes, reaching an octave above the root
        w = v + [v[0] + 12]
        return [w[j % 4] for j in range(24)]
    # the storm: eight notes rocketing up through two octaves
    w = v + [n + 12 for n in v] + [v[0] + 24, v[1] + 24]
    return [w[j % 8] for j in range(32)]


# Left hand: bare octaves, deep, held under everything.
def octaves(chord):
    r = VOICING[chord][0]
    return [r - 24, r - 12]


# The dotted melody. Mostly repeated notes, which is what makes it feel suspended
# rather than going anywhere.
R = None
MELODY = {
    6:  [(80, 1.5), (80, .5), (80, 2)],
    7:  [(81, 1.5), (81, .5), (80, 2)],
    8:  [(78, 1.5), (78, .5), (78, 2)],
    9:  [(80, 1.5), (80, .5), (78, 2)],
    10: [(85, 1.5), (85, .5), (80, 2)],
    11: [(80, 1.5), (80, .5), (76, 2)],
    12: [(81, 1.5), (81, .5), (81, 2)],
    13: [(78, 1.5), (78, .5), (78, 2)],
    14: [(80, 1.5), (80, .5), (80, 2)],
    15: [(85, 1.5), (85, .5), (85, 2)],
    22: [(80, 1.5), (80, .5), (80, 2)],
    23: [(81, 2), (80, 2)],
    24: [(78, 4)],
    25: [(80, 4)],
}
OCTAVE_DOUBLED = range(12, 16)          # the gathering, melody in octaves
STAB_BARS = [17, 19, 21]                # hammered chords in the storm

# Swell and recede: up to the storm, then away to nothing.
DYN = np.array([
    .30, .30, .33, .33, .36, .36,
    .42, .42, .45, .45, .50, .50,
    .58, .68, .80, .92,
    1.05, 1.10, 1.15, 1.15, 1.10, 1.00,
    .80, .62, .46, .36,
    .26, .18,
])
assert len(DYN) == BARS

SECTION_BARS = [0, 6, 12, 16, 22, 26]
SECTION_LABELS = ["Hushed", "The melody enters", "Gathering",
                  "The storm", "Receding", "Dying away"]
PEAK_BAR = 19

# ---------------- MIDI ----------------
# Written note lengths are short. The pedal lives in the synthesis, not here:
# midiutil cannot serialize overlapping same-pitch notes on one channel, and the
# figure repeats every pitch several times a bar.
mid = MIDIFile(4)
mid.addTempo(0, 0, BPM)
for tr, (name, ch) in enumerate([("Figuration", 0), ("Left hand octaves", 1),
                                 ("Melody", 2), ("Hammered chords", 3)]):
    mid.addTrackName(tr, 0, name)
    mid.addProgramChange(tr, ch, 0, 0)

for bar in range(BARS):
    t = bar * BEATS_PER_BAR
    ch = HARMONY[bar]
    notes = figure(ch, TEXTURE[bar])
    step = BEATS_PER_BAR / len(notes)
    vel = int(np.clip(52 * DYN[bar] + 26, 14, 122))
    for j, n in enumerate(notes):
        mid.addNote(0, 0, n, t + j * step, step * 0.7, vel)
    for n in octaves(ch):
        mid.addNote(1, 1, n, t, BEATS_PER_BAR - 0.15, int(np.clip(60 * DYN[bar] + 22, 16, 124)))
    if bar in MELODY:
        pos = 0.0
        for n, d in MELODY[bar]:
            mv = int(np.clip(64 * DYN[bar] + 34, 20, 126))
            mid.addNote(2, 2, n, t + pos, d * 0.9, mv)
            if bar in OCTAVE_DOUBLED:
                mid.addNote(2, 2, n - 12, t + pos, d * 0.9, mv - 14)
            pos += d
    if bar in STAB_BARS:
        for n in VOICING[ch] + [VOICING[ch][0] + 12, VOICING[ch][0] - 12]:
            mid.addNote(3, 3, n, t + 3, 0.8, 122)

with open(OUT / "moonlight_storm.mid", "wb") as f:
    mid.writeFile(f)


# ---------------- Synthesis ----------------
def f_of(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def env(n_samp, a, d, s, r):
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


rng_d = np.random.default_rng(3)
_piano_cache = {}


def piano(freq, dur, bright=1.0):
    """A concert piano under a held sustain pedal.

    Two refinements over `mozart_sonata_allegro`'s fortepiano:

    **Inharmonicity varies with pitch.** A piano's stiffness coefficient B is not
    constant — bass strings are long and flexible, treble strings short and stiff,
    so the treble stretches far more. Modelled as B rising from 0.00008 to 0.0013
    across the compass. Mozart's version used a single value; this is closer.

    **The pedal.** Decay is roughly half as fast, and nothing is damped at
    note-off, so every note rings its full natural length and piles into the next.
    That accumulation is the Moonlight sound, and it is why the written MIDI
    durations and the synthesized ones deliberately disagree.
    """
    key = (round(freq, 2), round(dur, 3), round(bright, 2))
    if key in _piano_cache:
        return _piano_cache[key]
    n = int(dur * SR)
    t = np.arange(n) / SR
    stiff = 0.00008 + 0.0013 * float(np.clip((freq - 90) / 1400, 0, 1))
    decay = 0.85 + 3.1 * float(np.clip((freq - 110) / 1100, 0, 1))
    sig = np.zeros(n)
    for h in range(1, 15):
        f = h * freq * np.sqrt(1 + stiff * h * h)
        if f >= SR / 2 * 0.9:
            break
        sig += (1.0 / h ** (1.5 - 0.3 * bright)) * np.sin(2 * np.pi * f * t) \
            * np.exp(-t * decay * (1 + 0.20 * h))
    sig /= max(np.max(np.abs(sig)), 1e-9)
    thump = lowpass(rng_d.standard_normal(n) * np.exp(-t * 120), 2400) * 0.09
    out_ = (sig + thump) * env(n, 0.003, 0.02, 0.9, 0.08)
    _piano_cache[key] = out_
    return out_


total_sec = BARS * BEATS_PER_BAR * BEAT + 5
out = np.zeros((int(total_sec * SR), 2))
NOTE_LOG = []


def pan_of(midi):
    return float(np.clip((midi - 44) / 46.0, 0.10, 0.90))


def place(sig, start_sec, gain, midi):
    s = int(start_sec * SR)
    e = min(s + len(sig), len(out))
    if e <= s:
        return
    p = pan_of(midi) * np.pi / 2
    out[s:e, 0] += sig[: e - s] * gain * np.cos(p)
    out[s:e, 1] += sig[: e - s] * gain * np.sin(p)


# PEDAL_RING is how long a note is allowed to sound regardless of what is written.
PEDAL_RING = 3.4

for bar in range(BARS):
    t0 = bar * BEATS_PER_BAR * BEAT
    ch = HARMONY[bar]
    dy = float(DYN[bar])
    notes = figure(ch, TEXTURE[bar])
    step = BEATS_PER_BAR * BEAT / len(notes)
    g = {"trip": 0.105, "sext": 0.072, "storm": 0.052}[TEXTURE[bar]]
    for j, n in enumerate(notes):
        place(piano(f_of(n), PEDAL_RING, 0.75), t0 + j * step, g * dy, n)
        NOTE_LOG.append((round(t0 + j * step, 4), n, 0))
    for n in octaves(ch):
        place(piano(f_of(n), PEDAL_RING + 1.2, 0.6), t0, 0.20 * dy, n)
        NOTE_LOG.append((round(t0, 4), n, 1))
    if bar in MELODY:
        pos = 0.0
        for n, d in MELODY[bar]:
            place(piano(f_of(n), max(d * BEAT, 1.0) + 1.6, 1.0), t0 + pos * BEAT, 0.30 * dy, n)
            NOTE_LOG.append((round(t0 + pos * BEAT, 4), n, 2))
            if bar in OCTAVE_DOUBLED:
                place(piano(f_of(n - 12), max(d * BEAT, 1.0) + 1.6, 0.9),
                      t0 + pos * BEAT, 0.17 * dy, n - 12)
                NOTE_LOG.append((round(t0 + pos * BEAT, 4), n - 12, 2))
            pos += d
    if bar in STAB_BARS:
        for n in VOICING[ch] + [VOICING[ch][0] + 12, VOICING[ch][0] - 12]:
            place(piano(f_of(n), 2.6, 1.0), t0 + 3 * BEAT, 0.16, n)
            NOTE_LOG.append((round(t0 + 3 * BEAT, 4), n, 3))


def reverb(x):
    """Five taps, long and dark. A pedalled piano is already a blur; the room
    only has to extend it. At 72 BPM a beat is 833 ms, so the longest tap sits
    inside one."""
    y = x.copy()
    for d_ms, g in ((89, 0.26), (149, 0.22), (241, 0.18), (379, 0.14), (557, 0.10)):
        d = int(d_ms / 1000 * SR)
        buf = np.zeros_like(x)
        buf[d:] = x[:-d]
        for c in range(2):
            buf[:, c] = lowpass(buf[:, c], 3400)
        y += buf * g
    return y


out = reverb(out)
out /= np.max(np.abs(out)) * 1.05
fade = int(4.5 * SR)
out[-fade:] *= np.linspace(1, 0, fade)[:, None]

wav_path = OUT / "moonlight_storm.wav"
mp3_path = OUT / "moonlight_storm.mp3"
wavfile.write(wav_path, SR, (out * 32767).astype(np.int16))

subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error",
                "-i", str(wav_path), "-b:a", "192k", str(mp3_path)], check=True)

bar_sec = BEATS_PER_BAR * BEAT
(OUT.parent / "structure.json").write_text(json.dumps({
    "bpm": BPM, "bars": BARS, "beats_per_bar": BEATS_PER_BAR,
    "duration_sec": total_sec, "bar_sec": bar_sec, "beat_sec": BEAT,
    "channels": 2,
    "section_starts_sec": [b * bar_sec for b in SECTION_BARS],
    "section_labels": SECTION_LABELS,
    "section_keys": ["C# minor"] * len(SECTION_BARS),
    "chords": HARMONY,
    "texture": TEXTURE,
    "dynamics": [round(float(x), 3) for x in DYN],
    "peak_sec": PEAK_BAR * bar_sec,
    "pedal_ring_sec": PEDAL_RING,
    "notes": [[s, n, tr] for s, n, tr in sorted(NOTE_LOG)],
    "has_drums": False,
    "pulse_source": "downbeat",
    "modulation_sec": None,
    "title": "moonlight storm  |  C# minor, 72 BPM",
}, indent=2) + "\n")

print(f"done: {total_sec:.2f}s, {BARS} bars, {len(NOTE_LOG)} notes, "
      f"peak at {PEAK_BAR * bar_sec:.1f}s")
