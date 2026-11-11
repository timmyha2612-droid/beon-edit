#!/usr/bin/env python3
"""B-roll gate: must print PASS before a B-roll pass is reported to Tim (references/broll-rulebook.md).
usage: python3 broll_gate.py --project "The Hired Home" --timeline "November Shoot 2 Concept 2" \
           --plan plan.json[,plan2.json] [--allow "B7,R3"] [--holds-ok "120-260,900-1010"]

Per shot (every ENABLED camera clip above V1 that isn't on a speaker track; titles, nested timelines,
compound clips and stills are skipped):
  speed    100% passes ("no reason to slow"); 96% + Nearest passes (25p cadence); anything slower needs a
           reason record in the plan (shake / match / stretch / hero) and must respect the floor:
           people talking 80%, people moving 60%, others 48%, 100 fps clips 25%
  retime   slowed shots: Optical Flow (Nearest only at 96%)
  gyro     stabilised (a Gyroflow render) or Orange-flagged waiting for gyroflow_headless.py; a camera file
           with no gyro track (no rtmd) is listed for Tim instead of failing; plan `gyro_skip` = Tim's reason
  zoom     peak (Resolve zoom x Dynamic Zoom) vs the pixelation limits: UHD fine 1.25 / fail 1.4,
           1080-high fine 1.0 / fail 1.15 (stabilised clips: the Gyroflow crop is extra, check a still)
  static   static shots need their Dynamic Zoom applied (plan dynamic_zoom.applied = true)
Whole timeline:
  speaker  the speaker never stays on screen more than 4 s at a time (V1 or a track named angle/cam/a-roll
           showing on top), except --holds-ok ranges (Tim's jokes, the first introduction)
  slivers  nothing shows for under 1 s (24 frames at 24p) between two other shots, checked per timeline item
           (never merged), so B-roll ending 1-2 frames before an A-roll cut is caught; no gaps
Reasons are read from the plan rows (`why`, from broll_auto.py) matched by slot (first word of the clip
name). A stabilised clip on the Gyroflow track takes the reason of the disabled original under it.
--allow    shot names Tim approved as exceptions (e.g. a shot he wants as it is)."""
import argparse, json, re, subprocess

FLOORS = {"talking": 80.0, "moving": 60.0}
REASONS = {"shake", "match", "stretch", "hero"}
SPEAKER_TRACK = re.compile(r"angle|cam\b|camera|multicam|a-?roll|interview|speaker", re.I)


# ---------- pure checks (tested without Resolve) ----------

def zoom_tier(peak, height):
    fine, fail = (1.25, 1.4) if height >= 2000 else (1.0, 1.15)
    return "ok" if peak <= fine + 1e-6 else ("check" if peak <= fail + 1e-6 else "fail")


def check_shot(shot, row, allow):
    """shot: dict(name, speed, retime ('optical_flow'|'nearest'|other|None), stabilised, colour, has_gyro,
    zoom, height, fps). row: plan row or None. Returns (problems, pending, notes)."""
    probs, pending, notes = [], [], []
    if shot["name"] in allow:
        return [], [], ["allowed by Tim"]
    why = (row or {}).get("why") or {}
    spd = shot["speed"]
    if spd >= 99.5:
        pass
    elif 95 <= spd <= 97 and shot["retime"] == "nearest":
        pass
    else:
        reason = why.get("speed_reason")
        if reason not in REASONS:
            probs.append(f"speed {spd:g}% with no valid reason (plan why.speed_reason: shake/match/stretch/hero)")
        people = (row or {}).get("people") or False
        floor = FLOORS.get(people, 60.0 if people else (25.0 if shot.get("fps", 50) >= 90 else 48.0))
        if spd < floor - 0.5:
            probs.append(f"speed {spd:g}% below the {floor:g}% floor"
                         + (f" (people {people})" if people else ""))
        if shot["retime"] != "optical_flow":
            probs.append("slowed but retime is not Optical Flow")
    if not shot["stabilised"] and not (row or {}).get("gyro_skip"):
        if shot["colour"] == "Orange":
            pending.append("Orange: run gyroflow_headless.py")
        elif not shot["has_gyro"]:
            notes.append("no gyro data: list for Tim")
        else:
            probs.append("not stabilised (flag Orange + gyroflow marker)")
    dz = (row or {}).get("dynamic_zoom")
    peak = shot["zoom"] * (1 + (dz["amount"] if dz else 0))
    zt = zoom_tier(peak, shot["height"])
    if zt == "fail":
        probs.append(f"zoom peak {peak:.2f}x pixelates on a {shot['height']}p source")
    elif zt == "check" or (shot["stabilised"] and peak > 1.0):
        notes.append(f"zoom {peak:.2f}x: check sharpness on a rendered still"
                     + (" (Gyroflow crop extra)" if shot["stabilised"] else ""))
    if dz and not dz.get("applied"):
        pending.append(f"static shot: add the Dynamic Zoom ({dz.get('dir', 'decide')} {dz.get('amount', 0.04):.0%})")
    if not row:
        notes.append("no plan row (pass --plan): reasons not checked")
    return probs, pending, notes


