# exec'd inside Resolve with resolve, project, WORK, NAME, A, B injected: configure Kinetic titles
# A..B-1 on "<NAME> Kinetic Subtitles" from WORK/plans.json + layout.json (kinetic_layout.py).
# Run 6-10 titles per call, one call at a time, SaveProject between calls.
# Words follow Txt1: its Center is the block anchor and its Size the base size, so Tim can move or
# scale a whole caption from the Inspector.
import json, re, sys
sys.path.insert(0, WORK)
from captions import KEYS
ns = {"resolve": resolve, "project": project, "WORK": WORK, "__name__": "lib"}
exec(open("/Users/timha/code/beon-edit/skills/subtitles/scripts/build_lib.py").read(), ns)
ns["subs_name"] = lambda n: n + " Kinetic Subtitles"
ns["step_config"](NAME, A, B)                       # text, word times, in/out, names
layout = json.load(open(WORK + "/layout.json"))[NAME]
items = ns["current_subs"](NAME).GetItemListInTrack("video", 1)
done = []
for n in range(A, min(B, len(items))):
    comp = items[n].GetFusionCompByIndex(1)
    main = comp.FindTool("Main")
    assert main.GetInput("Karaoke") is not None, "not a Kinetic title"
    comp.FindTool("FluidRevealWords").SetInput("OutDur", 0)    # hard swap between captions
    cap, keys = layout[n], KEYS.get(n, {})
    comp.FindTool("Txt1").SetInput("Center", cap["anchor"])
    words = cap["words"]
    a, b = cap["show"]
    gate = f"(time >= {a}{'' if b is None else f' and time < {b}'} and 1 or 0)"   # shown only on its shot
    for k in range(1, 13):
        w = comp.FindTool(f"W{k}")
        main.SetInput(f"Hi{k}", float(keys.get(k, 0)))
        if k <= len(words):
            x = words[k - 1]
            w.SetInput("StyledText", x["text"])
            w.SetInput("Style", x["style"])
            # Size is instanced from Txt1: an expression on it loops and blanks the whole frame, so
            # a slam / shrink-to-fit word scales through its own WordSize (base expression kept).
            w.Size.SetExpression(None)
            for inp in (w.WordSizeX, w.WordSizeY):
                e = inp.GetExpression() or "1"
                m = re.match(r"^[0-9.]+\*\((.*)\)$", e)
                base = m.group(1) if m else e
                inp.SetExpression(base if abs(x["scale"] - 1) < 1e-4 else f"{x['scale']}*({base})")
            w.Center.SetExpression(f"Point(Txt1.Center.X+({x['dx']})*Txt1.Size/0.075, Txt1.Center.Y+({x['dy']})*Txt1.Size/0.075)")
        else:
            w.SetInput("StyledText", "")
        start = f"(Main.WordTime{k} >= 0 and Main.WordTime{k} or {k - 1}*Main.WordStagger)+Main.SyncOffset"
        comp.FindTool(f"WordFx{k}").n1.SetExpression(f"{gate}*(1-(1-min(max((time-({start}))/max(Main.SnapIn,1),0),1))^3)")
    done.append((n + 1, " ".join(x["text"] + ("*" if x["style"] == "Italic" else "") for x in words)))
result = done
