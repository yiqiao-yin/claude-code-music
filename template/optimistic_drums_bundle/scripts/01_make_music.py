"""Compose and synthesize "optimistic drums".

Same framework as template/moody_drums_bundle: symbolic composition to MIDI,
then numerical synthesis to WAV, then an MP3 transcode. No AI audio anywhere.

Form: 24 bars at 104 BPM.
  bars  1-8   G major cycle
  bars  9-16  G major cycle (drums fully in)
  bars 17-24  the same cycle transposed up to C major  <- the lift
"""

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from midiutil import MIDIFile
from scipy.io import wavfile
from scipy.signal import butter, lfilter

BPM = 104
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
# G major cycle: Gmaj9 - Em7 - Cmaj7 - D6/9 | Gmaj9 - Bm7 - Am7 - D7
CHORDS_G = [
    [55, 59, 62, 66, 69],  # Gmaj9   G B D F# A
    [52, 55, 59, 62],      # Em7     E G B D
    [48, 52, 55, 59],      # Cmaj7   C E G B
    [50, 54, 57, 59, 64],  # D6/9    D F# A B E
    [55, 59, 62, 66, 69],  # Gmaj9
    [50, 54, 57, 59],      # Bm7     (D F# A B over a B root)
    [57, 60, 64, 67],      # Am7     A C E G
    [50, 54, 57, 60],      # D7      D F# A C
]
BASS_G = [43, 40, 36, 38, 43, 47, 45, 38]

# C major cycle: the same voicings a fourth up. Cmaj9 - Am7 - Fmaj7 - G6/9 | ...
CHORDS_C = [[n + 5 for n in ch] for ch in CHORDS_G]
BASS_C = [36, 45, 41, 43, 36, 40, 38, 43]

# Sparse, rising melody over the G cycle: (start_beat, midi_note, length_beats)
MELODY = [
    (0, 74, 1), (1, 76, 1), (2, 79, 2),
    (4, 78, 1.5), (5.5, 76, 0.5), (6, 74, 2),
    (8, 71, 1), (9, 74, 1), (10, 76, 2),
    (12, 78, 1), (13, 79, 1), (14, 81, 2),
    (16, 79, 1), (17, 78, 1), (18, 76, 2),
    (20, 74, 1), (21, 76, 1), (22, 79, 2),
    (24, 81, 1.5), (25.5, 79, 0.5), (26, 78, 2),
    (28, 76, 1), (29, 74, 1), (30, 71, 2),
]

# (chords, bass, melody transpose) per 8-bar section.
SECTIONS = [
    (CHORDS_G, BASS_G, 0),
    (CHORDS_G, BASS_G, 0),
    (CHORDS_C, BASS_C, 5),
]
BARS = len(SECTIONS) * 8
MOD_BAR = 16              # bar index where the key change lands
MOD_SEC = MOD_BAR * BEATS_PER_BAR * BEAT

# Drums: straight backbeat with a push on the "and" of 2. Enter at bar 3.
KICK = [0, 1.5, 2.5]
SNARE = [1, 3]
HATS = [k * 0.5 for k in range(8)]
DRUM_START_BAR = 2
OPEN_HAT_BARS = [2, 8, 16]     # section markers, incl. the modulation

# ---------------- MIDI ----------------
mid = MIDIFile(4)
mid.addTempo(0, 0, BPM)
mid.addTrackName(0, 0, "Pad")
mid.addTrackName(1, 0, "Bass")
mid.addTrackName(2, 0, "Lead")
mid.addTrackName(3, 0, "Drums")
mid.addProgramChange(0, 0, 0, 0)    # piano
mid.addProgramChange(1, 1, 0, 32)   # acoustic bass
mid.addProgramChange(2, 2, 0, 73)   # flute

