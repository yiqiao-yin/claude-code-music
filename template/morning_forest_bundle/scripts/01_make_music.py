"""Compose and synthesize "morning forest".

Same framework as the other bundles: symbolic composition to MIDI, numerical
synthesis to WAV, MP3 transcode, structure.json handoff. No AI audio anywhere.

Form: 40 bars at 112 BPM, five 8-bar sections following an arch —
  bars  1-8   C major   home, entering
  bars  9-16  D major   up
  bars 17-24  C major   and down
  bars 25-32  E major   up more (the peak)
  bars 33-40  C major   back down, resolving

Each modulation is prepared: bar 8 of every section is replaced by the dominant
seventh of the key the next section lands in, so the arch steps rather than jumps.
"""

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from midiutil import MIDIFile
from scipy.io import wavfile
from scipy.signal import butter, lfilter

BPM = 112
BEAT = 60.0 / BPM
SR = 44100
BEATS_PER_BAR = 4

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
# The C major cycle, on the C - G - Am axis. Voicings are open and sit high
# (MIDI 50-74) with no low thirds, which is what makes it read as "clear"
# rather than "warm".
BASE = [
    [60, 64, 67, 71, 74],  # Cmaj9        C E G B D
    [55, 59, 64, 69],      # G6/9         G B E A
    [57, 60, 64, 67],      # Am7          A C E G
    [53, 57, 60, 64, 71],  # Fmaj7(#11)   F A C E B  <- the B is the sparkle
    [60, 64, 67, 71, 74],  # Cmaj9
    [55, 59, 64, 69],      # G6/9
    [50, 53, 57, 60, 64],  # Dm9          D F A C E
    [55, 59, 64, 69],      # G6/9         (replaced by a pivot, see below)
]
BASE_BASS = [36, 43, 45, 41, 36, 43, 38, 43]

# Bar 8 of each section: the dominant of wherever we are going next. These are
# absolute chords, not transposed with the section.
PIVOTS = [
    ([57, 61, 64, 67], 45),   # A7 -> D major
    ([55, 59, 62, 65], 43),   # G7 -> C major
    ([59, 63, 66, 69], 47),   # B7 -> E major
    ([55, 59, 62, 65], 43),   # G7 -> C major
    ([60, 64, 67, 71, 74], 36),  # Cmaj9 — the piece lands home
]

# The arch. One transpose per 8-bar section: home, up, down, up more, down.
ARCH = [0, 2, 0, 4, 0]


def section(idx):
    """(chords, bass) for section idx, with the pivot substituted into bar 8."""
    tr = ARCH[idx]
    chords = [[n + tr for n in ch] for ch in BASE[:7]]
    bass = [b + tr for b in BASE_BASS[:7]]
    pivot_chord, pivot_bass = PIVOTS[idx]
    return chords + [pivot_chord], bass + [pivot_bass]


SECTIONS = [section(i) for i in range(len(ARCH))]
BARS = len(SECTIONS) * 8

# Melody covers beats 0-28 only. The last bar of every section is a rest — the
# breath before the key change, and what keeps the piece feeling airy.
MELODY = [
    (0, 76, 1.5), (1.5, 79, 0.5), (2, 84, 2),
    (4, 83, 1), (5, 81, 1), (6, 79, 2),
    (8, 76, 1), (9, 81, 1), (10, 79, 2),
    (12, 77, 1.5), (13.5, 76, 0.5), (14, 74, 2),
    (16, 72, 1), (17, 76, 1), (18, 79, 2),
    (20, 79, 1), (21, 83, 1), (22, 86, 2),
    (24, 84, 1.5), (25.5, 81, 0.5), (26, 79, 2),
]

# Drums: a light kit. Footstep kick, rim instead of snare, shaker instead of
# hats. The shaker runs from bar 1; the pulse joins at bar 5.
KICK = [0, 2]
RIM = [1, 3]
SHAKER = [k * 0.5 for k in range(8)]
PULSE_START_BAR = 4
PEAK_SECTION = 3               # brush snare only in the E major section

# ---------------- MIDI ----------------
mid = MIDIFile(4)
mid.addTempo(0, 0, BPM)
mid.addTrackName(0, 0, "Pad+Arp")
mid.addTrackName(1, 0, "Bass")
mid.addTrackName(2, 0, "Lead")
mid.addTrackName(3, 0, "Drums")
mid.addProgramChange(0, 0, 0, 11)   # vibraphone
mid.addProgramChange(1, 1, 0, 32)   # acoustic bass
mid.addProgramChange(2, 2, 0, 9)    # glockenspiel


