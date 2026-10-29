#!/usr/bin/env python3
"""Look at every A-roll join before Tim does: picture either side, the waveform across it, the jump size.
usage: cut_review.py CUT.json OUT_DIR [--per-sheet 6] [--workers 4]
CUT.json is cut_pieces.py output ("video", "wav", "pans", pieces[].subs with source in/out).
For each join between consecutive sub-pieces it renders one row:
  [last frame of A] [first frame of B] [A/B difference]  [waveform: 1 s before the cut | 1 s after]
in the 9:16 window (Pan from "pans" per label, Zoom 1), and measures
  shift%  head/frame shift across the cut (phase correlation, % of frame width)
  diff    mean absolute difference after aligning (0-255)
  air     silence across the join (s): should be about 0.22-0.30
and suggests: "invisible" (shift < 0.5% and diff < 6), "smooth cut" (shift < 2%, diff < 12, same
framing: a 4-frame Smooth Cut usually hides it), or "cover" (B-roll, angle change or punch-in).
"invisible" is about the picture only: a same-take join still needs the audio to flow (look at the
waveform) and still counts as a jump cut if the head moves between the frames.
Tested on Arriva Oct C1 (18 joins, 18 s in the VM with 4 workers).
Writes OUT_DIR/joins_NN.jpg and OUT_DIR/joins.json. Look at the sheets: mouth half-open on an
edge frame, a breath cut in half, or a waveform that runs into the cut line are things to fix."""
import argparse, json, os, subprocess, sys, wave
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import cv2

ap = argparse.ArgumentParser()
ap.add_argument("cut"); ap.add_argument("out")
ap.add_argument("--per-sheet", type=int, default=6); ap.add_argument("--workers", type=int, default=4)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
C = json.load(open(a.cut))
pans = C.get("pans") or {}
W, H = 3840, 2160


def probe(v):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate", "-of", "json", v], capture_output=True, text=True)
    s = json.loads(r.stdout)["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return s["width"], s["height"], float(n) / float(d)


def crop(pan, w, h, tw=1080, th=1920, zoom=1.0):
    s = th / h * zoom
    cw = min(w, tw / s); ch = min(h, th / s)
    cx = max(0, min(w - cw, w / 2 - pan / s - cw / 2))
    return int(cw) // 2 * 2, int(ch) // 2 * 2, int(cx), int(max(0, (h - ch) / 2))


def grab(t, pan):
    cw, ch, cx, cy = crop(pan, W, H)
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", C["video"], "-frames:v", "1",
                        "-vf", f"crop={cw}:{ch}:{cx}:{cy},scale=216:384", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                       capture_output=True, timeout=60)
    buf = r.stdout[:216 * 384 * 3]
    return np.frombuffer(buf, np.uint8).reshape(384, 216, 3).copy() if len(buf) == 216 * 384 * 3 else np.zeros((384, 216, 3), np.uint8)


def wav_energy(path):
    w = wave.open(path)
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    sr = w.getframerate(); hop = sr // 100; n = len(x) // hop
    return 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)


W, H, FPS = probe(C["video"])
fr = wav_energy(C["wav"]); thr = np.percentile(fr, 10) + 12
subs = [(p["label"], s) for p in C["pieces"] for s in p["subs"]]
joins = [(subs[i], subs[i + 1]) for i in range(len(subs) - 1)]


def wave_panel(t_out, t_in, w=520, h=384):
    pre = fr[max(0, int((t_out - 1) * 100)):int(t_out * 100)]
    seg = np.concatenate([pre, fr[int(t_in * 100):int((t_in + 1) * 100)]])
    img = np.full((h, w, 3), 24, np.uint8)
    if len(seg) == 0:
        return img, 0
    lo, hi = thr - 25, max(fr.max(), thr + 20)
    xs = np.linspace(0, w - 1, len(seg)).astype(int)
    ys = (h - 20 - (np.clip(seg, lo, hi) - lo) / (hi - lo) * (h - 40)).astype(int)
    for i in range(1, len(seg)):
        col = (80, 200, 255) if seg[i] > thr else (110, 110, 110)
        cv2.line(img, (xs[i - 1], ys[i - 1]), (xs[i], ys[i]), col, 2)
    ty = int(h - 20 - (thr - lo) / (hi - lo) * (h - 40))
    cv2.line(img, (0, ty), (w, ty), (60, 60, 160), 1)
    mid = int(w * len(pre) / len(seg))
    cv2.line(img, (mid, 0), (mid, h), (0, 0, 255), 2)
    k = int(t_out * 100) - 1; air = 0
    while k > 0 and fr[k] <= thr and air < 100:
        air += 1; k -= 1
    k = int(t_in * 100)
    while k < len(fr) and fr[k] <= thr and air < 200:
        air += 1; k += 1
    return img, air / 100


def one(j):
    (la, sa), (lb, sb) = j
    A = grab(sa[1] - 1.0 / FPS, pans.get(la, 0))
    B = grab(sb[0], pans.get(lb, 0))
    ga = cv2.cvtColor(A, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gb = cv2.cvtColor(B, cv2.COLOR_BGR2GRAY).astype(np.float32)
    (dx, dy), _ = cv2.phaseCorrelate(ga, gb)
    M = np.float32([[1, 0, -dx], [0, 1, -dy]])
    gb2 = cv2.warpAffine(gb, M, (216, 384), borderMode=cv2.BORDER_REPLICATE)
    diff = float(np.abs(ga[20:-20, 20:-20] - gb2[20:-20, 20:-20]).mean())
    shift = float(np.hypot(dx, dy) / 216 * 100)
    same = abs(pans.get(la, 0) - pans.get(lb, 0)) < 30
    sug = "invisible" if shift < 0.5 and diff < 6 else "smooth cut" if shift < 2 and diff < 12 and same else "cover"
    D = cv2.absdiff(A, B)
    wp, air = wave_panel(sa[1], sb[0])
    row = np.hstack([A, B, D * 3, wp])
    lab = np.zeros((28, row.shape[1], 3), np.uint8)
    cv2.putText(lab, f"{la} {sa[0]:.2f}-{sa[1]:.2f} | {lb} {sb[0]:.2f}-{sb[1]:.2f}  shift {shift:.1f}%  diff {diff:.1f}  air {air:.2f}s  -> {sug}",
                (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return {"a": [la, sa[0], sa[1]], "b": [lb, sb[0], sb[1]], "rec": sb[3] if len(sb) > 3 else None,
            "shift_pct": round(shift, 2), "diff": round(diff, 1), "air": air, "suggest": sug,
            "removed": sa[2]}, np.vstack([lab, row])


with ThreadPoolExecutor(a.workers) as ex:
    res = list(ex.map(one, joins))
for i in range(0, len(res), a.per_sheet):
    cv2.imwrite(f"{a.out}/joins_{i // a.per_sheet + 1:02d}.jpg", np.vstack([r[1] for r in res[i:i + a.per_sheet]]),
                [cv2.IMWRITE_JPEG_QUALITY, 75])
json.dump([r[0] for r in res], open(f"{a.out}/joins.json", "w"), indent=1)
for r, _ in res:
    print(f"rec {r['rec']!s:>5}  {r['a'][0]}->{r['b'][0]}  shift {r['shift_pct']:4.1f}%  diff {r['diff']:5.1f}  air {r['air']:.2f}s  {r['suggest']:10s} {r['removed']}")
print(f"{len(res)} joins, sheets in {a.out}")
