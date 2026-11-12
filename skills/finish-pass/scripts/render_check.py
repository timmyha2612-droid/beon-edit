#!/usr/bin/env python3
"""Check the actual render, not the timeline: every cut, black or frozen frames, flash frames, audio pops and level jumps.
usage: render_check.py PROXY.mp4 OUT_DIR [--cuts 12,101,150,...] [--per-sheet 6] [--music]
                       [--card JOB_CARD.md] [--fps 24] [--size 1080x1920] [--lufs -14] [--true-peak -1]
  PROXY.mp4  a small render of the timeline (finish-pass/scripts/resolve_proxy_render.py: half the delivery
             size, H.264)
  --cuts     record frames of the edit points (timeline frames from 0); default: detected from the picture
  --music    the render has music: don't flag quiet stretches as gaps
  --card     the job card: expected aspect, fps, loudness and true peak come from it and the client profile
             (house-rules beon_config.delivery). --fps/--size/--lufs/--true-peak override single values.
             None given: Beon default 9:16 1080x1920 24p, loudness reported only.
Flags (all with timecodes):
  BLACK   frames that are (near) black inside the edit
  FREEZE  6+ identical frames in a row (a held frame from a retime, a still, a missing render)
  FLASH   two cuts less than 3 frames apart (a 1-2 frame sliver)
  POP     a click at a cut: a sudden sample jump far above the audio around it
  LEVEL   speech level jumps more than 6 dB across a cut
  GAP     a silence longer than 0.8 s with speech on both sides (no music)
  LOUD    integrated loudness and true peak of the whole render (judged against the delivery target
          when one is known: more than 1 LU off, or true peak above the ceiling)
  FORMAT  the proxy's aspect or fps doesn't match delivery (a proxy is smaller, so only the shape is compared)
Writes OUT_DIR/cuts_NN.jpg (last and first frame of every cut, waveform +-1 s) and OUT_DIR/render_check.json.
Look at the sheets: they are what the viewer will see and hear, unlike the source-side checks."""
import argparse, json, os, pathlib, re, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "house-rules" / "scripts"))
try:
    import beon_config as bc
except ImportError:
    bc = None

ap = argparse.ArgumentParser()
ap.add_argument("proxy"); ap.add_argument("out")
ap.add_argument("--cuts", default=""); ap.add_argument("--per-sheet", type=int, default=6)
ap.add_argument("--music", action="store_true")
ap.add_argument("--card", help="job card: delivery from it and the client profile")
ap.add_argument("--fps", type=float, help="expected delivery fps (overrides the card)")
ap.add_argument("--size", help="expected delivery size WxH, e.g. 1080x1920 (overrides the card)")
ap.add_argument("--lufs", type=float, help="loudness target in LUFS (overrides the card)")
ap.add_argument("--true-peak", type=float, help="true peak ceiling in dBTP (overrides the card)")
a = ap.parse_args()
try:                                           # after parsing, so --help works without them
    import numpy as np
    import cv2
except ImportError as e:
    sys.exit(f"render_check.py needs a Python with numpy and opencv-python ({e.name} missing): use a venv, "
             "or the device VM if run_env is device-vm")
DEL = bc.delivery(a.card) if bc else {"aspect": "9:16", "width": 1080, "height": 1920, "fps": 24,
                                      "loudness_lufs": None, "true_peak_db": None}
if a.size:
    w_, h_ = a.size.lower().split("x"); DEL["width"], DEL["height"] = int(w_), int(h_)
    DEL["aspect"] = f"{DEL['width']}:{DEL['height']}"          # --size sets the shape too, so they can't disagree
if a.fps:
    DEL["fps"] = a.fps
if a.lufs is not None:
    DEL["loudness_lufs"] = a.lufs
if a.true_peak is not None:
    DEL["true_peak_db"] = a.true_peak
os.makedirs(a.out, exist_ok=True)
pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", a.proxy],
                               capture_output=True, text=True).stdout)
