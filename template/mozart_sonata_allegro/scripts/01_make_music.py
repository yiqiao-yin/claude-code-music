"""Compose and synthesize "mozart sonata allegro".

Same framework as the other bundles: symbolic composition to MIDI, numerical
synthesis to WAV, MP3 transcode, structure.json handoff. No AI audio anywhere.

The brief was "like Bach, but Mozart — a conventional piano sonata", chosen as a
quick opening movement, in minor, in sonata form. Four things separate Classical
from Baroque and all four are here:

  * **texture** — one singing line over a simple accompaniment, not four equal
    voices. Baroque fills every gap; Mozart leaves air.
  * **phrasing** — balanced four-bar units that breathe, with actual rests.
  * **the Alberti bass** — low, high, middle, high. The Mozart piano fingerprint.
  * **dynamics** — a harpsichord physically cannot play louder or softer, which
    is why the piano replaced it. Every bar here carries a gain multiplier.

Form: 48 bars of 4/4 at 138 BPM. Sonata form, which is a journey out and back —
the second subject is heard in E flat major, and heard again at the end in C
minor. Same tune, once bright and once dark. That reconciliation is the whole
point of the form.

  bars  1-8   First subject          C minor
  bars  9-12  Transition             modulating
  bars 13-20  Second subject         E flat major
  bars 21-32  Development            fragments pushed through keys
  bars 33-40  Recapitulation         C minor
  bars 41-46  Second subject again   now C minor
  bars 47-48  Coda

This is the repo's first stereo bundle: low notes sit left, high notes right,
which is how a piano actually reaches you.
"""

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from midiutil import MIDIFile
from scipy.io import wavfile
from scipy.signal import butter, lfilter

BPM = 138
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
# Left-hand voicings, close position in MIDI 44-60 where an Alberti figure sits.
# G7 is voiced B-D-F: the leading tone in the bass is the Classical sound, and
# the mode needs that B natural — C minor's own seventh is B flat.
VOICING = {
    "Cm":   [48, 51, 55],   # C3  Eb3 G3
    "G7":   [47, 50, 53],   # B2  D3  F3
    "Fm":   [53, 56, 60],   # F3  Ab3 C4
    "Ab":   [44, 48, 51],   # Ab2 C3  Eb3
    "Bb7":  [46, 50, 53],   # Bb2 D3  F3
    "Eb":   [51, 55, 58],   # Eb3 G3  Bb3
    "Ddim": [50, 53, 56],   # D3  F3  Ab3
}
TONES = {
    "Cm": "C D# G", "G7": "G B D F", "Fm": "F G# C", "Ab": "G# C D#",
    "Bb7": "A# D F G#", "Eb": "D# G A#", "Ddim": "D F G#",
}

# Alberti bass: low, high, middle, high — twice per bar of 4/4, eight eighths.
ALBERTI = [0, 2, 1, 2]

HARMONY = (
    ["Cm", "G7", "Cm", "G7", "Cm", "G7", "Fm", "G7"]          # first subject
    + ["Cm", "Ab", "Bb7", "Eb"]                                # transition
    + ["Eb", "Bb7", "Eb", "Ab", "Fm", "Bb7", "Eb", "Eb"]       # second subject, Eb
    + ["Cm", "Fm", "Bb7", "Eb", "Ab", "Ddim",
       "G7", "Cm", "Ab", "Fm", "G7", "G7"]                     # development
    + ["Cm", "G7", "Cm", "G7", "Cm", "G7", "Fm", "G7"]         # recapitulation
    + ["Cm", "G7", "Cm", "Fm", "Ddim", "G7"]                   # 2nd subject, now Cm
    + ["Cm", "Cm"]                                             # coda
)

