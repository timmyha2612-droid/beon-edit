#!/usr/bin/env python3
"""Run Tim's "Gyroflow Stabilize Flagged" headless on a timeline (every enabled Orange clip).
usage: python3 gyroflow_headless.py --project "The Hired Home" --timeline "November Shoot 2 Concept 2"
Same code path as Workspace > Scripts > Utility > Gyroflow Stabilize Flagged; the settings window is
skipped (its DEFAULTS), and each clip's marker preset {"gyroflow": {...}} still applies (broll_auto.py
writes those). Stabilised clips land on the "Gyroflow" track, coloured Yellow; originals are disabled.
The first run can report a false "render failed": run it again, it reuses the cached render.
Log: ~/Library/Logs/GyroflowResolve.log"""
import argparse, os
from _resolve import connect

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True); ap.add_argument("--timeline", required=True)
a = ap.parse_args()
resolve, pj, tl = connect(a.project, a.timeline)
F = os.path.expanduser("~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility/Gyroflow Stabilize Flagged.py")
src = open(F).read()
cut = src.rfind('if __name__ == "__main__"')
g = {"__name__": "gf_flagged_headless", "__file__": F, "resolve": resolve}
exec(compile(src[:cut], F, "exec"), g)
ns = g["ns"]
def _no_ui(*_a, **_k):
    raise RuntimeError("headless")
ns["get_ui"] = _no_ui
ns["resolve"] = resolve
ns["log"](f"==== Gyroflow Stabilize Flagged (headless, beon-edit) {a.project} / {a.timeline} ====")
ns["main"]()
print("DONE - check ~/Library/Logs/GyroflowResolve.log, then run broll_gate.py")
