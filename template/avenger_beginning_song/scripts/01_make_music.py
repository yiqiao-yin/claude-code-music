"""Compose and synthesize "avenger beginning song".

Same framework as the other bundles: symbolic composition to MIDI, numerical
synthesis to WAV, MP3 transcode, structure.json handoff. No AI audio anywhere.

The score is a two-handed keyboard layout, given note by note. The left hand
plays low power chords with no third (E+B, D+A, C+G) and the right hand plays
triads with the melody on top — the Silvestri fanfare voicing.

Form: 32 bars at 88 BPM, one chord per bar, each hit heavily accented and left
to ring into silence before the next.

  bars  1-14  the arrangement as written: Fanfare, Build-Up, Climax
  bars 15-28  the same again, with a sub-octave under every chord and the
              percussion at full weight
  bars 29-32  the descending run, once, as the ending

The descending run resolves the whole piece, so it is played only after the
restatement rather than at the end of each pass.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
from midiutil import MIDIFile
from scipy.io import wavfile
from scipy.signal import butter, lfilter

# Speed variants. AVENGER_SPEED=4 renders the same score four times faster with
# the pitch untouched: the tempo scales up and every absolute time constant —
# envelopes, decay rates, reverb taps, the tail — scales down by the same factor,
# so the sound keeps its proportions instead of turning to mud. This is a true
# tempo change, not a resample (which would raise the pitch two octaves) and not
# a time-stretch (which would smear these attacks).
SPEED = float(os.environ.get("AVENGER_SPEED", "1"))
SUFFIX = "" if SPEED == 1 else "_%gx" % SPEED
NAME = "avenger_beginning_song" + SUFFIX


def T(x):
    """A duration in seconds, scaled for the current speed."""
    return x / SPEED


def R(x):
    """An exponential decay rate, scaled for the current speed."""
    return x * SPEED


BASE_BPM = 88
BPM = BASE_BPM * SPEED
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
# Each bar is (left hand, right-hand events, melody notes, label).
# A right-hand event is (beat offset, [midi notes]); the pickup bars put their
# single note on beat 3 so it leads into the next downbeat.
# Melody notes are doubled by a horn on their own track.
#
#   E1 28  E2 40  B2 47  D2 38  A1 33  A2 45  E3 52  F#3 54  C2 36  G2 43
#   C3 48  G3 55  B3 59  D4 62  D#4 63  E4 64  F#4 66  G4 67  A4 69  B4 71
#   C5 72  E5 76  A5 81  B5 83

FANFARE = [
    # --- 1. Opening Fanfare ---
    ([40, 47], [(2, [59])],            [],    "E  (pickup)"),
    ([40, 47], [(0, [64, 67, 71])],    [],    "Em"),
    ([40, 47], [(0, [67, 71, 76])],    [],    "Em/G"),
    ([38, 45], [(0, [62, 66, 69])],    [],    "D"),
    # --- 2. The Build-Up ---
    ([40, 47], [(2, [59])],            [],    "E  (pickup)"),
    ([40, 47], [(0, [64, 67, 71])],    [],    "Em"),
    ([40, 47], [(0, [67, 71, 76])],    [],    "Em/G"),
    ([45, 52], [(0, [60, 64, 69])],    [],    "Am/C"),
    ([47, 54], [(0, [63, 66, 71])],    [],    "B/D#"),
    # --- 3. The Climax ---
    ([40, 47], [(2, [59])],            [],    "E  (pickup)"),
    ([40, 47], [(0, [64, 67, 71])],    [],    "Em"),
    ([40, 47], [(0, [67, 71, 76])],    [],    "Em/G"),
    ([48, 55], [(0, [67, 72, 76])],    [83],  "Cmaj7  (peak)"),
    ([38, 45], [(0, [69, 72, 76])],    [81],  "Am/D"),
]

# The descending run. The right hand is a single melody line here, carried by
# the horn, until the final chord.
CODA = [
    ([36, 43], [],                         [67, 66], "C"),
    ([33, 40], [],                         [64],     "Am"),
    ([38, 45], [],                         [62],     "D"),
    ([28, 40], [(0, [64, 67, 71, 76])],    [],       "Em  (smash)"),
]

# Melody notes in the coda are spread across the bar rather than stacked.
CODA_MELODY_BEATS = {0: [0.0, 2.0], 1: [0.0], 2: [0.0], 3: []}

SUB_OCTAVE_FLOOR = 26          # how low the pass-2 doubling is allowed to go


def build_bars():
    """Two passes of the fanfare, then the coda. Pass 2 adds a sub-octave under
    the left hand and under the right-hand chord, which is what 'fuller' means
    here — thickening downward, not stacking higher."""
    bars = []
    for p in (0, 1):
        for lh, rh, mel, label in FANFARE:
            if p == 0:
                bars.append((list(lh), [(b, list(ns)) for b, ns in rh], list(mel), label, 0))
            else:
                lh2 = list(lh)
                if lh[0] - 12 >= SUB_OCTAVE_FLOOR:
                    lh2 = [lh[0] - 12] + lh2
                rh2 = [(b, ([ns[0] - 12] + list(ns)) if b == 0 else list(ns)) for b, ns in rh]
                bars.append((lh2, rh2, list(mel), label, 1))
    for i, (lh, rh, mel, label) in enumerate(CODA):
        bars.append((list(lh), [(b, list(ns)) for b, ns in rh], list(mel), label, 2))
    return bars


BARS_DATA = build_bars()
BARS = len(BARS_DATA)

# Section boundaries, in bars: the three parts of each pass, then the coda.
SECTION_BARS = [0, 4, 9, 14, 18, 23, 28]
SECTION_LABELS = ["Opening Fanfare", "The Build-Up", "The Climax",
                  "Fanfare (restated)", "Build-Up (restated)", "Climax (restated)",
                  "Descending run"]
PEAK_BAR = 26                  # the Cmaj7 peak in the restatement

# Percussion. Timpani is tuned to the pitch class of the left-hand root, placed
# in MIDI 36-47; taiko and cymbal are unpitched.
TAIKO_NOTE, TIMP_NOTE, CYM_NOTE = 41, 45, 49


def timp_pitch(lh_root):
    return 36 + (lh_root % 12)


# ---------------- MIDI ----------------
mid = MIDIFile(4)
mid.addTempo(0, 0, BPM)
mid.addTrackName(0, 0, "Brass (RH)")
mid.addTrackName(1, 0, "Low Brass (LH)")
mid.addTrackName(2, 0, "Horn melody")
mid.addTrackName(3, 0, "Percussion")
mid.addProgramChange(0, 0, 0, 61)   # brass section
mid.addProgramChange(1, 1, 0, 58)   # tuba
mid.addProgramChange(2, 2, 0, 60)   # french horn

for bar, (lh, rh, mel, label, p) in enumerate(BARS_DATA):
    t = bar * BEATS_PER_BAR
    final = bar == BARS - 1
    lh_len = 4.6 if final else 3.2
    for n in lh:
        mid.addNote(1, 1, n, t, lh_len, 104 if p else 96)
    for b, notes in rh:
        dur = 4.4 if final else (1.6 if b == 2 else 2.8)
        vel = 88 if b == 2 else (102 if p else 96)
        for n in notes:
            mid.addNote(0, 0, n, t + b, dur, vel)
    if mel:
        if p == 2:
            for n, mb in zip(mel, CODA_MELODY_BEATS[bar - 28]):
                mid.addNote(2, 2, n, t + mb, 1.8, 100)
        else:
            for n in mel:
                mid.addNote(2, 2, n, t, 2.8, 104)

for bar, (lh, rh, mel, label, p) in enumerate(BARS_DATA):
    t = bar * BEATS_PER_BAR
    mid.addNote(3, 9, TAIKO_NOTE, t, 0.5, 108 if p else 96)
    mid.addNote(3, 9, TIMP_NOTE, t, 0.9, 100 if p else 90)
    if p and not any(b == 2 for b, _ in rh):
        mid.addNote(3, 9, TAIKO_NOTE, t + 2, 0.4, 84)      # answering hit
    if bar in SECTION_BARS:
        mid.addNote(3, 9, CYM_NOTE, t, 1.5, 96)

with open(OUT / (NAME + ".mid"), "wb") as f:
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


def brass(freq, dur, bite=1.0):
    """Right-hand brass. Ten harmonics with a slow rolloff, a short upward pitch
    scoop into the note, and a breath transient — the scoop and the noise are
    what make an additive stack read as brass rather than as an organ.

    The scoop integrates frequency to phase with cumsum; scaling `t` inside the
    sine would modulate phase and bend the whole note, not just its onset."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    scoop = 1 - 0.035 * np.exp(-t * R(55))
    ph = 2 * np.pi * np.cumsum(freq * scoop) / SR
    sig = np.zeros(n)
    for h in range(1, 11):
        if freq * h < SR / 2 * 0.9:
            sig += np.sin(h * ph) / h ** 0.9
    sig /= np.max(np.abs(sig))
    air = rng_d.standard_normal(n) * np.exp(-t * R(90)) * 0.06 * bite
    # the filter opens on the attack, giving the hit its edge
    bright, dark = lowpass(sig, 4200), lowpass(sig, 1500)
    m = np.exp(-t * R(6))
    return (bright * m + dark * (1 - m) + air) * env(n, T(0.035), T(0.18), 0.72, T(0.45))


