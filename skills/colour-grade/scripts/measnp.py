#!/usr/bin/env python3
"""Measure what a grade does to a shot, in the device VM (numpy), never inside Resolve.
usage: measnp.py jobs.json LUT1.cube[,LUT2.cube,...]
jobs.json = [{"key": "G1_1087", "src": "/path/clip.MP4", "t": 6.5, "pan": 170, "tilt": 0, "zoom": 1.0}, ...]
Crops the 9:16 window the 1080x1920 timeline shows (Pan/Tilt/Zoom as in the Inspector),
renders the source frame through each LUT exported with TimelineItem.ExportLUT (33pt cube),
and prints JSON per job and LUT: p50/p90/p99 luma, neutral Cb/Cr (Y>200, chroma<40),
the largest bright surfaces (area %, median Y, centre x/y) and the dense waveform top.
Input range pc matches Resolve on Sony XAVC (validated against Tim's still 1.1.1)."""
import json, os, subprocess, sys
import numpy as np
import cv2

W0, H0 = 180, 320

def crop_for(pan=0, tilt=0, zoom=1.0, W=3840, H=2160, tw=1080, th=1920):
    s = th / H * zoom
    cw = min(W, tw / s); ch = min(H, th / s)
    cx = W / 2 - pan / s - cw / 2; cy = H / 2 + tilt / s - ch / 2
    cx = max(0, min(W - cw, cx)); cy = max(0, min(H - ch, cy))
    return int(cw) // 2 * 2, int(ch) // 2 * 2, int(cx), int(cy)

def frame(src, t, crop, lut=None, W=W0, H=H0, rng="pc"):
    cw, ch, cx, cy = crop
    vf = (f"crop={cw}:{ch}:{cx}:{cy},scale={W}:{H}:in_range={rng}:in_color_matrix=bt709:"
          f"out_range=pc:flags=area,format=rgb48le")
    if lut:
        vf += f",lut3d=file='{lut}':interp=tetrahedral"
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1",
                        "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb48le", "-"],
                       capture_output=True, timeout=60)
    return np.frombuffer(r.stdout[:W * H * 6], np.uint16).reshape(H, W, 3).astype(np.float64) / 64.0

def ycc(a):
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    Y = .2126 * R + .7152 * G + .0722 * B
    return Y, (B - Y) / 1.8556, (R - Y) / 1.5748

def surfaces(Y, mask_from=None, k=3):
    base = Y if mask_from is None else mask_from
    mk = (base >= np.percentile(base, 85)).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(mk, 4)
    comps = sorted([(st[i, cv2.CC_STAT_AREA], i) for i in range(1, n)
                    if st[i, cv2.CC_STAT_AREA] >= 0.005 * Y.size], reverse=True)
    return [(round(a / Y.size * 100, 1), round(float(np.median(Y[lab == i]))),
             round(cen[i][0] / Y.shape[1], 2), round(cen[i][1] / Y.shape[0], 2)) for a, i in comps[:k]], lab, comps

def stats(a):
    Y, Cb, Cr = ycc(a)
    m = (Y > 200) & (np.hypot(Cb, Cr) < 40)
    surf, _, _ = surfaces(Y)
    return {"p50": round(float(np.percentile(Y, 50))), "p90": round(float(np.percentile(Y, 90))),
            "p99": round(float(np.percentile(Y, 99))),
            "neu": (round(float(Cb[m].mean()), 1), round(float(Cr[m].mean()), 1), round(float(m.mean() * 100), 1)) if m.sum() > 20 else None,
            "surf": surf,
            "wtop": round(float(np.median([np.percentile(Y[:, c:c + 10], 98) for c in range(0, Y.shape[1], 10)])))}

if __name__ == "__main__":
    jobs = json.load(open(sys.argv[1])); luts = sys.argv[2].split(",")
    out = {}
    for j in jobs:
        cr = crop_for(j.get("pan", 0), j.get("tilt", 0), j.get("zoom", 1.0))
        out[j["key"]] = {os.path.basename(L): stats(frame(j["src"], j["t"], cr, L)) for L in luts}
    print(json.dumps(out, indent=1))
