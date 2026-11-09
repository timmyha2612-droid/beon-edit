#!/usr/bin/env python3
"""Pick the smoothest window, speed and Gyroflow preset for every B-roll slot, numerically.

Footage Prep (gyro/rtmd) already scores each SELECT (stability, jitter, shaky_frac, movement): use it to
choose which selects are allowed (no shaky/whip/motion_blur/blocked flags, stability >= ~0.75). A slot only
plays ~1-3 s of a 3-12 s select, and Footage Prep doesn't score that stretch at the slot's speed. This script
does: one cheap decode per select (gray, 384 px wide). No images to look at, one line per slot.
Run it BEFORE placing B-roll and place exactly what it prints; open frames only for the
subject/people check of the winner (framing_sheet.py / one still).

usage:
  broll_auto.py SLOTS.json CLIP_DIR [-o plan.json] [--snippet resolve_apply.py]

SLOTS.json: [{"slot": "B6", "clip": "C0185", "rec": 74,            # timeline frames the shot plays
              "sel_frames": [[275, 528], ...],                      # footage-prep `selects` in_frame/out_frame (preferred)
              "sel": [[5.5, 10.56], ...],                           # or select windows in source seconds
              "movement": "pan_tilt",                               # footage-prep movement label (sets the Gyroflow preset)
              "x": 0.48, "zoom": 1.0,                               # 9:16 window (subject centre, zoom)
              "at": 635,                                            # timeline frame offset (for --snippet)
              "people": false,                                      # people moving -> 50-60%, no 30%
              "avoid": [[6.0, 7.5]]}, ...]                          # source ranges already used (optional)
  "sel" may be omitted: then the whole clip minus 1 s each end.

What it measures, all at OUTPUT timing (after the slow-down, inside the 9:16 window, px at 1080 wide):
  jit   p90 of high-frequency wobble (pos minus its ~0.5 s moving average)   pass < 1.0, check < 2.0, fix
  v     mean camera speed px/frame; cv = how uneven it is (> 0.3 = speeds up / slows down)
  rev   share of frames moving against the main direction (a reset or a change of move)
  sharp min Laplacian in the window vs the clip's median (< 0.6 = focus pull / blur)
  luma  range of mean brightness (> 12 = exposure jump)
Speeds tried: 48 / 40 / 30 % (empty house; 48 preferred), 60 / 50 % with "people".
On a 24p timeline 50p at <= 48% needs no invented frames; 100 fps clips go to 25%.

Treatment (printed per slot):
  speed + Retime (Optical Flow, Speed Warp Better below 48%)
  gyroflow preset (Tim's presets) when the file has a gyro track (Sony rtmd), else "no gyro: list for Tim"
  REJECT when even the best window is still 'fix' after slowing (Gyroflow can't save reversals,
  focus pulls, walking bob): re-pick another select for that line.
--snippet writes a ready-to-paste run_script body that appends the shots on V2 with the chosen
source range, speed, retime, Pan/Zoom, Orange colour and the Gyroflow marker (marker before retime).
Then run gyroflow_headless.py, then shake_check.py on a proxy render to confirm.
"""
import argparse, json, math, subprocess, sys
import numpy as np
import cv2

W, H = 384, 216


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,codec_tag_string,r_frame_rate:format=duration",
                          "-of", "json", path], capture_output=True, text=True).stdout
    j = json.loads(out)
    fps = 50.0
    gyro = False
    for s in j.get("streams", []):
        if s.get("codec_type") == "video":
            n, d = s["r_frame_rate"].split("/")
            fps = float(n) / float(d)
        if s.get("codec_tag_string") == "rtmd":
            gyro = True
    return fps, gyro, float(j["format"]["duration"])


def decode(path, a, b):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", path,
           "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W)