def low_brass(freq, dur):
    """Left-hand power chord: eight harmonics plus a sine sub, kept dark."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = sum(np.sin(2 * np.pi * freq * h * t) / h ** 1.05 for h in range(1, 9))
    sig = lowpass(sig, 1900) + 0.55 * np.sin(2 * np.pi * freq * t)
    return sig * env(n, T(0.018), T(0.22), 0.78, T(0.5))


def horn(freq, dur):
    """Melody doubling: rounder than the brass, fewer harmonics, softer attack."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    scoop = 1 - 0.02 * np.exp(-t * R(40))
    ph = 2 * np.pi * np.cumsum(freq * scoop) / SR
    sig = sum(np.sin(h * ph) / h ** 1.35 for h in range(1, 7))
    return lowpass(sig, 2600) * env(n, T(0.06), T(0.25), 0.8, T(0.5))


def timpani(freq, dur=None):
    """Pitched drum: the fundamental drops a little as the head relaxes."""
    dur = dur if dur is not None else T(1.1)
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = freq * (1 + 0.10 * np.exp(-t * R(22)))
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = (np.sin(ph) + 0.4 * np.sin(2.1 * ph)) * np.exp(-t * R(4.2))
    skin = rng_d.standard_normal(n) * np.exp(-t * R(60)) * 0.25
    return body + lowpass(skin, 2500)