for s, (chords, bass, _) in enumerate(SECTIONS):
    for i, ch in enumerate(chords):
        t = (s * 8 + i) * BEATS_PER_BAR
        for j, n in enumerate(ch):
            mid.addNote(0, 0, n, t + j * 0.08, BEATS_PER_BAR - 0.1, 62 - j * 4)
        mid.addNote(1, 1, bass[i], t, 2.5, 70)
        mid.addNote(1, 1, bass[i] + 7, t + 3, 1, 55)

for s, (_, _, tr) in enumerate(SECTIONS):
    for start, n, ln in MELODY:
        mid.addNote(2, 2, n + tr, start + s * 32, ln * 0.95, 80)

for bar in range(DRUM_START_BAR, BARS):
    t = bar * BEATS_PER_BAR
    for k in KICK:
        mid.addNote(3, 9, 36, t + k, 0.25, 100)
    for sn in SNARE:
        mid.addNote(3, 9, 38, t + sn, 0.25, 85)
    for h_i, h in enumerate(HATS):
        mid.addNote(3, 9, 42, t + h, 0.2, 62 if h_i % 2 == 0 else 40)
    if bar % 4 == 3:  # small fill on the last beat of every 4th bar
        mid.addNote(3, 9, 38, t + 3.5, 0.15, 70)
        mid.addNote(3, 9, 38, t + 3.75, 0.15, 80)
    if bar in OPEN_HAT_BARS:
        mid.addNote(3, 9, 46, t, 0.5, 90)

with open(OUT / "optimistic_drums.mid", "wb") as f:
    mid.writeFile(f)


