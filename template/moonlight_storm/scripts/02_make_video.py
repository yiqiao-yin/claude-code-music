"""Render the "moonlight storm" visualizer.

Stereo in, summed to mono for analysis. `pulse` comes from the downbeat: this
piece has continuous figuration, which saturates the onset detector exactly as
`mozart_sonata_allegro` did.

The new scene element is **the harmonic bloom**. Every note in the score flies
outward from the centre at an angle set by its pitch class, fading over the same
3.4 seconds the sustain pedal lets it ring. Because the angle is the pitch class,
each chord shows as a distinct set of arms, and a chord change visibly rotates the
whole flower. Density is the texture: sparse triplets at the start, a dense burst
at the storm, almost nothing at the end. It is the pedal made visible.
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


SR, raw = wavfile.read(OUT / "moonlight_storm.wav")
stereo = raw.astype(np.float32) / 32767
audio = stereo.mean(axis=1) if stereo.ndim > 1 else stereo
DUR = len(audio) / SR
N = int(np.ceil(DUR * FPS))

st = json.loads((OUT.parent / "structure.json").read_text())
SEC_STARTS, SEC_LABELS = st["section_starts_sec"], st["section_labels"]
BAR_SEC, BARS, CHORDS = st["bar_sec"], st["bars"], st["chords"]
TEXTURE = st["texture"]
DYNW = np.array(st["dynamics"])
RING = st["pedal_ring_sec"]
NOTES = st["notes"]
TITLE = st["title"]
print(f"[moonlight_storm] {DUR:.2f}s -> {N} frames, "
      f"{'stereo' if stereo.ndim > 1 else 'mono'}, {len(NOTES)} notes")

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
spec = np.zeros((N, NB))
win = np.hanning(2048)
for i in range(N):
    seg = audio[i * hop:i * hop + 2048]
    if len(seg) < 2048:
        seg = np.pad(seg, (0, 2048 - len(seg)))
    mag = np.abs(np.fft.rfft(seg * win))
    for b, m in enumerate(band_masks):
        spec[i, b] = mag[m].mean() if m.any() else 0
spec = np.log1p(spec * 20)
spec /= spec.max()
for i in range(1, N):
    spec[i] = np.maximum(spec[i], spec[i - 1] * 0.85)
    rms[i] = max(rms[i], rms[i - 1] * 0.9)

t_all = np.arange(N) / FPS
pulse = np.exp(-(t_all % BAR_SEC) * 2.6)
print("pulse from the downbeat: continuous figuration saturates the detector")

bar_idx = np.clip((t_all / BAR_SEC).astype(int), 0, BARS - 1)
sec_idx = np.clip(np.searchsorted(SEC_STARTS, t_all, side="right") - 1, 0, len(SEC_STARTS) - 1)
bloom_ev = np.zeros(N)
for s in SEC_STARTS[1:]:
    bloom_ev = np.maximum(bloom_ev, np.where(t_all >= s, np.exp(-(t_all - s) * 1.2), 0.0))

# the written swell drives the palette as well as the ear
dyn = np.array([DYNW[b] for b in bar_idx])
k = int(1.1 * FPS)
dyn = np.convolve(dyn, np.ones(k) / k, mode="same")
dyn = (dyn - dyn.min()) / max(float(np.ptp(dyn)), 1e-9)

# background: moonlight — deep blue-black, silvering toward the horizon
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
g = yy / H
bg = np.stack([9 + 16 * g, 12 + 20 * g, 26 + 30 * g], axis=-1)

rng = np.random.default_rng(7)
P = 180
px, py = rng.uniform(0, W, P), rng.uniform(0, H, P)
pz, pph = rng.uniform(0.3, 1.0, P), rng.uniform(0, 2 * np.pi, P)

# --- the harmonic bloom -------------------------------------------------------
NT = np.array([n[0] for n in NOTES])            # start times
NM = np.array([n[1] for n in NOTES])            # midi
order = np.argsort(NT)
NT, NM = NT[order], NM[order]
# angle from pitch class, radius speed from octave
NANG = -np.pi / 2 + (NM % 12) * (2 * np.pi / 12)
NSPD = 46 + 26 * np.clip((NM - 30) / 58.0, 0, 1)

ff = subprocess.Popen([
    ffmpeg_exe(), "-y", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", str(OUT / "moonlight_storm.wav"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
    "-c:a", "aac", "-b:a", "192k", "-shortest",
    str(OUT / "moonlight_storm_visualizer.mp4"),
], stdin=subprocess.PIPE)

cx, cy = W / 2, H * 0.46
for i in range(N):
    t = i / FPS
    B, Dy, bi, si = bloom_ev[i], dyn[i], bar_idx[i], sec_idx[i]

    frame = bg + 16 * B + np.array([16, 10, 4]) * Dy
    img = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8))

    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    r = 30 + 34 * rms[i] + 20 * Dy + 12 * pulse[i] + 12 * B
    base = np.array([120, 148, 210]) * (1 - Dy) + np.array([228, 208, 216]) * Dy
    for k2, a in ((2.4, 13), (1.7, 33), (1.2, 80), (1.0, 164)):
        rr = r * k2
        gd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                   fill=tuple(int(min(255, c) * a / 164) for c in base))
    glow = glow.filter(ImageFilter.GaussianBlur(30))
    img = Image.fromarray(np.clip(np.asarray(img).astype(np.int16)
                                  + np.asarray(glow).astype(np.int16), 0, 255).astype(np.uint8))

    d = ImageDraw.Draw(img, "RGBA")

    # --- the harmonic bloom: every ringing note, flying outward ---
    lo = np.searchsorted(NT, t - RING)
    hi = np.searchsorted(NT, t)
    for j in range(lo, hi):
        age = t - NT[j]
        if age < 0:
            continue
        life = age / RING
        rad = r + 34 + NSPD[j] * age
        if rad > 660:
            continue
        ca, sa = np.cos(NANG[j]), np.sin(NANG[j])
        # a streak, not a dot: the tail is where the note was a moment ago, which
        # reads as motion and survives against the glow
        tail = max(8.0, NSPD[j] * 0.16)
        x0, y0 = cx + rad * ca, cy + rad * sa
        x1, y1 = cx + (rad - tail) * ca, cy + (rad - tail) * sa
        al = int(238 * (1 - life) ** 1.2)
        if al < 8:
            continue
        # higher notes silver, lower notes blue
        h = float(np.clip((NM[j] - 34) / 54.0, 0, 1))
        col = (int(132 + 118 * h), int(160 + 82 * h), int(220 + 20 * h), al)
        d.line([x1, y1, x0, y0], fill=col, width=int(1 + 3 * (1 - life)))
        if life < 0.35:
            sdot = 2.4 * (1 - life / 0.35)
            d.ellipse([x0 - sdot, y0 - sdot, x0 + sdot, y0 + sdot],
                      fill=col[:3] + (min(255, al + 30),))

    if pulse[i] > 0.05:
        rr = r + 26 + 150 * (1 - pulse[i])
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=(206, 220, 250, int(90 * pulse[i])), width=2)
    if B > 0.02:
        rr = r + 50 + 700 * (1 - B)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  outline=(226, 232, 250, int(160 * B)), width=3)

    for b in range(NB):
        ang = -np.pi / 2 + 2 * np.pi * b / NB - t * 0.02
        r0 = r + 18
        r1 = r0 + 14 + 74 * spec[i, b]
        d.line([cx + r0 * np.cos(ang), cy + r0 * np.sin(ang),
                cx + r1 * np.cos(ang), cy + r1 * np.sin(ang)],
               fill=(int(140 + 70 * Dy), int(160 + 50 * Dy), 226,
                     int(min(255, 70 + 110 * spec[i, b] + 40 * B))), width=3)

    px[:] = (px + 0.12 * pz * np.sin(pph + t * 0.2)) % W
    py[:] = (py - 0.13 * pz) % H
    tw = 0.5 + 0.5 * np.sin(t * 0.8 + pph)
    for j in range(P):
        s = 0.9 + 1.7 * pz[j]
        al = int(min(255, 22 + 100 * tw[j] * pz[j] + 30 * B))
        d.ellipse([px[j] - s, py[j] - s, px[j] + s, py[j] + s], fill=(222, 232, 252, al))

    if stereo.ndim > 1:
        L = stereo[i * hop:i * hop + hop * 2, 0]
        Rr = stereo[i * hop:i * hop + hop * 2, 1]
        if len(L) > 0:
            xs = np.linspace(90, W - 90, len(L))
            d.line(list(zip(xs[::8], H - 74 + L[::8] * 34)), fill=(160, 180, 232, 110), width=2)
            d.line(list(zip(xs[::8], H - 40 + Rr[::8] * 34)),
                   fill=(206, 200, 226, 110), width=2)

    fade = min(1, t / 3, (DUR - t) / 4)
    d.text((80, 44), SEC_LABELS[si], font=FONT_SEC, fill=(232, 236, 250, int(230 * fade)))
    d.text((82, 80), "%s   ·   %s   ·   bar %d / %d"
           % (CHORDS[bi], TEXTURE[bi], bi + 1, BARS),
           font=FONT_CH, fill=(158, 174, 208, int(175 * fade)))
    d.text((80, H - 16), TITLE, fill=(198, 208, 232, int(155 * fade)))

    ff.stdin.write(np.asarray(img).tobytes())
    if i % 240 == 0:
        print("frame", i)

ff.stdin.close()
ff.wait()
print("done")
