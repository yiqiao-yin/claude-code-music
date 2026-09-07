"""Render the "morning forest" visualizer.

Same framework as the other bundles: per-frame RMS, 32-band log spectrum and
low-band onset detection off the WAV, Pillow frames, raw RGB piped to ffmpeg.
What's specific to this one:

  * a forest palette — light above, dark understory below, the reverse of the
    other two bundles' gradients
  * static god-rays, precomputed once and scaled per frame by loudness
  * the whole scene brightens and warms with the harmonic arch, driven by
    `section_transpose` from structure.json
"""

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.io import wavfile

OUT = Path(__file__).resolve().parent.parent / "assets"
W, H, FPS = 1280, 720, 24


def ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    from imageio_ffmpeg import get_ffmpeg_exe
    return get_ffmpeg_exe()


SR, audio = wavfile.read(OUT / "morning_forest.wav")
audio = audio.astype(np.float32) / 32767
DUR = len(audio) / SR
N = int(np.ceil(DUR * FPS))

struct = json.loads((OUT.parent / "structure.json").read_text())
SEC_STARTS = struct["section_starts_sec"]
SEC_TR = struct["section_transpose"]
TITLE = struct["title"]
print(f"duration {DUR:.2f}s -> {N} frames, {len(SEC_STARTS)} sections")

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

# --- the arch, as a per-frame envelope ---------------------------------------
# height[i] in [0, 1] tracks how far up the arch we are; smoothed over 1.5 s so
# the palette eases between keys instead of cutting. bloom[i] flashes at each
# section boundary.
t_all = np.arange(N) / FPS
step = np.zeros(N)
for s, start in enumerate(SEC_STARTS):
    step[t_all >= start] = SEC_TR[s] / max(SEC_TR)
k = int(1.5 * FPS)
height = np.convolve(step, np.ones(k) / k, mode="same")

bloom = np.zeros(N)
for start in SEC_STARTS[1:]:
    bloom = np.maximum(bloom, np.where(t_all >= start, np.exp(-(t_all - start) * 1.3), 0.0))

# --- background: light above, understory below -------------------------------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
g = yy / H


def gradient(top, bottom):
    return np.stack([top[c] * (1 - g) + bottom[c] * g for c in range(3)], axis=-1)


bg_low = gradient((58, 72, 54), (10, 18, 13))     # C major — cool green morning
bg_high = gradient((108, 112, 74), (18, 30, 20))  # E major — sun fully up

# --- god-rays: static geometry, precomputed once -----------------------------
shaft_layer = Image.new("RGB", (W, H), (0, 0, 0))
sd = ImageDraw.Draw(shaft_layer)
for s_i in range(6):
    x0 = -200 + s_i * 300
    wdt = 60 + 26 * ((s_i * 7) % 4)
    sd.polygon([(x0, -60), (x0 + wdt, -60), (x0 + wdt + 520, H + 60), (x0 + 520, H + 60)],
               fill=(46, 44, 26))
shafts = np.asarray(shaft_layer.filter(ImageFilter.GaussianBlur(45))).astype(np.float32)
shafts *= np.clip(1.25 - g, 0, 1)[..., None]      # rays fade toward the floor

# --- particles: pollen drifting in the light ---------------------------------
rng = np.random.default_rng(7)
P = 300
px = rng.uniform(0, W, P)
py = rng.uniform(0, H, P)
pz = rng.uniform(0.3, 1.0, P)
pph = rng.uniform(0, 2 * np.pi, P)

ff = subprocess.Popen([
    ffmpeg_exe(), "-y", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", str(OUT / "morning_forest.wav"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
    "-c:a", "aac", "-b:a", "192k", "-shortest",
    str(OUT / "morning_forest_visualizer.mp4"),
], stdin=subprocess.PIPE)

cx, cy = W / 2, H * 0.44
for i in range(N):
    t = i / FPS
    Hh, B = height[i], bloom[i]

    frame = bg_low * (1 - Hh) + bg_high * Hh
    frame = frame + shafts * (0.55 + 0.45 * rms[i] + 0.5 * B)
    frame = frame + 22 * B

    img = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)

    # the sun through the canopy: pale gold, whiter at the top of the arch
    r = 62 + 66 * rms[i] + 40 * pulse[i] + 22 * B
    base = np.array([190, 170, 90]) * (1 - Hh) + np.array([245, 235, 165]) * Hh
    for kk, a in ((2.3, 16), (1.6, 38), (1.15, 86), (1.0, 168)):
        rr = r * kk
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                   fill=tuple(int(c * a / 168) for c in base))
    glow = glow.filter(ImageFilter.GaussianBlur(30))
    img = Image.fromarray(np.clip(np.asarray(img).astype(np.int16)
                                  + np.asarray(glow).astype(np.int16), 0, 255).astype(np.uint8))

    d = ImageDraw.Draw(img, "RGBA")

    # ring on each kick
    if pulse[i] > 0.05:
        rr = r + 40 + 250 * (1 - pulse[i])
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=(235, 245, 205, int(180 * pulse[i])), width=3)

    # a wide ring at every section change — one per step of the arch
    if B > 0.02:
        rr = r + 60 + 880 * (1 - B)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=(255, 255, 235, int(210 * B)), width=5)

    # spectrum ring: fresh green against the gold
    for b in range(NB):
        ang = -np.pi / 2 + 2 * np.pi * b / NB + t * 0.06
        r0 = r + 28
        r1 = r0 + 22 + 105 * spec[i, b]
        d.line([cx + r0 * np.cos(ang), cy + r0 * np.sin(ang),
                cx + r1 * np.cos(ang), cy + r1 * np.sin(ang)],
               fill=(int(120 + 40 * Hh), int(225 + 20 * Hh), int(130 + 30 * Hh),
                     int(min(255, 95 + 135 * spec[i, b] + 40 * B))), width=4)

    # pollen: slow rise, gentle lateral sway
    px[:] = (px + 0.22 * pz * np.sin(pph + t * 0.25)) % W
    py[:] = (py - (0.22 + 0.14 * Hh) * pz) % H
    tw = 0.5 + 0.5 * np.sin(t * 1.4 + pph)
    for j in range(P):
        s = 1.1 + 2.3 * pz[j]
        a = int(min(255, 35 + 145 * tw[j] * pz[j] + 45 * B))
        d.ellipse([px[j] - s, py[j] - s, px[j] + s, py[j] + s], fill=(255, 248, 205, a))

    # waveform strip
    seg = audio[i * hop:i * hop + hop * 2]
    if len(seg) > 0:
        xs = np.linspace(80, W - 80, len(seg))
        ys = H - 90 + seg * 45
        d.line(list(zip(xs[::8], ys[::8])), fill=(205, 235, 175, 125), width=2)

    fade = min(1, t / 3, (DUR - t) / 3)
    d.text((80, H - 60), TITLE, fill=(240, 248, 220, int(190 * fade)))

    ff.stdin.write(np.asarray(img).tobytes())
    if i % 240 == 0:
        print("frame", i)

ff.stdin.close()
ff.wait()
print("done")
