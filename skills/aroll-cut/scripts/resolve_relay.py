"""Build a recut copy of a timeline from recut_plan.py output. The editor's timeline is never touched.
Run through the Resolve MCP run_script tool (sandboxed: paste the plan into PLAN). Two steps so each
call stays well under the 60 s limit:
  STEP = "create"  duplicate PLAN["source"] as PLAN["copy"], empty every track, re-add the markers
  STEP = "place"   append the items of TRACKS (e.g. ["video1"], then ["video2", "video3", "video4"])
                   at their planned record frames, then set Zoom/Pan/Tilt, speed (real-time length
                   first, then SetSpeed, as SetSpeed keeps the item length), retime settings, name,
                   colour and enabled state.
A-roll items are appended with their audio (multicam or A cam), everything else video only.
Check afterwards: item counts per track, the running time, and cut_review.py on a proxy render."""
import math

# Runs inside Resolve (no beon_config): the timeline fps comes from the source timeline itself.
PLAN = {}            # paste plan.json here
STEP = "create"      # "create" or "place"
TRACKS = ["video1"]  # for STEP = "place"

proj = resolve.GetProjectManager().GetCurrentProject()
tls = {proj.GetTimelineByIndex(i + 1).GetName(): proj.GetTimelineByIndex(i + 1) for i in range(proj.GetTimelineCount())}
src = tls[PLAN["source"]]
fps = float(src.GetSetting("timelineFrameRate"))
log = []
if STEP == "create":
    if PLAN["copy"] in tls:
        raise SystemExit(f"{PLAN['copy']!r} already exists: rename or delete it first (never overwrite)")
    dup = src.DuplicateTimeline(PLAN["copy"])
    proj.SetCurrentTimeline(dup)
    items = []
    for kind in ("video", "audio"):
        for ti in range(1, dup.GetTrackCount(kind) + 1):
            items += dup.GetItemListInTrack(kind, ti) or []
    if items:
        dup.DeleteClips(items, False)
    for f in list((dup.GetMarkers() or {}).keys()):
        dup.DeleteMarkerAtFrame(f)
    for f, m in PLAN["markers"].items():
        dup.AddMarker(int(f), m["color"], m["name"], m.get("note", ""), m.get("duration", 1), m.get("customData", ""))
    log.append(f"created {PLAN['copy']}, cleared {len(items)} items, {len(PLAN['markers'])} markers")
else:
    dup = tls[PLAN["copy"]]
    proj.SetCurrentTimeline(dup)
    mp = proj.GetMediaPool()
    ids = {}

    def walk(folder):
        for c in folder.GetClipList() or []:
            ids[c.GetUniqueId()] = c
        for sub in folder.GetSubFolderList() or []:
            walk(sub)
    walk(mp.GetRootFolder())
    T0 = dup.GetStartFrame()
    for it in [i for i in PLAN["items"] if i["track"] in TRACKS]:
        n_src = math.ceil(it["dur"] * it["src_fps"] / fps)          # real-time length; SetSpeed shortens the source
        ci = {"mediaPoolItem": ids[it["mpid"]], "startFrame": int(it["ss"]), "endFrame": int(it["ss"]) + n_src,
              "recordFrame": T0 + int(it["rec"]), "trackIndex": int(it["track"][5:])}
        if not it["with_audio"]:
            ci["mediaType"] = 1
        got = mp.AppendToTimeline([ci]) or []
        v = next((g for g in got if g.GetTrackTypeAndIndex()[0] == "video"), None)
        if v is None:
            log.append(f"FAILED {it['name']} at {it['rec']}")
            continue
        for k, val in (it.get("p") or {}).items():
            if val is not None and k in ("ZoomX", "ZoomY", "Pan", "Tilt"):
                v.SetProperty(k, val)
        if abs(it["speed"] - 100.0) > 0.01:
            v.SetSpeed({"Percentage": it["speed"], "RippleTimeline": False})
        for k in ("RetimeProcess", "MotionEstimation"):
            val = (it.get("p") or {}).get(k)
            if val:
                v.SetProperty(k, val)
        if it.get("name"):
            v.SetName(it["name"])
        if it.get("col"):
            v.SetClipColor(it["col"])
        if it.get("en") is False:
            v.SetClipEnabled(False)
        if v.GetStart() != T0 + int(it["rec"]) or v.GetDuration() != int(it["dur"]):
            log.append(f"CHECK {it['name']}: at {v.GetStart() - T0} for {v.GetDuration()} f, planned {it['rec']} for {it['dur']}")
    log.append(f"placed {TRACKS}")
result = {"log": log, "tracks": {f"{k}{i}": len(dup.GetItemListInTrack(k, i) or []) for k in ("video", "audio")
                                 for i in range(1, dup.GetTrackCount(k) + 1)},
          "end": dup.GetEndFrame() - dup.GetStartFrame()}
