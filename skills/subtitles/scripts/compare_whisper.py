"""Compare built captions against an independent Whisper large-v3 transcript of each short."""
import difflib
import glob
import json
import os
import re
import argparse
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subs_intake  # noqa: E402

ap = argparse.ArgumentParser(description="Compare built captions (WORK/plans.json) with WORK/verify/<tag>.json.")
ap.add_argument("work", nargs="?", help="work folder (default: from --card, else ~/subs_work)")
ap.add_argument("--card", help="job card: work folder and fps from it")
ap.add_argument("--fps", type=float, help="timeline fps (default: job card Delivery, else 24)")
ARGS = ap.parse_args()
BASE = (ARGS.work or subs_intake.work_dir(ARGS.card)).rstrip("/") + "/"
FPS = ARGS.fps or subs_intake.delivery(ARGS.card).get("fps", 24)
PLANS = json.load(open(BASE + "plans.json"))
# Words I removed on purpose (clean verbatim / dropped reactions) - differences here are expected.
IGNORABLE = {"like", "um", "uh", "you", "know", "i", "mean", "yeah", "yep", "yes", "right", "ok", "okay", "so",
             "absolutely", "exactly", "wow", "correct", "no", "really", "beautiful", "sweet", "thats", "and", "the", "a", "mm", "hmm"}
NUMS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "ten": "10", "twelve": "12", "fourteen": "14", "sixteen": "16"}


def norm_tokens(text):
    text = text.lower().replace("’", "'").replace("$", " ").replace("%", " percent ")
    out = []
    for raw in re.split(r"[\s\-–—/]+", text):
        t = re.sub(r"[^a-z0-9.']", "", raw).strip(".").replace("'", "")
        if not t:
            continue
        t = NUMS.get(t, t)
        out.append(t)
    return out


def whisper_words(tag):
    data = json.load(open(BASE + f"verify/{tag}.json"))
    words = []
    for seg in data["transcription"]:
        for tok in norm_tokens(seg["text"]):
            words.append((tok, seg["offsets"]["from"] / 1000 * FPS))
    return words


def compare(name):
    tag = re.match(r"^(\S+)", name).group(1)
    caps = PLANS[name]["caps"]
    cap_toks, owner = [], []
    for n, c in enumerate(caps):
        for t in norm_tokens(c["text"]):
            cap_toks.append(t)
            owner.append(n)
    ww = whisper_words(tag)
    sm = difflib.SequenceMatcher(None, cap_toks, [w for w, _ in ww], autojunk=False)
    issues = {}
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op == "equal":
            continue
        ours = cap_toks[a1:a2]
        theirs = [w for w, _ in ww[b1:b2]]
        # Pure deletions of filler/reaction words are my intended clean-ups.
        if not ours and all(t in IGNORABLE for t in theirs):
            continue
        n = owner[min(a1, len(owner) - 1)] if a1 < len(owner) else owner[-1]
        issues.setdefault(n, []).append((op, " ".join(ours), " ".join(theirs)))
    report = []
    for n in sorted(issues):
        ctx_from = max(0, cap_toks.index(cap_toks[0]))
        report.append({"cap": n + 1, "text": caps[n]["text"].replace("\n", " / "), "diffs": issues[n]})
    return tag, report


if __name__ == "__main__":
    total = 0
    lines = []
    for name in PLANS:
        tag = re.match(r"^(\S+)", name).group(1)
        if not os.path.exists(BASE + f"verify/{tag}.json"):
            lines.append(f"== {tag}: no whisper output yet")
            continue
        tag, rep = compare(name)
        total += len(rep)
        lines.append(f"== {tag}: {len(rep)} captions differ")
        for r in rep:
            d = "; ".join(f"{op}: ours[{o}] whisper[{t}]" for op, o, t in r["diffs"])
            lines.append(f"  #{r['cap']:2d} {r['text']}\n       {d}")
    print("\n".join(lines))
    print("TOTAL captions with differences:", total)