def top_layer(items, start, end):
    """items: [dict(track, start, end, speaker(bool), name)] enabled camera items; returns runs
    [(start, end, name, speaker)] of whatever is on top, None for gaps."""
    runs = []
    cur = None
    for f in range(start, end):
        top = None
        for it in items:
            if it["start"] <= f < it["end"] and (top is None or it["track"] > top["track"]):
                top = it
        key = (top["name"], top["speaker"], top.get("uid")) if top else (None, False, None)
        if cur and tuple(cur[2:]) == key and cur[1] == f:
            cur[1] = f + 1
        else:
            if cur:
                runs.append(tuple(cur))
            cur = [f, f + 1, key[0], key[1], key[2]]
    if cur:
        runs.append(tuple(cur))
    return runs


def merge_speaker(runs):
    """Join neighbouring speaker runs (V1 cut to a B-angle is still the speaker on screen)."""
    out = []
    for r in runs:
        r = tuple(r[:4])
        if out and r[3] and out[-1][3] and out[-1][1] == r[0]:
            out[-1] = (out[-1][0], r[1], out[-1][2] + "+" + r[2], True)
        else:
            out.append(r)
    return out


def check_slivers(runs, fps):
    """Per timeline item, never merged [Tim, Hired Home Nov S2 C4, 11 Nov 2026]: B-roll that ends 1-2 frames
    before an A-roll cut flashes the outgoing speaker shot for a frame, even when the next A-roll piece is the
    same camera clip (merge_speaker hid that: P5b showed 1 frame at 477 between B4 and P6). Any visible piece
    shorter than 1 s between two other pieces is a sliver; a B-roll edge 1-3 frames off an A-roll cut is named."""
    probs = []
    sliver = int(round(1 * fps))
    for i in range(1, len(runs) - 1):
        a, b, name = runs[i][0], runs[i][1], runs[i][2]
        if name is None or b - a >= sliver:
            continue
        msg = f"{name} shows only {b - a} frames at {a}-{b} (min {sliver})"
        prev_, next_ = runs[i - 1], runs[i + 1]
        if runs[i][3] and not prev_[3]:
            msg += f": B-roll '{prev_[2]}' ends {b - a} f before the A-roll cut at {b}; end it on the cut"
        elif runs[i][3] and not next_[3]:
            msg += f": B-roll '{next_[2]}' starts {b - a} f after the A-roll cut at {a}; start it on the cut"
        probs.append(msg)
    return probs


def check_timeline(runs, fps, holds_ok):
    probs = []
    limit = int(round(4 * fps))
    for i, (a, b, name, spk) in enumerate(runs):
        if name is None:
            probs.append(f"gap/black {a}-{b} ({b - a} frames)")
            continue
        if spk and b - a > limit and not any(h0 <= a and b <= h1 for h0, h1 in holds_ok):
            probs.append(f"speaker on screen {(b - a) / fps:.1f} s at {a}-{b} (max 4 s; cover it, or Tim allows it)")
    return probs


# ---------- Resolve ----------

