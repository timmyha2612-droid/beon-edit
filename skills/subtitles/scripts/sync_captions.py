#!/usr/bin/env python3
"""Caption timing from the timeline's own speech.
usage: sync_captions.py WORK/<name>_state.json OUT_DIR/tl.json PLAN.json [OUT_DIR/tl.wav]
(state from export_state.py, tl.json/tl.wav from timeline_audio.py). Only the lowest Text+ track is
treated as captions, so a Text+ question card above it is never touched. Prints every caption's old and
new span; PLAN.json feeds retime_captions_drt.py.
Each caption goes up 1 frame before its first spoken word; it snaps to a picture cut that falls up to 8
frames before the word or 6 after it. Captions under 14 frames are merged into the previous one when the
text fits on 2 lines of 28, otherwise flagged."""
import json, sys, re, difflib
if len(sys.argv) < 4 or sys.argv[1] in ("-h", "--help"):
    sys.exit(__doc__)
s = json.load(open(sys.argv[1])); d = json.load(open(sys.argv[2]))
sub_track = min(c[3] for c in s["caps"]); caps = sorted(c for c in s["caps"] if c[3] == sub_track); cuts = sorted({a for a, _ in s["v1"]} - {0}); FPS = s.get("fps", 24); end = max(c[1] for c in caps)
words = []
for seg in d["transcription"]:
    for t in seg["tokens"]:
        x = t["text"]
        if x.startswith("[_"):
            continue
        f = round(t["offsets"]["from"] / 1000 * FPS)
        if x.startswith(" ") or not words:
            words.append([f, x.strip()])
        else:
            words[-1][1] += x
env = None
if len(sys.argv) > 4:                            # audio level per frame, to catch words whisper puts in a pause
    import wave, array, math
    w = wave.open(sys.argv[4]); sr = w.getframerate(); a = array.array("h"); a.frombytes(w.readframes(w.getnframes()))
    hop = int(sr / FPS)
    env = [10 * math.log10(sum(x * x for x in a[i:i + hop:4]) / (hop / 4) / 32768 ** 2 + 1e-12) for i in range(0, len(a) - hop, hop)]
    quiet = sorted(env)[len(env) // 10] + 10


def to_speech(f):
    """Whisper often puts the first word after a pause at the start of the pause: move it to where
    speech actually starts (within a second). Simone C03c: "Wild." placed 6 frames into a pause."""
    if env is None or f >= len(env) or env[f] >= quiet:
        return f
    for k in range(f, min(f + round(FPS), len(env))):
        if env[k] >= quiet and (k + 1 >= len(env) or env[k + 1] >= quiet):
            return k
    return f


norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower().replace("%", "percent"))
toks = [(i, norm(x)) for i, c in enumerate(caps) for x in c[2].split() if norm(x)]
sm = difflib.SequenceMatcher(None, [t for _, t in toks], [norm(w[1]) for w in words], autojunk=False)
first = {}
for op, a1, a2, b1, b2 in sm.get_opcodes():
    if op in ("equal", "replace") and b2 > b1:
        for k in range(a2 - a1):
            first.setdefault(toks[a1 + k][0], to_speech(words[min(b1 + k, b2 - 1)][0]))
plan = []
for i, c in enumerate(caps):
    f = first.get(i)
    if i == 0:
        st = 0
    elif f is None:
        st = c[0]; print("no speech match, kept:", c[2].replace("\n", " / "))
    else:
        st = f - 1
        near = [x for x in cuts if f - 8 <= x <= f + 6]
        if near:
            st = min(near, key=lambda x: abs(x - f))
    plan.append([st, None, c[2]])
for i in range(1, len(plan)):                    # keep order
    if plan[i][0] <= plan[i - 1][0]:
        plan[i][0] = plan[i - 1][0] + 6


def fits(text):
    w = text.split()
    if len(" ".join(w)) <= 28:
        return " ".join(w)
    for k in range(1, len(w)):
        a, b = " ".join(w[:k]), " ".join(w[k:])
        if len(a) <= 28 and len(b) <= 28:
            return a + "\n" + b
    return None


live = list(range(len(plan)))
changed = True
while changed:
    changed = False
    for j in range(1, len(live)):
        a, b = live[j - 1], live[j]
        nxt = plan[live[j + 1]][0] if j + 1 < len(live) else end
        if nxt - plan[b][0] < 14:
            if plan[a][2].rstrip().endswith((".", "?", "!")):   # never join two sentences (Tim, C03c "Wild." | "We are salespeople.")
                print("short caption after a sentence end, kept:", plan[b][2].replace("\n", " / "))
                continue
            m = fits(plan[a][2].replace("\n", " ") + " " + plan[b][2].replace("\n", " "))
            if m:
                plan[a][2] = m; plan[b] = None; live.pop(j); changed = True; break
            print("short caption, can't merge:", plan[b][2].replace("\n", " / "))
for j, i in enumerate(live):
    plan[i][1] = plan[live[j + 1]][0] if j + 1 < len(live) else end
for c, p in zip(caps, plan):
    print(f"{c[0]:5}-{c[1]:5} -> " + (f"{p[0]:5}-{p[1]:5} ({p[1] - p[0]:3})  {p[2]!r}" if p else "merged into previous"))
json.dump([{"old": [c[0], c[2]], "new": p} for c, p in zip(caps, plan)], open(sys.argv[3], "w"), indent=1)
