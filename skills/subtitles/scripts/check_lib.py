"""Export one still per caption (just before it exits) from a short's main timeline."""
import json
import os
import time

# Inject WORK and FPS when exec-ing: `python3 subs_intake.py --card <job card>` prints both (WORK from
# the scratch folder, FPS from the job card Delivery line / client profile). Defaults: ~/subs_work, 24.
BASE = globals().get("WORK", os.path.expanduser("~/subs_work")).rstrip("/") + "/"
FPS = globals().get("FPS", 24)
PLANS = json.load(open(BASE + "plans.json"))


def tc(frames):
    f, r = int(frames), int(round(FPS))
    return "%02d:%02d:%02d:%02d" % (f // (3600 * r), f // (60 * r) % 60, f // r % 60, f % r)


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
