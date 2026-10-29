#!/usr/bin/env python3
"""Check the actual render, not the timeline: every cut, black or frozen frames, flash frames, audio pops and level jumps.
usage: render_check.py PROXY.mp4 OUT_DIR [--cuts 12,101,150,...] [--per-sheet 6] [--music]
  PROXY.mp4  a small render of the timeline (finish-pass/scripts/resolve_proxy_render.py: 540x960 H.264)
  --cuts     record frames of the edit points (timeline frames from 0); default: detected from the picture
  --music    the render has music: don't flag quiet stretches as gaps
Flags (all with timecodes):
  BLACK   frames that are (near) black inside the edit
  FREEZE  6+ identical frames in a row (a held frame from a retime, a still, a missing render)
  FLASH   two cuts less than 3 frames apart (a 1-2 frame sliver)
  POP     a click at a cut: a sudden sample jump far above the audio around it
  LEVEL   speech level jumps more than 6 dB across a cut
  GAP     a silence longer than 0.8 s with speech on both sides (no music)
  LOUD    integrated loudness and true peak of the whole render (reported, not judged)
Writes OUT_DIR/cuts_NN.jpg (last and first frame of every cut, waveform +-1 s) and OUT_DIR/render_check.json.
Look at the sheets: they are what Tim will see and hear, unlike the source-side checks."""
import argparse, json, os, re, subprocess
import numpy as np
import cv2

ap = argparse.ArgumentParser()
ap.add_argument("proxy"); ap.add_argument("out")
ap.add_argument("--cuts", default=""); ap.add_argument("--per-sheet", type=int, default=6)
ap.add_argument("--music", action="store_true")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", a.proxy],
                               capture_output=True, text=True).stdout)
