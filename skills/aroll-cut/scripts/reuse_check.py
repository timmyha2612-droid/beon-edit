"""Which source ranges of this concept are already used on another timeline in the project? (read-only)
Run through the Resolve MCP run_script tool (sandboxed, no file access). Set NAME (the concept's timeline),
optionally PLANNED (ranges you are about to cut, before they are on a timeline) and SKIP (timelines that
don't count, e.g. this concept's own older versions), run, read the result.

Tim, Hired Home Nov S2 C4 (11 Nov 2026): "some a roll is overlapping or already used in concept 2". Concepts from
one shoot share clips, so before cutting the A-roll (aroll-cut section 1) and before handing over, check every
A-roll and B-roll range against the project's other timelines. An overlapping A-roll take (same words, same
take) is never reused without Tim's yes; ask which versions count (a superseded, never-delivered version may
not). A B-roll clip used elsewhere is reported (same window = reuse, other window = same shot, Tim's call).

Matching is by File Path (clip names repeat across shoots), in seconds of source time.
result = {"<other timeline>": [[track, clip, my_in, my_out, my_item, their_item, their_in, their_out, verdict]]}
verdict: "overlap N.Ns" (same source time) or "same clip, other window"."""
NAME = "Concept timeline name"
PLANNED = []          # optional: [["C0173.MP4", in_s, out_s, "label"], ...] matched by clip name inside the same shoot folder
SKIP = []             # optional: timeline names to ignore (this concept's own versions are skipped automatically)
A_ROLL_ONLY = False   # True: only V1 of this timeline

proj = resolve.GetProjectManager().GetCurrentProject()
tls = {proj.GetTimelineByIndex(i + 1).GetName(): proj.GetTimelineByIndex(i + 1) for i in range(proj.GetTimelineCount())}
if NAME not in tls:
    raise SystemExit(f"no timeline {NAME!r}")


def ranges(tl, v1_only=False):
    out = []
    for k in range(1, tl.GetTrackCount("video") + 1):
        if v1_only and k > 1:
            break
        for it in tl.GetItemListInTrack("video", k) or []:
            m = it.GetMediaPoolItem()
            if not m:
                continue
            path = m.GetClipProperty("File Path") or ""
            if not path:
                continue
            try:
                fps = float(m.GetClipProperty("FPS") or 0)
            except ValueError:
                fps = 0
            if not fps:
                continue
            out.append([k, path, it.GetSourceStartFrame() / fps, it.GetSourceEndFrame() / fps, it.GetName()])
    return out


mine = ranges(tls[NAME], A_ROLL_ONLY)
folders = {p.rsplit("/", 1)[0] for _, p, *_ in mine}
for clip, a, b, label in PLANNED:
    for f in folders:
        mine.append([1, f + "/" + clip, a, b, label])
base = NAME.split(" v")[0]
result = {}
for name, tl in tls.items():
    if name == NAME or name in SKIP or name.split(" v")[0] == base:
        continue
    theirs = ranges(tl)
    hits = []
    for k, p, a, b, n in mine:
        for k2, p2, a2, b2, n2 in theirs:
            if p != p2:
                continue
            ov = min(b, b2) - max(a, a2)
            hits.append([k, p.rsplit("/", 1)[-1], round(a, 2), round(b, 2), n, n2, round(a2, 2), round(b2, 2),
                         f"overlap {ov:.1f}s" if ov > 0 else "same clip, other window"])
    if hits:
        result[name] = hits
