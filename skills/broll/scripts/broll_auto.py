#!/usr/bin/env python3
"""Pick the smoothest window, speed and Gyroflow preset for every B-roll slot, numerically.

Footage Prep (gyro/rtmd) already scores each SELECT (stability, jitter, shaky_frac, movement): use it to
choose which selects are allowed (no shaky/whip/motion_blur/blocked flags, stability >= ~0.75). A slot only
plays ~1-3 s of a 3-12 s select, and Footage Prep doesn't score that stretch at the slot's speed. This script
does: one cheap decode per select (gray, 384 px wide). No images to look at, one line per slot.
Run it BEFORE placing B-roll and place exactly what it prints; open frames only for the
subject/people check of the winner (framing_sheet.py / one still).

usage:
  broll_auto.py SLOTS.json CLIP_DIR [-o plan.json] [--snippet resolve_apply.py] [--card JOB_CARD.md]
  CLIP_DIR  the shoot folder or a card folder; "clip" is a stem (C0185), a file name with any video
            extension (C0185.mov), or a path relative to CLIP_DIR (A001/C0185.MP4). Each plan row keeps that
            path as `src_rel`; the snippet places media pool items by it (cards restart numbering)
  --card    delivery size and timeline fps from the job card / client profile (default 9:16 1080x1920 24p);
            --tl-fps / --size override it
  --no-gyroflow  Gyroflow isn't installed (also read from editor.json tools.gyroflow.installed: false):
            no Orange flags; shaky shots get slowed, replaced or marked for the editor instead

Without Footage Prep (editor.json tools.footage_prep, or the app not reachable) the slot inputs come from:
  sel        ingest.py gyro shake windows (bestwin.py ranks them) or the whole clip minus 1 s each end
  movement   omit it (the preset then follows the measured move) or set it from a motion card
  stability  omit it. Never invent one: without it a locked shot is not treated as camera-still, so check
             any locked shot this script slows for `shake` by eye (people or cars moving are not shake)
             and force "speed": 100 when the camera didn't move.

SLOTS.json: [{"slot": "B6", "clip": "C0185", "rec": 74,            # timeline frames the shot plays
              "sel_frames": [[275, 528], ...],                      # footage-prep `selects` in_frame/out_frame (preferred)
              "sel": [[5.5, 10.56], ...],                           # or select windows in source seconds
              "movement": "pan_tilt",                               # footage-prep movement label (sets the Gyroflow preset)
              "stability": 0.996,                                   # footage-prep metrics.stability; locked/steady
                                                                    #   at >= 0.95 = camera still: never slowed for
                                                                    #   shake, subject motion doesn't REJECT
              "x": 0.48, "zoom": 1.0,                               # 9:16 window (subject centre, zoom)
              "at": 635,                                            # timeline frame offset (for --snippet)
              "people": false,                                      # "talking" (>= 80%) | "moving" (>= 60%) | false
              "line": "the finishes are all custom",               # words the shot covers (goes into `why`)
              "subject": "stone benchtop",                         # what the Pan centres (goes into `why`)
              "match_v": 3.2,                                       # optional: camera speed (px/frame) of the
                                                                    #   neighbouring shots -> speed reason `match`
              "hero": false,                                        # optional: hero/mood shot -> may breathe
              "speed": 70, "speed_reason": "match",                 # optional: force a speed (reason required)
              "static_dz": "in", "dz_amount": 0.04,                 # optional: Dynamic Zoom for static shots
              "avoid": [[6.0, 7.5]]}, ...]                          # source ranges already used (optional)
  "sel" may be omitted: then the whole clip minus 1 s each end.

What it measures, all at OUTPUT timing (after the slow-down, inside the 9:16 window, px at 1080 wide):
  jit   p90 of high-frequency wobble (pos minus its ~0.5 s moving average)   pass < 1.0, check < 2.0, fix
  v     mean camera speed px/frame; cv = how uneven it is (> 0.3 = speeds up / slows down)
  rev   share of frames moving against the main direction (a reset or a change of move)
  sharp min Laplacian in the window vs the clip's median (< 0.6 = focus pull / blur)
  luma  range of mean brightness (> 12 = exposure jump)
Speed (Tim, 9 Nov 2026, references/broll-rulebook.md section 2): 100% unless there's a valid reason,
25p footage 96% Nearest (`cadence`). It only goes slower for a reason, printed per slot:
  shake    100% isn't clean (jitter/uneven), so the highest speed that is clean
  match    `match_v` given: the clean speed whose camera speed is closest to the neighbours'
  stretch  no window of the select is long enough at 100%
  hero     `hero: true`: the slowest clean speed (a shot that should breathe)
Floors: people talking 80%, people moving 60%, else 48%, 100 fps clips 25%.
Sizes below assume the 9:16 1080x1920 default; with --card/--size the 9:16 window and the px scale follow
the delivery (window = delivery aspect / source aspect of the frame width, px at the delivery width).

Treatment (printed per slot):
  speed + reason + Retime (none at 100%, Nearest at 96% cadence, Optical Flow, Speed Warp Better below 48%)
  zoom peak (zoom x Dynamic Zoom) against the pixelation limits (UHD 1.25 / 1.4, 1080-high 1.0 / 1.15);
  the Gyroflow crop isn't known before the render, so check stabilised shots on a still
  static shots: a Dynamic Zoom to add (3-5%, in or out by the shot), listed by --snippet
  gyroflow preset (Tim's presets) when the file has a gyro track (Sony rtmd) and Gyroflow is installed,
  else "no gyro: list for the editor" (row gyro_source "none"; non-Sony bodies always land here)
  REJECT when even the best window is still 'fix' after slowing (Gyroflow can't save reversals,
  focus pulls, walking bob): re-pick another select for that line.
Every row carries `why` (line, move, speed, gyro, pan, dynamic_zoom): the reason record the gate and the
QA checks read, and the hook requires in any B-roll placement script.
--snippet writes a ready-to-paste run_script body that appends the shots on V2 with the chosen
source range, speed (only when slowed), retime, Pan/Zoom, Orange colour and the Gyroflow marker (marker
before retime), plus the reason records.
Then run gyroflow_headless.py, then shake_check.py on a proxy render to confirm.
"""
import argparse, json, math, os, pprint, subprocess, sys
from _beon import add_delivery_args, delivery, find_clip, clip_stem, gyroflow_installed, footage_prep_enabled

