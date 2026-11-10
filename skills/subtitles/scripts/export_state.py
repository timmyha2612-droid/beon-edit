"""Read a finished timeline's cuts, A1 audio and Text+ captions for the speech-sync check (read-only).

exec in run_script_unsafe with `resolve`, `project`, `WORK` and `NAMES` (timeline names) injected.
Writes WORK/<name>_state.json:
  {name, start, fps, end, v1: [(rec0, rec1)], caps: [(rec0, rec1, text, track)],
   a1: [{rec0, rec1, src, t0}]}   # src = media file, t0/t1 = seconds into that file
Record frames are relative to the timeline start. Nothing in the project changes.
"""
import json
import os


def tc_seconds(tc, fps):
    h, m, s, f = (int(x) for x in tc.replace(";", ":").split(":"))
    return (h * 3600 + m * 60 + s) + f / fps


def export():
    tls = {project.GetTimelineByIndex(i).GetName(): project.GetTimelineByIndex(i)  # noqa: F821
           for i in range(1, project.GetTimelineCount() + 1)}  # noqa: F821
    done = {}
    for name in NAMES:  # noqa: F821
        t = tls[name]; st = t.GetStartFrame()
        fps = float(t.GetSetting("timelineFrameRate"))
        out = {"name": name, "start": st, "fps": fps, "end": t.GetEndFrame() - st,
               "v1": [(x.GetStart() - st, x.GetEnd() - st) for x in t.GetItemListInTrack("video", 1)], "a1": [], "caps": []}
        for x in t.GetItemListInTrack("audio", 1) or []:
            mpi = x.GetMediaPoolItem()
            clip_fps = float(mpi.GetClipProperty("FPS"))
            t0 = tc_seconds(mpi.GetClipProperty("Start TC"), clip_fps)
            out["a1"].append({"rec0": x.GetStart() - st, "rec1": x.GetEnd() - st, "src": mpi.GetClipProperty("File Path"),
                              "t0": x.GetSourceStartTime() - t0, "t1": x.GetSourceEndTime() - t0})
        for k in range(2, t.GetTrackCount("video") + 1):
            for x in t.GetItemListInTrack("video", k) or []:
                if x.GetName() == "Text+":
                    txt = x.GetFusionCompByIndex(1).FindTool("Template").GetInput("StyledText")
                    out["caps"].append((x.GetStart() - st, x.GetEnd() - st, txt, k))
        os.makedirs(WORK, exist_ok=True)  # noqa: F821
        json.dump(out, open(os.path.join(WORK, f"{name}_state.json"), "w"))  # noqa: F821
        done[name] = {"captions": len(out["caps"]), "a1": len(out["a1"])}
    return done
