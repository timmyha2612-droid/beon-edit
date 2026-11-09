#!/usr/bin/env python3
"""B-roll gate: must print PASS before a B-roll pass is reported to Tim.
usage: python3 broll_gate.py --project "The Hired Home" --timeline "November Shoot 2 Concept 2" [--allow "B7,R3"]

Checks every ENABLED video clip above V1 that comes from a camera file (titles, nested timelines,
compound clips, stills are skipped):
  speed   <= 60% (house 48% for empty-house 50p, 50-60% people); 25p shots at 96% Nearest are OK
  retime  Optical Flow (or Nearest at 96%)
  gyro    stabilised (a Gyroflow render, Yellow/Green) or Orange-flagged waiting for gyroflow_headless.py;
          a camera file with no gyro track (no rtmd) is listed for Tim instead of failing
--allow   shot names Tim approved as exceptions (e.g. a tripod shot he wants at 100%)."""
import argparse, subprocess
from _resolve import connect

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True); ap.add_argument("--timeline", required=True)
ap.add_argument("--allow", default="")
a = ap.parse_args()
allow = {s.strip() for s in a.allow.split(",") if s.strip()}
resolve, pj, tl = connect(a.project, a.timeline)
OF = getattr(resolve, "RETIME_OPTICAL_FLOW", 3); NEAR = getattr(resolve, "RETIME_NEAREST", 1)
rows, fails, pending, nogyro = [], 0, 0, []
_gyro = {}
def has_rtmd(p):
    if p not in _gyro:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_tag_string", "-of", "csv=p=0", p],
                             capture_output=True, text=True).stdout
        _gyro[p] = "rtmd" in out
    return _gyro[p]
for k in range(2, tl.GetTrackCount("video") + 1):
    tname = tl.GetTrackName("video", k)
    for it in tl.GetItemListInTrack("video", k) or []:
        if not it.GetClipEnabled():
            continue
        mpi = it.GetMediaPoolItem()
        path = mpi.GetClipProperty("File Path") if mpi else ""
        if not path or path.lower().endswith((".png", ".jpg", ".tif", ".drp")):
            continue
        name, col = it.GetName(), it.GetClipColor()
        spd = float((it.GetSpeed() or {}).get("Percentage", 100))
        rp = it.GetProperty("RetimeProcess")
        stab = "Gyroflow Cache" in path or tname.lower().startswith("gyroflow")
        prob = []
        if name in allow:
            rows.append((name, spd, "allowed by Tim")); continue
        if not (spd <= 60.5 or (95 <= spd <= 97 and rp == NEAR)):
            prob.append(f"speed {spd:g}% (want 48%)")
        if spd < 99 and rp not in (OF, NEAR):
            prob.append("retime not Optical Flow")
        if not stab:
            if col == "Orange":
                pending += 1; prob.append("Orange: run gyroflow_headless.py")
            elif not has_rtmd(path):
                nogyro.append(name)
            else:
                prob.append("not stabilised (flag Orange + gyroflow marker)")
        fails += bool([p for p in prob if not p.startswith("Orange")])
        rows.append((name, spd, "; ".join(prob) or "ok"))
for r in rows:
    print(f"{r[0]:<24} {r[1]:5.0f}%  {r[2]}")
if nogyro:
    print("no gyro data (list for Tim):", ", ".join(nogyro))
print("PASS" if not fails and not pending else f"FAIL ({fails} to fix, {pending} waiting for Gyroflow)")
