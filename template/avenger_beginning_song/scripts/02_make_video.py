"""Render the "avenger beginning song" visualizer.

Same framework as the other bundles: per-frame RMS, 32-band log spectrum and
low-band onset detection off the WAV, Pillow frames, raw RGB piped to ffmpeg.
What's specific to this one:

  * a scrolling piano roll of the actual score, read from structure.json, with
    the two hands in different colours. The brief was a two-handed layout, so
    the visualizer draws both hands.
  * a cold steel palette with white-gold impacts, and a hard flash on each hit
    rather than a continuous glow — the music is hits separated by silence
  * the section name and current chord, top-left
"""

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.io import wavfile

OUT = Path(__file__).resolve().parent.parent / "assets"
W, H, FPS = 1280, 720, 24


def ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    from imageio_ffmpeg import get_ffmpeg_exe
    return get_ffmpeg_exe()


SR, audio = wavfile.read(OUT / "avenger_beginning_song.wav")
audio = audio.astype(np.float32) / 32767
DUR = len(audio) / SR
N = int(np.ceil(DUR * FPS))

struct = json.loads((OUT.parent / "structure.json").read_text())
SEC_STARTS = struct["section_starts_sec"]
SEC_LABELS = struct["section_labels"]
BAR_SEC = struct["bar_sec"]
BARS = struct["bars"]
CHORDS = struct["chords"]
NOTES = struct["notes"]
PEAK = struct["peak_sec"]
TITLE = struct["title"]
print(f"duration {DUR:.2f}s -> {N} frames, {BARS} bars, {len(NOTES)} notes")

FONT_SEC = ImageFont.load_default(size=30)
FONT_CH = ImageFont.load_default(size=17)

hop = SR // FPS
rms = np.array([np.sqrt(np.mean(audio[i * hop:(i + 1) * hop] ** 2))
                if (i + 1) * hop <= len(audio) else 0 for i in range(N)])
rms = rms / rms.max()

NB = 32
freqs = np.fft.rfftfreq(2048, 1 / SR)
edges = np.geomspace(40, 4000, NB + 1)
band_masks = [(freqs >= edges[b]) & (freqs < edges[b + 1]) for b in range(NB)]
low_mask = (freqs >= 40) & (freqs < 120)

spec = np.zeros((N, NB))
low = np.zeros(N)
win = np.hanning(2048)
for i in range(N):
    seg = audio[i * hop:i * hop + 2048]
    if len(seg) < 2048:
        seg = np.pad(seg, (0, 2048 - len(seg)))
    mag = np.abs(np.fft.rfft(seg * win))
    for b, m in enumerate(band_masks):
        spec[i, b] = mag[m].mean() if m.any() else 0
    low[i] = mag[low_mask].mean()

spec = np.log1p(spec * 20)
spec /= spec.max()
for i in range(1, N):
    spec[i] = np.maximum(spec[i], spec[i - 1] * 0.85)
    rms[i] = max(rms[i], rms[i - 1] * 0.9)

flux = np.maximum(low - np.roll(low, 1), 0)
thresh = np.convolve(flux, np.ones(9) / 9, mode="same") * 1.6 + 0.02 * flux.max()
onsets = flux > thresh
pulse = np.zeros(N)
for i in range(N):
    pulse[i] = 1.0 if onsets[i] else (pulse[i - 1] * 0.78 if i else 0)
print("hits detected:", int(onsets.sum()))

t_all = np.arange(N) / FPS
bar_idx = np.clip((t_all / BAR_SEC).astype(int), 0, BARS - 1)
sec_idx = np.searchsorted(SEC_STARTS, t_all, side="right") - 1
bloom = np.zeros(N)
for start in SEC_STARTS[1:]:
    bloom = np.maximum(bloom, np.where(t_all >= start, np.exp(-(t_all - start) * 1.5), 0.0))
# the restatement is heavier: everything warms from the halfway point
weight = np.clip((t_all - SEC_STARTS[3]) / 4.0, 0, 1)
peak_glow = np.where(np.abs(t_all - PEAK) < 3.0,
                     np.exp(-np.abs(t_all - PEAK) * 1.1), 0.0)

# background: cold steel, darkest at the top
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
g = yy / H
bg = np.stack([10 + 20 * g, 14 + 20 * g, 24 + 22 * g], axis=-1)

rng = np.random.default_rng(7)
P = 260
px = rng.uniform(0, W, P)
py = rng.uniform(0, H, P)
pz = rng.uniform(0.3, 1.0, P)
pph = rng.uniform(0, 2 * np.pi, P)

# --- piano roll geometry -----------------------------------------------------
ROLL_TOP, ROLL_BOT = 452, 598
ROLL_X0, ROLL_X1 = 90, W - 90
PLAYHEAD = 470                 # x of "now"; most of the band shows what's coming
WINDOW_BACK, WINDOW_FWD = 2.0, 6.0
PITCH_LO, PITCH_HI = 24, 90
TRACK_COL = {0: (255, 196, 96), 1: (96, 150, 232), 2: (250, 246, 232)}


def roll_y(midi):
    f = (midi - PITCH_LO) / (PITCH_HI - PITCH_LO)
    return ROLL_BOT - f * (ROLL_BOT - ROLL_TOP)


