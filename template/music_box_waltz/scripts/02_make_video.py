"""Render the "music box waltz" visualizer.

Same framework as the other bundles: per-frame RMS, 32-band log spectrum and
low-band onset detection off the WAV, Pillow frames, raw RGB piped to ffmpeg.
What's specific to this one:

  * a warm antique palette — dusty rose and sepia rather than anything cold
  * three beat markers orbiting the centre, completing one revolution per bar
    with the current beat enlarged. This is the first 3/4 bundle in the repo and
    the orbit is what makes the meter visible: you can count 1-2-3 off the screen.
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


SR, audio = wavfile.read(OUT / "music_box_waltz.wav")
audio = audio.astype(np.float32) / 32767
DUR = len(audio) / SR
N = int(np.ceil(DUR * FPS))

struct = json.loads((OUT.parent / "structure.json").read_text())
SEC_STARTS = struct["section_starts_sec"]
SEC_LABELS = struct["section_labels"]
BAR_SEC = struct["bar_sec"]
BEAT_SEC = struct["beat_sec"]
BPB = struct["beats_per_bar"]
BARS = struct["bars"]
CHORDS = struct["chords"]
DRUMS_IN = struct["drums_in_sec"]
VARIATION = struct["variation_sec"]
TITLE = struct["title"]
print(f"duration {DUR:.2f}s -> {N} frames, {BARS} bars of {BPB}/4")

FONT_SEC = ImageFont.load_default(size=28)
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
pulse = np.zeros(N)
for i in range(N):
    pulse[i] = 1.0 if onsets[i] else (pulse[i - 1] * 0.78 if i else 0)
print("onsets detected:", int(onsets.sum()))

t_all = np.arange(N) / FPS
bar_idx = np.clip((t_all / BAR_SEC).astype(int), 0, BARS - 1)
sec_idx = np.searchsorted(SEC_STARTS, t_all, side="right") - 1
bloom = np.zeros(N)
for start in SEC_STARTS[1:]:
    bloom = np.maximum(bloom, np.where(t_all >= start, np.exp(-(t_all - start) * 1.3), 0.0))
warmth = np.clip((t_all - DRUMS_IN) / 3.0, 0, 1)
lift = np.clip((t_all - VARIATION) / 2.5, 0, 1) * np.clip((VARIATION + 11 - t_all) / 2.5, 0, 1)

# background: warm antique, lighter toward the bottom like aged paper
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
g = yy / H
bg = np.stack([26 + 26 * g, 18 + 18 * g, 20 + 14 * g], axis=-1)

rng = np.random.default_rng(7)
P = 230
px = rng.uniform(0, W, P)
py = rng.uniform(0, H, P)
pz = rng.uniform(0.3, 1.0, P)
pph = rng.uniform(0, 2 * np.pi, P)

ff = subprocess.Popen([
    ffmpeg_exe(), "-y", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", str(OUT / "music_box_waltz.wav"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
    "-c:a", "aac", "-b:a", "192k", "-shortest",
    str(OUT / "music_box_waltz_visualizer.mp4"),
], stdin=subprocess.PIPE)

cx, cy = W / 2, H * 0.43
ORBIT_R = 250
for i in range(N):
    t = i / FPS
    B, Wm, L, bi, si = bloom[i], warmth[i], lift[i], bar_idx[i], max(0, sec_idx[i])
    in_bar = (t % BAR_SEC) / BAR_SEC          # 0..1 through the bar
    beat = int((t % BAR_SEC) / BEAT_SEC) % BPB

    frame = bg + 20 * B + np.array([6, 4, 0]) * Wm + np.array([4, 3, 5]) * L
    img = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))

    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    r = 54 + 58 * rms[i] + 30 * pulse[i] + 22 * B
    base = np.array([224, 168, 126]) + np.array([16, 20, 10]) * Wm + np.array([10, 6, 24]) * L
    for k, a in ((2.2, 16), (1.6, 38), (1.15, 86), (1.0, 168)):
        rr = r * k
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                   fill=tuple(int(min(255, c) * a / 168) for c in base))
    glow = glow.filter(ImageFilter.GaussianBlur(30))
    img = Image.fromarray(np.clip(np.asarray(img).astype(np.int16)
                                  + np.asarray(glow).astype(np.int16), 0, 255).astype(np.uint8))

    d = ImageDraw.Draw(img, "RGBA")

    if pulse[i] > 0.05:
        rr = r + 40 + 250 * (1 - pulse[i])
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=(255, 226, 198, int(180 * pulse[i])), width=3)
    if B > 0.02:
        rr = r + 60 + 820 * (1 - B)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=(255, 244, 228, int(195 * B)), width=4)

    # spectrum ring, dusty rose against the warm ground
    for b in range(NB):
        ang = -np.pi / 2 + 2 * np.pi * b / NB + t * 0.05
        r0 = r + 26
        r1 = r0 + 20 + 98 * spec[i, b]
        d.line([cx + r0 * np.cos(ang), cy + r0 * np.sin(ang),
                cx + r1 * np.cos(ang), cy + r1 * np.sin(ang)],
               fill=(214, 156, 168, int(min(255, 92 + 132 * spec[i, b] + 40 * B))), width=4)

    # --- the waltz: three markers, one turn per bar ---
    # The whole ring rotates once per bar, so the marker that is currently on
    # the beat sits at the top. Count 1-2-3 straight off the screen.
    d.ellipse([cx - ORBIT_R, cy - ORBIT_R, cx + ORBIT_R, cy + ORBIT_R],
              outline=(190, 150, 140, 55), width=1)
    for b in range(BPB):
        ang = -np.pi / 2 + 2 * np.pi * (b / BPB - in_bar)
        mx, my = cx + ORBIT_R * np.cos(ang), cy + ORBIT_R * np.sin(ang)
        if b == beat:
            frac = (t % BEAT_SEC) / BEAT_SEC
            s = 15 - 5 * frac
            col = (255, 236, 206, 240) if b == 0 else (246, 208, 178, 210)
            d.ellipse([mx - s - 5, my - s - 5, mx + s + 5, my + s + 5],
                      outline=col[:3] + (110,), width=2)
        else:
            s, col = 6, (196, 158, 146, 120)
        d.ellipse([mx - s, my - s, mx + s, my + s], fill=col)

    # dust in the light
    px[:] = (px + 0.16 * pz * np.sin(pph + t * 0.24)) % W
    py[:] = (py - 0.17 * pz) % H
    tw = 0.5 + 0.5 * np.sin(t * 1.1 + pph)
    for j in range(P):
        s = 1.0 + 2.0 * pz[j]
        a = int(min(255, 30 + 128 * tw[j] * pz[j] + 40 * B))
        d.ellipse([px[j] - s, py[j] - s, px[j] + s, py[j] + s], fill=(255, 238, 214, a))

    seg = audio[i * hop:i * hop + hop * 2]
    if len(seg) > 0:
        xs = np.linspace(80, W - 80, len(seg))
        ys = H - 78 + seg * 40
        d.line(list(zip(xs[::8], ys[::8])), fill=(226, 190, 176, 120), width=2)

    fade = min(1, t / 3, (DUR - t) / 3)
    d.text((80, 46), SEC_LABELS[si], font=FONT_SEC, fill=(250, 234, 216, int(232 * fade)))
    d.text((82, 84), "%s   ·   bar %d / %d   ·   beat %d of %d"
           % (CHORDS[bi], bi + 1, BARS, beat + 1, BPB),
           font=FONT_CH, fill=(212, 172, 160, int(180 * fade)))
    d.text((80, H - 34), TITLE, fill=(232, 204, 190, int(170 * fade)))

    ff.stdin.write(np.asarray(img).tobytes())
    if i % 240 == 0:
        print("frame", i)

ff.stdin.close()
ff.wait()
print("done")