np = cv2 = None    # imported in main(), so --help works without numpy/opencv
W, H = 384, 216
WIN = 0.316        # 9:16 window as a share of a 16:9 frame's width (set per delivery in main)
OUT_W = 1080       # delivery width in px (jitter and speeds are px at this width)


def probe(path):
    """fps, gyro (Sony rtmd track; other bodies: False), duration, height, width. Never raises on odd files."""
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,codec_tag_string,r_frame_rate,height,width:format=duration",
                          "-of", "json", path], capture_output=True, text=True).stdout
    try:
        j = json.loads(out or "{}")
    except ValueError:
        j = {}
    fps = 50.0
    gyro = False
    height, width = 2160, 3840
    vseen = False
    for s in j.get("streams", []):
        if s.get("codec_type") == "video" and not vseen:
            vseen = True
            try:
                n, d = s.get("r_frame_rate", "50/1").split("/")
                fps = float(n) / float(d) or fps
            except (ValueError, ZeroDivisionError):
                pass
            height = int(s.get("height") or height)
            width = int(s.get("width") or width)
        if s.get("codec_tag_string") == "rtmd":
            gyro = True
    try:
        dur = float((j.get("format") or {}).get("duration"))
    except (TypeError, ValueError):
        raise SystemExit(f"{path}: ffprobe can't read it")
    return fps, gyro, dur, height, width


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
    ww = WIN / zoom * W
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
    p = p * (OUT_W / (WIN / zoom * W))                       # W-px -> output px (window = WIN/zoom of width)
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


REASONS = {"shake", "match", "stretch", "hero", "cadence"}


def speed_ladder(fps, people, tl_fps=24.0):
    """Tim, 9 Nov 2026: 100% unless there's a reason; floors by what's in the shot."""
    base = 96.0 if 23.5 < fps < 26 and abs(tl_fps - 24) < 0.5 else 100.0   # 25p on a 24p timeline: 96% Nearest
    if people == "talking":
        floor = 80.0
    elif people:
        floor = 60.0
    elif fps >= 90:
        floor = 25.0
    else:
        floor = 48.0
    ladder = [base] + [float(s) for s in (90, 80, 70, 60, 55, 48, 40, 30, 25) if s < base and s >= floor]
    return base, floor, ladder