def measure(fr, x, zoom):
    """per source frame: dx, dy (in W-px), sharpness and luma inside the 9:16 window."""
    f = fr.astype(np.float32)
    win = np.hanning(W).astype(np.float32)[None, :] * np.hanning(H).astype(np.float32)[:, None]
    d = np.array([cv2.phaseCorrelate(f[i - 1], f[i], win)[0] for i in range(1, len(f))])
    ww = 0.316 / zoom * W
    x0 = int(max(0, min(W - ww, x * W - ww / 2)))
    hh = H / zoom
    y0 = int((H - hh) / 2)
    crop = fr[:, y0:int(y0 + hh), x0:int(x0 + ww)]
    sharp = np.array([cv2.Laplacian(c, cv2.CV_32F).var() for c in crop])
    luma = crop.reshape(len(crop), -1).mean(1)
    return d, sharp, luma


def score(d, sharp, luma, s0, n_src, step, zoom, med_sharp):
    """window of n_src source frames starting at s0, played at `step` source frames per output frame."""
    seg = d[s0:s0 + n_src - 1]
    pos = np.vstack([[0, 0], np.cumsum(seg, 0)])          # source-frame positions
    t_out = np.arange(0, n_src - 1, step)
    p = np.stack([np.interp(t_out, np.arange(len(pos)), pos[:, j]) for j in range(2)], 1)
    p = p * (1080 / (0.316 / zoom * W))                      # W-px -> output px (window = 0.316/zoom of width)
    v = np.diff(p, axis=0)
    if len(v) < 6:
        return None
    m = 12                                                   # ~0.5 s at 24p
    ker = np.ones(m) / m
    pad = np.pad(p, ((m, m), (0, 0)), mode="edge")
    sm = np.stack([np.convolve(pad[:, j], ker, "same")[m:-m] for j in range(2)], 1)
    vs = np.diff(sm, axis=0)
    sp = np.hypot(vs[:, 0], vs[:, 1])
    vmean = float(sp.mean())
    cv = float(sp.std() / (vmean + 0.3))
    main = vs.sum(0)
    rev = float(np.mean((vs @ main) < 0)) if vmean > 0.4 else 0.0
    sh = sharp[s0:s0 + n_src]
    lu = luma[s0:s0 + n_src]
    return dict(jit=float(np.percentile(np.hypot(*(np.diff(p - sm, axis=0)).T), 90)),
                v=vmean, vx=float(abs(vs[:, 0]).mean()), vy=float(abs(vs[:, 1]).mean()),
                cv=cv, rev=rev, sharp=float(sh.min() / (med_sharp + 1e-6)),
                luma=float(lu.max() - lu.min()))


def tier(j):
    return "pass" if j < 1.0 else "check" if j < 2.0 else "fix"


