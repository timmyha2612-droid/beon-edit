#!/usr/bin/env python3
"""One-pass, resumable shoot ingest for the device VM: probe, gyro shake, keyframes, contact sheets.
usage: ingest.py SHOOT_DIR CACHE_DIR SHEET_DIR [--budget 160] [--workers 4] [--per-sheet 8]
  SHOOT_DIR  connected folder with the camera cards (searched recursively for .MP4/.MOV)
  CACHE_DIR  VM scratch (outside mnt/), e.g. ~/work/<shoot>  - probe.json, gyro/*.json, fr/*.jpg
  SHEET_DIR  non-Dropbox connected folder for the sheets you stage and look at
Each device_bash call is a fresh shell (background jobs die when it returns) with a ~180 s limit,
so the script stops itself at --budget seconds and you simply run it again until it prints DONE.
Already-finished work is skipped. 4K long-GOP decodes and 2 kHz Sony gyro are the slow parts:
frames run in a 4-way pool, gyro is binned per frame (shake = RMS of per-frame gyro minus a 0.4 s
moving average, deg/s, per 1 s window every 0.5 s), clips over 5 GB skip gyro (8-min tripod
interviews blew the 3 GB VM memory). Needs ffmpeg, numpy, opencv, telemetry_parser (pip)."""
import argparse, glob, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("shoot"); ap.add_argument("cache"); ap.add_argument("sheets")
ap.add_argument("--budget", type=float, default=160); ap.add_argument("--workers", type=int, default=4)
ap.add_argument("--per-sheet", type=int, default=8)
a = ap.parse_args()
T0 = time.time()
left = lambda: a.budget - (time.time() - T0)
for d in (a.cache, f"{a.cache}/gyro", f"{a.cache}/fr", a.sheets):
    os.makedirs(d, exist_ok=True)
skip = ("_claude", "_shotlog", "gyroflow", "stabiliz", "stabilis", "_gf_")   # scratch and Gyroflow renders
files = sorted(p for p in glob.glob(f"{a.shoot}/**/*", recursive=True)
               if p.lower().endswith((".mp4", ".mov")) and not os.path.basename(p).startswith("._")
               and not any(s in p.lower() for s in skip))
key = lambda p: os.path.splitext(os.path.basename(p))[0]

# 1. probe
pp = f"{a.cache}/probe.json"
probe = json.load(open(pp)) if os.path.exists(pp) else {}
def do_probe(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", f],
                       capture_output=True, text=True, timeout=30)
    j = json.loads(r.stdout or "{}"); fmt = j.get("format", {}); tags = fmt.get("tags", {})
    v = next((s for s in j.get("streams", []) if s["codec_type"] == "video"), {})
    tc = next((s.get("tags", {}).get("timecode") for s in j.get("streams", []) if s.get("tags", {}).get("timecode")), None)
    n, d = (v.get("r_frame_rate") or "0/1").split("/")
    return key(f), {"file": f, "dur": round(float(fmt.get("duration", 0)), 2), "fps": float(n) / max(1, float(d)),
                    "wh": f'{v.get("width")}x{v.get("height")}', "created": tags.get("creation_time"), "tc": tc,
                    "bytes": os.path.getsize(f), "audio_ch": [s.get("channels") for s in j.get("streams", []) if s["codec_type"] == "audio"]}
todo = [f for f in files if key(f) not in probe]
with ThreadPoolExecutor(a.workers) as ex:
    for k, v in ex.map(do_probe, todo):
        probe[k] = v
json.dump(probe, open(pp, "w"), indent=0)

# 2. keyframes (4 per clip) for the sheets
def do_frames(f):
    k = key(f); dur = probe[k]["dur"]
    for p in (0.08, 0.35, 0.62, 0.9):
        o = f"{a.cache}/fr/{k}_{p}.jpg"
        if not os.path.exists(o) and left() > 5:
            subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{dur*p:.2f}", "-i", f, "-frames:v", "1",
                            "-vf", "scale=320:-2", "-q:v", "4", o, "-y"], timeout=60)
todo = [f for f in files if not os.path.exists(f"{a.cache}/fr/{key(f)}_0.9.jpg")]
with ThreadPoolExecutor(a.workers) as ex:
    list(ex.map(do_frames, todo))

