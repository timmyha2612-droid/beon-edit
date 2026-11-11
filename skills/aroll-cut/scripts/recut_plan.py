#!/usr/bin/env python3
"""Plan an A-roll recut on a copy of a timeline and ripple everything else to match (offline, no Resolve).
usage: recut_plan.py snapshot.json edits.json plan.json
snapshot.json  from resolve_snapshot.py
edits.json     {"copy": "Oct C1 no-uh (Claude test)", "aroll": "video1",
                "replace": [{"old": [i, j], "new": [[ss, se], ...], "why": "..."}, ...]}
               old = first and last index (0-based, inclusive) of the A-roll items being replaced;
               new = their replacement source ranges in the same media's frames (end exclusive), in
               order; "new": [] removes them (items that sat only on them are dropped, markers move to the
               join). Untouched A-roll items stay exactly as they are; gaps between items are kept.
Every other item (B-roll, Gyroflow, angle tracks, markers) keeps its length and moves with the
words it sat on: its start is mapped through the A-roll by source time; one that started exactly at
an A-roll join starts at the new join; one that sat in a gap keeps its distance to the piece before.
If a moved item now runs into the next item on its track it is shortened to meet it (reported).
An edge that sat on an A-roll join (or within 3 frames of one) lands exactly on the new join, so B-roll
never ends a frame or two before a cut after a recut (Tim, 11 Nov 2026: 1-frame speaker flash = glitch).
Writes plan.json for resolve_relay.py and prints a before/after table to check."""
import json, math, sys

snap, edits = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
TL_FPS = float(snap.get("fps") or 24)
T0 = snap["start"]
AR = edits.get("aroll", "video1")
A = sorted(snap["tracks"][AR]["items"], key=lambda r: r["s"])


def fps_of(it):
    try:
        return float(it.get("fps") or TL_FPS)
    except ValueError:
        return TL_FPS


# 1. groups of old A-roll items -> new pieces
rep = {tuple(r["old"]): r for r in edits["replace"]}
groups, i = [], 0
while i < len(A):
    hit = next((k for k in rep if k[0] == i), None)
    if hit:
        groups.append({"old": list(range(hit[0], hit[1] + 1)), "new": rep[hit]["new"], "why": rep[hit].get("why", "")})
        i = hit[1] + 1
    else:
        groups.append({"old": [i], "new": [[A[i]["ss"], A[i]["se"]]], "why": ""})
        i += 1
cursor, pieces = A[0]["s"], []
for gi, g in enumerate(groups):
    first = A[g["old"][0]]
    if gi:
        prev_last = A[groups[gi - 1]["old"][-1]]
        cursor += first["s"] - prev_last["e"]                      # keep the gap before this group
    sf = fps_of(first)
    g["ns"] = cursor
    for ss, se in g["new"]:
        dur = int(round((se - ss) * TL_FPS / sf))
        src = next((A[k] for k in g["old"] if A[k]["ss"] <= ss < A[k]["se"]), first)
        pieces.append({"group": gi, "ns": cursor, "ne": cursor + dur, "ss": ss, "se": se, "from": A.index(src)})
        cursor += dur
    g["ne"] = cursor
gidx = {k: gi for gi, g in enumerate(groups) for k in g["old"]}


def M(r):
    """New record frame for old record frame r."""
    if r < A[0]["s"]:
        return r
    for k, it in enumerate(A):
        if it["s"] <= r < it["e"]:
            g = groups[gidx[k]]; sf = fps_of(it)
            src = it["ss"] + (r - it["s"]) * sf / TL_FPS
            mine = [p for p in pieces if p["group"] == gidx[k]]
            if not mine:                                          # group removed ("new": []): collapses to its join
                return g["ns"]
            if r == it["s"]:                                      # started at a join: keep it at the join
                p = next((p for p in mine if p["se"] > src), mine[-1])
                return p["ns"]
            p = next((p for p in mine if p["ss"] <= src < p["se"]), None)
            if p:
                return p["ns"] + int(round((src - p["ss"]) * TL_FPS / sf))
            p = next((p for p in mine if p["ss"] > src), None)     # source was cut: snap to the next join
            return p["ns"] if p else g["ne"]
        nxt = A[k + 1]["s"] if k + 1 < len(A) else math.inf
        if it["e"] <= r < nxt:                                    # in a gap: keep the distance
            return M(it["e"] - 1) + 1 + (r - it["e"])
    return r


