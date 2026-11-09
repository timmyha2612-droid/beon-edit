#!/usr/bin/env python3
"""PreToolUse guard for Resolve run_script calls (beon-edit plugin).

Blocks a script that appends camera video above V1 (B-roll) unless it also
  - sets a slow-down (SetSpeed),
  - sets the retime (RetimeProcess), and
  - flags the shot for Gyroflow (Orange colour + a "gyroflow" marker preset),
which is what broll-qaqc/scripts/broll_auto.py --snippet writes.

Not B-roll (counters, titles, logo, nested timelines, a static shot Tim approved)?
Put a comment in the script:  # broll-ok: <reason>
Exit 2 = block; the message goes back to Claude."""
import json, re, sys

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
if "SetSpeed" not in script:
    missing.append("SetSpeed (48% house speed, from broll_auto.py)")
if "RetimeProcess" not in script:
    missing.append("RetimeProcess (optical flow)")
if not (re.search(r"Orange", script) and "gyroflow" in script.lower()):
    missing.append("Gyroflow flag (Orange + gyroflow marker preset)")
if not missing:
    sys.exit(0)
sys.stderr.write(
    "beon-edit B-roll gate: this script places B-roll on V2+ without " + "; ".join(missing) + ".\n"
    "Every B-roll pass: Footage Prep selects -> broll-qaqc/scripts/broll_auto.py SLOTS.json CLIP_DIR --snippet apply.py "
    "-> paste its snippet (window, speed, retime, Pan/Zoom, Orange + gyroflow marker) -> scripts/gyroflow_headless.py "
    "-> scripts/broll_gate.py must print PASS. If this append is not B-roll (titles, counters, logo, nested timeline) "
    "or Tim approved an exception, add a comment '# broll-ok: <reason>' to the script.\n")
sys.exit(2)
