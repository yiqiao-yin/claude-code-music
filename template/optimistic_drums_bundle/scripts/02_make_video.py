"""Render the "optimistic drums" visualizer.

Same framework as template/moody_drums_bundle: analyse the WAV per frame
(RMS, 32-band log spectrum, low-band onset detection), draw each frame with
Pillow, pipe raw RGB into ffmpeg. Two things differ:

  * warm sunrise palette instead of the cold purple one
  * the scene reads structure.json and blooms at the key change
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


SR, audio = wavfile.read(OUT / "optimistic_drums.wav")
audio = audio.astype(np.float32) / 32767
DUR = len(audio) / SR
N = int(np.ceil(DUR * FPS))

struct = json.loads((OUT.parent / "structure.json").read_text())
MOD_SEC = struct["modulation_sec"]
TITLE = struct["title"]
print(f"duration {DUR:.2f}s -> {N} frames, modulation at {MOD_SEC:.2f}s")

# per-frame loudness (RMS) and log spectrum
hop = SR // FPS
rms = np.array([np.sqrt(np.mean(audio[i * hop:(i + 1) * hop] ** 2))
                if (i + 1) * hop <= len(audio) else 0 for i in range(N)])
rms = rms / rms.max()

NB = 32
freqs = np.fft.rfftfreq(2048, 1 / SR)
edges = np.geomspace(40, 4000, NB + 1)
band_masks = [(freqs >= edges[b]) & (freqs < edges[b + 1]) for b in range(NB)]
low_mask = (freqs >= 40) & (freqs < 120)

# One FFT pass feeds both the spectrum ring and the onset detector; the moody
# template computed the same FFT twice.
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

# kick onsets: sudden rises in low-band energy
flux = np.maximum(low - np.roll(low, 1), 0)
thresh = np.convolve(flux, np.ones(9) / 9, mode="same") * 1.6 + 0.02 * flux.max()
onsets = flux > thresh
pulse = np.zeros(N)
for i in range(N):
    pulse[i] = 1.0 if onsets[i] else (pulse[i - 1] * 0.78 if i else 0)
print("kick onsets detected:", int(onsets.sum()))

# key-change envelopes: `lift` is the permanent palette shift, `bloom` the
# one-off flash right at the modulation
t_all = np.arange(N) / FPS
lift = np.clip((t_all - MOD_SEC) / 1.5, 0, 1)
bloom = np.where(t_all >= MOD_SEC, np.exp(-(t_all - MOD_SEC) * 1.1), 0.0)

# background: warm sunrise gradient, cooling upward, brighter after the lift
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
g = yy / H
bg_a = np.stack([16 + 30 * g, 12 + 20 * g, 24 + 14 * g], axis=-1)   # G major
bg_b = np.stack([26 + 44 * g, 22 + 34 * g, 20 + 18 * g], axis=-1)   # C major

# particles
rng = np.random.default_rng(7)
P = 260
px = rng.uniform(0, W, P)
py = rng.uniform(0, H, P)
pz = rng.uniform(0.3, 1.0, P)
pph = rng.uniform(0, 2 * np.pi, P)

ff = subprocess.Popen([
    ffmpeg_exe(), "-y", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", str(OUT / "optimistic_drums.wav"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
    "-c:a", "aac", "-b:a", "192k", "-shortest",
    str(OUT / "optimistic_drums_visualizer.mp4"),
], stdin=subprocess.PIPE)

cx, cy = W / 2, H * 0.44
for i in range(N):
    t = i / FPS
    L, B = lift[i], bloom[i]

    frame = bg_a * (1 - L) + bg_b * L
    frame = frame + 4 * np.sin(t * 0.35)          # slow breathing
    frame = frame + 30 * B                        # modulation flash

    img = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)

    # central orb: amber in G, gold-white in C
    r = 70 + 70 * rms[i] + 45 * pulse[i] + 25 * B
    base = np.array([210, 130, 45]) * (1 - L) + np.array([255, 195, 90]) * L
    for k, a in ((2.2, 18), (1.6, 40), (1.15, 90), (1.0, 170)):
        rr = r * k
        col = tuple(int(c * a / 170) for c in base)
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col)
    glow = glow.filter(ImageFilter.GaussianBlur(28))
    img = Image.fromarray(np.clip(np.asarray(img).astype(np.int16)
                                  + np.asarray(glow).astype(np.int16), 0, 255).astype(np.uint8))

    d = ImageDraw.Draw(img, "RGBA")

    # expanding ring on each kick
    if pulse[i] > 0.05:
        rr = r + 40 + 260 * (1 - pulse[i])
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=(255, 235, 195, int(200 * pulse[i])), width=3)

    # one big ring launched by the key change
    if B > 0.02:
        rr = r + 60 + 900 * (1 - B)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=(255, 250, 235, int(220 * B)), width=5)

    # spectrum ring, teal against the warm background
    for b in range(NB):
        ang = -np.pi / 2 + 2 * np.pi * b / NB + t * 0.08
        r0 = r + 30
        r1 = r0 + 25 + 110 * spec[i, b]
        x0, y0 = cx + r0 * np.cos(ang), cy + r0 * np.sin(ang)
        x1, y1 = cx + r1 * np.cos(ang), cy + r1 * np.sin(ang)
        alpha = int(min(255, 90 + 140 * spec[i, b] + 40 * B))
        col = (int(90 + 60 * L), int(220 + 20 * L), int(200 + 30 * L), alpha)
        d.line([x0, y0, x1, y1], fill=col, width=4)

    # particles drifting upward, twinkling; they rise faster after the lift
    px[:] = (px + 0.25 * pz * np.sin(pph + t * 0.3)) % W
    py[:] = (py - (0.35 + 0.35 * L) * pz) % H
    tw = 0.5 + 0.5 * np.sin(t * 1.7 + pph)
    for j in range(P):
        s = 1.2 + 2.5 * pz[j]
        a = int(min(255, 40 + 150 * tw[j] * pz[j] + 50 * B))
        d.ellipse([px[j] - s, py[j] - s, px[j] + s, py[j] + s], fill=(255, 240, 210, a))

    # bottom waveform strip
    seg = audio[i * hop:i * hop + hop * 2]
    if len(seg) > 0:
        xs = np.linspace(80, W - 80, len(seg))
        ys = H - 90 + seg * 45
        d.line(list(zip(xs[::8], ys[::8])), fill=(255, 205, 150, 130), width=2)

    # title fade in/out
    fade = min(1, t / 3, (DUR - t) / 3)
    d.text((80, H - 60), TITLE, fill=(255, 240, 220, int(190 * fade)))

    ff.stdin.write(np.asarray(img).tobytes())
    if i % 240 == 0:
        print("frame", i)

ff.stdin.close()
ff.wait()
print("done")
