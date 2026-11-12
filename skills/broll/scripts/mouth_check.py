"""Edge-frame mouth check for people B-roll.
usage: mouth_check.py CLIP T_IN DUR_S [real|slow] --dir SHOOT [--prefix LIAM.A_FX3_]  -> JSON line
  CLIP     stem (C0123), file name (any video extension) or path relative to --dir (A001/C0123.MP4);
           a stem is searched for under --dir, also as <prefix><stem> or <anything>_<stem>
  --dir    the shoot folder (shot log "shoot.shoot_folder"); --prefix the camera's file-name prefix
           (shot log shoot.cameras[].name_pattern without the *)
Checks the first/last 0.3 s of the shot (what lands on the cut). Mouth-open ratio
MAR = inner-lip gap / mouth width per face (Haar face -> FaceMesh on the crop).
MAR > 0.35 = mouth wide open. If an edge fails, tries nudging the whole window
by up to +-0.5 s in 2-frame steps and reports the smallest clean shift."""
import argparse, os, json, subprocess
from _beon import find_clip
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("clip"); ap.add_argument("t_in", type=float); ap.add_argument("dur", type=float)
ap.add_argument("mode", nargs="?", default="real", choices=["real", "slow"])
ap.add_argument("--dir", help="shoot folder the clip is in (or under)"); ap.add_argument("--prefix", default="")
A = ap.parse_args()
import numpy as np, cv2
import mediapipe as mp
CLIP_PATH = find_clip(A.dir, A.clip, A.prefix)
def path(c):
    return CLIP_PATH
TH = 0.35; EDGE = 0.3; NUDGE = 0.5
clip, t_in, dur = A.clip, A.t_in, A.dur
fps = float(subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=r_frame_rate","-of","csv=p=0",path(clip)],capture_output=True,text=True).stdout.strip().split("/")[0])
a = max(0, t_in - NUDGE); b = t_in + dur + NUDGE
W, H = 1920, 1080
raw = subprocess.run(["ffmpeg","-v","error","-ss",f"{a:.3f}","-t",f"{b-a:.3f}","-i",path(clip),"-vf",f"scale={W}:{H},eq=contrast=1.3:saturation=1.3:gamma=0.9","-pix_fmt","bgr24","-f","rawvideo","-"],capture_output=True).stdout
frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
haar = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, min_detection_confidence=0.3)
cache = {}
def mar(i):
    if i in cache: return cache[i]
    img = frames[i]; g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = haar.detectMultiScale(g, 1.1, 5, minSize=(40, 40))
    best = None
    for (x, y, w, h) in faces:
        cx, cy, s = x + w/2, y + h/2, int(max(w, h) * 1.8)
        x0, y0 = int(max(0, cx - s/2)), int(max(0, cy - s/2))
        crop = img[y0:y0+s, x0:x0+s]
        if crop.size == 0: continue
        crop = cv2.resize(crop, (256, 256))
        r = mesh.process(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
        if not r.multi_face_landmarks: continue
        L = r.multi_face_landmarks[0].landmark
        gap = np.hypot(L[13].x - L[14].x, L[13].y - L[14].y); wid = np.hypot(L[78].x - L[308].x, L[78].y - L[308].y)
        m = gap / max(wid, 1e-6)
        best = m if best is None else max(best, m)
    cache[i] = best; return best
n_edge = max(1, int(round(EDGE * fps)))
def check(shift):
    i0 = int(round((t_in + shift - a) * fps)); i1 = int(round((t_in + shift + dur - a) * fps))
    if i0 < 0 or i1 > len(frames): return None
    head = [mar(i) for i in range(i0, min(i0 + n_edge, len(frames)))]
    tail = [mar(i) for i in range(max(i0, i1 - n_edge), i1)]
    hv = [v for v in head if v is not None]; tv = [v for v in tail if v is not None]
    return {"head_max": round(max(hv), 2) if hv else None, "tail_max": round(max(tv), 2) if tv else None,
            "faces_seen": bool(hv or tv), "ok": (not hv or max(hv) <= TH) and (not tv or max(tv) <= TH)}
res = {"clip": clip, "t_in": t_in, "dur": dur, "fps": fps}
base = check(0.0); res["edges"] = base
if base and not base["ok"]:
    step = 2 / fps; fix = None
    for k in range(1, int(NUDGE / step) + 1):
        for sgn in (-1, 1):
            r = check(sgn * k * step)
            if r and r["ok"]:
                fix = {"shift_s": round(sgn * k * step, 3), "new_t_in": round(t_in + sgn * k * step, 3), **r}; break
        if fix: break
    res["nudge"] = fix or "no clean window within +-0.5 s, re-pick"
print(json.dumps(res, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
