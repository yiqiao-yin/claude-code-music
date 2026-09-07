"""Compose and synthesize "simple bach tune".

Same framework as the other bundles: symbolic composition to MIDI, numerical
synthesis to WAV, MP3 transcode, structure.json handoff. No AI audio anywhere.

The figure is the one from Bach's Prelude in C, BWV 846: a five-note broken
chord played root - 3rd - 5th - 8ve - 10th, then the upper three again, and the
whole eight-note group twice per bar in 16th notes.

    bar of C:  C4 E4 G4 C5 E5 G4 C5 E5  |  C4 E4 G4 C5 E5 G4 C5 E5

Form: 16 bars at 72 BPM, four 4-bar phrases, never leaving C major —
  bars  1-4   C   Dm  G/B   C     the statement
  bars  5-8   Am  Dm  G     C     first descending-fifths chain
  bars  9-12  F   B°  Em    Am    second chain, the low point
  bars 13-16  Dm  G7  C     C     cadence home

Every chord change is a fifth down or a step, and the whole thing is white keys.
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
    """System ffmpeg if present, else the static binary from imageio-ffmpeg."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    from imageio_ffmpeg import get_ffmpeg_exe
    return get_ffmpeg_exe()


# ---------------- Musical material ----------------
# One five-note cell per bar, ascending. The figure indexes into it.
CELLS = [
    [60, 64, 67, 72, 76],  #  1 C      C4 E4 G4 C5 E5
    [62, 65, 69, 74, 77],  #  2 Dm     D4 F4 A4 D5 F5
    [59, 62, 67, 71, 74],  #  3 G/B    B3 D4 G4 B4 D5  (V in first inversion;
                           #           the seventh is held back until bar 14)
    [60, 64, 67, 72, 76],  #  4 C
    [57, 60, 64, 69, 72],  #  5 Am     A3 C4 E4 A4 C5
    [62, 65, 69, 74, 77],  #  6 Dm
    [55, 59, 62, 67, 71],  #  7 G      G3 B3 D4 G4 B4
    [60, 64, 67, 72, 76],  #  8 C
    [53, 57, 60, 65, 69],  #  9 F      F3 A3 C4 F4 A4
    [59, 62, 65, 71, 74],  # 10 Bdim   B3 D4 F4 B4 D5
    [52, 55, 59, 64, 67],  # 11 Em     E3 G3 B3 E4 G4
    [57, 60, 64, 69, 72],  # 12 Am
    [62, 65, 69, 74, 77],  # 13 Dm
    [55, 59, 62, 65, 71],  # 14 G7     G3 B3 D4 F4 B4
    [60, 64, 67, 72, 76],  # 15 C
    [60, 64, 67, 72, 76],  # 16 C
]
CHORD_NAMES = ["C", "Dm", "G/B", "C", "Am", "Dm", "G", "C",
               "F", "Bdim", "Em", "Am", "Dm", "G7", "C", "C"]

# The figure: root, 3rd, 5th, 8ve, 10th, then the upper three again.
# Played twice per bar, sixteen 16th notes in all.
FIGURE = [0, 1, 2, 3, 4, 2, 3, 4]
STEPS_PER_BAR = 16
STEP = 0.25            # beats per 16th

# Continuo: the root of each chord an octave below the cell. Bar 3 and bar 10
# are inversions — G/B and Bdim both take B as their bass, which is the point
# of the voicing.
BASS = [c[0] - 12 for c in CELLS]

# An upper voice entering with the second phrase: one held note per bar,
# alternating between the fifth and the root of each chord so it forms a
# stepwise descent E-D-D-C-C-B-B-A-A and then climbs home.
UPPER = {
    4: 76, 5: 74, 6: 74, 7: 72,       # E5 D5 D5 C5
    8: 72, 9: 71, 10: 71, 11: 69,     # C5 B4 B4 A4
    12: 69, 13: 71, 14: 72, 15: 76,   # A4 B4 C5 E5
}

