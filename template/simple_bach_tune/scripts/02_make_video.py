"""Render the "simple bach tune" visualizer.

Same framework as the other bundles: per-frame RMS, 32-band log spectrum and
low-band onset detection off the WAV, Pillow frames, raw RGB piped to ffmpeg.
What's specific to this one:

  * a candlelit stone palette — cool slate above, warm below
  * a ring of sixteen ticks, one per bar, with the current bar lit. The piece is
    a strict sixteen-bar sequence and this makes that structure visible.
  * the current chord name, read from structure.json, in the top-left corner
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


SR, audio = wavfile.read(OUT / "simple_bach_tune.wav")
audio = audio.astype(np.float32) / 32767
DUR = len(audio) / SR
N = int(np.ceil(DUR * FPS))

struct = json.loads((OUT.parent / "structure.json").read_text())
SEC_STARTS = struct["section_starts_sec"]
BAR_SEC = struct["bar_sec"]
BARS = struct["bars"]
CHORDS = struct["chords"]
DRUMS_IN = struct["drums_in_sec"]
TITLE = struct["title"]
print(f"duration {DUR:.2f}s -> {N} frames, {BARS} bars, {len(SEC_STARTS)} phrases")

FONT_CHORD = ImageFont.load_default(size=38)
FONT_BAR = ImageFont.load_default(size=16)

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
print("kick onsets detected:", int(onsets.sum()))

# per-frame structure: which bar, which phrase, and a bloom at each phrase start
t_all = np.arange(N) / FPS
bar_idx = np.clip((t_all / BAR_SEC).astype(int), 0, BARS - 1)
bloom = np.zeros(N)
for start in SEC_STARTS[1:]:
    bloom = np.maximum(bloom, np.where(t_all >= start, np.exp(-(t_all - start) * 1.4), 0.0))
# the kit entering is its own small event
warmth = np.clip((t_all - DRUMS_IN) / 3.0, 0, 1)

# background: cool slate above, candle warmth below
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
g = yy / H
bg = np.stack([16 + 26 * g, 19 + 18 * g, 32 + 6 * g], axis=-1)

rng = np.random.default_rng(7)
P = 240
px = rng.uniform(0, W, P)
py = rng.uniform(0, H, P)
pz = rng.uniform(0.3, 1.0, P)
pph = rng.uniform(0, 2 * np.pi, P)

ff = subprocess.Popen([
    ffmpeg_exe(), "-y", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", str(OUT / "simple_bach_tune.wav"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
    "-c:a", "aac", "-b:a", "192k", "-shortest",
    str(OUT / "simple_bach_tune_visualizer.mp4"),
], stdin=subprocess.PIPE)

cx, cy = W / 2, H * 0.44
TICK_R = 268
for i in range(N):
    t = i / FPS
    B, Wm, bi = bloom[i], warmth[i], bar_idx[i]

    frame = bg + 18 * B + np.array([6, 3, 0]) * Wm
    img = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))

    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    # candle-gold orb
    r = 58 + 62 * rms[i] + 34 * pulse[i] + 20 * B
    base = np.array([225, 178, 100]) + np.array([18, 12, 0]) * Wm
    for k, a in ((2.3, 15), (1.6, 36), (1.15, 84), (1.0, 166)):
        rr = r * k
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                   fill=tuple(int(c * a / 166) for c in base))
    glow = glow.filter(ImageFilter.GaussianBlur(30))
    img = Image.fromarray(np.clip(np.asarray(img).astype(np.int16)
                                  + np.asarray(glow).astype(np.int16), 0, 255).astype(np.uint8))

    d = ImageDraw.Draw(img, "RGBA")

    if pulse[i] > 0.05:
        rr = r + 38 + 240 * (1 - pulse[i])
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=(245, 228, 195, int(170 * pulse[i])), width=3)
    if B > 0.02:
        rr = r + 60 + 820 * (1 - B)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=(250, 245, 235, int(200 * B)), width=5)

    # spectrum ring, cool ivory against the gold
    for b in range(NB):
        ang = -np.pi / 2 + 2 * np.pi * b / NB + t * 0.04
        r0 = r + 26
        r1 = r0 + 20 + 100 * spec[i, b]
        d.line([cx + r0 * np.cos(ang), cy + r0 * np.sin(ang),
                cx + r1 * np.cos(ang), cy + r1 * np.sin(ang)],
               fill=(196, 206, 232, int(min(255, 90 + 130 * spec[i, b] + 40 * B))), width=4)

    # sixteen bar ticks — the sequence made visible, current bar lit
    frac = (t % BAR_SEC) / BAR_SEC
    for b in range(BARS):
        ang = -np.pi / 2 + 2 * np.pi * b / BARS
        ca, sa = np.cos(ang), np.sin(ang)
        if b == bi:
            ln, wd, col = 26 + 10 * (1 - frac), 4, (255, 236, 200, 235)
        elif b < bi:
            ln, wd, col = 13, 2, (200, 190, 175, 120)
        else:
            ln, wd, col = 10, 2, (150, 158, 180, 70)
        d.line([cx + TICK_R * ca, cy + TICK_R * sa,
                cx + (TICK_R + ln) * ca, cy + (TICK_R + ln) * sa], fill=col, width=wd)
    # phrase markers: a longer tick every four bars
    for b in range(0, BARS, 4):
        ang = -np.pi / 2 + 2 * np.pi * b / BARS
        ca, sa = np.cos(ang), np.sin(ang)
        d.line([cx + (TICK_R - 12) * ca, cy + (TICK_R - 12) * sa,
                cx + (TICK_R - 2) * ca, cy + (TICK_R - 2) * sa],
               fill=(235, 220, 190, 150), width=2)

    # dust motes in the candlelight
    px[:] = (px + 0.18 * pz * np.sin(pph + t * 0.22)) % W
    py[:] = (py - 0.20 * pz) % H
    tw = 0.5 + 0.5 * np.sin(t * 1.2 + pph)
    for j in range(P):
        s = 1.0 + 2.0 * pz[j]
        a = int(min(255, 30 + 130 * tw[j] * pz[j] + 40 * B))
        d.ellipse([px[j] - s, py[j] - s, px[j] + s, py[j] + s], fill=(250, 238, 210, a))

    seg = audio[i * hop:i * hop + hop * 2]
    if len(seg) > 0:
        xs = np.linspace(80, W - 80, len(seg))
        ys = H - 90 + seg * 45
        d.line(list(zip(xs[::8], ys[::8])), fill=(215, 205, 185, 120), width=2)

    # chord readout, kept in the dark top-left corner: over the orb it washes
    # out completely once the glow is at full size
    fade = min(1, t / 3, (DUR - t) / 3)
    d.text((80, 54), CHORDS[bi], font=FONT_CHORD, fill=(250, 235, 205, int(235 * fade)))
    d.text((82, 102), "bar %d / %d" % (bi + 1, BARS), font=FONT_BAR,
           fill=(178, 186, 208, int(165 * fade)))
    d.text((80, H - 60), TITLE, fill=(235, 228, 212, int(190 * fade)))

    ff.stdin.write(np.asarray(img).tobytes())
    if i % 240 == 0:
        print("frame", i)

ff.stdin.close()
ff.wait()
print("done")