def arp_notes(ch):
    """Eight 8th-note steps up and back down through the chord, an octave above
    the pad voicing. The octave offset is not only for register: pad and arp
    share MIDI track 0 / channel 0, and midiutil cannot serialize two overlapping
    notes of the same pitch on the same channel. No voicing here contains a note
    12 semitones below another, so +12 guarantees no collision."""
    tones = [n + 12 for n in ch]
    seq = list(range(len(tones))) + list(range(len(tones) - 2, 0, -1))
    return [tones[seq[j % len(seq)]] for j in range(8)]


for s, (chords, bass) in enumerate(SECTIONS):
    for i, ch in enumerate(chords):
        t = (s * 8 + i) * BEATS_PER_BAR
        for j, n in enumerate(ch):
            mid.addNote(0, 0, n, t + j * 0.05, BEATS_PER_BAR - 0.1, 46 - j * 3)
        for j, n in enumerate(arp_notes(ch)):
            mid.addNote(0, 0, n, t + j * 0.5, 0.45, 58 if j % 2 == 0 else 44)
        mid.addNote(1, 1, bass[i], t, 2.5, 70)
        mid.addNote(1, 1, bass[i] + 7, t + 3, 1, 55)

for s, tr in enumerate(ARCH):
    for start, n, ln in MELODY:
        mid.addNote(2, 2, n + tr, start + s * 32, ln * 0.95, 82)

for bar in range(BARS):
    t = bar * BEATS_PER_BAR
    for h_i, h in enumerate(SHAKER):
        mid.addNote(3, 9, 70, t + h, 0.2, 58 if h_i % 2 == 0 else 40)
    if bar >= PULSE_START_BAR:
        for k in KICK:
            mid.addNote(3, 9, 36, t + k, 0.25, 88)
        for r in RIM:
            mid.addNote(3, 9, 37, t + r, 0.15, 72)
        if bar // 8 == PEAK_SECTION:
            for r in RIM:
                mid.addNote(3, 9, 38, t + r, 0.25, 70)
        if bar % 8 == 7:
            mid.addNote(3, 9, 37, t + 3.5, 0.1, 60)
            mid.addNote(3, 9, 37, t + 3.75, 0.1, 76)

with open(OUT / "morning_forest.mid", "wb") as f:
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

_pluck_cache = {}


def pluck(freq, dur):
    """Karplus-Strong. Cached per (pitch, duration) — the arpeggio repeats the
    same pitches hundreds of times and the loop is pure Python."""
    key = (round(freq, 2), round(dur, 3))
    if key in _pluck_cache:
        return _pluck_cache[key]
    n = int(dur * SR)
    L = max(2, int(SR / freq))
    buf = rng_d.standard_normal(L)
    out_ = np.zeros(n)
    for i in range(n):
        out_[i] = buf[i % L]
        buf[i % L] = 0.5 * (buf[i % L] + buf[(i + 1) % L]) * 0.996
    out_ /= np.max(np.abs(out_))
    out_ = lowpass(out_, 5000) * env(n, 0.001, 0.05, 0.8, dur * 0.5)
    _pluck_cache[key] = out_
    return out_


def sweep_pad(freq, dur, f0=500, f1=3200):
    """Bed pad whose filter opens across the note — light coming up."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for det in (-0.3, 0.3):
        f = freq * 2 ** (det / 100)
        for h in range(1, 8):
            sig += np.sin(2 * np.pi * f * h * t) / h ** 1.4
    lo, hi = lowpass(sig, f0), lowpass(sig, f1)
    m = np.linspace(0, 1, n)
    return (lo * (1 - m) + hi * m) * env(n, 0.7, 0.5, 0.65, 1.0)


def bell_lead(freq, dur):
    """FM bell attack over a sustaining sine core: crisp onset, singing tail."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    mod = np.sin(2 * np.pi * freq * 3 * t) * 4 * np.exp(-t * 5)
    strike = np.sin(2 * np.pi * freq * t + mod) * np.exp(-t * 1.8)
    body = np.sin(2 * np.pi * freq * t) * env(n, 0.02, 0.25, 0.5, 0.35)
    return strike * 0.7 + body * 0.5


def bass_voice(freq, dur, drive=1.3):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.tanh(np.sin(2 * np.pi * freq * t) * drive) + 0.18 * np.sin(2 * np.pi * freq * 2 * t)
    return sig * env(n, 0.02, 0.25, 0.6, 0.35)


def kick_soft(dur=0.4):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 120 * np.exp(-t * 20) + 44
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def rim(dur=0.06):
    n = int(dur * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 400 * t) * np.exp(-t * 90)
            + rng_d.standard_normal(n) * np.exp(-t * 300) * 0.4)


