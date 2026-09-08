"""Compose and synthesize "music box waltz".

Same framework as the other bundles: symbolic composition to MIDI, numerical
synthesis to WAV, MP3 transcode, structure.json handoff. No AI audio anywhere.

The melody was supplied as an 8-bar tune in 3/4, note by note, every bar summing
to exactly three beats. It uses only C D E F G — no B anywhere — so the mode is
undetermined by the melody alone and the harmony decides it. It is harmonised
here in **D Dorian**: the tune ends on D, which becomes the tonic instead of a
hanging second, and the B natural in the G major chord is the raised sixth that
makes it Dorian rather than plain D minor.

Form: 40 bars of 3/4 at 132 BPM.

  bars  1-4   Intro          music box alone over the waltz accompaniment
  bars  5-12  Theme          the tune as written, no drums
  bars 13-20  Theme + drums  the brushed waltz kit enters
  bars 21-28  Variation      the tune an octave up, with a counter-line below
  bars 29-36  Theme returns  back at written pitch, full
  bars 37-40  Coda           the last phrase again, settling onto a held D
"""

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from midiutil import MIDIFile
from scipy.io import wavfile
from scipy.signal import butter, lfilter

BPM = 132
BEAT = 60.0 / BPM
SR = 44100
BEATS_PER_BAR = 3            # a waltz: the first non-4/4 bundle in the repo

OUT = Path(__file__).resolve().parent.parent / "assets"
OUT.mkdir(parents=True, exist_ok=True)