def clean(m):
    return m["jit"] < 1.0 and m["rev"] <= 0.15 and m["cv"] <= 0.6 and m["sharp"] >= 0.6 and m["luma"] <= 15


STILL_STAB = 0.95   # Footage Prep gyro stability at or above this on a locked/steady shot = the camera is still


def gyro_still(sl):
    """Footage Prep's gyro says the camera didn't move (Tim, 10 Nov 2026). Optical flow then only sees the
    subject (people talking, turning, cars), which isn't shake, so it's no reason to slow the shot."""
    return sl.get("movement") in ("locked", "steady") and float(sl.get("stability") or 0) >= STILL_STAB


def choose(best_by, base, sl, forced):
    """Pick the speed and name the reason (rulebook section 2)."""
    if not best_by:
        return None, None
    if (forced is None and gyro_still(sl) and base in best_by
            and not sl.get("hero") and sl.get("match_v") is None):
        return best_by[base], base_reason(base)
    if forced is not None:
        c = best_by.get(float(forced))
        return (c, sl.get("speed_reason") or ("cadence" if float(forced) == base == 96 else "none")) if c else (None, None)
    cleans = [c for c in best_by.values() if clean(c[4])]
    if sl.get("hero") and cleans:
        c = min(cleans, key=lambda c: c[1])
        return c, ("hero" if c[1] < base else base_reason(base))
    if sl.get("match_v") is not None and cleans:
        c = min(cleans, key=lambda c: (abs(c[4]["v"] - float(sl["match_v"])), -c[1]))
        return c, ("match" if c[1] < base else base_reason(base))
    for spd in sorted(best_by, reverse=True):
        c = best_by[spd]
        if clean(c[4]):
            if spd >= base:
                return c, base_reason(base)
            return c, ("shake" if base in best_by else "stretch")
    c = min(best_by.values(), key=lambda c: c[0])         # nothing clean: least bad, flagged by the action
    if c[1] >= base:
        return c, base_reason(base)
    return c, ("shake" if base in best_by else "stretch")


def base_reason(base):
    return "cadence" if base == 96 else "none"


def speed_text(spd, reason, sl, m):
    if reason == "none":
        return "100%: no reason to slow"
    if reason == "cadence":
        return "96% Nearest: 25p on a 24p timeline, every frame plays once"
    if reason == "shake":
        return f"{spd:g}%: shake/jerkiness at the faster speeds (jitter {m['jit']:.2f} px at this speed)"
    if reason == "match":
        if sl.get("match_v") is None:
            return f"{spd:g}%: matches the neighbours' camera speed (forced; camera speed here {m['v']:.1f} px/frame)"
        return f"{spd:g}%: matches the neighbours' camera speed ({m['v']:.1f} vs {float(sl['match_v']):.1f} px/frame)"
    if reason == "stretch":
        return f"{spd:g}%: the select is too short to fill the slot at 100%"
    if reason == "hero":
        return f"{spd:g}%: hero/mood shot, let it breathe"
    return f"{spd:g}%: {reason}"