def preset(m, people, movement=None):
    # Footage Prep's gyro-based movement label wins when given (locked/steady/pan/tilt/pan_tilt/gimbal/handheld)
    if movement in ("locked", "steady"):
        return {"smoothness": 0.3, "horizon": True, "horizon_amount": 100}
    if movement == "tilt":
        return {"smoothness": 0.5, "horizon": True, "horizon_amount": 100, "horizon_roll": 0.0}
    if movement == "handheld":
        return {"smoothness": 0.8, "horizon": False}
    if movement in ("pan", "pan_tilt", "gimbal"):
        return {"smoothness": 0.5, "horizon": True, "horizon_amount": 100}
    if people or m["jit"] >= 2.0:
        return {"smoothness": 0.8, "horizon": False}                       # handheld follow / walk
    if m["v"] < 0.4:
        return {"smoothness": 0.3, "horizon": True, "horizon_amount": 100}  # static
    if m["vy"] > 1.5 * m["vx"]:
        return {"smoothness": 0.5, "horizon": True, "horizon_amount": 100, "horizon_roll": 0.0}  # tilt reveal
    return {"smoothness": 0.5, "horizon": True, "horizon_amount": 100}      # slide / push / orbit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slots"); ap.add_argument("clipdir")
    ap.add_argument("-o", default="broll_plan.json"); ap.add_argument("--snippet")
    ap.add_argument("--tl-fps", type=float, default=24.0)
    ap.add_argument("--why", action="store_true", help="print the best window at every speed")
    a = ap.parse_args()
    slots = json.load(open(a.slots))
    plan = []
    cache = {}
    for sl in slots:
        clip = sl["clip"]
        path = f"{a.clipdir.rstrip('/')}/{clip}.MP4"
        fps, gyro, dur = probe(path)
        if sl.get("sel_frames"):                             # straight from footage-prep `selects` (in_frame/out_frame)
            sels = [[a_ / fps, b_ / fps] for a_, b_ in sl["sel_frames"]]
        else:
            sels = sl.get("sel") or [[1.0, dur - 1.0]]
        x, zoom = sl.get("x", 0.5), sl.get("zoom", 1.0)
        speeds = [60, 50] if sl.get("people") else ([25, 30, 40, 48] if fps >= 90 else [48, 40, 30])
        avoid = sl.get("avoid", [])
        best_by = {}                                         # speed -> best window at that speed
        for a0, b0 in sels:
            key = (clip, a0, b0, x, zoom)
            if key not in cache:
                fr = decode(path, a0, b0)
                cache[key] = measure(fr, x, zoom) + (fr,)
            d, sharp, luma, fr = cache[key]
            med = float(np.median(sharp))
            for spd in speeds:
                step = spd / 100 * fps / a.tl_fps            # source frames per output frame
                n_src = int(math.ceil(sl["rec"] * step)) + 1
                for s0 in range(0, len(fr) - n_src + 1, 2):
                    t0 = a0 + s0 / fps
                    t1 = t0 + n_src / fps
                    if any(t0 < e and t1 > s for s, e in avoid):
                        continue
                    # Gyroflow Stabilize Flagged renders the shot at 100% (+1 s handles) and re-applies the
                    # speed, so the clip needs the full real-time length + 1 s after the in point.
                    if t0 + sl["rec"] / a.tl_fps + 1.0 > dur - 0.02:
                        continue
                    m = score(d, sharp, luma, s0, n_src, step, zoom, med)
                    if m is None:
                        continue
                    cost = (m["jit"] + 3 * m["rev"] + 1.0 * min(m["cv"], 1.5)
                            + 2 * max(0, 0.6 - m["sharp"]) + 0.08 * max(0, m["luma"] - 12)
                            + 0.15 * max(0, m["v"] - 10))
                    if spd not in best_by or cost < best_by[spd][0]:
                        best_by[spd] = (cost, spd, t0, n_src, m)
        if a.why:
            for spd_, c_ in sorted(best_by.items(), reverse=True):
                mm = c_[4]
                print(f"   {sl['slot']} @{spd_}% {c_[2]:.2f}s jit {mm['jit']:.2f} v {mm['v']:.1f} cv {mm['cv']:.2f} "
                      f"rev {mm['rev']:.2f} sharp {mm['sharp']:.2f} luma {mm['luma']:.1f}")
        # Tim's ladder: the house speed first; slow down only if it doesn't pass clean.
        best = None
        for spd in sorted(best_by, reverse=True):
            c = best_by[spd]
            m = c[4]
            if m["jit"] < 1.0 and m["rev"] <= 0.15 and m["cv"] <= 0.6 and m["sharp"] >= 0.6 and m["luma"] <= 15:
                best = c
                break
        if best is None and best_by:
            best = min(best_by.values(), key=lambda c: c[0])
        if best is None:
            print(f"{sl['slot']:<8} {clip}  no window long enough in the selects", flush=True)
            plan.append(dict(slot=sl["slot"], clip=clip, action="REPICK", why="selects too short"))
            continue
        cost, spd, t0, n_src, m = best
        sf = int(round(t0 * fps))
        app_len = int(math.ceil(sl["rec"] * fps / a.tl_fps))  # append real-time length, then SetSpeed
        bad = []
        if m["rev"] > 0.15: bad.append("reversal")
        if m["sharp"] < 0.6: bad.append("soft")
        if m["luma"] > 15: bad.append("exposure")
        if m["cv"] > 0.6: bad.append("uneven")
        t = tier(m["jit"])
        if bad or (t == "fix" and not gyro):
            action = "REJECT (" + ",".join(bad or ["shaky, no gyro"]) + "): re-pick"
        elif gyro:
            action = "gyroflow" + ("" if t != "fix" else " (strong)")
        else:
            action = "use" if t == "pass" else "no gyro: list for Tim"
        gf = preset(m, sl.get("people"), sl.get("movement")) if gyro and not action.startswith("REJECT") else None
        row = dict(slot=sl["slot"], clip=clip, at=sl.get("at"), src_in=round(t0, 2), src_out=round(t0 + n_src / fps, 2),
                   sf=sf, ef=sf + app_len, speed=spd, rec=sl["rec"], x=x, zoom=zoom,
                   jit=round(m["jit"], 2), tier=t, v=round(m["v"], 1), cv=round(m["cv"], 2),
                   rev=round(m["rev"], 2), sharp=round(m["sharp"], 2), luma=round(m["luma"], 1),
                   gyro=gyro, action=action, gyroflow=gf)
        plan.append(row)
        print(f"{row['slot']:<8} {clip} {row['src_in']:6.2f}-{row['src_out']:6.2f}s @{spd}%  jit {row['jit']:.2f} {t:<5} "
              f"v {row['v']:4.1f} cv {row['cv']:.2f} rev {row['rev']:.2f} sharp {row['sharp']:.2f}  -> {action}"
              + (f" {json.dumps(gf)}" if gf else ""), flush=True)
    json.dump(plan, open(a.o, "w"), indent=1)
    if a.snippet:
        write_snippet(plan, a.snippet)