def ffmpeg_exe():
    """System ffmpeg if present, else the static binary from imageio-ffmpeg."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    from imageio_ffmpeg import get_ffmpeg_exe
    return get_ffmpeg_exe()


# ---------------- Musical material ----------------
# The supplied tune, exactly as written: (midi note, length in beats) per bar.
#   C4 60   D4 62   E4 64   F4 65   G4 67
THEME = [
    [(64, 1.5), (65, 0.5), (64, 1)],      # E4:1.5 F4:0.5 E4:1
    [(67, 2), (67, 1)],                   # G4:2   G4:1
    [(62, 1.5), (64, 0.5), (62, 1)],      # D4:1.5 E4:0.5 D4:1
    [(65, 2), (65, 1)],                   # F4:2   F4:1
    [(60, 2), (62, 1)],                   # C4:2   D4:1
    [(64, 2), (65, 1)],                   # E4:2   F4:1
    [(64, 2), (67, 0.5), (65, 0.5)],      # E4:2   G4:0.5 F4:0.5
    [(64, 2), (62, 1)],                   # E4:2   D4:1
]

# Bars 1-2 and 3-4 are the same shape a step apart, so the harmony sequences too.
# Dm - G is the Dorian move; C - Dm at the end is the bVII - i modal cadence.
THEME_CHORDS = ["Dm", "G", "Am", "F", "C", "Dm", "C", "Dm"]

# Three-note accompaniment voicings, kept in MIDI 48-60 so they sit under the
# melody without crowding it, and the bass root for each.
VOICING = {
    "Dm": ([50, 53, 57], 38),    # D3 F3 A3   / D2
    "G":  ([50, 55, 59], 43),    # D3 G3 B3   / G2   <- the B is the Dorian sixth
    "Am": ([52, 57, 60], 45),    # E3 A3 C4   / A2
    "F":  ([48, 53, 57], 41),    # C3 F3 A3   / F2
    "C":  ([52, 55, 60], 36),    # E3 G3 C4   / C2
}

# The coda: the tune's last two bars, then D settles and rings.
CODA = [
    [(64, 2), (67, 0.5), (65, 0.5)],
    [(64, 2), (62, 1)],
    [(62, 3)],
    [(62, 3)],
]
CODA_CHORDS = ["C", "Dm", "G", "Dm"]

# A counter-line under the octave-up variation, one note per bar.
COUNTER = [50, 55, 52, 53, 48, 50, 52, 50]

INTRO_BARS = 4
SECTIONS = [
    ("Intro", 0, ["Dm", "Dm", "G", "G"], None, 0),
    ("Theme", 4, THEME_CHORDS, 0, 0),
    ("Theme with drums", 12, THEME_CHORDS, 0, 1),
    ("Variation, an octave up", 20, THEME_CHORDS, 12, 1),
    ("Theme returns", 28, THEME_CHORDS, 0, 1),
    ("Coda", 36, CODA_CHORDS, 0, 1),
]
BARS = 40
DRUM_START_BAR = 12
VARIATION_BAR = 20


def bar_plan():
    """(chord, melody-or-None, transpose, drums?) for each of the 40 bars."""
    plan = []
    for name, start, chords, transpose, drums in SECTIONS:
        tune = CODA if name == "Coda" else THEME
        for i, ch in enumerate(chords):
            mel = None if transpose is None else tune[i % len(tune)]
            plan.append((ch, mel, transpose or 0, bool(drums), name))
    return plan


PLAN = bar_plan()
assert len(PLAN) == BARS, len(PLAN)
SECTION_BARS = [s[1] for s in SECTIONS]
SECTION_LABELS = [s[0] for s in SECTIONS]

# ---------------- MIDI ----------------
mid = MIDIFile(4)
mid.addTempo(0, 0, BPM)
mid.addTrackName(0, 0, "Accordion (waltz chords)")
mid.addTrackName(1, 0, "Bass")
mid.addTrackName(2, 0, "Music box")
mid.addTrackName(3, 0, "Drums")
mid.addProgramChange(0, 0, 0, 21)   # accordion
mid.addProgramChange(1, 1, 0, 32)   # acoustic bass
mid.addProgramChange(2, 2, 0, 10)   # music box

for bar, (ch, mel, tr, drums, name) in enumerate(PLAN):
    t = bar * BEATS_PER_BAR
    notes, root = VOICING[ch]
    # oom - pah - pah
    mid.addNote(1, 1, root, t, 0.9, 78)
    for beat in (1, 2):
        for j, n in enumerate(notes):
            mid.addNote(0, 0, n, t + beat + j * 0.02, 0.8, 58 - j * 4)
    if mel:
        pos = 0.0
        for n, d in mel:
            mid.addNote(2, 2, n + tr, t + pos, d * 0.92, 92)
            pos += d
    if bar >= VARIATION_BAR and bar < VARIATION_BAR + 8:
        mid.addNote(1, 1, COUNTER[bar - VARIATION_BAR], t + 1.5, 1.2, 58)

for bar, (ch, mel, tr, drums, name) in enumerate(PLAN):
    t = bar * BEATS_PER_BAR
    for b in range(BEATS_PER_BAR):
        mid.addNote(3, 9, 70, t + b, 0.2, 44 if b else 56)          # shaker
    if drums:
        mid.addNote(3, 9, 36, t, 0.4, 84)                            # felt kick
        for b in (1, 2):
            mid.addNote(3, 9, 38, t + b, 0.3, 60)                    # brush
    if bar in SECTION_BARS:
        mid.addNote(3, 9, 81, t, 1.2, 72)                            # triangle

with open(OUT / "music_box_waltz.mid", "wb") as f:
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

# A struck metal bar is inharmonic: its modes sit near these ratios, not at
# whole-number harmonics. That is what separates a music box from a bell or an
# FM tone, and higher modes die away faster than the fundamental.
BAR_MODES = [(1.00, 1.00), (2.76, 0.42), (5.40, 0.20), (8.93, 0.10)]
_box_cache = {}


def music_box(freq, dur):
    key = (round(freq, 2), round(dur, 3))
    if key in _box_cache:
        return _box_cache[key]
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for ratio, amp in BAR_MODES:
        f = freq * ratio
        if f < SR / 2 * 0.9:
            sig += amp * np.sin(2 * np.pi * f * t) * np.exp(-t * (2.6 + ratio * 1.1))
    sig /= np.max(np.abs(sig))
    strike = rng_d.standard_normal(n) * np.exp(-t * 320) * 0.07
    out_ = (sig + strike) * env(n, 0.001, 0.02, 0.9, 0.25)
    _box_cache[key] = out_
    return out_


def accordion(freq, dur):
    """Reedy and slightly out of tune with itself, with a shallow tremolo — the
    tremolo is applied to amplitude, so there is no phase-modulation trap."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for det in (-0.6, 0.6):
        f = freq * 2 ** (det / 100)
        for h in range(1, 9):
            if f * h < SR / 2 * 0.9:
                sig += np.sin(2 * np.pi * f * h * t) / h ** 1.15
    trem = 1 + 0.06 * np.sin(2 * np.pi * 5.5 * t)
    return lowpass(sig, 3000) * trem * env(n, 0.05, 0.12, 0.8, 0.18)


def waltz_bass(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 2 * t)
           + 0.12 * np.sin(2 * np.pi * freq * 3 * t))
    return lowpass(sig, 1100) * env(n, 0.01, 0.15, 0.55, 0.25)


def kick_felt(dur=0.35):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 100 * np.exp(-t * 24) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 11)


def brush(dur=0.22):
    n = int(dur * SR); t = np.arange(n) / SR
    b, a = butter(2, [1200 / (SR / 2), 6000 / (SR / 2)], btype="band")
    return lfilter(b, a, rng_d.standard_normal(n) * np.exp(-t * 18)) * 0.9


def shaker(dur=0.06):
    n = int(dur * SR); t = np.arange(n) / SR
    b, a = butter(2, 9000 / (SR / 2), btype="high")
    return lfilter(b, a, rng_d.standard_normal(n) * np.exp(-t * 95))


