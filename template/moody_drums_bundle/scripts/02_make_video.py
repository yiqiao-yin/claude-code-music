import shutil
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "assets"


def ffmpeg_exe():
    """System ffmpeg if present, else the static binary from imageio-ffmpeg."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    from imageio_ffmpeg import get_ffmpeg_exe
    return get_ffmpeg_exe()


SR, audio = wavfile.read(OUT / "moody_drums.wav")
audio = audio.astype(np.float32) / 32767
DUR = len(audio) / SR
W, H, FPS = 1280, 720, 24
N = int(np.ceil(DUR * FPS))
print(f"duration {DUR:.2f}s -> {N} frames")

# per-frame loudness (RMS) and low-band energy
hop = SR // FPS
rms = np.array([np.sqrt(np.mean(audio[i*hop:(i+1)*hop] ** 2)) if (i+1)*hop <= len(audio) else 0 for i in range(N)])
rms = rms / rms.max()
# spectrum per frame (32 bands, log spaced)
NB = 32
freqs = np.fft.rfftfreq(2048, 1 / SR)
edges = np.geomspace(40, 4000, NB + 1)
spec = np.zeros((N, NB))
for i in range(N):
    seg = audio[i*hop:i*hop+2048]
    if len(seg) < 2048: seg = np.pad(seg, (0, 2048 - len(seg)))
    mag = np.abs(np.fft.rfft(seg * np.hanning(2048)))
    for b in range(NB):
        m = (freqs >= edges[b]) & (freqs < edges[b+1])
        spec[i, b] = mag[m].mean() if m.any() else 0
spec = np.log1p(spec * 20); spec /= spec.max()
# smooth
for i in range(1, N):
    spec[i] = np.maximum(spec[i], spec[i-1] * 0.85)
    rms[i] = max(rms[i], rms[i-1] * 0.9)

# --- kick onset detection: low-band (40-120 Hz) energy, flag sudden rises ---
low = np.zeros(N)
for i in range(N):
    seg = audio[i*hop:i*hop+2048]
    if len(seg) < 2048: seg = np.pad(seg, (0, 2048 - len(seg)))
    mag = np.abs(np.fft.rfft(seg * np.hanning(2048)))
    low[i] = mag[(freqs >= 40) & (freqs < 120)].mean()
flux = np.maximum(low - np.roll(low, 1), 0)          # positive change only
thresh = np.convolve(flux, np.ones(9) / 9, mode="same") * 1.6 + 0.02 * flux.max()
onsets = flux > thresh
pulse = np.zeros(N)                                    # decaying flash per onset
for i in range(N):
    pulse[i] = 1.0 if onsets[i] else (pulse[i-1] * 0.78 if i else 0)
print("kick onsets detected:", int(onsets.sum()))

# background gradient (static)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
bg = np.zeros((H, W, 3), np.float32)
g = yy / H
bg[..., 0] = 8 + 14 * g
bg[..., 1] = 6 + 8 * g
bg[..., 2] = 20 + 30 * g

# particles
rng = np.random.default_rng(7)
P = 220
px = rng.uniform(0, W, P); py = rng.uniform(0, H, P)
pz = rng.uniform(0.3, 1.0, P)          # depth -> size/speed
pph = rng.uniform(0, 2*np.pi, P)

ff = subprocess.Popen([
    ffmpeg_exe(), "-y", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", str(OUT / "moody_drums.wav"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
    "-c:a", "aac", "-b:a", "192k", "-shortest",
    str(OUT / "moody_drums_visualizer.mp4")
], stdin=subprocess.PIPE)

cx, cy = W / 2, H * 0.44
for i in range(N):
    t = i / FPS
    frame = bg.copy()
    # slow colour breathing
    frame[..., 2] += 6 * np.sin(t * 0.25)

    img = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)

    # central orb, radius follows loudness
    r = 70 + 70 * rms[i] + 45 * pulse[i]
    for k, a in ((2.2, 18), (1.6, 40), (1.15, 90), (1.0, 170)):
        rr = r * k
        col = (int(60 * a / 170), int(40 * a / 170), int(150 * a / 170))
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col)
    glow = glow.filter(ImageFilter.GaussianBlur(28))
    img = Image.fromarray(np.clip(np.asarray(img).astype(np.int16) + np.asarray(glow).astype(np.int16), 0, 255).astype(np.uint8))

    d = ImageDraw.Draw(img, "RGBA")
    # expanding ring on each kick
    if pulse[i] > 0.05:
        rr = r + 40 + 260 * (1 - pulse[i])
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(230, 200, 255, int(200 * pulse[i])), width=3)
    # spectrum ring around the orb
    for b in range(NB):
        ang = -np.pi / 2 + 2 * np.pi * b / NB + t * 0.05
        r0 = r + 30
        r1 = r0 + 25 + 110 * spec[i, b]
        x0, y0 = cx + r0 * np.cos(ang), cy + r0 * np.sin(ang)
        x1, y1 = cx + r1 * np.cos(ang), cy + r1 * np.sin(ang)
        alpha = int(90 + 140 * spec[i, b])
        d.line([x0, y0, x1, y1], fill=(170, 150, 255, alpha), width=4)

    # particles drifting upward, twinkling
    px[:] = (px + 0.25 * pz * np.sin(pph + t * 0.3)) % W
    py[:] = (py - 0.35 * pz) % H
    tw = 0.5 + 0.5 * np.sin(t * 1.7 + pph)
    for j in range(P):
        s = 1.2 + 2.5 * pz[j]
        a = int(40 + 150 * tw[j] * pz[j])
        d.ellipse([px[j] - s, py[j] - s, px[j] + s, py[j] + s], fill=(200, 200, 255, a))

    # bottom waveform strip
    seg = audio[i*hop:i*hop+hop*2]
    if len(seg) > 0:
        xs = np.linspace(80, W - 80, len(seg))
        ys = H - 90 + seg * 45
        d.line(list(zip(xs[::8], ys[::8])), fill=(150, 130, 220, 120), width=2)

    # title fade in/out
    fade = min(1, t / 3, (DUR - t) / 3)
    d.text((80, H - 60), "moody (with drums)  |  A minor, 68 BPM", fill=(210, 205, 240, int(180 * fade)))

    ff.stdin.write(np.asarray(img).tobytes())
    if i % 240 == 0: print("frame", i)

ff.stdin.close(); ff.wait()
print("done")