vs = next(s for s in pr["streams"] if s["codec_type"] == "video")
n_, d_ = vs["r_frame_rate"].split("/"); FPS = float(n_) / float(d_)
W, H = 135, 240
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.proxy, "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                     capture_output=True).stdout
F = np.frombuffer(raw, np.uint8)[: len(raw) // (W * H * 3) * W * H * 3].reshape(-1, H, W, 3)
G = F.mean(3)
aud = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", a.proxy, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                                   capture_output=True).stdout, np.int16).astype(np.float32) / 32768
SR = 16000
hop = SR // 100
env = 20 * np.log10(np.sqrt((aud[: len(aud) // hop * hop].reshape(-1, hop) ** 2).mean(1)) + 1e-9)
thr = np.percentile(env, 10) + 12
tc = lambda f: f"{int(f // FPS // 60):02d}:{int(f // FPS % 60):02d}:{int(f % FPS):02d}"
flags = []

d = np.abs(np.diff(G, axis=0)).mean((1, 2))
if a.cuts:
    cuts = [int(c) for c in a.cuts.split(",") if c]
else:                                          # detect: a big jump in picture relative to its neighbours
    med = np.array([np.median(d[max(0, i - 5):i + 6]) for i in range(len(d))])
    cuts = [i + 1 for i in range(len(d)) if d[i] > max(12, 4 * med[i])]
lum = G.mean((1, 2))
def spans(mask, minlen=1):
    out, k = [], 0
    while k < len(mask):
        if mask[k]:
            k0 = k
            while k < len(mask) and mask[k]:
                k += 1
            if k - k0 >= minlen:
                out.append((k0, k))
        k += 1
    return out
for s0, s1 in spans(lum < 12):
    if s0 > 2 and s1 < len(lum) - 3:
        flags.append({"t": tc(s0), "kind": "BLACK", "msg": f"{s1 - s0} black frame(s) from {s0}"})
for s0, s1 in spans(d < 0.15, 5):
    if lum[s0 + 1:s1 + 1].mean() >= 12:                     # a black stretch is reported above
        flags.append({"t": tc(s0 + 1), "kind": "FREEZE", "msg": f"{s1 - s0 + 1} identical frames from {s0 + 1}"})
for c1, c2 in zip(cuts, cuts[1:]):
    if c2 - c1 < 3:
        flags.append({"t": tc(c1), "kind": "FLASH", "msg": f"cuts at {c1} and {c2}: {c2 - c1}-frame sliver"})
rows, info = [], []
for c in cuts:
    s = int(c / FPS * SR)
    w = aud[max(0, s - 160):s + 160]
    if len(w) > 20:
        dd = np.abs(np.diff(w)); base = np.median(np.abs(np.diff(aud[max(0, s - 8000):s + 8000]))) + 1e-6
        if dd.max() > 25 * base and dd.max() > 0.05:
            flags.append({"t": tc(c), "kind": "POP", "msg": f"sample jump {dd.max():.3f} ({dd.max() / base:.0f}x the surroundings)"})
    k = int(c / FPS * 100)
    pre, post = env[max(0, k - 50):k], env[k:k + 50]
    pre_s, post_s = pre[pre > thr], post[post > thr]
    if len(pre_s) > 10 and len(post_s) > 10 and abs(np.median(pre_s) - np.median(post_s)) > 6:
        flags.append({"t": tc(c), "kind": "LEVEL", "msg": f"speech {np.median(pre_s):.0f} -> {np.median(post_s):.0f} dB across the cut"})
    A_ = cv2.resize(F[max(0, c - 1)], (108, 192)); B_ = cv2.resize(F[min(len(F) - 1, c)], (108, 192))
    seg = env[max(0, k - 100):k + 100]
    wp = np.full((192, 300, 3), 24, np.uint8)
    if len(seg) > 1:
        lo, hi = thr - 25, max(env.max(), thr + 20)
        xs = np.linspace(0, 299, len(seg)).astype(int); ys = (182 - (np.clip(seg, lo, hi) - lo) / (hi - lo) * 172).astype(int)
        for i in range(1, len(seg)):
            cv2.line(wp, (xs[i - 1], ys[i - 1]), (xs[i], ys[i]), (80, 200, 255) if seg[i] > thr else (110, 110, 110), 1)
        cv2.line(wp, (int(300 * min(100, k) / len(seg)), 0), (int(300 * min(100, k) / len(seg)), 192), (0, 0, 255), 1)
    lab = np.zeros((22, 516, 3), np.uint8)
    cv2.putText(lab, f"cut {c} ({tc(c)})", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    rows.append(np.vstack([lab, np.hstack([A_, B_, wp])]))
if not a.music:
    sil = env <= thr; k = 0
    while k < len(sil):
        if sil[k]:
            k0 = k
            while k < len(sil) and sil[k]:
                k += 1
            if k - k0 > 80 and k0 > 100 and k < len(sil) - 100:
                flags.append({"t": tc(k0 / 100 * FPS), "kind": "GAP", "msg": f"{(k - k0) / 100:.2f}s of silence mid-edit (a break, or a gap to close?)"})
        k += 1
lo = subprocess.run(["ffmpeg", "-v", "info", "-nostats", "-i", a.proxy, "-af", "ebur128=peak=true", "-f", "null", "-"],
                    capture_output=True, text=True).stderr
I = re.findall(r"I:\s+(-?[\d.]+) LUFS", lo); TP = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", lo)
flags.append({"t": "-", "kind": "LOUD", "msg": f"integrated {I[-1] if I else '?'} LUFS, true peak {TP[-1] if TP else '?'} dBFS"})
for i in range(0, len(rows), a.per_sheet):
    cv2.imwrite(f"{a.out}/cuts_{i // a.per_sheet + 1:02d}.jpg", np.vstack(rows[i:i + a.per_sheet]), [cv2.IMWRITE_JPEG_QUALITY, 75])
json.dump({"fps": FPS, "frames": len(F), "cuts": cuts, "flags": flags}, open(f"{a.out}/render_check.json", "w"), indent=1)
print(f"{len(F)} frames at {FPS:g} fps, {len(cuts)} cuts")
for f in flags:
    print(f"{f['t']:>9}  {f['kind']:7s} {f['msg']}")