SNAP = 3
OLD_JOINS = sorted({a["s"] for a in A} | {A[-1]["e"]})


def snap_join(r):
    """The old A-roll join an edge sat on (within SNAP frames), or None."""
    j = min(OLD_JOINS, key=lambda j: abs(j - r))
    return j if abs(j - r) <= SNAP else None


plan = {"source": snap["name"], "copy": edits["copy"], "aroll_track": int(AR[5:]), "items": [], "markers": {}, "notes": []}
for p in pieces:
    o = A[p["from"]]
    plan["items"].append({"track": AR, "mpid": o["mpid"], "clip": o["clip"], "rec": p["ns"] - T0, "dur": p["ne"] - p["ns"],
                          "ss": p["ss"], "src_fps": fps_of(o), "speed": 100.0, "p": o.get("p", {}), "name": o["name"],
                          "col": o["col"], "en": o["en"], "with_audio": True})
for key, tr in snap["tracks"].items():
    if key == AR or key.startswith("audio"):
        continue
    rows = []
    for it in sorted(tr["items"], key=lambda r: r["s"]):
        sp = it.get("speed") or {}
        pct = float(sp.get("Percentage", sp.get("percentage", 100.0)) or 100.0) if isinstance(sp, dict) else 100.0
        # Edges on A-roll cuts stay on the cuts [Tim, Hired Home Nov S2 C4, 11 Nov 2026]: an edge that sat on an
        # old join (or within SNAP frames of one) lands exactly on the new join, so a recut never leaves a 1-2 frame
        # flash of the speaker between B-roll and the next A-roll piece (B4 ended 1 f before P6: glitch).
        ns, ne = M(it["s"]), M(it["s"]) + (it["e"] - it["s"])
        js, je = snap_join(it["s"]), snap_join(it["e"])
        if js is not None:
            ns = M(js)
        if je is not None:
            ne = M(je)
            if ne - ns != it["e"] - it["s"]:
                plan["notes"].append(f"{key} '{it['name']}' end kept on the A-roll cut: {it['e'] - it['s']} -> {ne - ns} frames")
        else:
            ne = ns + (it["e"] - it["s"])
        rows.append({"track": key, "mpid": it["mpid"], "clip": it["clip"], "rec": ns - T0, "dur": ne - ns,
                     "old_rec": it["s"] - T0, "ss": it["ss"], "src_fps": fps_of(it), "speed": pct, "p": it.get("p", {}),
                     "name": it["name"], "col": it["col"], "en": it["en"], "with_audio": False})
    for a_, b_ in zip(rows, rows[1:]):
        if a_["rec"] + a_["dur"] > b_["rec"]:
            plan["notes"].append(f"{key} '{a_['name']}' shortened {a_['dur']} -> {b_['rec'] - a_['rec']} frames to meet '{b_['name']}'")
            a_["dur"] = b_["rec"] - a_["rec"]
    plan["items"] += [r for r in rows if r["dur"] > 0]
for f, m in (snap.get("markers") or {}).items():
    plan["markers"][str(M(int(float(f)) + T0) - T0)] = m
old_len = A[-1]["e"] - A[0]["s"]; new_len = pieces[-1]["ne"] - pieces[0]["ns"]
print(f"A-roll {old_len} -> {new_len} frames ({(new_len - old_len) / TL_FPS:+.2f}s)")
for g in groups:
    if g["why"]:
        o = [(A[k]["ss"], A[k]["se"]) for k in g["old"]]
        print(f"  items {g['old']} {o} -> {g['new']}  rec {A[g['old'][0]]['s'] - T0}->{g['ns'] - T0}  {g['why']}")
for r in plan["items"]:
    if r["track"] != AR and r["rec"] != r["old_rec"]:
        print(f"  {r['track']} {r['name'][:28]:28s} {r['old_rec']:5d} -> {r['rec']:5d}  ({r['dur']} f)")
for n in plan["notes"]:
    print("  !", n)
json.dump(plan, open(sys.argv[3], "w"), indent=1)
print("wrote", sys.argv[3])