def taiko(dur=None):
    dur = dur if dur is not None else T(1.0)
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 95 * np.exp(-t * R(14)) + 46
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * R(5.0))
    thwack = lowpass(rng_d.standard_normal(n) * np.exp(-t * R(45)), 900) * 0.5
    return body + thwack


def cymbal(dur=None):
    """A swell rather than a crash: the noise ramps up into the downbeat, so it
    is placed early and lands on the hit."""
    dur = dur if dur is not None else T(2.2)
    n = int(dur * SR)
    t = np.arange(n) / SR
    b, a = butter(2, 5000 / (SR / 2), btype="high")
    noise = lfilter(b, a, rng_d.standard_normal(n))
    swell = np.clip(t / (dur * 0.45), 0, 1) ** 2
    decay = np.exp(-np.maximum(t - dur * 0.45, 0) * R(2.6))
    return noise * swell * decay


total_sec = BARS * BEATS_PER_BAR * BEAT + T(4)
out = np.zeros(int(total_sec * SR))
drums = np.zeros_like(out)
NOTE_LOG = []          # (start_sec, dur_sec, midi, track) for the visualizer


def place(buf, sig, start_sec, gain):
    s = int(start_sec * SR)
    if s < 0:
        sig = sig[-s:]
        s = 0
    e = min(s + len(sig), len(buf))
    buf[s:e] += sig[: e - s] * gain


