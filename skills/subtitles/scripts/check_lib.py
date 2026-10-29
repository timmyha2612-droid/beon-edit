"""Export one still per caption (just before it exits) from a short's main timeline."""
import json
import os
import time

BASE = globals().get("WORK", os.path.expanduser("~/subs_work")).rstrip("/") + "/"  # set WORK when exec-ing
PLANS = json.load(open(BASE + "plans.json"))


def tc(frames):
    f = int(frames)
    return "%02d:%02d:%02d:%02d" % (f // 86400, f // 1440 % 60, f // 24 % 60, f % 24)


def stills(name, a, b, tag):
    tl = None
    for i in range(1, project.GetTimelineCount() + 1):
        if project.GetTimelineByIndex(i).GetName() == name:
            tl = project.GetTimelineByIndex(i)
    project.SetCurrentTimeline(tl)
    assert project.GetCurrentTimeline().GetName() == name
    os.makedirs(BASE + "checks", exist_ok=True)
    resolve.OpenPage("color")
    time.sleep(1.5)
    caps = PLANS[name]["caps"]
    done = 0
    for n in range(a, min(b, len(caps))):
        c = caps[n]
        f = tl.GetStartFrame() + c["end"] - max(c["out_dur"], 0) - 2
        tl.SetCurrentTimecode(tc(f))
        time.sleep(0.9)
        if project.ExportCurrentFrameAsStill(BASE + f"checks/{tag}_{n:02d}.png"):
            done += 1
    resolve.OpenPage("edit")
    return done
