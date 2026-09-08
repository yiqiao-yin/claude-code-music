"""Compose and synthesize "church passacaglia".

Same framework as the other bundles: symbolic composition to MIDI, numerical
synthesis to WAV, MP3 transcode, structure.json handoff. No AI audio anywhere.

A passacaglia: one short bass line, repeated unchanged for the whole piece, with
the music above it growing more elaborate each time round. The brief was "baroque
like Bach, harpsichord, in church, solemn" — which resolved to a pipe organ, since
a harpsichord is a chamber instrument and cannot sustain.

**E Phrygian.** A passacaglia's classic ground is the descending tetrachord
E-D-C-B, and that descent is what Phrygian is made of. Phrygian is also literally
one of the church modes, and its fingerprint — the flat second, F natural, falling
to E — becomes the cadence that ends every pass.

Form: 40 bars of 3/4 at 80 BPM. The ground is 8 bars; it plays five times.

  pass 1  bars  1-8   pedal alone, stating the ground
  pass 2  bars  9-16  + sustained chords
  pass 3  bars 17-24  + a slow melody
  pass 4  bars 25-32  + running figuration
  pass 5  bars 33-40  full organ, melody doubled at the octave

There is no percussion. Baroque church music has none, and a drum kit would fight
everything else — so this is the repo's first drumless bundle.
"""

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from midiutil import MIDIFile
from scipy.io import wavfile
from scipy.signal import butter, lfilter

BPM = 80
BEAT = 60.0 / BPM
SR = 44100
BEATS_PER_BAR = 3

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
# The ground. Root motion E D C B C B F E — a descending tetrachord, a rocking
# C-B, then the Phrygian flat-II to i cadence that no other mode has.
GROUND_BASS = [40, 38, 36, 35, 36, 35, 41, 40]        # E2 D2 C2 B1 C2 B1 F2 E2
GROUND_CHORDS = [
    [52, 55, 59],   # Em    E3 G3 B3
    [50, 53, 57],   # Dm    D3 F3 A3
    [48, 52, 55],   # C     C3 E3 G3
    [50, 55, 59],   # G/B   D3 G3 B3   <- G major, not B diminished
    [48, 52, 55],   # C
    [50, 55, 59],   # G/B
    [48, 53, 57],   # F     C3 F3 A3   <- the flat II
    [47, 52, 55],   # Em    B2 E3 G3
]
CHORD_NAMES = ["Em", "Dm", "C", "G/B", "C", "G/B", "F", "Em"]

# The melody, one bar at a time: (midi, beats). It descends B-A-G-G-E-D, lifts to
# F and falls to E — the Phrygian cadence sung rather than merely played.
MELODY = [
    [(71, 3)],              # B4
    [(69, 2), (65, 1)],     # A4 F4
    [(67, 3)],              # G4
    [(67, 2), (62, 1)],     # G4 D4
    [(64, 3)],              # E4
    [(62, 3)],              # D4
    [(65, 3)],              # F4   <- flat II
    [(64, 3)],              # E4
]

# Running figuration: six eighth notes per bar through the chord, an octave up.
# chord + 12 can never collide with the chord itself here — no voicing contains a
# note twelve semitones below another — so both can share MIDI channel 0.
FIG_PATTERN = [0, 1, 2, 0, 1, 2]

GROUND_BARS = len(GROUND_BASS)
PASSES = 5
BARS = GROUND_BARS * PASSES

# (label, pedal, chords, melody, figuration, melody octave doubling)
PASS_PLAN = [
    ("The ground, alone",      True, False, False, False, False),
    ("Chords enter",           True, True,  False, False, False),
    ("The melody enters",      True, True,  True,  False, False),
    ("Figuration enters",      True, True,  True,  True,  False),
    ("Full organ",             True, True,  True,  True,  True),
]
SECTION_BARS = [p * GROUND_BARS for p in range(PASSES)]
SECTION_LABELS = [p[0] for p in PASS_PLAN]

# Pipe organ registrations, as (harmonic multiple, amplitude). A real stop at 16'
# sounds an octave below the written note, 8' at pitch, 4' an octave up, 2 2/3'
# a twelfth, 2' two octaves, and a mixture adds the higher ranks on top.
REG_PEDAL     = [(0.5, 0.70), (1, 1.00), (2, 0.45)]
REG_PRINCIPAL = [(1, 1.00), (2, 0.50), (3, 0.22), (4, 0.18)]
REG_FULL      = [(1, 1.00), (2, 0.60), (3, 0.30), (4, 0.25), (6, 0.14), (8, 0.10)]
REG_FLUTE     = [(1, 1.00), (2, 0.25)]

# ---------------- MIDI ----------------
mid = MIDIFile(4)
mid.addTempo(0, 0, BPM)
mid.addTrackName(0, 0, "Organ manual")
mid.addTrackName(1, 0, "Organ pedal")
mid.addTrackName(2, 0, "Organ melody")
mid.addTrackName(3, 0, "Organ figuration")
for tr, ch in ((0, 0), (1, 1), (2, 2), (3, 3)):
    mid.addProgramChange(tr, ch, 0, 19)      # church organ on every part