# The melody, bar by bar: (midi or None for a rest, length in beats).
R = None
MELODY = [
    # --- first subject: a rising arpeggio, answered by a falling scale ---
    [(72, 1), (75, 1), (79, 1), (84, 1)],
    [(83, 2), (79, 2)],
    [(79, 1), (77, 1), (75, 1), (74, 1)],
    [(74, 3), (R, 1)],
    [(72, 1), (75, 1), (79, 1), (84, 1)],
    [(83, 2), (86, 2)],
    [(84, 1), (82, 1), (80, 1), (79, 1)],
    [(79, 4)],
    # --- transition: running eighths, agitated, climbing toward E flat ---
    [(72, .5), (74, .5), (75, .5), (77, .5), (79, .5), (80, .5), (79, .5), (77, .5)],
    [(80, .5), (82, .5), (84, .5), (82, .5), (80, .5), (79, .5), (80, .5), (82, .5)],
    [(82, .5), (84, .5), (86, .5), (84, .5), (82, .5), (80, .5), (77, .5), (79, .5)],
    [(82, 2), (R, 2)],
    # --- second subject: lyrical, longer notes, the contrast ---
    [(79, 2), (82, 1), (79, 1)],
    [(77, 2), (74, 2)],
    [(75, 1), (79, 1), (82, 1), (87, 1)],
    [(84, 3), (R, 1)],
    [(80, 2), (84, 1), (80, 1)],
    [(82, 2), (77, 2)],
    [(79, 1), (77, 1), (75, 1), (74, 1)],
    [(75, 4)],
    # --- development: the opening arpeggio pushed through seven keys ---
    [(72, 1), (75, 1), (79, 1), (84, 1)],
    [(77, 1), (80, 1), (84, 1), (80, 1)],
    [(70, 1), (74, 1), (77, 1), (82, 1)],
    [(75, 1), (79, 1), (82, 1), (87, 1)],
    [(68, 1), (72, 1), (75, 1), (80, 1)],
    [(74, 1), (77, 1), (80, 1), (86, 1)],
    [(71, 1), (74, 1), (77, 1), (83, 1)],
    [(72, 1), (75, 1), (79, 1), (84, 1)],
    # fragmentation: down to two notes, then one, over a dominant pedal
    [(80, 2), (75, 2)],
    [(80, 2), (77, 2)],
    [(83, 2), (79, 2)],
    [(83, 1), (83, 1), (83, 1), (83, 1)],
    # --- recapitulation: the first subject, unchanged ---
    [(72, 1), (75, 1), (79, 1), (84, 1)],
    [(83, 2), (79, 2)],
    [(79, 1), (77, 1), (75, 1), (74, 1)],
    [(74, 3), (R, 1)],
    [(72, 1), (75, 1), (79, 1), (84, 1)],
    [(83, 2), (86, 2)],
    [(84, 1), (82, 1), (80, 1), (79, 1)],
    [(79, 4)],
    # --- the second subject again, rewritten in C minor ---
    [(75, 2), (79, 1), (75, 1)],
    [(74, 2), (71, 2)],
    [(72, 1), (75, 1), (79, 1), (84, 1)],
    [(80, 3), (R, 1)],
    [(77, 2), (80, 1), (77, 1)],
    [(79, 2), (74, 2)],
    # --- coda ---
    [(84, 2), (79, 1), (75, 1)],
    [(72, 4)],
]

BARS = len(HARMONY)
assert len(MELODY) == BARS

SECTION_BARS = [0, 8, 12, 20, 32, 40, 46]
SECTION_LABELS = ["First subject", "Transition", "Second subject, in E flat",
                  "Development", "Recapitulation", "Second subject, now in C minor",
                  "Coda"]
SECTION_KEYS = ["C minor", "modulating", "E flat major", "modulating",
                "C minor", "C minor", "C minor"]
# Where the harmony sits relative to home, for the visualizer's key compass:
# 0 = home, 1 = fully away, in between = travelling.
SECTION_DISTANCE = [0.0, 0.5, 1.0, 0.75, 0.0, 0.0, 0.0]

# Phrase dynamics. A harpsichord cannot do this and a piano is built for it, so
# it is the most audible thing separating this bundle from simple_bach_tune.
def dynamics():
    d = np.ones(BARS)
    d[0:8] = 1.00                                   # first subject: forte
    d[2:4] = np.linspace(0.92, 0.80, 2)             # ... easing off into the rest
    d[8:12] = np.linspace(0.78, 1.05, 4)            # transition: crescendo
    d[12:20] = 0.66                                 # second subject: piano
    d[16:20] = np.linspace(0.66, 0.88, 4)           # ... warming into the close
    d[20:32] = np.linspace(0.72, 1.12, 12)          # development: long build
    d[32:40] = 1.00                                 # recapitulation: forte again
    d[34:36] = np.linspace(0.92, 0.80, 2)
    d[40:46] = np.linspace(0.70, 1.00, 6)           # second subject, growing
    d[46:48] = 1.10                                 # coda
    return d


DYN = dynamics()

# ---------------- MIDI ----------------
mid = MIDIFile(4)
mid.addTempo(0, 0, BPM)
mid.addTrackName(0, 0, "Piano left hand")
mid.addTrackName(1, 0, "Piano left hand (bass)")
mid.addTrackName(2, 0, "Piano right hand")
mid.addTrackName(3, 0, "Piano right hand (octave)")
for tr, ch in ((0, 0), (1, 1), (2, 2), (3, 3)):
    mid.addProgramChange(tr, ch, 0, 0)      # acoustic grand

for bar in range(BARS):
    t = bar * BEATS_PER_BAR
    v = VOICING[HARMONY[bar]]
    vel = int(np.clip(58 * DYN[bar], 20, 118))
    for half in range(2):
        for j, idx in enumerate(ALBERTI):
            mid.addNote(0, 0, v[idx], t + half * 2 + j * 0.5, 0.45, vel)
    pos = 0.0
    for n, d in MELODY[bar]:
        if n is not None:
            mid.addNote(2, 2, n, t + pos, d * 0.94, int(np.clip(84 * DYN[bar], 24, 124)))
        pos += d

with open(OUT / "mozart_sonata_allegro.mid", "wb") as f:
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

INHARMONICITY = 0.0004     # B, the stiffness coefficient of a real piano string