def shaker(dur=0.07):
    n = int(dur * SR); t = np.arange(n) / SR
    b, a = butter(2, 9000 / (SR / 2), btype="high")
    return lfilter(b, a, rng_d.standard_normal(n) * np.exp(-t * 80))


def snare_brush(dur=0.45):
    n = int(dur * SR); t = np.arange(n) / SR
    b, a = butter(2, [900 / (SR / 2), 4500 / (SR / 2)], btype="band")
    return lfilter(b, a, rng_d.standard_normal(n) * np.exp(-t * 7)) * 0.9


total_sec = BARS * BEATS_PER_BAR * BEAT + 4
out = np.zeros(int(total_sec * SR))
drums = np.zeros_like(out)


def place(buf, sig, start_sec, gain):
    s = int(start_sec * SR)
    e = min(s + len(sig), len(buf))
    buf[s:e] += sig[: e - s] * gain


for s, (chords, bass) in enumerate(SECTIONS):
    for i, ch in enumerate(chords):
        t0 = (s * 8 + i) * BEATS_PER_BAR * BEAT
        for j, n in enumerate(ch):
            place(out, sweep_pad(f_of(n), BEATS_PER_BAR * BEAT + 1.0), t0 + j * 0.04, 0.025)
        for j, n in enumerate(arp_notes(ch)):
            place(out, pluck(f_of(n), 0.45), t0 + j * 0.5 * BEAT, 0.075 if j % 2 == 0 else 0.055)
        place(out, bass_voice(f_of(bass[i]), 2.6 * BEAT), t0, 0.32)
        place(out, bass_voice(f_of(bass[i] + 7), 1.1 * BEAT), t0 + 3 * BEAT, 0.20)

for s, tr in enumerate(ARCH):
    for start, n, ln in MELODY:
        place(out, bell_lead(f_of(n + tr), ln * BEAT + 0.5), (start + s * 32) * BEAT, 0.30)

for bar in range(BARS):
    t0 = bar * BEATS_PER_BAR * BEAT
    for h_i, h in enumerate(SHAKER):
        place(drums, shaker(), t0 + h * BEAT, 0.10 if h_i % 2 == 0 else 0.055)
    if bar >= PULSE_START_BAR:
        for k in KICK:
            place(drums, kick_soft(), t0 + k * BEAT, 0.55)
        for r in RIM:
            place(drums, rim(), t0 + r * BEAT, 0.35)
        if bar // 8 == PEAK_SECTION:
            for r in RIM:
                place(drums, snare_brush(), t0 + r * BEAT, 0.22)
        if bar % 8 == 7:
            place(drums, rim(), t0 + 3.5 * BEAT, 0.22)
            place(drums, rim(), t0 + 3.75 * BEAT, 0.32)


def reverb(x):
    """Short and bright — an open clearing, not a cathedral. Longest tap
    (181 ms) is well under one beat (536 ms) so the pulse stays clean."""
    y = x.copy()
    for d_ms, g in ((53, 0.22), (79, 0.18), (113, 0.14), (181, 0.10)):
        d = int(d_ms / 1000 * SR)
        buf = np.zeros_like(x)
        buf[d:] = x[:-d]
        y += lowpass(buf, 6000) * g
    return y


out = reverb(out) + drums * 0.8
out /= np.max(np.abs(out)) * 1.05
fade = int(3 * SR)
out[-fade:] *= np.linspace(1, 0, fade)

wav_path = OUT / "morning_forest.wav"
mp3_path = OUT / "morning_forest.mp3"
wavfile.write(wav_path, SR, (out * 32767).astype(np.int16))

subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error",
                "-i", str(wav_path), "-b:a", "192k", str(mp3_path)], check=True)

sec_starts = [s * 8 * BEATS_PER_BAR * BEAT for s in range(len(ARCH))]
(OUT.parent / "structure.json").write_text(json.dumps({
    "bpm": BPM,
    "bars": BARS,
    "beats_per_bar": BEATS_PER_BAR,
    "duration_sec": total_sec,
    "section_starts_sec": sec_starts,
    "section_transpose": ARCH,
    "section_keys": ["C major", "D major", "C major", "E major", "C major"],
    "modulation_sec": None,
    "peak_sec": sec_starts[PEAK_SECTION],
    "title": "morning forest  |  C major, arch to E and back, 112 BPM",
}, indent=2) + "\n")

print(f"done: {total_sec:.2f}s, {BARS} bars, sections at "
      f"{', '.join('%.1f' % s for s in sec_starts)}")
