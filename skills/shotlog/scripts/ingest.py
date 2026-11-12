#!/usr/bin/env python3
"""One-pass, resumable shoot ingest: probe, gyro shake, keyframes, contact sheets, camera facts.
usage: ingest.py SHOOT_DIR CACHE_DIR SHEET_DIR [--budget S] [--workers 4] [--per-sheet 8]
  SHOOT_DIR  folder with the camera cards (searched recursively for .MP4/.MOV)
  CACHE_DIR  scratch, e.g. <scratch_root>/<client>-<shoot>/ingest - probe.json, gyro/*.json, fr/*.jpg,
             cameras_suggested.json
  SHEET_DIR  folder for the sheets you look at (never in a synced folder: editor.json synced_folders, Dropbox)
Budget: locally (editor.json run_env.mode "local", the default) there is none, it runs to the end.
If run_env is device-vm, each device_bash call is a fresh shell (background jobs die when it returns)
with a ~180 s limit, so the script stops itself at --budget seconds (default run_env.shell_budget_s
minus 20, else 160) and you simply run it again until it prints DONE. The VM usually has no
editor.json, so pass --budget from the Mac's editor.json; with no setup file on a non-Mac it uses 160.
--budget always wins.
Already-finished work is skipped. 4K long-GOP decodes and 2 kHz Sony gyro are the slow parts:
frames run in a 4-way pool, gyro is binned per frame (shake = RMS of per-frame gyro minus a 0.4 s
moving average, deg/s, per 1 s window every 0.5 s), clips over 5 GB skip gyro (8-min tripod
interviews blew the 3 GB VM memory).
cameras_suggested.json: per card folder fps, res, codec, ext, name pattern, model and log profile
(Sony XML sidecar), gyro found. Suggestions only: Claude confirms them with the editor and writes
shotlog.json > shoot.cameras, never overwriting a field already set.
Needs ffmpeg, numpy, opencv, telemetry_parser (pip)."""
import argparse, glob, json, os, pathlib, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "house-rules" / "scripts"))
try:
    import beon_config as bc
except ImportError:                       # plugin copy without house-rules: behave as before
    bc = None

ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], epilog=__doc__,
                             formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("shoot"); ap.add_argument("cache"); ap.add_argument("sheets")
ap.add_argument("--budget", type=float, default=None,
                help="stop after this many seconds (default: none locally; device-vm: shell budget)")
ap.add_argument("--workers", type=int, default=4)
ap.add_argument("--per-sheet", type=int, default=8)
a = ap.parse_args()
ED = bc.load_editor() if bc else {}
RUN = ED.get("run_env") or {}
# Inside the VM the Mac's editor.json is usually absent: no setup file and not a Mac = assume the VM.
NO_SETUP = not bc or not any((bc.HOME / n).exists() for n in ("editor.json", "config.json"))
if a.budget is None:
    if NO_SETUP and sys.platform != "darwin":
        a.budget = 160.0
    elif RUN.get("mode") == "device-vm":
        a.budget = max(30.0, float(RUN["shell_budget_s"]) - 20) if RUN.get("shell_budget_s") else 160.0
    else:
        a.budget = float("inf")
if bc:
    for d in (a.cache, a.sheets):
        if bc.in_synced_folder(d, ED):
            raise SystemExit(f"refusing {d!r}: frames and sheets never go in a synced folder (editor.json synced_folders, Dropbox)")
import numpy as np
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
                    "bytes": os.path.getsize(f), "audio_ch": [s.get("channels") for s in j.get("streams", []) if s["codec_type"] == "audio"],
                    "codec": v.get("codec_name"), "model": tags.get("com.apple.quicktime.model") or tags.get("model")}
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

# 4. camera facts per card folder -> cameras_suggested.json (suggestions; never written to the shot log)
def sony_xml(f):
    """model and log profile from the Sony sidecar (C0001M01.XML next to C0001.MP4), if there is one."""
    st = os.path.splitext(f)[0]
    for x in (st + "M01.XML", st + "M01.xml"):
        if os.path.exists(x):
            t = open(x, errors="ignore").read(200000)
            m = re.search(r'modelName="([^"]+)"', t); g = re.search(r'CaptureGammaEquation" value="([^"]+)"', t)
            return (m.group(1) if m else None), (g.group(1) if g else None)
    return None, None
cams = {}
for f in files:
    rel = os.path.relpath(f, a.shoot); folder = rel.split(os.sep)[0] if os.sep in rel else "."
    cams.setdefault(folder, []).append(f)
sugg = []
for folder, fs in sorted(cams.items()):
    pr = [probe[key(f)] for f in fs if key(f) in probe]
    if not pr:
        continue
    common = lambda vals: max(set(vals), key=vals.count) if vals else None
    stems = [key(f) for f in fs]; pre = os.path.commonprefix(stems)
    model, log = sony_xml(fs[0])
    gy = [json.load(open(f"{a.cache}/gyro/{key(f)}.json")) for f in fs if os.path.exists(f"{a.cache}/gyro/{key(f)}.json")]
    fps = common([round(p["fps"], 3) for p in pr])
    sugg.append({"folder": folder, "clips": len(fs), "fps": int(fps) if fps and fps == int(fps) else fps,
                 "res": common([p["wh"] for p in pr]), "codec": common([p.get("codec") for p in pr]),
                 "ext": common([os.path.splitext(f)[1] for f in fs]),
                 "name_pattern": (pre + "*") if pre else None,
                 "model": model or common([p.get("model") for p in pr if p.get("model")]), "log": log,
                 "gyro_found": (any("err" not in g for g in gy) if gy else None),
                 "audio_ch": common([tuple(p.get("audio_ch") or []) for p in pr])})
json.dump({"shoot_dir": os.path.abspath(a.shoot), "note": "suggestions for shotlog.json > shoot.cameras; confirm role, "
           "gyro (sony-rtmd | none) and log with the editor; never overwrite a set field", "cameras": sugg},
          open(f"{a.cache}/cameras_suggested.json", "w"), indent=1)

# 5. sheets (8 clips per sheet, label: name, duration, fps, shake, created)
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