def zoom_tier(peak, height):
    """Rulebook section 5: UHD fine to 1.25, check to 1.4; 1080-high fine to 1.0, check to 1.15."""
    fine, fail = (1.25, 1.4) if height >= 2000 else (1.0, 1.15)
    return "ok" if peak <= fine + 1e-6 else ("check" if peak <= fail + 1e-6 else "fail")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slots"); ap.add_argument("clipdir")
    ap.add_argument("-o", default="broll_plan.json"); ap.add_argument("--snippet")
    ap.add_argument("--tl-fps", type=float, help="timeline fps (default: --card delivery, else 24)")
    add_delivery_args(ap, fps=False)
    ap.add_argument("--no-gyroflow", action="store_true",
                    help="Gyroflow not installed (default: editor.json tools.gyroflow.installed)")
    ap.add_argument("--why", action="store_true", help="print the best window at every speed")
    a = ap.parse_args()
    global np, cv2, WIN, OUT_W
    import numpy as np
    import cv2
    dl = delivery(a)
    if a.tl_fps is None:
        a.tl_fps = dl["fps"]
    OUT_W = dl["width"]
    has_gf = gyroflow_installed() and not a.no_gyroflow
    fp_on = footage_prep_enabled()
    if not has_gf:
        print("Gyroflow not installed: no Orange flags; shaky shots get slowed (shake), replaced or marked "
              "(plan gyro_skip) for the editor", flush=True)
    slots = json.load(open(a.slots))
    plan = []
    cache = {}
    stems = {}                                               # stem -> first file (Sony cards restart numbering)
    for sl in slots:
        clip = sl["clip"]
        path = find_clip(a.clipdir, clip)
        clip = clip_stem(clip)                               # names use the stem; the snippet matches src_rel
        rel = os.path.relpath(path, os.path.expanduser(a.clipdir)).replace(os.sep, "/")
        src_rel = path if rel.startswith("..") else rel      # shoot-relative path (A001/C0001.MP4)
        other = stems.setdefault(clip.lower(), path)
        if os.path.realpath(other) != os.path.realpath(path):
            print(f"{sl['slot']:<8} NOTE {clip} names two files ({other}, {path}): "
                  f"the snippet places each by its file path (src_rel), not by name", flush=True)
        fps, gyro, dur, height, width = probe(path)
        gyro_src = "sony-rtmd" if gyro else "none"
        if (dl["width"], dl["height"]) == (1080, 1920) and abs(width / height - 16 / 9) < 0.01:
            WIN = 0.316
        else:
            WIN = min(1.0, (dl["width"] / dl["height"]) / (width / height))
        gyro = gyro and has_gf                               # no Gyroflow = treat as no gyro for the action
        if sl.get("sel_frames"):                             # straight from footage-prep `selects` (in_frame/out_frame)
            sels = [[a_ / fps, b_ / fps] for a_, b_ in sl["sel_frames"]]
        else:
            sels = sl.get("sel") or [[1.0, dur - 1.0]]
        x, zoom = sl.get("x", 0.5), sl.get("zoom", 1.0)
        people = sl.get("people")
        if people is True:
            people = "moving"
        base, floor, ladder = speed_ladder(fps, people, a.tl_fps)
        forced = sl.get("speed")
        if forced is not None:
            if sl.get("speed_reason") not in REASONS and float(forced) < base:
                sys.exit(f"{sl['slot']}: speed {forced}% needs speed_reason, one of {sorted(REASONS)}")
            if float(forced) < floor:
                print(f"{sl['slot']:<8} WARNING forced {forced}% is below the {floor}% floor for this shot", flush=True)
            ladder = [float(forced)]
        avoid = sl.get("avoid", [])
        best_by = {}                                         # speed -> best window at that speed
        for a0, b0 in sels:
            key = (clip, a0, b0, x, zoom)
            if key not in cache:
                fr = decode(path, a0, b0)
                cache[key] = measure(fr, x, zoom) + (fr,)
            d, sharp, luma, fr = cache[key]
            med = float(np.median(sharp))
            for spd in ladder:
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
                print(f"   {sl['slot']} @{spd_:g}% {c_[2]:.2f}s jit {mm['jit']:.2f} v {mm['v']:.1f} cv {mm['cv']:.2f} "
                      f"rev {mm['rev']:.2f} sharp {mm['sharp']:.2f} luma {mm['luma']:.1f}"
                      + ("  clean" if clean(mm) else ""))
        best, reason = choose(best_by, base, sl, forced)
        if best is None:
            print(f"{sl['slot']:<8} {clip}  no window long enough in the selects", flush=True)
            plan.append(dict(slot=sl["slot"], clip=clip, src_rel=src_rel, action="REPICK", why={"speed": "selects too short"}))
            continue
        cost, spd, t0, n_src, m = best
        sf = int(round(t0 * fps))
        app_len = int(math.ceil(sl["rec"] * fps / a.tl_fps))  # append real-time length, then SetSpeed
        still = gyro_still(sl)                               # flow motion = the subject, not the camera
        if sl.get("stability") is None and reason == "shake":
            print(f"{sl['slot']:<8} WARNING slowed for shake with no `stability` ({sl.get('movement') or 'movement unset'}): "
                  + (f"pass Footage Prep's metrics.stability (>= {STILL_STAB} on a locked/steady shot = subject "
                     f"motion, plays at 100%)" if fp_on else
                     "check it by eye; if the camera didn't move (only people or cars), force \"speed\": 100"),
                  flush=True)
        bad = []
        if m["rev"] > 0.15 and not still: bad.append("reversal")
        if m["sharp"] < 0.6: bad.append("soft")
        if m["luma"] > 15: bad.append("exposure")
        if m["cv"] > 0.6 and not still: bad.append("uneven")
        t = "pass" if still else tier(m["jit"])
        static = sl.get("movement") in ("locked", "steady") or m["v"] < 0.4
        dz = None
        if static:
            dz = {"dir": sl.get("static_dz") or "decide", "amount": float(sl.get("dz_amount", 0.04)), "applied": False}
        peak = zoom * (1 + (dz["amount"] if dz else 0))
        ztier = zoom_tier(peak, height)
        if ztier == "fail":
            bad.append(f"zoom {peak:.2f}x pixelates")
        if bad or (t == "fix" and not gyro):
            action = "REJECT (" + ",".join(bad or ["shaky, no gyro"]) + "): re-pick"
        elif gyro:
            action = "gyroflow" + ("" if t != "fix" else " (strong)")
        else:
            action = "use" if t == "pass" else ("no gyro: list for the editor" if has_gf else
                                                "no Gyroflow: slow (shake), replace or mark for the editor")
        gf = preset(m, people, sl.get("movement")) if gyro and not action.startswith("REJECT") else None
        retime = None if spd >= 99.5 else ("nearest" if reason == "cadence" else "optical_flow")
        why = dict(line=sl.get("line", ""),
                   move=(sl.get("movement") or "measured") + f", camera speed {m['v']:.1f} px/frame"
                        + (", static" if static else "")
                        + (f" (Footage Prep gyro stability {float(sl['stability']):.3f}: camera still, "
                           f"measured motion is the subject)" if still else ""),
                   speed=speed_text(spd, reason, sl, m),
                   speed_reason=reason,
                   gyro=(f"preset {gf['smoothness']}" + (" + horizon lock" if gf.get("horizon") else " no lock")
                         + f" ({sl.get('movement') or 'measured move'})") if gf else
                        ("rejected shot" if gyro else "no gyro track: list for the editor" if gyro_src == "none"
                         else "Gyroflow not installed: slowed, replaced or marked by the editor"),
                   pan=f"x {x:.2f} centres {sl.get('subject') or 'the subject (name it in the slot)'}",
                   zoom=f"peak {peak:.2f}x on {height}p source: {ztier}"
                        + ("" if not gf else " (plus the Gyroflow crop: check a still)"))
        if dz:
            why["dynamic_zoom"] = (f"static shot: zoom {dz['dir']} {dz['amount'] * 100:.0f}%"
                                   + (" (pick in or out by the shot)" if dz["dir"] == "decide" else ""))
        row = dict(slot=sl["slot"], clip=clip, src_rel=src_rel, at=sl.get("at"), src_in=round(t0, 2), src_out=round(t0 + n_src / fps, 2),
                   sf=sf, ef=sf + app_len, speed=spd, retime=retime, rec=sl["rec"], x=x, zoom=zoom, fps=fps,
                   people=people or False, jit=round(m["jit"], 2), tier=t, v=round(m["v"], 1), cv=round(m["cv"], 2),
                   rev=round(m["rev"], 2), sharp=round(m["sharp"], 2), luma=round(m["luma"], 1),
                   gyro=gyro, gyro_source=gyro_src, still=still, action=action, gyroflow=gf, dynamic_zoom=dz, zoom_peak=round(peak, 3),
                   zoom_tier=ztier, why=why)
        plan.append(row)
        print(f"{row['slot']:<8} {clip} {row['src_in']:6.2f}-{row['src_out']:6.2f}s @{spd:g}% ({reason})  "
              f"jit {row['jit']:.2f} {t:<5} v {row['v']:4.1f} cv {row['cv']:.2f} rev {row['rev']:.2f} "
              f"sharp {row['sharp']:.2f} zoom {peak:.2f} {ztier}  -> {action}"
              + (f" {json.dumps(gf)}" if gf else "") + (f"  DZ {dz['dir']} {dz['amount']:.0%}" if dz else ""),
              flush=True)
    json.dump(plan, open(a.o, "w"), indent=1)
    if a.snippet:
        write_snippet(plan, a.snippet, dl["width"])