SNIP = '''# paste into run_script. Needs: tl = current timeline, rows below, clips from the shoot bin.
import math
mp = project.GetMediaPool(); tl = project.GetCurrentTimeline()
BIN = None  # set: the shoot folder object (assert '/<shoot>/' in File Path)
ROWS = %s
clips = {c.GetName().rsplit('.', 1)[0]: c for c in BIN.GetClipList()}
out = []
for r in ROWS:
    if r['action'].startswith(('REJECT', 'REPICK')):
        out.append((r['slot'], 'skipped', r['action'])); continue
    it = mp.AppendToTimeline([{'mediaPoolItem': clips[r['clip']], 'startFrame': r['sf'], 'endFrame': r['ef'],
                               'recordFrame': tl.GetStartFrame() + r['at'], 'trackIndex': 2, 'mediaType': 1}])[0]
    it.SetName('%%s %%s' %% (r['slot'], r['clip'][1:]))
    z = r['zoom']; it.SetProperty('ZoomX', z); it.SetProperty('ZoomY', z)
    it.SetProperty('Pan', (0.5 - r['x']) * 1080 * z)   # 9:16 fit-space; CONFIRM with one still per timeline
    if r['gyroflow']:
        it.AddMarker(0, 'Sand', 'gyroflow', 'auto preset', 1, json.dumps({'gyroflow': r['gyroflow']}))
        it.SetClipColor('Orange')
    it.SetSpeed({'Percentage': float(r['speed']), 'RippleTimeline': False})
    it.SetProperty('RetimeProcess', resolve.RETIME_OPTICAL_FLOW)
    if r['speed'] < 48: it.SetProperty('MotionEstimation', resolve.MOTION_EST_SPEED_WARP_BETTER)
    out.append((r['slot'], it.GetStart(), it.GetEnd()))
result = out
'''


def write_snippet(plan, path):
    txt = "import json\n" + SNIP % json.dumps(plan, indent=0).replace("null", "None").replace("true", "True").replace("false", "False")
    open(path, "w").write(txt)
    print(f"snippet -> {path}  (set BIN; rows need 'at' = timeline frame offset, from the slot's \"at\")")


if __name__ == "__main__":
    main()
