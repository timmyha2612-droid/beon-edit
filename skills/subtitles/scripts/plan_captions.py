"""Turn hand-written captions into build plans (start/end/text/per-word times) and validate them.

    python3 plan_captions.py WORK_DIR

Reads WORK_DIR/words.json (from export_words.py) and WORK_DIR/captions.py, which defines
CAPTIONS = {"<timeline name prefix>": [(first transcript word index, "Caption\ntext"), ...]}.
Writes WORK_DIR/plans.json for build_lib.py and prints anything that needs a look.
"""
import difflib
import json
import os
import re
import sys


BASE = (sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/subs_work")).rstrip("/") + "/"
MAX_LINE, MAX_WORDS, MAX_FRAMES = 28, 12, 118
IN_DUR, OUT_DUR, LAST_OUT, LEAD, MIN_SHOW, MIN_GAP = 18, 4, 0, 2, 6, 4
# A caption start moves onto a picture cut (Tim, Simone C03, 3 Nov 2026) only when the cut is up to
# SNAP_BEFORE frames before its first spoken word or SNAP_AFTER frames after it. Speech comes first
# (Tim, 4 Nov 2026): further off, the caption keeps the speech timing.
SNAP_BEFORE, SNAP_AFTER = 8, 6


def norm(t):
    return re.sub(r"[^a-z0-9']", "", t.lower().replace("’", "'"))


def spread(times, latest, gap=None):
    """Spoken times, nudged so words always reveal one at a time (>= MIN_GAP frames apart)
    and no later than `latest`. Falls back to an even spread when the caption is too short."""
    gap = MIN_GAP if gap is None else gap
    t = [max(0, x) for x in times]
    for i in range(1, len(t)):                       # push clumped words later
        t[i] = max(t[i], t[i - 1] + gap)
    if t and t[-1] > latest:                         # too late: pull back from the end
        t[-1] = latest
        for i in range(len(t) - 2, -1, -1):
            t[i] = min(t[i], t[i + 1] - gap)
    if t and t[0] < 0:                               # not enough room: even spread
        step = latest / max(len(t) - 1, 1)
        t = [round(i * step) for i in range(len(t))]
    return t


def tokens_of(text):
    out = []
    for tok in text.split():
        parts = [norm(p) for p in re.split(r"[-–—/]", tok) if norm(p)]
        out.append(parts or [norm(tok)])
    return out


def align(text, words):
    """Frame each display token is spoken at, from the transcript words it covers."""
    toks = tokens_of(text)
    flat = [(i, p) for i, parts in enumerate(toks) for p in parts]
    sm = difflib.SequenceMatcher(None, [p for _, p in flat], [norm(w[2]) for w in words], autojunk=False)
    frames, exact = [None] * len(toks), [False] * len(toks)
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        for k in range(a2 - a1):
            ti = flat[a1 + k][0]
            if frames[ti] is not None:
                continue
            if op == "equal":
                frames[ti], exact[ti] = words[b1 + k][0], True
            elif op == "replace" and b2 > b1:
                frames[ti] = words[b1 + min(k * (b2 - b1) // (a2 - a1), b2 - b1 - 1)][0]
    for i in range(len(frames)):
        if frames[i] is None:
            prev = next((frames[j] for j in range(i - 1, -1, -1) if frames[j] is not None), words[0][0] if words else 0)
            nxt = next((frames[j] for j in range(i + 1, len(frames)) if frames[j] is not None), None)
            frames[i] = prev if nxt is None else (prev + nxt) // 2
    return frames, sum(exact)


def main():
    sys.path.insert(0, BASE)
    from captions import CAPTIONS
    data = json.load(open(BASE + "words.json"))
    plans, problems = {}, []
    for key, caps in CAPTIONS.items():
        name = [k for k in data if k.startswith(key)][0]
        d = data[name]
        W, length = d["words"], d["end"] - d["start"]
        idx = [i for i, _ in caps]
        if idx != sorted(set(idx)):
            problems.append((key, "indices not increasing"))
        out = []
        for n, (i, text) in enumerate(caps):
            start = 0 if (n == 0 and W[i][0] <= 3) else max(0, W[i][0])
            nxt = caps[n + 1][0] if n + 1 < len(caps) else None
            end = (0 if False else W[nxt][0]) if nxt is not None else length
            seg = W[i:nxt] if nxt is not None else W[i:]
            lines = text.split("\n")
            if len(lines) > 2 or max(len(l) for l in lines) > MAX_LINE:
                problems.append((key, n, "too wide", text))
            if len(text.split()) > MAX_WORDS:
                problems.append((key, n, "too many words", text))
            frames, matched = align(text, seg)
            out.append({"start": start, "end": end, "text": text, "frames": [max(start, f) for f in frames],
                        "matched": matched, "tokens": len(text.split())})
        cut_frames = sorted({s for s, _ in d.get("cuts", [])} - {0})
        for n, c in enumerate(out):
            near = [f for f in cut_frames if -SNAP_BEFORE <= f - c["start"] <= SNAP_AFTER]
            if n and near:
                snapped = min(near, key=lambda f: abs(f - c["start"]))
                if out[n - 1]["start"] < snapped:
                    c["start"] = snapped
        for n, c in enumerate(out):
            if n + 1 < len(out):
                c["end"] = out[n + 1]["start"]
            dur = c["end"] - c["start"]
            if dur <= 0 or dur > MAX_FRAMES:
                problems.append((key, n, f"duration {dur}", c["text"]))
            fr = sorted(c["frames"])
            c["frames"] = fr
            c["out_dur"] = LAST_OUT if n + 1 == len(out) else OUT_DUR
            # Every word gets at least MIN_SHOW frames on screen: words spoken right at the end
            # of a caption reveal a little early instead of flashing.
            latest = max(0, dur - c["out_dur"] - MIN_SHOW)
            spoken = [f - c["start"] for f in fr]
            t = spread(spoken, latest)
            if len(t) > 1 and min(b - a for a, b in zip(t, t[1:])) < MIN_GAP:
                # Very fast speech: let the last word land later (up to 2 frames before the exit)
                # so every word still gets its own beat instead of clumping.
                roomier = spread(spoken, max(latest, dur - c["out_dur"] - 2))
                if min(b - a for a, b in zip(roomier, roomier[1:])) > min(b - a for a, b in zip(t, t[1:])):
                    t = roomier
            c["times"] = t
            c["in_dur"] = max(8, min(IN_DUR, dur - c["out_dur"] - c["times"][-1] + LEAD))
            if c["matched"] < c["tokens"] - 1:
                problems.append((key, n, f"only {c['matched']}/{c['tokens']} words match", c["text"]))
        plans[name] = {"start": d["start"], "end": d["end"], "caps": out}
    json.dump(plans, open(BASE + "plans.json", "w"), indent=1)
    print("captions:", sum(len(v["caps"]) for v in plans.values()), "shorts:", len(plans))
    for p in problems:
        print("PROBLEM", p)


main()