def fortepiano(freq, dur, bright=1.0):
    """A Mozart-era piano: lighter and more wooden than a modern grand.

    The one detail that matters most is **inharmonicity**. A piano string is
    stiff, not an ideal string, so its overtones are stretched sharp:

        f_n = n * f0 * sqrt(1 + B * n**2)

    with B around 0.0004. Without that stretch an additive stack sounds like an
    organ; with it, it sounds struck. It is also why the music box in
    `music_box_waltz` needed *fixed* inharmonic ratios and this needs a
    *progressive* one — different physics, different formula.

    Two more: higher partials die faster than the fundamental, and low notes ring
    longer than high ones. Plus a hammer thump, which is the wooden part.
    """
    key = (round(freq, 2), round(dur, 3), round(bright, 2))
    if key in _piano_cache:
        return _piano_cache[key]
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    # low strings ring on; the top of the keyboard is nearly percussive
    base_decay = 1.6 + 5.5 * np.clip((freq - 130) / 900, 0, 1)
    for h in range(1, 15):
        f = h * freq * np.sqrt(1 + INHARMONICITY * h * h)
        if f >= SR / 2 * 0.9:
            break
        amp = (1.0 / h ** (1.45 - 0.25 * bright))
        sig += amp * np.sin(2 * np.pi * f * t) * np.exp(-t * base_decay * (1 + 0.22 * h))
    sig /= max(np.max(np.abs(sig)), 1e-9)
    thump = lowpass(rng_d.standard_normal(n) * np.exp(-t * 130), 2600) * 0.10
    out_ = (sig + thump) * env(n, 0.002, 0.02, 0.9, 0.06)
    _piano_cache[key] = out_
    return out_


total_sec = BARS * BEATS_PER_BAR * BEAT + 4
out = np.zeros((int(total_sec * SR), 2))          # stereo


def pan_of(midi):
    """Low notes left, high notes right — how a piano actually reaches you."""
    return float(np.clip((midi - 46) / 44.0, 0.10, 0.90))


def place(sig, start_sec, gain, midi):
    s = int(start_sec * SR)
    e = min(s + len(sig), len(out))
    if e <= s:
        return
    p = pan_of(midi) * np.pi / 2
    out[s:e, 0] += sig[: e - s] * gain * np.cos(p)
    out[s:e, 1] += sig[: e - s] * gain * np.sin(p)


for bar in range(BARS):
    t0 = bar * BEATS_PER_BAR * BEAT
    v = VOICING[HARMONY[bar]]
    dy = DYN[bar]
    for half in range(2):
        for j, idx in enumerate(ALBERTI):
            n = v[idx]
            place(fortepiano(f_of(n), 0.9 * BEAT + 0.3, 0.7),
                  t0 + (half * 2 + j * 0.5) * BEAT, 0.115 * dy, n)
    pos = 0.0
    for n, d in MELODY[bar]:
        if n is not None:
            place(fortepiano(f_of(n), d * BEAT + 0.55, 1.0), t0 + pos * BEAT, 0.30 * dy, n)
        pos += d


def reverb(x):
    """A salon, not a church. Short and bright — Classical music was written for
    rooms with people and furniture in them. At 138 BPM a beat is 435 ms, so the
    longest tap stays well inside one."""
    y = x.copy()
    for d_ms, g in ((41, 0.22), (67, 0.17), (103, 0.13), (163, 0.09)):
        d = int(d_ms / 1000 * SR)
        buf = np.zeros_like(x)
        buf[d:] = x[:-d]
        for c in range(2):
            buf[:, c] = lowpass(buf[:, c], 5600)
        y += buf * g
    return y


out = reverb(out)
out /= np.max(np.abs(out)) * 1.05
fade = int(3 * SR)
out[-fade:] *= np.linspace(1, 0, fade)[:, None]

wav_path = OUT / "mozart_sonata_allegro.wav"
mp3_path = OUT / "mozart_sonata_allegro.mp3"
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
    "channels": 2,
    "section_starts_sec": [b * bar_sec for b in SECTION_BARS],
    "section_labels": SECTION_LABELS,
    "section_keys": SECTION_KEYS,
    "section_distance": SECTION_DISTANCE,
    "chords": HARMONY,
    "dynamics": [round(float(x), 3) for x in DYN],
    "has_drums": False,
    # The onset detector is wrong for this piece in the opposite way it was wrong
    # for church_passacaglia: not too few transients but too many. The Alberti
    # bass puts an attack every 217 ms, so `pulse` never decays and the ring sits
    # lit 88% of the time. Events come from the downbeat instead.
    "pulse_source": "downbeat",
    "modulation_sec": SECTION_BARS[2] * bar_sec,
    "title": "mozart sonata allegro  |  C minor, sonata form, 138 BPM",
}, indent=2) + "\n")

print(f"done: {total_sec:.2f}s, {BARS} bars at {BPM} BPM, stereo, sections at "
      f"{', '.join('%.1f' % (b * bar_sec) for b in SECTION_BARS)}")