for bar, (lh, rh, mel, label, p) in enumerate(BARS_DATA):
    t0 = bar * BEATS_PER_BAR * BEAT
    final = bar == BARS - 1
    lh_sec = (4.6 if final else 3.2) * BEAT
    for n in lh:
        place(out, low_brass(f_of(n), lh_sec + T(0.4)), t0, 0.16 if p else 0.14)
        NOTE_LOG.append((t0, lh_sec, n, 1))
    for b, notes in rh:
        dur = (4.4 if final else (1.6 if b == 2 else 2.8)) * BEAT
        g = 0.085 if b == 2 else (0.105 if p else 0.095)
        for n in notes:
            place(out, brass(f_of(n), dur + T(0.4), 1.0 if b == 0 else 0.6),
                  t0 + b * BEAT, g)
            NOTE_LOG.append((t0 + b * BEAT, dur, n, 0))
    if mel:
        beats = CODA_MELODY_BEATS[bar - 28] if p == 2 else [0.0] * len(mel)
        for n, mb in zip(mel, beats):
            d = (1.8 if p == 2 else 2.8) * BEAT
            place(out, horn(f_of(n), d + T(0.4)), t0 + mb * BEAT, 0.20)
            NOTE_LOG.append((t0 + mb * BEAT, d, n, 2))

for bar, (lh, rh, mel, label, p) in enumerate(BARS_DATA):
    t0 = bar * BEATS_PER_BAR * BEAT
    place(drums, taiko(), t0, 0.60 if p else 0.50)
    place(drums, timpani(f_of(timp_pitch(lh[-1]))), t0, 0.42 if p else 0.36)
    if p and not any(b == 2 for b, _ in rh):
        place(drums, taiko(T(0.7)), t0 + 2 * BEAT, 0.26)
    if bar in SECTION_BARS:
        place(drums, cymbal(), t0 - T(2.2) * 0.45, 0.16)


def reverb(x):
    """A big hall — the longest of the five bundles, which is what an orchestral
    fanfare wants. The longest tap (421 ms) still sits under one beat (682 ms),
    so successive hits stay separate."""
    y = x.copy()
    for d_ms, g in ((113, 0.34), (179, 0.28), (271, 0.22), (421, 0.16)):
        d = int(T(d_ms / 1000) * SR)
        buf = np.zeros_like(x)
        buf[d:] = x[:-d]
        y += lowpass(buf, 3200) * g
    return y


out = reverb(out) + drums * 0.8
out /= np.max(np.abs(out)) * 1.05
fade = int(T(3) * SR)
out[-fade:] *= np.linspace(1, 0, fade)

wav_path = OUT / (NAME + ".wav")
mp3_path = OUT / (NAME + ".mp3")
wavfile.write(wav_path, SR, (out * 32767).astype(np.int16))

subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error",
                "-i", str(wav_path), "-b:a", "192k", str(mp3_path)], check=True)

bar_sec = BEATS_PER_BAR * BEAT
(OUT.parent / ("structure%s.json" % SUFFIX)).write_text(json.dumps({
    "bpm": BPM,
    "speed": SPEED,
    "bars": BARS,
    "beats_per_bar": BEATS_PER_BAR,
    "duration_sec": total_sec,
    "bar_sec": bar_sec,
    "section_starts_sec": [b * bar_sec for b in SECTION_BARS],
    "section_labels": SECTION_LABELS,
    "section_keys": ["E minor"] * len(SECTION_BARS),
    "chords": [b[3] for b in BARS_DATA],
    "peak_sec": PEAK_BAR * bar_sec,
    "modulation_sec": None,
    "notes": [[round(s, 4), round(d, 4), n, tr] for s, d, n, tr in sorted(NOTE_LOG)],
    "title": "avenger beginning song%s  |  E minor, %g BPM" % (
        "" if SPEED == 1 else "  (%gx)" % SPEED, BPM),
}, indent=2) + "\n")

print(f"done [{NAME}]: {total_sec:.2f}s at {BPM:g} BPM, {BARS} bars, "
      f"{len(NOTE_LOG)} notes, peak at {PEAK_BAR * bar_sec:.1f}s")
