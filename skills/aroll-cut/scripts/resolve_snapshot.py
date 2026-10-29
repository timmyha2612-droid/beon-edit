"""Read-only snapshot of a timeline, for an offline recut (recut_plan.py) and resolve_relay.py.
Run through the Resolve MCP run_script tool (sandboxed, no file access): set NAME, run, save the
returned JSON as snapshot.json. Touches nothing. Audio items are listed so linked A-roll audio can be
checked, but resolve_relay.py recreates them from the video items (multicam/A-roll appends bring
their audio)."""
NAME = "Oct C1"
proj = resolve.GetProjectManager().GetCurrentProject()
tl = None
for i in range(proj.GetTimelineCount()):
    t = proj.GetTimelineByIndex(i + 1)
    if t.GetName() == NAME:
        tl = t
if tl is None:
    raise SystemExit(f"no timeline {NAME!r} in project {proj.GetName()!r}")
P = ["ZoomX", "ZoomY", "Pan", "Tilt", "RetimeProcess", "MotionEstimation"]
snap = {"project": proj.GetName(), "name": NAME, "start": tl.GetStartFrame(), "end": tl.GetEndFrame(),
        "fps": tl.GetSetting("timelineFrameRate"), "markers": tl.GetMarkers(), "tracks": {}}
for kind in ("video", "audio"):
    for ti in range(1, tl.GetTrackCount(kind) + 1):
        rows = []
        for it in tl.GetItemListInTrack(kind, ti) or []:
            m = it.GetMediaPoolItem()
            r = {"name": it.GetName(), "s": it.GetStart(), "e": it.GetEnd(),
                 "ss": it.GetSourceStartFrame(), "se": it.GetSourceEndFrame(),
                 "mpid": m.GetUniqueId() if m else None, "clip": m.GetName() if m else None,
                 "fps": m.GetClipProperty("FPS") if m else None,
                 "col": it.GetClipColor(), "en": it.GetClipEnabled()}
            if kind == "video":
                r["p"] = {k: it.GetProperty(k) for k in P}
                r["speed"] = it.GetSpeed()
            rows.append(r)
        snap["tracks"][f"{kind}{ti}"] = {"name": tl.GetTrackName(kind, ti), "items": rows}
result = snap