SNIP = '''# paste into run_script. Needs: tl = current timeline, rows below, clips from the shoot bin.
# Every row carries 'why' (the reason record, Tim 9 Nov 2026); the beon-edit hook checks it's here.
import math
mp = project.GetMediaPool(); tl = project.GetCurrentTimeline()
BIN = None  # set: the shoot folder object (assert '/<shoot>/' in File Path)
PAN_W = %d  # delivery width (job card Delivery / client profile)
ROWS = %s
ITEMS = BIN.GetClipList()

def item_for(r):
    # by file path first: two cards can hold the same stem (A001/C0001, A002/C0001)
    rel = r.get('src_rel') or ''
    if rel:
        hits = [c for c in ITEMS if (lambda fp: fp == rel or fp.endswith('/' + rel))(
                c.GetClipProperty('File Path') or '')]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise Exception('%%s: %%d media pool items match %%s' %% (r['slot'], len(hits), rel))
    hits = [c for c in ITEMS if c.GetName().rsplit('.', 1)[0] == r['clip']]
    if len(hits) != 1:
        raise Exception('%%s: %%d media pool items named %%s (need the file path)' %% (r['slot'], len(hits), r['clip']))
    return hits[0]

out = []
for r in ROWS:
    if r['action'].startswith(('REJECT', 'REPICK')):
        out.append((r['slot'], 'skipped', r['action'])); continue
    it = mp.AppendToTimeline([{'mediaPoolItem': item_for(r), 'startFrame': r['sf'], 'endFrame': r['ef'],
                               'recordFrame': tl.GetStartFrame() + r['at'], 'trackIndex': 2, 'mediaType': 1}])[0]
    it.SetName('%%s %%s' %% (r['slot'], r['clip'][1:]))
    z = r['zoom']; it.SetProperty('ZoomX', z); it.SetProperty('ZoomY', z)
    it.SetProperty('Pan', (0.5 - r['x']) * PAN_W * z)  # fit-space (delivery width); CONFIRM with one still per timeline
    if r['gyroflow']:
        it.AddMarker(0, 'Sand', 'gyroflow', 'auto preset', 1, json.dumps({'gyroflow': r['gyroflow']}))
        it.SetClipColor('Orange')
    if r['speed'] < 99.5:                               # 100%%: no SetSpeed, no retime
        it.SetSpeed({'Percentage': float(r['speed']), 'RippleTimeline': False})
        if r['retime'] == 'nearest':
            it.SetProperty('RetimeProcess', resolve.RETIME_NEAREST)
        else:
            it.SetProperty('RetimeProcess', resolve.RETIME_OPTICAL_FLOW)
            if r['speed'] < 48: it.SetProperty('MotionEstimation', resolve.MOTION_EST_SPEED_WARP_BETTER)
    out.append((r['slot'], it.GetStart(), it.GetEnd(), r['why']['speed']))
result = out
'''


def write_snippet(plan, path, pan_w=1080):
    # a Python literal, not JSON text: reason strings may contain words like "true" or "null"
    txt = "import json\n" + SNIP % (pan_w, pprint.pformat(plan, width=120, sort_dicts=False))
    nogf = [r["slot"] for r in plan if not r.get("gyroflow") and not str(r.get("action", "")).startswith(("REJECT", "REPICK"))]
    if nogf:
        txt = (f"# broll-nogyro: {', '.join(nogf)} have no Gyroflow flag (no gyro track, or Gyroflow not installed); "
               "listed for the editor\n") + txt
    open(path, "w").write(txt)
    print(f"snippet -> {path}  (set BIN; rows need 'at' = timeline frame offset, from the slot's \"at\")")
    dz = [r for r in plan if r.get("dynamic_zoom")]
    if dz:
        print("Dynamic Zoom to add by hand or with the DRT clone method (static shots, rulebook section 5):")
        for r in dz:
            print(f"  {r['slot']} {r['clip']}: {r['why']['dynamic_zoom']}; set dynamic_zoom.applied true in the plan after")


if __name__ == "__main__":
    main()