# 3. gyro (one clip at a time: memory)
def do_gyro(f):
    import telemetry_parser
    k = key(f); dst = f"{a.cache}/gyro/{k}.json"; fps = probe[k]["fps"] or 25
    if probe[k]["bytes"] > 5e9:
        json.dump({"clip": k, "err": "skipped: file over 5 GB"}, open(dst, "w")); return
    try:
        imu = telemetry_parser.Parser(f).normalized_imu()
        ts = np.array([s["timestamp_ms"] for s in imu if s.get("gyro")]) / 1000.0
        g = np.array([s["gyro"] for s in imu if s.get("gyro")], float)
        if len(ts) < 10:
            json.dump({"clip": k, "err": "no gyro"}, open(dst, "w")); return
        ts -= ts[0]; nb = int(ts[-1] * fps); idx = np.minimum((ts * fps).astype(int), nb - 1)
        cnt = np.maximum(np.bincount(idx, minlength=nb), 1).astype(float)
        gf = np.vstack([np.bincount(idx, weights=g[:, i], minlength=nb) / cnt for i in range(3)]).T
        kk = max(3, int(round(fps * 0.4)) | 1); pad = np.pad(gf, ((kk // 2, kk // 2), (0, 0)), mode="edge")
        sm = np.vstack([np.convolve(pad[:, i], np.ones(kk) / kk, "valid") for i in range(3)]).T
        jit = np.linalg.norm(gf - sm, axis=1); spd = np.linalg.norm(sm, axis=1)
        win = [[round(s0, 1), round(float(np.sqrt(np.mean(jit[int(s0 * fps):int((s0 + 1) * fps)] ** 2))), 3),
                round(float(np.mean(spd[int(s0 * fps):int((s0 + 1) * fps)])), 2)] for s0 in np.arange(0, ts[-1] - 1, 0.5)]
        sh = [w[1] for w in win] or [0]
        json.dump({"clip": k, "fps": fps, "dur": round(float(ts[-1]), 2), "shake_med": round(float(np.median(sh)), 3),
                   "shake_p90": round(float(np.percentile(sh, 90)), 3), "speed_med": round(float(np.median([w[2] for w in win] or [0])), 2),
                   "win": win}, open(dst, "w"))
    except Exception as e:
        json.dump({"clip": k, "err": str(e)[:200]}, open(dst, "w"))
for f in files:
    if left() < 20:
        break
    if not os.path.exists(f"{a.cache}/gyro/{key(f)}.json"):
        do_gyro(f)

# 4. sheets (8 clips per sheet, label: name, duration, fps, shake, created)
import cv2
done_all = all(os.path.exists(f"{a.cache}/fr/{key(f)}_0.9.jpg") and os.path.exists(f"{a.cache}/gyro/{key(f)}.json") for f in files)
if done_all or left() > 10:
    rows = []
    for f in files:
        k = key(f); g = {}
        gp = f"{a.cache}/gyro/{k}.json"
        if os.path.exists(gp): g = json.load(open(gp))
        ims = [cv2.resize(cv2.imread(f"{a.cache}/fr/{k}_{p}.jpg") if os.path.exists(f"{a.cache}/fr/{k}_{p}.jpg") else np.zeros((180, 320, 3), np.uint8), (320, 180))
               for p in ("0.08", "0.35", "0.62", "0.9")]
        lab = np.zeros((26, 1280, 3), np.uint8); pr = probe[k]
        cv2.putText(lab, f"{k}  {pr['dur']}s {pr['fps']:g}fps  shake {g.get('shake_med', '-')}  {(pr.get('created') or '')[11:19]}",
                    (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        rows.append(np.vstack([lab, np.hstack(ims)]))
    for i in range(0, len(rows), a.per_sheet):
        cv2.imwrite(f"{a.sheets}/sheet_{i // a.per_sheet + 1:02d}.jpg", np.vstack(rows[i:i + a.per_sheet]), [cv2.IMWRITE_JPEG_QUALITY, 70])
print("DONE" if done_all else f"PARTIAL ({len(files)} clips) - run again", f"{time.time() - T0:.0f}s")
