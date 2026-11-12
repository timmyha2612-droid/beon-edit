#!/usr/bin/env python3
"""PreToolUse guard for Resolve run_script calls (beon-edit plugin), the Beon B-roll rulebook.

Blocks a script that appends camera video above V1 (B-roll) unless it
  - carries a reason record per shot ('why', from broll/scripts/broll_auto.py), because speed is
    100% by default and every slow-down needs a valid reason ([Tim, 9 Nov 2026]),
  - sets the retime (RetimeProcess) whenever it slows a shot (SetSpeed), and
  - flags the shots for Gyroflow (Orange colour + a "gyroflow" marker preset),
which is what broll_auto.py --snippet writes. The Gyroflow flag is only required when
~/.beon-edit/editor.json says tools.gyroflow.installed is true (or doesn't say); an editor without
Gyroflow gets the other two checks only.

Not B-roll (counters, titles, logo, nested timelines, a shot the editor approved)?
Put a comment in the script:  # broll-ok: <reason>
B-roll with no gyro data, or a drone shot (no Gyroflow needed)?  # broll-nogyro: <reason>
Exit 2 = block; the message goes back to Claude."""
import json, pathlib, re, sys

try:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "skills" / "house-rules" / "scripts"))
    import beon_config as bc
except Exception as e:
    bc = None
    sys.stderr.write(f"beon-edit B-roll gate: can't import beon_config ({e}); assuming Gyroflow is installed.\n")


def gyroflow_installed():
    if not bc:
        return True
    try:
        g = (bc.load_editor().get("tools") or {}).get("gyroflow") or {}
    except Exception:
        return True
    return g.get("installed") is not False if isinstance(g, dict) else True


try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
script = (data.get("tool_input") or {}).get("script") or ""
if "AppendToTimeline" not in script:
    sys.exit(0)
if re.search(r"#\s*broll-ok\s*:\s*\S", script):
    sys.exit(0)
upper = re.search(r"""['"]trackIndex['"]\s*:\s*([2-9]|1\d)""", script)
video = re.search(r"""['"]mediaType['"]\s*:\s*1""", script)
if not (upper and video):
    sys.exit(0)
missing = []
if not re.search(r"""['"]why['"]\s*:""", script):
    missing.append("a reason record per shot ('why' from broll_auto.py: line, move, speed + reason, gyro, pan)")
if "SetSpeed" in script and "RetimeProcess" not in script:
    missing.append("RetimeProcess for the slowed shots (Optical Flow; Nearest only at 96%)")
nogyro = re.search(r"#\s*broll-nogyro\s*:\s*\S", script)
gyro = gyroflow_installed()
if gyro and not nogyro and not (re.search(r"Orange", script) and "gyroflow" in script.lower()):
    missing.append("Gyroflow flag (Orange + gyroflow marker preset), or '# broll-nogyro: <reason>'")
if not missing:
    sys.exit(0)
if gyro:
    flow = ("-> paste its snippet (window, speed only when slowed, retime, Pan/Zoom, Orange + gyroflow marker, why) "
            "-> scripts/gyroflow_headless.py -> scripts/broll_gate.py --plan plan.json must print PASS. ")
else:
    flow = ("-> paste its snippet (window, speed only when slowed, retime, Pan/Zoom, why) "
            "-> scripts/broll_gate.py --plan plan.json. Gyroflow isn't installed (editor.json tools.gyroflow), "
            "so handheld shots can't be stabilised: tell the editor which shots need a re-pick or Speed Warp. ")
sys.stderr.write(
    "beon-edit B-roll gate: this script places B-roll on V2+ without " + "; ".join(missing) + ".\n"
    "B-roll rulebook (broll/references/broll-rulebook.md): 100% unless there's a valid reason to slow "
    "(shake, match the neighbours' camera speed, stretch, hero), and every shot records why. "
    "Every B-roll pass: selects (Footage Prep, or the contact-sheet fallback) -> broll/scripts/broll_auto.py "
    "SLOTS.json CLIP_DIR --snippet apply.py " + flow +
    "If this append is not B-roll (titles, counters, logo, nested timeline) or the editor approved an exception, "
    "add a comment '# broll-ok: <reason>' to the script.\n")
sys.exit(2)