# Drums: a light pulse well behind the counterpoint. Shaker joins for the
# second half of the opening phrase, the kit at the top of phrase two.
KICK = [0, 2]
RIM = [1, 3]
SHAKER = [k * 0.5 for k in range(8)]
SHAKER_START_BAR = 2
DRUM_START_BAR = 4

BARS = len(CELLS)
PHRASE = 4
SECTION_STARTS = [b * BEATS_PER_BAR * BEAT for b in range(0, BARS, PHRASE)]

# ---------------- MIDI ----------------
mid = MIDIFile(4)
mid.addTempo(0, 0, BPM)
mid.addTrackName(0, 0, "Harpsichord")
mid.addTrackName(1, 0, "Continuo")
mid.addTrackName(2, 0, "Upper voice")
mid.addTrackName(3, 0, "Drums")
mid.addProgramChange(0, 0, 0, 6)    # harpsichord
mid.addProgramChange(1, 1, 0, 42)   # cello
mid.addProgramChange(2, 2, 0, 40)   # violin

for bar, cell in enumerate(CELLS):
    t = bar * BEATS_PER_BAR
    for j in range(STEPS_PER_BAR):
        n = cell[FIGURE[j % len(FIGURE)]]
        vel = 74 if j % 8 == 0 else (66 if j % 4 == 0 else 58)
        mid.addNote(0, 0, n, t + j * STEP, STEP - 0.01, vel)
    mid.addNote(1, 1, BASS[bar], t, BEATS_PER_BAR - 0.2, 68)
    if bar in UPPER:
        mid.addNote(2, 2, UPPER[bar], t, BEATS_PER_BAR - 0.1, 66)

for bar in range(BARS):
    t = bar * BEATS_PER_BAR
    if bar >= SHAKER_START_BAR:
        for h_i, h in enumerate(SHAKER):
            mid.addNote(3, 9, 70, t + h, 0.2, 54 if h_i % 2 == 0 else 38)
    if bar >= DRUM_START_BAR:
        for k in KICK:
            mid.addNote(3, 9, 36, t + k, 0.25, 82)
        for r in RIM:
            mid.addNote(3, 9, 37, t + r, 0.15, 68)
        if bar % PHRASE == PHRASE - 1:
            mid.addNote(3, 9, 37, t + 3.5, 0.1, 58)
            mid.addNote(3, 9, 37, t + 3.75, 0.1, 74)

with open(OUT / "simple_bach_tune.mid", "wb") as f:
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

_harp_cache = {}


def harpsichord(freq, dur=0.9):
    """Bright plucked-string tone: twelve harmonics rolling off slowly at
    1/h**0.75, an exponential body decay, and a short noise burst standing in
    for the quill. Cached — the figure repeats the same pitches all piece."""
    key = round(freq, 2)
    if key in _harp_cache:
        return _harp_cache[key]
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for h in range(1, 13):
        if freq * h < SR / 2 * 0.9:
            sig += np.sin(2 * np.pi * freq * h * t) / h ** 0.75
    sig /= np.max(np.abs(sig))
    quill = rng_d.standard_normal(n) * np.exp(-t * 250) * 0.18
    out_ = (sig * np.exp(-t * 3.2) + quill) * env(n, 0.002, 0.02, 0.9, 0.15)
    _harp_cache[key] = out_
    return out_


def continuo(freq, dur):
    """Bowed low voice under the figure — six harmonics, soft attack."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = sum(np.sin(2 * np.pi * freq * h * t) / h ** 1.2 for h in range(1, 7))
    return lowpass(sig, 1300) * env(n, 0.06, 0.3, 0.7, 0.5)


def viol(freq, dur):
    """Sustained upper voice: eight harmonics, gentle 4.5 Hz vibrato easing in.

    The vibrato integrates frequency to phase with cumsum rather than scaling
    `t` inside the sine. Writing `sin(2*pi*f*h*vib*t)` looks equivalent but
    modulates phase, so the instantaneous frequency picks up a `t * dvib/dt`
    term that grows without bound — on these 3.7 s notes that is a ~30 percent
    pitch deviation instead of the intended 0.3 percent."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    vib = 1 + 0.003 * np.sin(2 * np.pi * 4.5 * t) * np.minimum(t / 0.8, 1)
    sig = np.zeros(n)
    for h in range(1, 9):
        phase = 2 * np.pi * np.cumsum(freq * h * vib) / SR
        sig += np.sin(phase) / h ** 1.1
    return lowpass(sig, 2600) * env(n, 0.15, 0.35, 0.75, 0.6)


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


