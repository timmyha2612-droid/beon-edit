#!/usr/bin/env python3
"""Intake values for the subtitle scripts: work folder, fps, frame size, language and Whisper model.

    python3 subs_intake.py [--card JOB_CARD.md]

Prints them as JSON, so Claude can inject WORK / FPS into the scripts exec'd inside Resolve
(build_lib, check_lib, export_words ...). The command-line scripts import it and take --card.
Where each value comes from (house-rules/references/intake.md):
  work      bc.scratch_dir(client, shoot, concept) / "subs" with a job card, else ~/subs_work
  fps, size job card Delivery line < client profile delivery < Beon default 9:16 1080x1920 24p (bc.delivery)
  language  shoot.language < client profile language < "en"
  whisper   editor.json tools.whisper.model, else ~/whisper-models/ggml-large-v3.bin
Stdlib only. Without beon_config (or with no card) every value falls back to the old default.
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "house-rules" / "scripts"))
try:
    import beon_config as bc
except ImportError:  # plugin copied without house-rules: old defaults only
    bc = None

DEFAULT_WORK = os.path.expanduser("~/subs_work")
DEFAULT_MODEL = os.path.expanduser("~/whisper-models/ggml-large-v3.bin")
DEFAULT_FPS, DEFAULT_SIZE, DEFAULT_LANG = 24, (1080, 1920), "en"


def card(path):
    """The job card as a dict ({} without one)."""
    if not path or bc is None:
        return {}
    return bc.load_card(path)


def work_dir(card_path=None):
    c = card(card_path)
    if not c or bc is None:
        return DEFAULT_WORK
    folder = c.get("Shoot", "")
    filled = bool(folder) and not bc.unfilled(folder) and folder.strip().lower() not in ("n/a", "na", "none", "-")
    shoot = bc.load_shoot(folder) if filled else {}
    client = shoot.get("client") or c.get("Client") or "client"
    name = shoot.get("shoot") or (pathlib.Path(folder.rstrip("/")).name if filled else "")
    if not name:
        return DEFAULT_WORK
    concept = c.get("Concept") if not bc.unfilled(c.get("Concept")) else None
    return str(bc.scratch_dir(client, name, concept) / "subs")


def delivery(card_path=None):
    if bc is None:
        return {"fps": DEFAULT_FPS, "width": DEFAULT_SIZE[0], "height": DEFAULT_SIZE[1]}
    return bc.delivery(card(card_path) or None)


def language(card_path=None):
    c = card(card_path)
    if not c or bc is None:
        return DEFAULT_LANG
    folder = c.get("Shoot", "")
    shoot = bc.load_shoot(folder) if folder and not bc.unfilled(folder) else {}
    prof = bc.load_client(c.get("Client")) if c.get("Client") and not bc.unfilled(c.get("Client")) else {}
    for v in (shoot.get("language"), prof.get("language")):
        if v and v != "ask":
            return str(v).replace("_", "-").split("-")[0].lower()   # whisper takes the base code: en-AU -> en
    return DEFAULT_LANG


def whisper_model():
    if bc is not None:
        m = ((bc.load_editor().get("tools") or {}).get("whisper") or {}).get("model")
        if m:
            return os.path.expanduser(m)
    return DEFAULT_MODEL


def values(card_path=None):
    d = delivery(card_path)
    return {"work": work_dir(card_path), "fps": d.get("fps", DEFAULT_FPS), "width": d.get("width"),
            "height": d.get("height"), "language": language(card_path), "whisper_model": whisper_model()}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Print the intake values the subtitle scripts use, as JSON.")
    ap.add_argument("--card", help="job card (.md); without it the old defaults")
    print(json.dumps(values(ap.parse_args().card), indent=1))
