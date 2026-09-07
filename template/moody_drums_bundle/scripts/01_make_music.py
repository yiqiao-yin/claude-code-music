import shutil
import subprocess
from pathlib import Path

import numpy as np
from midiutil import MIDIFile
from scipy.io import wavfile
from scipy.signal import butter, lfilter

OUT = Path(__file__).resolve().parent.parent / "assets"
OUT.mkdir(parents=True, exist_ok=True)


def ffmpeg_exe():
    """System ffmpeg if present, else the static binary from imageio-ffmpeg."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    from imageio_ffmpeg import get_ffmpeg_exe
    return get_ffmpeg_exe()


BPM = 68
BEAT = 60.0 / BPM
SR = 44100

# Key of A minor. Progression: Am9 - Fmaj7 - Cmaj7 - Em7 | Am9 - Fmaj7 - Dm7 - E7 (x2)
# Notes as MIDI numbers.
CHORDS = [
    [57, 60, 64, 67, 71],  # Am9
    [53, 57, 60, 64],      # Fmaj7
    [48, 52, 55, 59],      # Cmaj7
    [52, 55, 59, 62],      # Em7
    [57, 60, 64, 67, 71],  # Am9
    [53, 57, 60, 64],      # Fmaj7
    [50, 53, 57, 60],      # Dm7
    [52, 56, 59, 62],      # E7
]
BASS = [45, 41, 36, 40, 45, 41, 38, 40]

# Sparse melody: (start_beat, midi_note, length_beats)
MELODY = [
    (0, 76, 3), (3, 72, 1),
    (4, 74, 2), (6, 72, 1.5), (7.5, 71, 0.5),
    (8, 72, 2), (10, 67, 2),
    (12, 71, 3), (15, 69, 1),
    (16, 76, 2), (18, 79, 1), (19, 77, 1),
    (20, 76, 2), (22, 72, 2),
    (24, 74, 1.5), (25.5, 72, 1.5), (27, 69, 1),
    (28, 68, 3), (31, 71, 1),
]

BARS = len(CHORDS) * 2
BEATS_PER_BAR = 4

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

for rep in range(2):
    for i, ch in enumerate(CHORDS):
        t = (rep * 8 + i) * BEATS_PER_BAR
        for j, n in enumerate(ch):
            mid.addNote(0, 0, n, t + j * 0.08, BEATS_PER_BAR - 0.1, 62 - j * 4)
        mid.addNote(1, 1, BASS[i], t, 2.5, 70)
        mid.addNote(1, 1, BASS[i] + 7, t + 3, 1, 55)
for start, n, ln in MELODY:
    for rep in range(2):
        mid.addNote(2, 2, n, start + rep * 32, ln * 0.95, 80)

# Drum pattern per bar (beats): kick, snare, hats. Drums enter at bar 3.
KICK = [0, 2.5]
SNARE = [1, 3]
HATS = [k * 0.5 for k in range(8)]
DRUM_START_BAR = 2
for bar in range(DRUM_START_BAR, BARS):
    t = bar * BEATS_PER_BAR
    for k in KICK:
        mid.addNote(3, 9, 36, t + k, 0.25, 100)
    for sn in SNARE:
        mid.addNote(3, 9, 38, t + sn, 0.25, 85)
    for h_i, h in enumerate(HATS):
        mid.addNote(3, 9, 42, t + h, 0.2, 60 if h_i % 2 == 0 else 38)
    if bar % 4 == 3:  # small fill on last beat of every 4th bar
        mid.addNote(3, 9, 38, t + 3.5, 0.15, 70)
        mid.addNote(3, 9, 38, t + 3.75, 0.15, 80)

with open(OUT / "moody_drums.mid", "wb") as f:
    mid.writeFile(f)

# ---------------- Synthesis ----------------
def f_of(n):
    return 440.0 * 2 ** ((n - 69) / 12)

def env(n_samp, a, d, s, r, total):
    t = np.arange(n_samp) / SR
    e = np.ones(n_samp) * s
    a_n = int(a * SR); d_n = int(d * SR); r_n = int(r * SR)
    e[:a_n] = np.linspace(0, 1, a_n)
    e[a_n:a_n + d_n] = np.linspace(1, s, d_n)
    if r_n < n_samp:
        e[-r_n:] *= np.linspace(1, 0, r_n)
    return e

def lowpass(x, cutoff, order=2):
    b, a = butter(order, cutoff / (SR / 2))
    return lfilter(b, a, x)

def pad_voice(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for det in (-0.4, 0, 0.4):
        f = freq * 2 ** (det / 100)
        # soft saw (few harmonics)
        for h in range(1, 6):
            sig += np.sin(2 * np.pi * f * h * t) / (h ** 1.6)
    sig *= env(n, 0.9, 0.5, 0.7, 1.2, dur)
    return lowpass(sig, 1400)

def bass_voice(freq, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 2 * t)
    return sig * env(n, 0.02, 0.3, 0.6, 0.4, dur)

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
    return sig * env(n, 0.08, 0.3, 0.75, 0.5, dur)

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
    b, a = butter(2, [1500 / (SR/2), 7000 / (SR/2)], btype="band")
    noise = lfilter(b, a, noise)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 28)
    return noise * 0.8 + tone * 0.6

def hat(dur=0.09):
    n = int(dur * SR); t = np.arange(n) / SR
    noise = rng_d.standard_normal(n) * np.exp(-t * 60)
    b, a = butter(2, 7000 / (SR/2), btype="high")
    return lfilter(b, a, noise)

rng_d = np.random.default_rng(3)
total_sec = BARS * BEATS_PER_BAR * BEAT + 4
out = np.zeros(int(total_sec * SR))

def place(sig, start_sec, gain):
    s = int(start_sec * SR)
    e = min(s + len(sig), len(out))
    out[s:e] += sig[: e - s] * gain

for rep in range(2):
    for i, ch in enumerate(CHORDS):
        t0 = (rep * 8 + i) * BEATS_PER_BAR * BEAT
        for j, n in enumerate(ch):
            place(pad_voice(f_of(n), BEATS_PER_BAR * BEAT + 1.0), t0 + j * 0.06, 0.05)
        place(bass_voice(f_of(BASS[i]), 2.6 * BEAT), t0, 0.35)
        place(bass_voice(f_of(BASS[i] + 7), 1.1 * BEAT), t0 + 3 * BEAT, 0.22)
for start, n, ln in MELODY:
    for rep in range(2):
        place(lead_voice(f_of(n), ln * BEAT + 0.4), (start + rep * 32) * BEAT, 0.28)

drums = np.zeros_like(out)
def place_d(sig, start_sec, gain):
    s_ = int(start_sec * SR); e_ = min(s_ + len(sig), len(drums))
    drums[s_:e_] += sig[: e_ - s_] * gain
for bar in range(DRUM_START_BAR, BARS):
    t0 = bar * BEATS_PER_BAR * BEAT
    for k in KICK:
        place_d(kick(), t0 + k * BEAT, 0.9)
    for sn in SNARE:
        place_d(snare(), t0 + sn * BEAT, 0.45)
    for h_i, h in enumerate(HATS):
        place_d(hat(), t0 + h * BEAT, 0.16 if h_i % 2 == 0 else 0.09)
    if bar % 4 == 3:
        place_d(snare(0.2), t0 + 3.5 * BEAT, 0.3)
        place_d(snare(0.2), t0 + 3.75 * BEAT, 0.38)

# simple reverb: feedback delays
def reverb(x):
    y = x.copy()
    for d_ms, g in ((97, 0.32), (151, 0.26), (233, 0.2), (389, 0.15)):
        d = int(d_ms / 1000 * SR)
        buf = np.zeros_like(x)
        buf[d:] = x[:-d]
        y += lowpass(buf, 3500) * g
    return y

out = reverb(out) + drums * 0.8
out /= np.max(np.abs(out)) * 1.05
# fade out tail
fade = int(3 * SR)
out[-fade:] *= np.linspace(1, 0, fade)
wav_path = OUT / "moody_drums.wav"
mp3_path = OUT / "moody_drums.mp3"
wavfile.write(wav_path, SR, (out * 32767).astype(np.int16))

subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error",
                "-i", str(wav_path), "-b:a", "192k", str(mp3_path)], check=True)

print("done", total_sec)
