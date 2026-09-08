"""Render the "church passacaglia" visualizer.

Same framework as the other bundles: per-frame RMS, 32-band log spectrum and
low-band onset detection off the WAV, Pillow frames, raw RGB piped to ffmpeg.
What's specific to this one:

  * **the first drumless bundle**, which changes how the scene is driven. With no
    kit there is almost nothing for the spectral-flux onset detector to catch, so
    a `pulse`-weighted orb would sit still for a minute and a half. Here the orb
    is driven mostly by `rms` and by bar position, with `pulse` as a small extra.
  * a stone-and-candle palette, and stained-glass colour in the spectrum ring
  * the ground drawn as accumulating rings — one per pass, each with eight ticks
    for the eight bars of the ground. Completed rings stay. That is what a
    passacaglia *is*: the same circle, walked again with more on top.
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


SR, audio = wavfile.read(OUT / "church_passacaglia.wav")
audio = audio.astype(np.float32) / 32767
DUR = len(audio) / SR
N = int(np.ceil(DUR * FPS))

struct = json.loads((OUT.parent / "structure.json").read_text())
SEC_STARTS = struct["section_starts_sec"]
SEC_LABELS = struct["section_labels"]
BAR_SEC = struct["bar_sec"]
BARS = struct["bars"]
CHORDS = struct["chords"]
GROUND_BARS = struct["ground_bars"]
PASSES = struct["passes"]
TITLE = struct["title"]
print(f"[church_passacaglia] {DUR:.2f}s -> {N} frames, "
      f"{PASSES} passes over {GROUND_BARS} bars")

FONT_SEC = ImageFont.load_default(size=27)
FONT_CH = ImageFont.load_default(size=16)

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
t_all = np.arange(N) / FPS

# --- where `pulse` comes from when there is no kit -------------------------
# The spectral-flux detector needs a percussive transient. This piece has none:
# organ pipes speak slowly and never stop, so the detector fires on noise-floor
# drift instead of on events — 585 hits across 2256 frames, leaving the impact
# ring lit on 98% of them. Measured, not guessed.
#
# So for a drumless piece the pulse comes from the *score* instead. The musical
# event here is the chord change on each downbeat, which structure.json knows
# about and the audio does not advertise.
if struct.get("has_drums", True):
    pulse = np.zeros(N)
    for i in range(N):
        pulse[i] = 1.0 if onsets[i] else (pulse[i - 1] * 0.78 if i else 0)
    print("onsets detected:", int(onsets.sum()))
else:
    pulse = np.exp(-(t_all % BAR_SEC) * 2.8)
    print("drumless: pulse taken from the downbeat, not the onset detector "
          "(which fired %d times on %d frames — noise, not events)"
          % (int(onsets.sum()), N))
bar_idx = np.clip((t_all / BAR_SEC).astype(int), 0, BARS - 1)
ground_pos = bar_idx % GROUND_BARS
pass_idx = np.clip(bar_idx // GROUND_BARS, 0, PASSES - 1)
sec_idx = pass_idx
bloom = np.zeros(N)
for start in SEC_STARTS[1:]:
    bloom = np.maximum(bloom, np.where(t_all >= start, np.exp(-(t_all - start) * 1.1), 0.0))
# how far through the whole piece — the organ swells as the passes stack
build = np.clip(t_all / max(SEC_STARTS[-1], 1e-9), 0, 1)

# background: cold stone, a little warmer low down where the candles are
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
g = yy / H
bg = np.stack([14 + 26 * g, 15 + 20 * g, 22 + 12 * g], axis=-1)

rng = np.random.default_rng(7)
P = 200
px = rng.uniform(0, W, P)
py = rng.uniform(0, H, P)
pz = rng.uniform(0.3, 1.0, P)
pph = rng.uniform(0, 2 * np.pi, P)

ff = subprocess.Popen([
    ffmpeg_exe(), "-y", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", str(OUT / "church_passacaglia.wav"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
    "-c:a", "aac", "-b:a", "192k", "-shortest",
    str(OUT / "church_passacaglia_visualizer.mp4"),
], stdin=subprocess.PIPE)

cx, cy = W / 2, H * 0.44
RING_R0, RING_DR = 168, 33
for i in range(N):
    t = i / FPS
    B, Bu, bi, gp, pi_ = bloom[i], build[i], bar_idx[i], ground_pos[i], pass_idx[i]
    in_bar = (t % BAR_SEC) / BAR_SEC

    frame = bg + 22 * B + np.array([9, 6, 1]) * Bu
    img = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))

    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    # With no drums there is nothing percussive to size the orb, so loudness and
    # the swell do the work; pulse is a small seasoning rather than the driver.
    r = 46 + 82 * rms[i] + 26 * Bu + 18 * pulse[i] + 20 * B
    base = np.array([196, 158, 108]) + np.array([46, 44, 40]) * Bu
    for k, a in ((2.3, 15), (1.65, 36), (1.2, 84), (1.0, 166)):
        rr = r * k
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                   fill=tuple(int(min(255, c) * a / 166) for c in base))
    glow = glow.filter(ImageFilter.GaussianBlur(34))
    img = Image.fromarray(np.clip(np.asarray(img).astype(np.int16)
                                  + np.asarray(glow).astype(np.int16), 0, 255).astype(np.uint8))

    d = ImageDraw.Draw(img, "RGBA")

    if pulse[i] > 0.05:
        rr = r + 34 + 190 * (1 - pulse[i])
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=(240, 224, 190, int(120 * pulse[i])), width=2)
    if B > 0.02:
        rr = r + 60 + 760 * (1 - B)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=(236, 228, 206, int(190 * B)), width=4)

    # spectrum ring: stained glass, cool blue warming to amber as the organ fills
    for b in range(NB):
        ang = -np.pi / 2 + 2 * np.pi * b / NB + t * 0.018
        r0 = r + 22
        r1 = r0 + 16 + 88 * spec[i, b]
        col = (int(96 + 120 * Bu), int(126 + 62 * Bu), int(196 - 70 * Bu),
               int(min(255, 84 + 130 * spec[i, b] + 40 * B)))
        d.line([cx + r0 * np.cos(ang), cy + r0 * np.sin(ang),
                cx + r1 * np.cos(ang), cy + r1 * np.sin(ang)], fill=col, width=4)

    # --- the ground, as accumulating rings ---
    # One ring per pass, eight ticks each for the eight bars of the ground.
    # Rings that have been walked stay on screen. The current one is lit, and its
    # current bar brightest — the same circle, walked again with more on top.
    for p in range(PASSES):
        if p > pi_:
            break
        R = RING_R0 + p * RING_DR
        cur = p == pi_
        d.ellipse([cx - R, cy - R, cx + R, cy + R],
                  outline=(216, 196, 158, 90 if cur else 34), width=2 if cur else 1)
        for k in range(GROUND_BARS):
            ang = -np.pi / 2 + 2 * np.pi * k / GROUND_BARS
            mx, my = cx + R * np.cos(ang), cy + R * np.sin(ang)
            if cur and k == gp:
                s = 9 - 3 * in_bar
                d.ellipse([mx - s - 4, my - s - 4, mx + s + 4, my + s + 4],
                          outline=(255, 238, 206, 130), width=2)
                col = (255, 240, 210, 245)
            elif cur and k < gp:
                s, col = 4, (226, 206, 170, 150)
            elif cur:
                s, col = 3, (150, 150, 156, 80)
            else:
                s, col = 3, (176, 162, 136, 70)
            d.ellipse([mx - s, my - s, mx + s, my + s], fill=col)

    # dust in the light shafts
    px[:] = (px + 0.13 * pz * np.sin(pph + t * 0.19)) % W
    py[:] = (py - 0.15 * pz) % H
    tw = 0.5 + 0.5 * np.sin(t * 0.9 + pph)
    for j in range(P):
        s = 1.0 + 2.0 * pz[j]
        a = int(min(255, 26 + 120 * tw[j] * pz[j] + 40 * B))
        d.ellipse([px[j] - s, py[j] - s, px[j] + s, py[j] + s], fill=(252, 238, 210, a))

    seg = audio[i * hop:i * hop + hop * 2]
    if len(seg) > 0:
        xs = np.linspace(80, W - 80, len(seg))
        ys = H - 74 + seg * 36
        d.line(list(zip(xs[::8], ys[::8])), fill=(198, 190, 170, 110), width=2)

    fade = min(1, t / 3, (DUR - t) / 3)
    d.text((80, 46), SEC_LABELS[sec_idx[i]], font=FONT_SEC,
           fill=(242, 234, 216, int(230 * fade)))
    d.text((82, 82), "%s   ·   pass %d of %d   ·   ground bar %d of %d"
           % (CHORDS[bi], pi_ + 1, PASSES, gp + 1, GROUND_BARS),
           font=FONT_CH, fill=(178, 172, 158, int(178 * fade)))
    d.text((80, H - 32), TITLE, fill=(214, 206, 190, int(168 * fade)))

    ff.stdin.write(np.asarray(img).tobytes())
    if i % 240 == 0:
        print("frame", i)

ff.stdin.close()
ff.wait()
print("done")
