"""Connect to the running DaVinci Resolve Studio from an external python (Bash), not from run_script."""
import os, sys
API = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
os.environ.setdefault("RESOLVE_SCRIPT_API", API)
os.environ.setdefault("RESOLVE_SCRIPT_LIB", "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so")
sys.path.append(API + "/Modules")


def connect(project=None, timeline=None):
    import DaVinciResolveScript as dvr
    resolve = dvr.scriptapp("Resolve")
    if not resolve:
        raise SystemExit("cannot reach Resolve (Studio running? Preferences > General > External scripting = Local)")
    pj = resolve.GetProjectManager().GetCurrentProject()
    tl = pj.GetCurrentTimeline()
    if project and pj.GetName() != project:
        raise SystemExit(f"open project is {pj.GetName()!r}, expected {project!r}")
    if timeline and tl.GetName() != timeline:
        for i in range(1, pj.GetTimelineCount() + 1):
            t = pj.GetTimelineByIndex(i)
            if t.GetName() == timeline:
                pj.SetCurrentTimeline(t); tl = t; break
        else:
            raise SystemExit(f"no timeline {timeline!r}")
    return resolve, pj, tl