# ---------------- Synthesis ----------------
def f_of(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def env(n_samp, a, d, s, r):
    """Linear ADSR over n_samp samples. Segments are clamped so short notes
    never wrap around (the moody template assumed a + d + r < duration)."""
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


def pad_voice(freq, dur):
    # Brighter and quicker to speak than the moody pad: shorter attack,
    # 2200 Hz cutoff instead of 1400 Hz.
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for det in (-0.4, 0, 0.4):
        f = freq * 2 ** (det / 100)
        for h in range(1, 6):
            sig += np.sin(2 * np.pi * f * h * t) / (h ** 1.6)
    sig *= env(n, 0.5, 0.4, 0.7, 0.8)
    return lowpass(sig, 2200)


def bass_voice(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 2 * t)
    return sig * env(n, 0.02, 0.3, 0.6, 0.4)


def lead_voice(freq, dur):
    """Sine plus a third harmonic, with a 5 Hz vibrato easing in over 0.6 s.

    The vibrato integrates frequency to phase with cumsum. The original form,
    `sin(2*pi * freq * vib * t)`, modulates phase instead: the instantaneous
    frequency gains a `t * dvib/dt` term that grows without bound, turning an
    intended +-7 cents into 14.4 semitones of swing on a 1 s note and 23.6 on a
    3 s note."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5 * t) * np.minimum(t / 0.6, 1)
    ph = 2 * np.pi * np.cumsum(freq * vib) / SR
    sig = np.sin(ph) + 0.15 * np.sin(3 * ph)
    return sig * env(n, 0.06, 0.3, 0.75, 0.4)


rng_d = np.random.default_rng(3)


def kick(dur=0.45):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 150 * np.exp(-t * 18) + 45          # pitch sweep down
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 7)
    click = rng_d.standard_normal(n) * np.exp(-t * 400) * 0.3
    return body + click


def snare(dur=0.3):
    n = int(dur * SR); t = np.arange(n) / SR
    noise = rng_d.standard_normal(n) * np.exp(-t * 16)
    b, a = butter(2, [1500 / (SR / 2), 7000 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 28)
    return noise * 0.8 + tone * 0.6


def hat(dur=0.09):
    n = int(dur * SR); t = np.arange(n) / SR
    noise = rng_d.standard_normal(n) * np.exp(-t * 60)
    b, a = butter(2, 7000 / (SR / 2), btype="high")
    return lfilter(b, a, noise)


def open_hat(dur=0.45):
    n = int(dur * SR); t = np.arange(n) / SR
    noise = rng_d.standard_normal(n) * np.exp(-t * 7)
    b, a = butter(2, 6000 / (SR / 2), btype="high")
    return lfilter(b, a, noise)


total_sec = BARS * BEATS_PER_BAR * BEAT + 4
out = np.zeros(int(total_sec * SR))
drums = np.zeros_like(out)


def place(buf, sig, start_sec, gain):
    s = int(start_sec * SR)
    e = min(s + len(sig), len(buf))
    buf[s:e] += sig[: e - s] * gain


for s, (chords, bass, _) in enumerate(SECTIONS):
    for i, ch in enumerate(chords):
        t0 = (s * 8 + i) * BEATS_PER_BAR * BEAT
        for j, n in enumerate(ch):
            place(out, pad_voice(f_of(n), BEATS_PER_BAR * BEAT + 1.0), t0 + j * 0.06, 0.05)
        place(out, bass_voice(f_of(bass[i]), 2.6 * BEAT), t0, 0.35)
        place(out, bass_voice(f_of(bass[i] + 7), 1.1 * BEAT), t0 + 3 * BEAT, 0.22)

for s, (_, _, tr) in enumerate(SECTIONS):
    for start, n, ln in MELODY:
        place(out, lead_voice(f_of(n + tr), ln * BEAT + 0.4), (start + s * 32) * BEAT, 0.28)

for bar in range(DRUM_START_BAR, BARS):
    t0 = bar * BEATS_PER_BAR * BEAT
    for k in KICK:
        place(drums, kick(), t0 + k * BEAT, 0.9)
    for sn in SNARE:
        place(drums, snare(), t0 + sn * BEAT, 0.45)
    for h_i, h in enumerate(HATS):
        place(drums, hat(), t0 + h * BEAT, 0.16 if h_i % 2 == 0 else 0.09)
    if bar % 4 == 3:
        place(drums, snare(0.2), t0 + 3.5 * BEAT, 0.3)
        place(drums, snare(0.2), t0 + 3.75 * BEAT, 0.38)
    if bar in OPEN_HAT_BARS:
        place(drums, open_hat(), t0, 0.13)


def reverb(x):
    """Tighter than the moody template: shorter taps, less of them in the tail."""
    y = x.copy()
    for d_ms, g in ((61, 0.26), (89, 0.20), (127, 0.15), (211, 0.11)):
        d = int(d_ms / 1000 * SR)
        buf = np.zeros_like(x)
        buf[d:] = x[:-d]
        y += lowpass(buf, 4500) * g
    return y


out = reverb(out) + drums * 0.8
out /= np.max(np.abs(out)) * 1.05
fade = int(3 * SR)
out[-fade:] *= np.linspace(1, 0, fade)

wav_path = OUT / "optimistic_drums.wav"
mp3_path = OUT / "optimistic_drums.mp3"
wavfile.write(wav_path, SR, (out * 32767).astype(np.int16))

subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error",
                "-i", str(wav_path), "-b:a", "192k", str(mp3_path)], check=True)

# Hand the musical structure to the video script so it can react to the key
# change without duplicating constants.
(OUT.parent / "structure.json").write_text(json.dumps({
    "bpm": BPM,
    "bars": BARS,
    "beats_per_bar": BEATS_PER_BAR,
    "duration_sec": total_sec,
    "section_starts_sec": [s * 8 * BEATS_PER_BAR * BEAT for s in range(len(SECTIONS))],
    "section_keys": ["G major", "G major", "C major"],
    "modulation_sec": MOD_SEC,
    "title": "optimistic (with drums)  |  G major -> C major, 104 BPM",
}, indent=2) + "\n")

print(f"done: {total_sec:.2f}s, {BARS} bars, modulation at {MOD_SEC:.2f}s")