def main():
    from _resolve import connect
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True); ap.add_argument("--timeline", required=True)
    ap.add_argument("--plan", default=""); ap.add_argument("--allow", default="")
    ap.add_argument("--holds-ok", default="", help="timeline frame ranges (from timeline start) Tim allows over 4 s")
    a = ap.parse_args()
    allow = {s.strip() for s in a.allow.split(",") if s.strip()}
    holds = [tuple(int(x) for x in r.split("-")) for r in a.holds_ok.split(",") if r.strip()]
    plan = {}
    for p in [p for p in a.plan.split(",") if p.strip()]:
        for r in json.load(open(p)):
            plan[r["slot"]] = r
    resolve, pj, tl = connect(a.project, a.timeline)
    OF = getattr(resolve, "RETIME_OPTICAL_FLOW", 3); NEAR = getattr(resolve, "RETIME_NEAREST", 1)
    fps = float(tl.GetSetting("timelineFrameRate") or 24)
    t0 = tl.GetStartFrame()
    probe = {}

    def info(path):
        if path not in probe:
            out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_tag_string,height,r_frame_rate",
                                  "-of", "json", path], capture_output=True, text=True).stdout
            j = json.loads(out or "{}")
            h, f, g = 2160, 50.0, False
            for s in j.get("streams", []):
                if s.get("codec_tag_string") == "rtmd":
                    g = True
                if s.get("height"):
                    h = int(s["height"]); n, d = s["r_frame_rate"].split("/"); f = float(n) / float(d)
            probe[path] = (h, f, g)
        return probe[path]

    rows, fails, pending, nogyro, notes_all = [], 0, 0, [], []
    disabled_by_start = {}
    layer = []
    shots = []
    for k in range(1, tl.GetTrackCount("video") + 1):
        tname = tl.GetTrackName("video", k) or ""
        speaker = k == 1 or bool(SPEAKER_TRACK.search(tname))
        for it in tl.GetItemListInTrack("video", k) or []:
            mpi = it.GetMediaPoolItem()
            path = mpi.GetClipProperty("File Path") if mpi else ""
            if not path or path.lower().endswith((".png", ".jpg", ".tif", ".drp")):
                continue
            name = it.GetName() or ""
            if not it.GetClipEnabled():
                disabled_by_start[it.GetStart()] = name
                continue
            layer.append(dict(track=k, start=it.GetStart() - t0, end=it.GetEnd() - t0, speaker=speaker, name=name,
                              uid=f"{k}:{it.GetStart()}"))
            if speaker:
                continue
            shots.append((it, k, tname, name, path))
    for it, k, tname, name, path in shots:
        h, f, g = info(path)
        stab = "Gyroflow Cache" in path or tname.lower().startswith("gyroflow")
        slot = name.split(" ")[0]
        if slot not in plan and it.GetStart() in disabled_by_start:
            slot = disabled_by_start[it.GetStart()].split(" ")[0]
        rp = it.GetProperty("RetimeProcess")
        shot = dict(name=name, speed=float((it.GetSpeed() or {}).get("Percentage", 100)),
                    retime="optical_flow" if rp == OF else ("nearest" if rp == NEAR else None),
                    stabilised=stab, colour=it.GetClipColor(), has_gyro=g,
                    zoom=float(it.GetProperty("ZoomX") or 1.0), height=h, fps=f)
        probs, pend, notes = check_shot(shot, plan.get(slot), allow)
        if any(n.startswith("no gyro") for n in notes):
            nogyro.append(name)
        fails += bool(probs); pending += bool(pend)
        rows.append((name, shot["speed"], "; ".join(probs + pend + notes) or "ok"))
    end = max([it["end"] for it in layer] or [0])
    runs = top_layer(layer, 0, end)
    tl_probs = check_timeline(merge_speaker(runs), fps, holds) + check_slivers(runs, fps)
    for r in rows:
        print(f"{r[0]:<24} {r[1]:5.0f}%  {r[2]}")
    for p in tl_probs:
        print("timeline:", p)
    if nogyro:
        print("no gyro data (list for Tim):", ", ".join(nogyro))
    fails += len(tl_probs)
    print("PASS" if not fails and not pending else f"FAIL ({fails} to fix, {pending} waiting for Gyroflow / Dynamic Zoom)")


if __name__ == "__main__":
    main()
