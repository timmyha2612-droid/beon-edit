"""Read-only: list the subtitle / title looks already used on the project's other timelines.

Subtitles Step 0, look-up order step 3 (Tim, 9 Nov 2026): when the client profile doesn't give the
caption look, see what the editor used on other timelines of the same project, then confirm it with them.

Run inside Resolve (run_script_unsafe), with `resolve` and `project` injected:
    ns = {"resolve": resolve, "project": project, "__name__": "lib"}
    exec(open("<skill>/scripts/read_styles.py").read(), ns)
    result = ns["scan"](limit_timelines=40)            # or scan(names=["C2a", "C3"])

Returns one row per distinct look: {look, kind, count, timelines[], example, values}. Nothing is changed:
no timeline is switched, nothing is selected or edited. Titles inside nested subtitle timelines are found
by scanning those timelines too (they're ordinary timelines in the project). Keep each call under 60 s:
pass names= or a smaller limit_timelines on big projects."""
import json

FRW_KEYS = ("Font", "Style", "Red", "Green", "Blue", "Size", "Tracking", "LineSpacing", "Position", "Rise",
            "InBlur", "OutBlur", "OutLift")
TEXT_KEYS = ("Font", "Style", "Size", "Red1", "Green1", "Blue1", "Center", "CharacterSpacing", "LineSpacing")


def _val(v):
    if isinstance(v, dict):                          # Position/Center come back as {1.0: x, 2.0: y, 3.0: z}
        v = [v[k] for k in sorted(v)][:2]
    if isinstance(v, float):
        v = round(v, 4)
    if isinstance(v, list):
        v = [round(x, 4) if isinstance(x, float) else x for x in v]
    return v


def _read(item):
    if not item.GetFusionCompCount():
        return None
    comp = item.GetFusionCompByIndex(1)
    if comp is None:
        return None
    for group in ("FluidRevealWords",):
        g = comp.FindTool(group)
        if g:
            kind = "Fluid Reveal Words"
            if comp.FindTool("Txt1") and g.GetInput("Hi1") is not None:
                kind = "Fluid Reveal Words Hook/Kinetic"
            return kind, {k: _val(g.GetInput(k)) for k in FRW_KEYS if g.GetInput(k) is not None}
    tools = comp.GetToolList(False, "TextPlus") or {}
    for t in tools.values():
        return "Text+ (" + (item.GetName() or "title") + ")", {k: _val(t.GetInput(k)) for k in TEXT_KEYS
                                                              if t.GetInput(k) is not None}
    return None


def _describe(values):
    font = " ".join(str(values.get(k, "")) for k in ("Font", "Style")).strip()
    rgb = [values.get(k) for k in ("Red", "Green", "Blue")]
    if None in rgb:
        rgb = [values.get(k) for k in ("Red1", "Green1", "Blue1")]
    colour = "white" if rgb == [1, 1, 1] or rgb == [1.0, 1.0, 1.0] else f"rgb {rgb}"
    pos = values.get("Position") or values.get("Center")
    return f"{font or '?'}, size {values.get('Size', '?')}, {colour}, position {pos}"


def scan(names=None, limit_timelines=40, max_items_per_tl=60):
    looks = {}
    n_tl = project.GetTimelineCount()
    checked = 0
    for i in range(1, n_tl + 1):
        tl = project.GetTimelineByIndex(i)
        name = tl.GetName()
        if names and name not in names:
            continue
        if not names and checked >= limit_timelines:
            break
        checked += 1
        seen = 0
        for k in range(1, tl.GetTrackCount("video") + 1):
            for it in tl.GetItemListInTrack("video", k) or []:
                if seen >= max_items_per_tl:
                    break
                r = _read(it)
                if not r:
                    continue
                seen += 1
                kind, values = r
                key = kind + json.dumps({k_: values.get(k_) for k_ in ("Font", "Style", "Size", "Red", "Red1")},
                                        sort_keys=True, default=str)
                row = looks.setdefault(key, {"kind": kind, "count": 0, "timelines": [], "values": values,
                                             "example": f"{name} V{k} {it.GetName()}"})
                row["count"] += 1
                if name not in row["timelines"]:
                    row["timelines"].append(name)
    out = sorted(looks.values(), key=lambda r: -r["count"])
    for r in out:
        r["look"] = _describe(r["values"])
    return {"timelines_checked": checked, "of": n_tl, "looks": out}


# same keys as build_lib.STYLE_KEYS, so the file works with build_lib.step_config and Auto Subtitles
STYLE_KEYS = ("Font", "Style", "Red", "Green", "Blue", "Alpha", "Size", "Tracking", "LineSpacing", "Position",
              "JustifyL", "WordStagger", "SyncOffset", "InCurve", "InEaseIn", "InEaseOut", "Rise", "InBlur",
              "OutCurve", "OutEaseIn", "OutEaseOut", "OutLift", "OutBlur")


def save_style(timeline_name, item_name, work):
    """After the editor confirms a look found by scan(): copy that Fluid Reveal Words title's full style into
    <work>/style.json (the file build_lib and Auto Subtitles apply; a cache, the job card Subtitles line is
    the record). Read-only on the project."""
    for i in range(1, project.GetTimelineCount() + 1):
        tl = project.GetTimelineByIndex(i)
        if tl.GetName() != timeline_name:
            continue
        for k in range(1, tl.GetTrackCount("video") + 1):
            for it in tl.GetItemListInTrack("video", k) or []:
                if it.GetName() != item_name or not it.GetFusionCompCount():
                    continue
                g = it.GetFusionCompByIndex(1).FindTool("FluidRevealWords")
                if not g:
                    continue
                style = {key: _val(g.GetInput(key)) for key in STYLE_KEYS if g.GetInput(key) is not None}
                path = work.rstrip("/") + "/style.json"
                json.dump(style, open(path, "w"), indent=1)
                return {"saved": path, "style": style}
    return {"error": f"no Fluid Reveal Words title named {item_name!r} on {timeline_name!r}"}