for bar in range(BARS):
    g = bar % GROUND_BARS
    _, ped, cho, mel, fig, dbl = PASS_PLAN[bar // GROUND_BARS]
    t = bar * BEATS_PER_BAR
    last = bar == BARS - 1
    hold = BEATS_PER_BAR + 2.0 if last else BEATS_PER_BAR - 0.08
    if ped:
        mid.addNote(1, 1, GROUND_BASS[g], t, hold, 88)
    if cho:
        for n in GROUND_CHORDS[g]:
            mid.addNote(0, 0, n, t, hold, 70)
    if mel:
        pos = 0.0
        for n, d in MELODY[g]:
            mid.addNote(2, 2, n, t + pos, d - 0.06, 82)
            if dbl:
                mid.addNote(2, 2, n + 12, t + pos, d - 0.06, 66)
            pos += d
    if fig and not last:
        for j, idx in enumerate(FIG_PATTERN):
            mid.addNote(3, 3, GROUND_CHORDS[g][idx] + 12, t + j * 0.5, 0.45, 62)

with open(OUT / "church_passacaglia.mid", "wb") as f:
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
_organ_cache = {}


def organ_pipe(freq, dur, ranks, chiff=1.0):
    """A rank of flue pipes.

    Three things separate this from a plain additive stack, and all three are
    what make it read as an organ rather than a synthesizer:

      * **no decay.** Wind keeps blowing, so the tone sustains flat until the key
        is released. Sustain sits at 0.97 and the attack is slow.
      * **chiff** — the breathy transient as a pipe speaks, before the tone
        settles. Band-passed noise, gone in about 80 ms.
      * **per-pipe detune.** No two pipes in a real rank are perfectly in tune.
        The offset is derived from the rank number, so it is deterministic.
    """
    key = (round(freq, 2), round(dur, 3), id(ranks), round(chiff, 2))
    if key in _organ_cache:
        return _organ_cache[key]
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for mult, amp in ranks:
        f = freq * mult
        if f >= SR / 2 * 0.9:
            continue
        detune = 1 + 0.0006 * (((int(mult * 100) * 7919) % 13) - 6)
        sig += amp * np.sin(2 * np.pi * f * detune * t)
    sig /= max(np.max(np.abs(sig)), 1e-9)
    b, a = butter(2, [min(freq * 1.5, 8000) / (SR / 2),
                      min(freq * 5, SR / 2 * 0.9) / (SR / 2)], btype="band")
    speak = lfilter(b, a, rng_d.standard_normal(n)) * np.exp(-t * 45) * 0.09 * chiff
    out_ = (sig + speak) * env(n, 0.085, 0.10, 0.97, 0.22)
    _organ_cache[key] = out_
    return out_


total_sec = BARS * BEATS_PER_BAR * BEAT + 4
out = np.zeros(int(total_sec * SR))


def place(buf, sig, start_sec, gain):
    s = int(start_sec * SR)
    e = min(s + len(sig), len(buf))
    buf[s:e] += sig[: e - s] * gain


for bar in range(BARS):
    g = bar % GROUND_BARS
    _, ped, cho, mel, fig, dbl = PASS_PLAN[bar // GROUND_BARS]
    t0 = bar * BEATS_PER_BAR * BEAT
    last = bar == BARS - 1
    hold = (BEATS_PER_BAR + 2.0 if last else BEATS_PER_BAR - 0.08) * BEAT
    full = bar >= SECTION_BARS[4]
    if ped:
        place(out, organ_pipe(f_of(GROUND_BASS[g]), hold + 0.5, REG_PEDAL, 1.2),
              t0, 0.30 if full else 0.26)
    if cho:
        reg = REG_FULL if full else REG_PRINCIPAL
        for n in GROUND_CHORDS[g]:
            place(out, organ_pipe(f_of(n), hold + 0.5, reg), t0, 0.085)
    if mel:
        pos = 0.0
        for n, d in MELODY[g]:
            place(out, organ_pipe(f_of(n), d * BEAT + 0.5, REG_FLUTE, 0.7), t0 + pos * BEAT, 0.20)
            if dbl:
                place(out, organ_pipe(f_of(n + 12), d * BEAT + 0.5, REG_FLUTE, 0.5),
                      t0 + pos * BEAT, 0.10)
            pos += d
    if fig and not last:
        for j, idx in enumerate(FIG_PATTERN):
            place(out, organ_pipe(f_of(GROUND_CHORDS[g][idx] + 12), 0.5 * BEAT + 0.35,
                                  REG_PRINCIPAL, 0.9), t0 + j * 0.5 * BEAT, 0.075)


def reverb(x):
    """A stone church. Six taps rather than four, because density is what makes a
    reverb sound like a room rather than an echo, and darker than any other bundle
    at 2600 Hz. At 80 BPM a beat is 750 ms, so the longest tap still lands inside
    one beat — even a cathedral has to stay legible."""
    y = x.copy()
    for d_ms, g in ((109, 0.30), (173, 0.26), (251, 0.22), (367, 0.19),
                    (487, 0.15), (631, 0.11)):
        d = int(d_ms / 1000 * SR)
        buf = np.zeros_like(x)
        buf[d:] = x[:-d]
        y += lowpass(buf, 2600) * g
    return y


# No percussion, so nothing is added dry — the whole mix goes through the room.
out = reverb(out)
out /= np.max(np.abs(out)) * 1.05
fade = int(3.5 * SR)
out[-fade:] *= np.linspace(1, 0, fade)

wav_path = OUT / "church_passacaglia.wav"
mp3_path = OUT / "church_passacaglia.mp3"
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
    "ground_bars": GROUND_BARS,
    "passes": PASSES,
    "section_starts_sec": [b * bar_sec for b in SECTION_BARS],
    "section_labels": SECTION_LABELS,
    "section_keys": ["E phrygian"] * PASSES,
    "chords": [CHORD_NAMES[b % GROUND_BARS] for b in range(BARS)],
    "has_drums": False,
    "modulation_sec": None,
    "title": "church passacaglia  |  E phrygian, 3/4, 80 BPM",
}, indent=2) + "\n")

print(f"done: {total_sec:.2f}s, {BARS} bars of {BEATS_PER_BAR}/4, {PASSES} passes "
      f"over an {GROUND_BARS}-bar ground, at "
      f"{', '.join('%.1f' % (b * bar_sec) for b in SECTION_BARS)}")