def triangle(dur=1.4):
    """Same inharmonic-bar idea as the music box, pitched high and left to ring."""
    n = int(dur * SR); t = np.arange(n) / SR
    sig = np.zeros(n)
    for ratio, amp in BAR_MODES:
        f = 2100 * ratio
        if f < SR / 2 * 0.9:
            sig += amp * np.sin(2 * np.pi * f * t) * np.exp(-t * (1.8 + ratio * 0.35))
    return sig / np.max(np.abs(sig))


total_sec = BARS * BEATS_PER_BAR * BEAT + 4
out = np.zeros(int(total_sec * SR))
drums = np.zeros_like(out)


def place(buf, sig, start_sec, gain):
    s = int(start_sec * SR)
    e = min(s + len(sig), len(buf))
    buf[s:e] += sig[: e - s] * gain


for bar, (ch, mel, tr, drum_on, name) in enumerate(PLAN):
    t0 = bar * BEATS_PER_BAR * BEAT
    notes, root = VOICING[ch]
    intro = bar < INTRO_BARS
    place(out, waltz_bass(f_of(root), 0.95 * BEAT + 0.15), t0, 0.26 if intro else 0.30)
    for beat in (1, 2):
        for j, n in enumerate(notes):
            place(out, accordion(f_of(n), 0.82 * BEAT + 0.12),
                  t0 + (beat + j * 0.02) * BEAT, 0.055 if intro else 0.075)
    if mel:
        pos = 0.0
        for n, d in mel:
            place(out, music_box(f_of(n + tr), d * BEAT + 0.7), t0 + pos * BEAT, 0.34)
            pos += d
    else:
        # the intro: the music box picks out the chord, one note per beat
        for beat, n in enumerate(notes):
            place(out, music_box(f_of(n + 12), BEAT + 0.7), t0 + beat * BEAT, 0.22)
    if VARIATION_BAR <= bar < VARIATION_BAR + 8:
        place(out, accordion(f_of(COUNTER[bar - VARIATION_BAR]), 1.2 * BEAT + 0.2),
              t0 + 1.5 * BEAT, 0.085)

for bar, (ch, mel, tr, drum_on, name) in enumerate(PLAN):
    t0 = bar * BEATS_PER_BAR * BEAT
    for b in range(BEATS_PER_BAR):
        place(drums, shaker(), t0 + b * BEAT, 0.075 if b == 0 else 0.045)
    if drum_on:
        place(drums, kick_felt(), t0, 0.50)
        for b in (1, 2):
            place(drums, brush(), t0 + b * BEAT, 0.22)
    if bar in SECTION_BARS:
        place(drums, triangle(), t0, 0.10)


def reverb(x):
    """A small bright room — a music box on a shelf, not a hall. At 132 BPM a
    beat is 455 ms, so the longest tap stays well inside one beat and the
    oom-pah-pah keeps its edges."""
    y = x.copy()
    for d_ms, g in ((67, 0.26), (101, 0.21), (151, 0.16), (239, 0.12)):
        d = int(d_ms / 1000 * SR)
        buf = np.zeros_like(x)
        buf[d:] = x[:-d]
        y += lowpass(buf, 5200) * g
    return y


out = reverb(out) + drums * 0.8
out /= np.max(np.abs(out)) * 1.05
fade = int(3 * SR)
out[-fade:] *= np.linspace(1, 0, fade)

wav_path = OUT / "music_box_waltz.wav"
mp3_path = OUT / "music_box_waltz.mp3"
wavfile.write(wav_path, SR, (out * 32767).astype(np.int16))

subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error",
                "-i", str(wav_path), "-b:a", "192k", str(mp3_path)], check=True)

bar_sec = BEATS_PER_BAR * BEAT
(OUT.parent / "structure.json").write_text(json.dumps({
    "bpm": BPM,
    "bars": BARS,
    "beats_per_bar": BEATS_PER_BAR,
    "duration_sec": total_sec,
    "bar_sec": bar_sec,
    "beat_sec": BEAT,
    "section_starts_sec": [b * bar_sec for b in SECTION_BARS],
    "section_labels": SECTION_LABELS,
    "section_keys": ["D dorian"] * len(SECTION_BARS),
    "chords": [p[0] for p in PLAN],
    "drums_in_sec": DRUM_START_BAR * bar_sec,
    "variation_sec": VARIATION_BAR * bar_sec,
    "modulation_sec": None,
    "title": "music box waltz  |  D dorian, 3/4, 132 BPM",
}, indent=2) + "\n")

print(f"done: {total_sec:.2f}s, {BARS} bars of {BEATS_PER_BAR}/4 at {BPM} BPM, "
      f"sections at {', '.join('%.1f' % (b * bar_sec) for b in SECTION_BARS)}")
