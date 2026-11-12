"""Print a timeline's words with their indices, cuts (‖) and pauses (|frames) for writing captions.

    python3 show_words.py WORK_DIR C5b [C6a ...]
"""
import json
import sys

if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"):
    sys.exit(__doc__)
d = json.load(open(sys.argv[1].rstrip("/") + "/words.json"))
for name in sys.argv[2:]:
    key = [k for k in d if k.startswith(name)][0]
    v = d[key]
    cut_starts = {s for s, e in v["cuts"]}
    print("=====", key, "len", v["end"] - v["start"], "cuts", [s for s, e in v["cuts"]])
    line, prev = [], None
    for i, (t0, t1, w) in enumerate(v["words"]):
        mark = ""
        if prev is not None:
            gap = t0 - prev
            if any(prev <= c <= t0 for c in cut_starts):
                mark = " ‖"
            elif gap >= 6:
                mark = f" |{gap}"
        line.append(f"{mark} {i}:{w}@{t0}")
        prev = t1
    print("".join(line))