NOTES = sorted(NOTES, key=lambda n: n[0])
note_starts = np.array([n[0] for n in NOTES])

ff = subprocess.Popen([
    ffmpeg_exe(), "-y", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", str(OUT / "avenger_beginning_song.wav"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
    "-c:a", "aac", "-b:a", "192k", "-shortest",
    str(OUT / "avenger_beginning_song_visualizer.mp4"),
], stdin=subprocess.PIPE)

cx, cy = W / 2, H * 0.31
for i in range(N):
    t = i / FPS
    B, Wt, PG, bi, si = bloom[i], weight[i], peak_glow[i], bar_idx[i], max(0, sec_idx[i])

    frame = bg + 26 * B + 30 * PG + np.array([5, 2, 0]) * Wt
    img = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))

    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    # impact core: sized mostly by the hit, not by a continuous level
    r = 40 + 46 * rms[i] + 78 * pulse[i] + 30 * B + 26 * PG
    base = (np.array([150, 178, 235]) * (1 - Wt) + np.array([255, 214, 140]) * Wt)
    base = base * (1 - PG) + np.array([255, 250, 240]) * PG
    for k, a in ((2.4, 14), (1.7, 34), (1.2, 82), (1.0, 168)):
        rr = r * k
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                   fill=tuple(int(c * a / 168) for c in base))
    glow = glow.filter(ImageFilter.GaussianBlur(32))
    img = Image.fromarray(np.clip(np.asarray(img).astype(np.int16)
                                  + np.asarray(glow).astype(np.int16), 0, 255).astype(np.uint8))

    d = ImageDraw.Draw(img, "RGBA")

    # shockwave on each hit
    if pulse[i] > 0.04:
        rr = r + 50 + 420 * (1 - pulse[i])
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=(255, 244, 225, int(215 * pulse[i])), width=int(2 + 4 * pulse[i]))
    if B > 0.02:
        rr = r + 70 + 900 * (1 - B)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=(220, 232, 255, int(190 * B)), width=4)

    # spectrum ring
    for b in range(NB):
        ang = -np.pi / 2 + 2 * np.pi * b / NB + t * 0.03
        r0 = r + 26
        r1 = r0 + 18 + 96 * spec[i, b]
        col = (int(120 + 110 * Wt), int(158 + 52 * Wt), int(228 - 88 * Wt),
               int(min(255, 88 + 130 * spec[i, b] + 50 * B)))
        d.line([cx + r0 * np.cos(ang), cy + r0 * np.sin(ang),
                cx + r1 * np.cos(ang), cy + r1 * np.sin(ang)], fill=col, width=4)

    # embers
    px[:] = (px + 0.30 * pz * np.sin(pph + t * 0.3)) % W
    py[:] = (py - 0.42 * pz) % H
    tw = 0.5 + 0.5 * np.sin(t * 1.6 + pph)
    for j in range(P):
        s = 1.0 + 2.1 * pz[j]
        a = int(min(255, 28 + 120 * tw[j] * pz[j] + 50 * B))
        d.ellipse([px[j] - s, py[j] - s, px[j] + s, py[j] + s],
                  fill=(255, 226, 180, a))

    # --- the score, scrolling ---
    px_per_sec = (ROLL_X1 - PLAYHEAD) / WINDOW_FWD
    lo, hi = np.searchsorted(note_starts, t - WINDOW_BACK - 4), \
             np.searchsorted(note_starts, t + WINDOW_FWD)
    for ns, nd, nm, tr in NOTES[lo:hi]:
        x0 = PLAYHEAD + (ns - t) * px_per_sec
        x1 = x0 + nd * px_per_sec
        if x1 < ROLL_X0 or x0 > ROLL_X1:
            continue
        x0, x1 = max(x0, ROLL_X0), min(x1, ROLL_X1)
        y = roll_y(nm)
        live = ns <= t < ns + nd
        col = TRACK_COL[tr]
        a = 235 if live else (120 if ns > t else 70)
        h = 5 if live else 3
        d.rectangle([x0, y - h, x1, y + h], fill=col + (a,))
        if live:
            d.rectangle([x0, y - h - 2, x1, y + h + 2], outline=(255, 255, 255, 150), width=1)
    d.line([PLAYHEAD, ROLL_TOP - 6, PLAYHEAD, ROLL_BOT + 6],
           fill=(255, 255, 255, 120), width=2)

    # waveform strip
    seg = audio[i * hop:i * hop + hop * 2]
    if len(seg) > 0:
        xs = np.linspace(80, W - 80, len(seg))
        ys = H - 78 + seg * 38
        d.line(list(zip(xs[::8], ys[::8])), fill=(170, 196, 236, 120), width=2)

    fade = min(1, t / 3, (DUR - t) / 3)
    d.text((80, 46), SEC_LABELS[si], font=FONT_SEC, fill=(238, 242, 252, int(235 * fade)))
    d.text((82, 88), "%s   ·   bar %d / %d" % (CHORDS[bi].strip(), bi + 1, BARS),
           font=FONT_CH, fill=(168, 190, 226, int(180 * fade)))
    d.text((80, H - 34), TITLE, fill=(210, 224, 244, int(170 * fade)))

    ff.stdin.write(np.asarray(img).tobytes())
    if i % 240 == 0:
        print("frame", i)

ff.stdin.close()
ff.wait()
print("done")
