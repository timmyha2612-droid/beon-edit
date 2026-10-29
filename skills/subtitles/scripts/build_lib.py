"""Build steps for subtitle timelines, each small enough for one short Resolve call.

Executed inside Resolve with `resolve` and `project` injected. Never creates timelines or
changes settings (that deadlocks Resolve 21.1); the working timeline is a duplicate.
"""
import json
import os

BASE = globals().get("WORK", os.path.expanduser("~/subs_work")).rstrip("/") + "/"  # set WORK when exec-ing
TITLE = "Fluid Reveal Words"
PLANS = json.load(open(BASE + "plans.json"))


def tc(frames):
    f = int(frames)
    return "%02d:%02d:%02d:%02d" % (f // 86400, f // 1440 % 60, f // 24 % 60, f % 24)


def timeline_named(name):
    for i in range(1, project.GetTimelineCount() + 1):
        t = project.GetTimelineByIndex(i)
        if t.GetName() == name:
            return t
    return None


def subs_name(name):
    return name + " Subtitles"


def step_dup(name):
    src = timeline_named(name)
    assert src and not timeline_named(subs_name(name)), "missing source or subtitles already exist"
    project.SetCurrentTimeline(src)
    src.SetCurrentTimecode(tc(src.GetEndFrame()))
    dup = src.DuplicateTimeline(subs_name(name))
    assert dup and project.GetCurrentTimeline().GetName() == subs_name(name)
    items = []
    for kind in ("video", "audio"):
        for t in range(1, dup.GetTrackCount(kind) + 1):
            items += dup.GetItemListInTrack(kind, t) or []
    if items:
        dup.DeleteClips(items, False)
    left = sum(len(dup.GetItemListInTrack(k, t) or []) for k in ("video", "audio") for t in range(1, dup.GetTrackCount(k) + 1))
    return {"dup": dup.GetName(), "cleared": len(items), "left": left}


def current_subs(name):
    tl = project.GetCurrentTimeline()
    assert tl.GetName() == subs_name(name), f"current timeline is {tl.GetName()}"
    return tl


def move_playhead(tl, frame):
    """Set the playhead and wait until Resolve reports it there (inserts land at the playhead)."""
    import time
    want = tc(frame)
    for _ in range(40):
        tl.SetCurrentTimecode(want)
        if tl.GetCurrentTimecode() == want:
            return
        time.sleep(0.05)
    raise RuntimeError(f"playhead would not move to {want}")


def step_insert(name, a, b):
    tl = current_subs(name)
    base = tl.GetStartFrame()
    caps = PLANS[name]["caps"]
    for c in caps[a:b]:
        move_playhead(tl, base + c["start"])
        item = tl.InsertFusionTitleIntoTimeline(TITLE)
        assert item, "insert failed"
        assert item.GetStart() == base + c["start"], f"title landed at {item.GetStart() - base}, wanted {c['start']}"
        tails = [i for i in tl.GetItemListInTrack("video", 1) if i.GetStart() >= item.GetEnd()]
        if tails:
            tl.DeleteClips(tails, False)
    return len(tl.GetItemListInTrack("video", 1))


def step_trim(name):
    tl = current_subs(name)
    base, end = tl.GetStartFrame(), tl.GetStartFrame() + PLANS[name]["end"] - PLANS[name]["start"]
    move_playhead(tl, end)
    if tl.InsertFusionTitleIntoTimeline(TITLE):
        extra = [i for i in tl.GetItemListInTrack("video", 1) if i.GetStart() >= end]
        if extra:
            tl.DeleteClips(extra, False)
    spans = [(i.GetStart() - base, i.GetEnd() - base) for i in tl.GetItemListInTrack("video", 1)]
    want = [(c["start"], c["end"]) for c in PLANS[name]["caps"]]
    return {"match": spans == want, "n": len(spans), "first_bad": next(((s, w) for s, w in zip(spans, want) if s != w), None)}


def step_reset(name):
    """Remove every title from the subtitles timeline so it can be rebuilt."""
    tl = current_subs(name)
    items = tl.GetItemListInTrack("video", 1) or []
    if items:
        tl.DeleteClips(items, False)
    return len(tl.GetItemListInTrack("video", 1) or [])


# Look of a hand-styled title, copied onto every caption. Per-caption values (text, word
# timing, in/out lengths) are set separately. The custom curve shapes (InLookup/OutLookup)
# can't be copied by script: change those in build_presets.py and reinstall the title.
STYLE_KEYS = ("Font", "Style", "Red", "Green", "Blue", "Alpha", "Size", "Tracking", "LineSpacing", "Position",
              "JustifyL", "WordStagger", "SyncOffset", "InCurve", "InEaseIn", "InEaseOut", "Rise", "InBlur",
              "OutCurve", "OutEaseIn", "OutEaseOut", "OutLift", "OutBlur")


def read_style(item):
    g = item.GetFusionCompByIndex(1).FindTool("FluidRevealWords")
    style = {}
    for k in STYLE_KEYS:
        v = g.GetInput(k)
        if isinstance(v, dict):                     # Position comes back as {1.0: x, 2.0: y, 3.0: z}
            v = [v[key] for key in sorted(v)][:2]
        if v is not None:
            style[k] = v
    return style


def apply_style(g, style, last=False):
    for k, v in style.items():
        if last and k in ("OutLift", "OutBlur"):
            continue                                # the last caption holds, no outro
        g.SetInput(k, v)


def step_read_style(name):
    """Save the look of the Fluid Reveal Words title Tim styled and selected on `name` to WORK/style.json."""
    src = timeline_named(name)
    project.SetCurrentTimeline(src)
    sel = [i for i in (src.GetSelectedClips() or []) if i.GetFusionCompCount() and i.GetFusionCompByIndex(1).FindTool("FluidRevealWords")]
    assert sel, "select the styled Fluid Reveal Words title first"
    style = read_style(sel[0])
    json.dump(style, open(BASE + "style.json", "w"), indent=1)
    return style


STYLE = json.load(open(BASE + "style.json")) if os.path.exists(BASE + "style.json") else None


def step_config(name, a, b):
    tl = current_subs(name)
    caps = PLANS[name]["caps"]
    items = tl.GetItemListInTrack("video", 1)
    for n in range(a, min(b, len(caps))):
        c, it = caps[n], items[n]
        assert it.GetStart() - tl.GetStartFrame() == c["start"]
        comp = it.GetFusionCompByIndex(1)
        g, main = comp.FindTool("FluidRevealWords"), comp.FindTool("Main")
        assert main.GetInput("WordTime1") is not None, "old title version"
        if STYLE:
            apply_style(g, STYLE, last=not c["out_dur"])
        g.SetInput("TextContent", c["text"])
        g.SetInput("InDur", c["in_dur"])
        g.SetInput("OutDur", c["out_dur"])
        if not STYLE or not c["out_dur"]:
            g.SetInput("OutBlur", 6 if c["out_dur"] else 0)
            g.SetInput("OutLift", 0.015 if c["out_dur"] else 0)
        for k in range(1, 13):
            main.SetInput(f"WordTime{k}", c["times"][k - 1] if k <= len(c["times"]) else -1)
        it.SetName(f"Sub {n + 1:02d}")
    return min(b, len(caps))


def step_place(name):
    src = timeline_named(name)
    project.SetCurrentTimeline(src)
    assert project.GetCurrentTimeline().GetName() == name
    src.AddTrack("video")
    track = src.GetTrackCount("video")
    src.SetTrackName("video", track, "Subtitles")
    pool = []

    def walk(folder):
        for c in folder.GetClipList() or []:
            if c.GetName() == subs_name(name) and c.GetClipProperty("Type") == "Timeline":
                pool.append(c)
        for f in folder.GetSubFolderList() or []:
            walk(f)

    walk(project.GetMediaPool().GetRootFolder())
    length = PLANS[name]["end"] - PLANS[name]["start"]
    placed = project.GetMediaPool().AppendToTimeline([{"mediaPoolItem": pool[0], "startFrame": 0, "endFrame": length,
                                                       "trackIndex": track, "recordFrame": src.GetStartFrame(), "mediaType": 1}])
    on = [(i.GetName(), i.GetStart() - src.GetStartFrame(), i.GetEnd() - src.GetStartFrame()) for i in src.GetItemListInTrack("video", track)]
    return {"track": track, "placed": bool(placed), "items": on}
