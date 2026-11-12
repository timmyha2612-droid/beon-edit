#!/usr/bin/env python3
"""UserPromptSubmit hook (beon-edit plugin): keep the learning loop listening during every job ([Tim, Q14]).

When this session has a job card (house-rules/references/job-card.md), every message from the person
editing gets a short reminder attached: if the message corrects the edit or teaches something, write it
into the lessons inbox now, with its kind (general / client / concept / unsure). Sessions without a job
card get nothing, so normal chats aren't touched. The editor's name comes from the card's Editor line,
else ~/.beon-edit/editor.json. The editor approves their own lessons at the end of the job.
Never blocks (exit 0 always); without beon_config it still runs, with a plainer placeholder check."""
import json, os, pathlib, re, sys

try:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "skills" / "house-rules" / "scripts"))
    import beon_config as bc
except Exception as e:
    bc = None
    sys.stderr.write(f"beon-edit learning: can't import beon_config ({e}); using the card only.\n")

if bc:
    JOBS = str(bc.JOBS)
else:
    JOBS = os.path.expanduser(os.environ.get("BEON_JOBS_DIR",
                              os.path.join(os.environ.get("BEON_HOME", "~/.beon-edit"), "jobs")))

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
    empty = bc.unfilled(v) if bc else (not v or "<" in v or " | " in v)
    if empty or v.lower() in ("n/a", "na", "-"):
        return ""                                                       # blank or still the template placeholder
    return v


def editor_name():
    name = field("Editor")
    if not name and bc:
        try:
            name = bc.load_editor().get("name") or ""
        except Exception:
            name = ""
    return name


root = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
editor = editor_name() or "unknown (ask the editor their name)"
inbox = field("Lessons inbox") or "<shoot>/_shotlog/lessons/<concept>.jsonl (add a 'Lessons inbox:' line to the job card)"
client = field("Client") or ""
print(
    "beon-edit learning (always on during a job): if this message corrects the edit, says how something should be done, "
    "or explains why, record it now before acting: "
    f"python3 \"{root}/skills/learn-from-tim/scripts/lessons.py\" add \"{inbox}\" --who \"{editor}\" --said \"<their words>\" "
    "--rule \"<one-line rule>\" --kind general|client|concept|unsure"
    + (f" (client profile: {client})" if client else "")
    + ". General = every client, client = only this client, concept = only this video (never into the plugin), "
    "unsure = ask the editor at the end of the job. Plain instructions for this edit alone are not lessons; don't log those."
)
sys.exit(0)
