"""Render the "mozart sonata allegro" visualizer.

Same framework as the other bundles, with three things specific to this one:

  * **stereo input.** The first stereo bundle in the repo. Analysis sums to mono
    (an FFT of a stereo pair is not meaningful), but the waveform strip draws
    both channels so the panning is visible.
  * **`pulse` from the downbeat, not the detector** — for the opposite reason to
    `church_passacaglia`. There the organ had no transients and the detector fired
    on noise; here the Alberti bass has an attack every 217 ms, so the detector
    saturates and the ring never goes out. Either way the fix is the same: take
    the event from the score.
  * **the tonal journey** — a plot of how far the harmony has travelled from home,
    drawn across the frame. Sonata form *is* a journey out and back, and this
    draws it: the line leaves home for the second subject, wanders through the
    development, and comes back for the recapitulation.
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


SR, raw = wavfile.read(OUT / "mozart_sonata_allegro.wav")
stereo = raw.astype(np.float32) / 32767
audio = stereo.mean(axis=1) if stereo.ndim > 1 else stereo
DUR = len(audio) / SR
N = int(np.ceil(DUR * FPS))

struct = json.loads((OUT.parent / "structure.json").read_text())
SEC_STARTS = struct["section_starts_sec"]
SEC_LABELS = struct["section_labels"]
SEC_KEYS = struct["section_keys"]
SEC_DIST = struct["section_distance"]
BAR_SEC = struct["bar_sec"]
BARS = struct["bars"]
CHORDS = struct["chords"]
DYN = np.array(struct["dynamics"])
TITLE = struct["title"]
print(f"[mozart_sonata_allegro] {DUR:.2f}s -> {N} frames, "
      f"{'stereo' if stereo.ndim > 1 else 'mono'}")

FONT_SEC = ImageFont.load_default(size=27)
FONT_CH = ImageFont.load_default(size=16)
FONT_TAG = ImageFont.load_default(size=13)

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

if struct.get("pulse_source", "onsets") == "downbeat":
    pulse = np.exp(-(t_all % BAR_SEC) * 3.2)
    print("pulse from the downbeat: the detector saturates here (%d onsets on %d "
          "frames — the Alberti bass never stops)" % (int(onsets.sum()), N))
else:
    pulse = np.zeros(N)
    for i in range(N):
        pulse[i] = 1.0 if onsets[i] else (pulse[i - 1] * 0.78 if i else 0)
    print("onsets detected:", int(onsets.sum()))

bar_idx = np.clip((t_all / BAR_SEC).astype(int), 0, BARS - 1)
sec_idx = np.clip(np.searchsorted(SEC_STARTS, t_all, side="right") - 1, 0, len(SEC_STARTS) - 1)
bloom = np.zeros(N)
for start in SEC_STARTS[1:]:
    bloom = np.maximum(bloom, np.where(t_all >= start, np.exp(-(t_all - start) * 1.3), 0.0))

# The score's own dynamics drive the visual weight. Loud-and-soft is the thing
# that separates a piano from a harpsichord, so it should be visible.
dyn = np.array([DYN[b] for b in bar_idx])
k = int(0.8 * FPS)
dyn = np.convolve(dyn, np.ones(k) / k, mode="same")
dyn = (dyn - dyn.min()) / max(float(np.ptp(dyn)), 1e-9)

# distance from the home key, smoothed
dist_step = np.array([SEC_DIST[s] for s in sec_idx])
kk = int(1.6 * FPS)
dist = np.convolve(dist_step, np.ones(kk) / kk, mode="same")

# background: warm paper and candle, a salon rather than a nave
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
g = yy / H
bg = np.stack([24 + 28 * g, 20 + 22 * g, 26 + 14 * g], axis=-1)

rng = np.random.default_rng(7)
P = 210
px = rng.uniform(0, W, P)
py = rng.uniform(0, H, P)
pz = rng.uniform(0.3, 1.0, P)
pph = rng.uniform(0, 2 * np.pi, P)

# --- the tonal journey plot -------------------------------------------------
JX0, JX1, JY0, JY1 = 96, W - 96, 470, 556
jx = np.linspace(JX0, JX1, N)
jy = JY1 - dist * (JY1 - JY0)

ff = subprocess.Popen([
    ffmpeg_exe(), "-y", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", str(OUT / "mozart_sonata_allegro.wav"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
    "-c:a", "aac", "-b:a", "192k", "-shortest",
    str(OUT / "mozart_sonata_allegro_visualizer.mp4"),
], stdin=subprocess.PIPE)

cx, cy = W / 2, H * 0.30
for i in range(N):
    t = i / FPS
    B, Dy, bi, si = bloom[i], dyn[i], bar_idx[i], sec_idx[i]

    frame = bg + 20 * B + np.array([10, 7, 2]) * Dy
    img = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))

    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    # size follows loudness *and* the written dynamic — the crescendo through the
    # development is in the score, not only in the waveform
    r = 40 + 54 * rms[i] + 30 * Dy + 22 * pulse[i] + 18 * B
    base = np.array([214, 176, 128]) + np.array([32, 30, 22]) * Dy
    for k2, a in ((2.3, 15), (1.65, 36), (1.2, 84), (1.0, 166)):
        rr = r * k2
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                   fill=tuple(int(min(255, c) * a / 166) for c in base))
    glow = glow.filter(ImageFilter.GaussianBlur(30))
    img = Image.fromarray(np.clip(np.asarray(img).astype(np.int16)
                                  + np.asarray(glow).astype(np.int16), 0, 255).astype(np.uint8))

    d = ImageDraw.Draw(img, "RGBA")

    if pulse[i] > 0.05:
        rr = r + 32 + 200 * (1 - pulse[i])
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=(248, 228, 196, int(150 * pulse[i])), width=2)
    if B > 0.02:
        rr = r + 56 + 760 * (1 - B)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=(250, 240, 222, int(190 * B)), width=4)

    for b in range(NB):
        ang = -np.pi / 2 + 2 * np.pi * b / NB + t * 0.045
        r0 = r + 22
        r1 = r0 + 16 + 92 * spec[i, b]
        d.line([cx + r0 * np.cos(ang), cy + r0 * np.sin(ang),
                cx + r1 * np.cos(ang), cy + r1 * np.sin(ang)],
               fill=(190, 158, 200, int(min(255, 88 + 128 * spec[i, b] + 40 * B))), width=4)

    # --- the tonal journey: how far from home, over time ---
    d.line([JX0, JY1, JX1, JY1], fill=(150, 132, 120, 70), width=1)
    d.line([JX0, JY0, JX1, JY0], fill=(150, 132, 120, 40), width=1)
    d.text((JX0 - 10, JY1 - 7), "home", font=FONT_TAG, fill=(168, 150, 136, 130), anchor="rm")
    d.text((JX0 - 10, JY0 - 7), "away", font=FONT_TAG, fill=(168, 150, 136, 100), anchor="rm")
    for s in range(1, len(SEC_STARTS)):
        sx = JX0 + (SEC_STARTS[s] / DUR) * (JX1 - JX0)
        d.line([sx, JY0 - 6, sx, JY1 + 6], fill=(150, 132, 120, 45), width=1)
    pts = list(zip(jx[:i + 1:2], jy[:i + 1:2]))
    if len(pts) > 1:
        d.line(pts, fill=(244, 206, 150, 210), width=3)
    ahead = list(zip(jx[i::4], jy[i::4]))
    if len(ahead) > 1:
        d.line(ahead, fill=(150, 132, 120, 45), width=1)
    d.ellipse([jx[i] - 6, jy[i] - 6, jx[i] + 6, jy[i] + 6], fill=(255, 236, 200, 250))

    px[:] = (px + 0.20 * pz * np.sin(pph + t * 0.26)) % W
    py[:] = (py - 0.22 * pz) % H
    tw = 0.5 + 0.5 * np.sin(t * 1.3 + pph)
    for j in range(P):
        s = 1.0 + 1.9 * pz[j]
        a = int(min(255, 28 + 118 * tw[j] * pz[j] + 40 * B))
        d.ellipse([px[j] - s, py[j] - s, px[j] + s, py[j] + s], fill=(252, 236, 206, a))

    # both channels, so the panning is visible
    if stereo.ndim > 1:
        segL = stereo[i * hop:i * hop + hop * 2, 0]
        segR = stereo[i * hop:i * hop + hop * 2, 1]
        if len(segL) > 0:
            xs = np.linspace(90, W - 90, len(segL))
            d.line(list(zip(xs[::8], H - 84 + segL[::8] * 30)), fill=(196, 172, 220, 120), width=2)
            d.line(list(zip(xs[::8], H - 44 + segR[::8] * 30)), fill=(232, 194, 158, 120), width=2)
            d.text((72, H - 90), "L", font=FONT_TAG, fill=(196, 172, 220, 140), anchor="rm")
            d.text((72, H - 50), "R", font=FONT_TAG, fill=(232, 194, 158, 140), anchor="rm")

    fade = min(1, t / 3, (DUR - t) / 3)
    d.text((80, 42), SEC_LABELS[si], font=FONT_SEC, fill=(248, 236, 218, int(232 * fade)))
    d.text((82, 78), "%s   ·   %s   ·   bar %d / %d"
           % (CHORDS[bi], SEC_KEYS[si], bi + 1, BARS),
           font=FONT_CH, fill=(190, 168, 152, int(180 * fade)))
    d.text((80, H - 18), TITLE, fill=(216, 200, 184, int(160 * fade)))

    ff.stdin.write(np.asarray(img).tobytes())
    if i % 240 == 0:
        print("frame", i)

ff.stdin.close()
ff.wait()
print("done")
