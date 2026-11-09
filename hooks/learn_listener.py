#!/usr/bin/env python3
"""UserPromptSubmit hook (beon-edit plugin): keep the learning loop listening during every job (Tim, Q14).

When this session has a job card (house-rules/references/job-card.md), every message from the person
editing gets a short reminder attached: if the message corrects the edit or teaches something, write it
into the lessons inbox now, with its kind (general / client / concept / unsure). Sessions without a job
card get nothing, so normal chats aren't touched. Never blocks (exit 0 always)."""
import json, os, re, sys

JOBS = os.path.expanduser(os.environ.get("BEON_JOBS_DIR", "~/.beon-edit/jobs"))

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
sid = data.get("session_id") or ""
card = os.path.join(JOBS, f"{sid}.md")
if not sid or not os.path.exists(card):
    sys.exit(0)
try:
    text = open(card, encoding="utf-8").read()
except Exception:
    sys.exit(0)


def field(name):
    m = re.search(rf"^{name}:[ \t]*(\S[^\n]*)$", text, re.M)       # never runs onto the next line
    v = m.group(1).strip() if m else ""
    if not v or v.lower() in ("n/a", "na", "-") or "<" in v or v.startswith("Tim |"):
        return ""                                                       # blank or still the template placeholder
    return v


root = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
editor = field("Editor") or "unknown (ask)"
inbox = field("Lessons inbox") or "<shoot>/_shotlog/lessons/<concept>.jsonl (add a 'Lessons inbox:' line to the job card)"
client = field("Client") or ""
print(
    "beon-edit learning (always on during a job): if this message corrects the edit, says how something should be done, "
    "or explains why, record it now before acting: "
    f"python3 \"{root}/skills/learn-from-tim/scripts/lessons.py\" add \"{inbox}\" --who \"{editor}\" --said \"<their words>\" "
    "--rule \"<one-line rule>\" --kind general|client|concept|unsure"
    + (f" (client profile: {client})" if client else "")
    + ". General = every client, client = only this client, concept = only this video (never into the plugin), "
    "unsure = ask at the end of the job. Plain instructions for this edit alone are not lessons; don't log those."
)
sys.exit(0)
