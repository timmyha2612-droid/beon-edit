#!/usr/bin/env python3
"""Run Tim's "Gyroflow Stabilize Flagged" headless on a timeline (every enabled Orange clip).
usage: python3 gyroflow_headless.py --project "The Hired Home" --timeline "November Shoot 2 Concept 2" [--script PATH]
Script path: --script, else editor.json tools.gyroflow.stabilize_script ("<Fusion Scripts>" = Resolve's
Fusion/Scripts folder), else <Fusion Scripts>/Utility/Gyroflow Stabilize Flagged.py.
Gyroflow not installed (editor.json tools.gyroflow.installed: false): it stops and says so; the gate then
wants unstabilised shots slowed, replaced or marked.
Same code path as Workspace > Scripts > Utility > Gyroflow Stabilize Flagged; the settings window is
skipped (its DEFAULTS), and each clip's marker preset {"gyroflow": {...}} still applies (broll_auto.py
writes those). Stabilised clips land on the "Gyroflow" track, coloured Yellow; originals are disabled.
The first run can report a false "render failed": run it again, it reuses the cached render.
Log: ~/Library/Logs/GyroflowResolve.log"""
import argparse, os
from _beon import gyroflow_installed, gyroflow_script

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--project", required=True); ap.add_argument("--timeline", required=True)
ap.add_argument("--script", help="path to Gyroflow Stabilize Flagged.py (default from editor.json)")
a = ap.parse_args()
if not a.script and not gyroflow_installed():
    raise SystemExit("Gyroflow isn't installed (editor.json tools.gyroflow.installed: false): nothing to run. "
                     "Slow (shake), replace or mark the handheld shots, then run broll_gate.py")
F = os.path.expanduser(a.script) if a.script else gyroflow_script()
if not os.path.isfile(F):
    raise SystemExit(f"no Gyroflow Stabilize Flagged script at {F} (set editor.json tools.gyroflow.stabilize_script)")
from _resolve import connect
resolve, pj, tl = connect(a.project, a.timeline)
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
