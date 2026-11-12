#!/usr/bin/env python3
"""Measure what a grade does to a shot, outside Resolve (numpy), never inside Resolve's Python.
Runs on the local Mac (or the device VM if run_env is device-vm).
usage: measnp.py jobs.json LUT1.cube[,LUT2.cube,...] [--card JOB.md | --size 1080x1920] [--src-size 3840x2160]
jobs.json = [{"key": "G1_1087", "src": "/path/clip.MP4", "t": 6.5, "pan": 170, "tilt": 0, "zoom": 1.0}, ...]
  (a job may add "src_size": "WxH" for a clip ffprobe reads wrong, e.g. a rotated vertical clip)
Crops the window the timeline shows (Pan/Tilt/Zoom as in the Inspector). Timeline size: --size, else
the job card Delivery line / client profile delivery (--card, via beon_config), else Beon's 1080x1920.
Source size: --src-size, else the job's "src_size", else ffprobe, else 3840x2160.
Then renders the source frame through each LUT exported with TimelineItem.ExportLUT (33pt cube),
and prints JSON per job and LUT: p50/p90/p99 luma, neutral Cb/Cr (Y>200, chroma<40),
the largest bright surfaces (area %, median Y, centre x/y) and the dense waveform top.
Input range pc matches Resolve on Sony XAVC (validated against Tim's still 1.1.1)."""
import argparse, json, os, pathlib, subprocess, sys
try:
    import numpy as np
    import cv2
except ImportError:                      # --help still works; main() says what to install
    np = cv2 = None

W0, H0 = 180, 320
TIMELINE = (1080, 1920)                  # Beon default; job card Delivery / client profile override
SOURCE = (3840, 2160)                    # fallback when ffprobe can't read the clip
_probed = {}

def need_numpy():
    if np is None or cv2 is None:
        sys.exit("needs numpy and opencv: pip install numpy opencv-python-headless")

def wxh(s):
    w, h = str(s).lower().split("x")
    return int(w), int(h)

def probe_size(src):
    """Source width x height from ffprobe, cached; SOURCE if it can't be read."""
    if src not in _probed:
        try:
            r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height", "-of", "csv=p=0:s=x", src],
                               capture_output=True, text=True, timeout=30)
            _probed[src] = wxh(r.stdout.strip().splitlines()[0])
        except Exception:
            _probed[src] = SOURCE
    return _probed[src]

def add_geometry_args(ap):
    ap.add_argument("--card", help="job card: timeline size from its Delivery line / the client profile")
    ap.add_argument("--size", help="timeline WxH (default: from --card, else %dx%d)" % TIMELINE)
    ap.add_argument("--src-size", help="source WxH for every job (default: probed with ffprobe)")

def timeline_size(a):
    if a.size:
        return wxh(a.size)
    if a.card:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "house-rules" / "scripts"))
        import beon_config as bc
        d = bc.delivery(a.card)
        return int(d["width"]), int(d["height"])
    return TIMELINE

def crop_job(j, a, tl):
    """Crop box for job j: source size from --src-size, the job's src_size, or ffprobe."""
    W, H = wxh(a.src_size) if a.src_size else wxh(j["src_size"]) if j.get("src_size") else probe_size(j["src"])
    return crop_for(j.get("pan", 0), j.get("tilt", 0), j.get("zoom", 1.0), W, H, tl[0], tl[1])

def crop_for(pan=0, tilt=0, zoom=1.0, W=3840, H=2160, tw=1080, th=1920):
    s = th / H * zoom
    cw = min(W, tw / s); ch = min(H, th / s)
    cx = W / 2 - pan / s - cw / 2; cy = H / 2 + tilt / s - ch / 2
    cx = max(0, min(W - cw, cx)); cy = max(0, min(H - ch, cy))
    return int(cw) // 2 * 2, int(ch) // 2 * 2, int(cx), int(cy)

def thumb_size(tl):
    """Measuring thumbnail: 180 px wide, timeline aspect (180x320 for 9:16)."""
    return W0, max(2, int(round(W0 * tl[1] / tl[0] / 2)) * 2)

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
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jobs"); ap.add_argument("luts", help="comma-separated .cube files")
    add_geometry_args(ap)
    a = ap.parse_args()
    need_numpy()
    jobs = json.load(open(a.jobs)); luts = a.luts.split(","); tl = timeline_size(a)
    out = {}
    for j in jobs:
        cr = crop_job(j, a, tl)
        out[j["key"]] = {os.path.basename(L): stats(frame(j["src"], j["t"], cr, L, *thumb_size(tl))) for L in luts}
    print(json.dumps(out, indent=1))
