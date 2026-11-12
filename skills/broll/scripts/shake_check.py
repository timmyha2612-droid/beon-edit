"""shake_check.py (v4: Savitzky-Golay 9/2 detrend, ends trimmed; features restricted to low-temporal-change background; floor ~0.3 px p90; calibrated +1px sigma shake ->2.0, +2px ->3.3)
shake_check.py RENDER.mp4 SHOTS.json OUTDIR [--card JOB_CARD.md] [--fps 24] [--size 1080x1920]
SHOTS.json: [{"shot": "R1 2474", "start": tl_frame, "dur": frames}, ...] (timeline fps from --fps / the job card
Delivery, default 24; render frame = timeline frame). Measured at half the delivery size, px at the delivery width.
Per shot: camera jitter (high-pass of the global similarity path, px at the delivery width, 1080 by default) and glitch candidates
(frames whose local residual flow or frame difference spikes vs. neighbours). Writes OUTDIR/report.json and
OUTDIR/<shot>_spikes.jpg strips (frame before | spike frame | after, plus residual-flow heatmap)."""
import argparse, os, json, subprocess
from _beon import add_delivery_args, delivery
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("render"); ap.add_argument("shots"); ap.add_argument("outdir"); add_delivery_args(ap)
A = ap.parse_args(); DL = delivery(A)
import numpy as np, cv2
from scipy.signal import savgol_filter
src, shots_p, out = A.render, A.shots, A.outdir; os.makedirs(out, exist_ok=True)
shots = json.load(open(shots_p))
W, H = DL["width"] // 2, DL["height"] // 2; K = DL["width"] / W; FPS = DL["fps"]
def read(f0, n):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", "%.4f" % ((f0 + 0.01) / FPS), "-i", src, "-frames:v", str(n),
                          "-vf", "scale=%d:%d" % (W, H), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    k = len(raw) // (W * H * 3); return np.frombuffer(raw[:k * W * H * 3], np.uint8).reshape(k, H, W, 3)
rep = []
for s in shots:
    a, n = s["start"] + 2, s["dur"] - 4
    fr = read(a, n); g = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in fr]
    stack = np.stack(g).astype(np.float32); tstd = cv2.GaussianBlur(stack.std(0), (41, 41), 0)
    mask = (tstd < np.percentile(tstd, 55)).astype(np.uint8) * 255
    path = [np.zeros(4)]; resid = []; dif = []; inl = []
    for i in range(1, len(g)):
        p0 = cv2.goodFeaturesToTrack(g[i - 1], 600, 0.005, 10, mask=mask)
        T = None
        if p0 is not None and len(p0) > 20:
            p1, st, _ = cv2.calcOpticalFlowPyrLK(g[i - 1], g[i], p0, None)
            ok = st.ravel() == 1
            if ok.sum() > 15:
                T, mm = cv2.estimateAffinePartial2D(p0[ok], p1[ok], method=cv2.RANSAC, ransacReprojThreshold=1.5)
                inl.append(float(mm.mean()) if mm is not None else 0.0)
        if T is None: T = np.array([[1, 0, 0], [0, 1, 0]], float)
        dx, dy = T[0, 2], T[1, 2]; da = np.arctan2(T[1, 0], T[0, 0]); ds = np.hypot(T[0, 0], T[1, 0]) - 1
        path.append(path[-1] + np.array([dx, dy, da, ds]))
        fl = cv2.calcOpticalFlowFarneback(g[i - 1], g[i], None, 0.5, 3, 21, 3, 5, 1.1, 0)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        gx = T[0, 0] * xx + T[0, 1] * yy + T[0, 2] - xx; gy = T[1, 0] * xx + T[1, 1] * yy + T[1, 2] - yy
        r = np.hypot(fl[..., 0] - gx, fl[..., 1] - gy)
        resid.append(float(np.percentile(r, 95))); dif.append(float(np.abs(g[i].astype(np.float32) - g[i - 1]).mean()))
    P = np.array(path)
    if len(P) > 8:
        sm = savgol_filter(P, 9, 2, axis=0, mode="interp"); hp = (P - sm)[3:-3]
        jit = np.hypot(hp[:, 0], hp[:, 1]) * K
        rot = np.abs(hp[:, 2]) * (H / 2) * K  # rotation jitter expressed as px at frame edge
        j = np.maximum(jit, rot)
    else:
        j = np.zeros(len(P))
    resid = np.array(resid); dif = np.array(dif)
    def spikes(v):
        if len(v) < 5: return []
        med = np.array([np.median(v[max(0, i - 4):i + 5]) for i in range(len(v))]) + 1e-3
        return [int(i) for i in np.where((v / med > 2.2) & (v > np.median(v) + 0.6))[0]]
    sp = sorted(set(spikes(resid) + spikes(dif)))
    item = {"shot": s["shot"], "start": s["start"], "dur": s["dur"], "jitter_p90": round(float(np.percentile(j, 90)), 2),
            "jitter_max": round(float(j.max()), 2), "inlier_med": round(float(np.median(inl)), 2) if inl else None, "resid_p95_med": round(float(np.median(resid)), 2) if len(resid) else None,
            "glitch_frames": [a + 1 + i for i in sp], "tier": "pass" if np.percentile(j, 90) < 1.0 else ("check" if np.percentile(j, 90) < 1.6 else "fix")}
    rep.append(item); print(json.dumps(item), flush=True)
    if sp:
        tiles = []
        for i in sp[:4]:
            k = i + 1
            fl = cv2.calcOpticalFlowFarneback(g[k - 1], g[k], None, 0.5, 3, 21, 3, 5, 1.1, 0)
            hm = cv2.applyColorMap(np.clip(np.hypot(fl[..., 0], fl[..., 1]) * 20, 0, 255).astype(np.uint8), cv2.COLORMAP_JET)
            row = np.hstack([fr[k - 1], fr[k], fr[min(k + 1, len(fr) - 1)], hm])
            cv2.putText(row, "%s tl %d" % (s["shot"], a + k), (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            tiles.append(cv2.resize(row, (row.shape[1] // 2, row.shape[0] // 2)))
        cv2.imwrite(os.path.join(out, s["shot"].replace(" ", "_") + "_spikes.jpg"), np.vstack(tiles), [cv2.IMWRITE_JPEG_QUALITY, 75])
json.dump(rep, open(os.path.join(out, "report.json"), "w"), indent=1)
