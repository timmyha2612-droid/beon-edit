#!/usr/bin/env python3
"""Suggest Temp / Tint / HDR Global per hero shot from four calibration LUTs (device VM, numpy).
usage: calib.py jobs.json LUTDIR OUTDIR [--cb -5] [--cr 5] [--y 896]
LUTDIR holds base.cube (0/0/0), t200.cube (Temp +200), n20.cube (Tint +20), hm1.cube (HDR -1),
each exported from ONE fresh clip of a scratch timeline (one ApplyGradeFromDRX per clip).
jobs.json as in measnp.py. For each job: neutrals measured on a fixed mask (from base), a 2x2
linear solve of Temp/Tint to the target Cb/Cr, and Global from the largest near-white surface
that isn't clipped (windows/sky median > 990 are skipped). Writes OUTDIR/calib.json and
OUTDIR/calib_sheet.jpg (base-grade thumbnails) - look at it before trusting any number.
Flags shots with < 5% neutral pixels (balance unreliable: judge by eye, tell Tim)."""
import argparse, json, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measnp

ap = argparse.ArgumentParser()
ap.add_argument("jobs"); ap.add_argument("lutdir"); ap.add_argument("outdir")
ap.add_argument("--cb", type=float, default=-5); ap.add_argument("--cr", type=float, default=5)
ap.add_argument("--y", type=float, default=896)
a = ap.parse_args()
os.makedirs(a.outdir, exist_ok=True)
L = {k: os.path.join(a.lutdir, k + ".cube") for k in ("base", "t200", "n20", "hm1")}
res, thumbs = {}, []
for j in json.load(open(a.jobs)):
    cr = measnp.crop_for(j.get("pan", 0), j.get("tilt", 0), j.get("zoom", 1.0))
    F = {k: measnp.frame(j["src"], j["t"], cr, p) for k, p in L.items()}
    Yb, Cbb, Crb = measnp.ycc(F["base"])
    m = (Yb > 200) & (np.hypot(Cbb, Crb) < 40)
    weak = m.mean() < 0.05
    if m.sum() < 30:
        m = (Yb > np.percentile(Yb, 60)) & (np.hypot(Cbb, Crb) < 60)
    _, lab, comps = measnp.surfaces(Yb)
    surf = next((i for area, i in comps if np.median(Yb[lab == i]) <= 990), None)
    meas = {}
    for k, f in F.items():
        Y, Cb, Cr = measnp.ycc(f)
        meas[k] = {"cb": float(Cb[m].mean()), "cr": float(Cr[m].mean()),
                   "surf": float(np.median(Y[lab == surf])) if surf else None}
    b = meas["base"]
    M = np.array([[(meas["t200"]["cb"] - b["cb"]) / 200, (meas["n20"]["cb"] - b["cb"]) / 20],
                  [(meas["t200"]["cr"] - b["cr"]) / 200, (meas["n20"]["cr"] - b["cr"]) / 20]])
    T, N = np.linalg.solve(M, [a.cb - b["cb"], a.cr - b["cr"]])
    H = None
    if surf is not None and meas["hm1"]["surf"] is not None and b["surf"] != meas["hm1"]["surf"]:
        H = (a.y - b["surf"]) / (b["surf"] - meas["hm1"]["surf"])   # per +1 of Global
    res[j["key"]] = {"temp": int(round(T / 10) * 10), "tint": round(float(N) * 2) / 2,
                     "hdr_global": None if H is None else round(float(H), 2),
                     "base_neutral": [round(b["cb"], 1), round(b["cr"], 1)],
                     "base_surface": None if b["surf"] is None else round(b["surf"]),
                     "neutral_pct": round(float(m.mean() * 100), 1), "flag": "few neutrals" if weak else ""}
    im = np.clip(F["base"] / 1023 * 255, 0, 255).astype(np.uint8)[..., ::-1].copy()
    if surf is not None:
        im[(lab == surf) & ((np.indices(lab.shape).sum(0) % 6) == 0)] = (0, 255, 255)
    cv2.putText(im, j["key"], (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1, cv2.LINE_AA)
    thumbs.append(im)
    r = res[j["key"]]
    print(f"{j['key']:14s} Temp {r['temp']:+5d} Tint {r['tint']:+5.1f} Global {r['hdr_global']}  "
          f"base Cb/Cr {r['base_neutral']} surface {r['base_surface']} neutrals {r['neutral_pct']}% {r['flag']}")
json.dump(res, open(os.path.join(a.outdir, "calib.json"), "w"), indent=1)
rows = [np.hstack(thumbs[i:i + 10]) for i in range(0, len(thumbs), 10)]
w = max(r.shape[1] for r in rows)
rows = [np.hstack([r, np.zeros((r.shape[0], w - r.shape[1], 3), np.uint8)]) for r in rows]
cv2.imwrite(os.path.join(a.outdir, "calib_sheet.jpg"), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 80])