vs = next(s for s in pr["streams"] if s["codec_type"] == "video")
n_, d_ = vs["r_frame_rate"].split("/"); FPS = float(n_) / float(d_)
PW, PH = int(vs.get("width") or 540), int(vs.get("height") or 960)
if PH >= PW:                                   # analyse at 240 on the long side (135x240 for a 9:16 proxy)
    W, H = int(round(240 * PW / PH)), 240
    TW, TH = 108, 192
else:
    W, H = 240, int(round(240 * PH / PW))
    TW, TH = 192, 108
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
try:
    m_ = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)\s*", str(DEL.get("aspect") or ""))
    want = float(m_.group(1)) / float(m_.group(2)) if m_ else float(DEL["width"]) / float(DEL["height"])
    if abs(PW / PH - want) > 0.01:
        flags.append({"t": "-", "kind": "FORMAT", "msg": f"proxy is {PW}x{PH}, delivery aspect is {DEL.get('aspect') or str(DEL['width']) + ':' + str(DEL['height'])}"})
    if DEL.get("fps") and abs(FPS - float(DEL["fps"])) > 0.01:
        flags.append({"t": "-", "kind": "FORMAT", "msg": f"render is {FPS:g} fps, delivery is {DEL['fps']} fps"})
except (TypeError, ValueError, ZeroDivisionError):
    pass

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
    A_ = cv2.resize(F[max(0, c - 1)], (TW, TH)); B_ = cv2.resize(F[min(len(F) - 1, c)], (TW, TH))
    seg = env[max(0, k - 100):k + 100]
    wp = np.full((TH, 300, 3), 24, np.uint8)
    if len(seg) > 1:
        lo, hi = thr - 25, max(env.max(), thr + 20)
        xs = np.linspace(0, 299, len(seg)).astype(int); ys = (TH - 10 - (np.clip(seg, lo, hi) - lo) / (hi - lo) * (TH - 20)).astype(int)
        for i in range(1, len(seg)):
            cv2.line(wp, (xs[i - 1], ys[i - 1]), (xs[i], ys[i]), (80, 200, 255) if seg[i] > thr else (110, 110, 110), 1)
        cv2.line(wp, (int(300 * min(100, k) / len(seg)), 0), (int(300 * min(100, k) / len(seg)), TH), (0, 0, 255), 1)
    lab = np.zeros((22, 2 * TW + 300, 3), np.uint8)
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
msg = f"integrated {I[-1] if I else '?'} LUFS, true peak {TP[-1] if TP else '?'} dBFS"
off = []
if I and isinstance(DEL.get("loudness_lufs"), (int, float)) and abs(float(I[-1]) - DEL["loudness_lufs"]) > 1:
    off.append(f"target {DEL['loudness_lufs']} LUFS")
if TP and isinstance(DEL.get("true_peak_db"), (int, float)) and float(TP[-1]) > DEL["true_peak_db"]:
    off.append(f"ceiling {DEL['true_peak_db']} dBTP")
if off:
    msg += " -- OFF delivery: " + ", ".join(off)
elif DEL.get("loudness_lufs") is None:
    msg += " (no loudness target in the client profile or job card: reported only)"
flags.append({"t": "-", "kind": "LOUD", "msg": msg})
for i in range(0, len(rows), a.per_sheet):
    cv2.imwrite(f"{a.out}/cuts_{i // a.per_sheet + 1:02d}.jpg", np.vstack(rows[i:i + a.per_sheet]), [cv2.IMWRITE_JPEG_QUALITY, 75])
json.dump({"fps": FPS, "frames": len(F), "size": f"{PW}x{PH}", "delivery": DEL, "cuts": cuts, "flags": flags}, open(f"{a.out}/render_check.json", "w"), indent=1)
print(f"{len(F)} frames at {FPS:g} fps, {len(cuts)} cuts")
for f in flags:
    print(f"{f['t']:>9}  {f['kind']:7s} {f['msg']}")