total_sec = BARS * BEATS_PER_BAR * BEAT + 4
out = np.zeros(int(total_sec * SR))
drums = np.zeros_like(out)


def place(buf, sig, start_sec, gain):
    s = int(start_sec * SR)
    e = min(s + len(sig), len(buf))
    buf[s:e] += sig[: e - s] * gain


for bar, cell in enumerate(CELLS):
    t0 = bar * BEATS_PER_BAR * BEAT
    for j in range(STEPS_PER_BAR):
        n = cell[FIGURE[j % len(FIGURE)]]
        g = 0.30 if j % 8 == 0 else (0.26 if j % 4 == 0 else 0.22)
        place(out, harpsichord(f_of(n)), t0 + j * STEP * BEAT, g)
    place(out, continuo(f_of(BASS[bar]), BEATS_PER_BAR * BEAT + 0.3), t0, 0.30)
    if bar in UPPER:
        place(out, viol(f_of(UPPER[bar]), BEATS_PER_BAR * BEAT + 0.4), t0, 0.17)

for bar in range(BARS):
    t0 = bar * BEATS_PER_BAR * BEAT
    if bar >= SHAKER_START_BAR:
        for h_i, h in enumerate(SHAKER):
            place(drums, shaker(), t0 + h * BEAT, 0.085 if h_i % 2 == 0 else 0.05)
    if bar >= DRUM_START_BAR:
        for k in KICK:
            place(drums, kick_soft(), t0 + k * BEAT, 0.45)
        for r in RIM:
            place(drums, rim(), t0 + r * BEAT, 0.30)
        if bar % PHRASE == PHRASE - 1:
            place(drums, rim(), t0 + 3.5 * BEAT, 0.20)
            place(drums, rim(), t0 + 3.75 * BEAT, 0.28)


def reverb(x):
    """A stone room. Longer than morning forest, shorter than moody's
    cathedral; the longest tap (331 ms) stays well under one beat (833 ms) so
    the 16th notes never smear into each other."""
    y = x.copy()
    for d_ms, g in ((89, 0.28), (137, 0.22), (211, 0.17), (331, 0.12)):
        d = int(d_ms / 1000 * SR)
        buf = np.zeros_like(x)
        buf[d:] = x[:-d]
        y += lowpass(buf, 4000) * g
    return y


out = reverb(out) + drums * 0.8
out /= np.max(np.abs(out)) * 1.05
fade = int(3 * SR)
out[-fade:] *= np.linspace(1, 0, fade)

wav_path = OUT / "simple_bach_tune.wav"
mp3_path = OUT / "simple_bach_tune.mp3"
wavfile.write(wav_path, SR, (out * 32767).astype(np.int16))

subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error",
                "-i", str(wav_path), "-b:a", "192k", str(mp3_path)], check=True)

(OUT.parent / "structure.json").write_text(json.dumps({
    "bpm": BPM,
    "bars": BARS,
    "beats_per_bar": BEATS_PER_BAR,
    "duration_sec": total_sec,
    "section_starts_sec": SECTION_STARTS,
    "section_keys": ["C major"] * len(SECTION_STARTS),
    "chords": CHORD_NAMES,
    "bar_sec": BEATS_PER_BAR * BEAT,
    "drums_in_sec": DRUM_START_BAR * BEATS_PER_BAR * BEAT,
    "modulation_sec": None,
    "title": "simple bach tune  |  C major, 72 BPM",
}, indent=2) + "\n")

print(f"done: {total_sec:.2f}s, {BARS} bars, phrases at "
      f"{', '.join('%.1f' % s for s in SECTION_STARTS)}, drums in at "
      f"{DRUM_START_BAR * BEATS_PER_BAR * BEAT:.1f}s")
