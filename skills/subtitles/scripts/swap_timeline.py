"""Swap a timeline for its edited DRT, keeping the old one as a backup.

exec in run_script_unsafe with `resolve`, `project`, `NAME` (timeline), `DRT` (edited export) and
optional `TAG` (default "pre-subsync") injected. Imports DRT into the old timeline's bin, checks the
length, the V1/A1 clips and every non-caption item are unchanged, renames the old one "<NAME> <TAG>"
and moves it into a "Backup" sub-bin, and gives the import NAME. If that backup name is taken it adds 2, 3...; a failed rename stops the swap. Never deletes anything.
"""
import time

TAG = globals().get("TAG", "pre-subsync")
pm = resolve.GetProjectManager(); mp = project.GetMediaPool()  # noqa: F821
tls = {project.GetTimelineByIndex(i).GetName(): project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)}  # noqa: F821
old = tls[NAME]  # noqa: F821
pm.SaveProject()


def find_bin(folder):
    for c in folder.GetClipList() or []:
        if c.GetClipProperty("Type") == "Timeline" and c.GetName() == NAME:  # noqa: F821
            return folder, c
    for f in folder.GetSubFolderList() or []:
        hit = find_bin(f)
        if hit:
            return hit
    return None


home, item = find_bin(mp.GetRootFolder())
mp.SetCurrentFolder(home)
new = mp.ImportTimelineFromFile(DRT, {"timelineName": NAME + " import", "importSourceClips": False})  # noqa: F821
time.sleep(1)
assert new, "import failed"


def shape(t):
    s = t.GetStartFrame()
    return [[(x.GetName(), x.GetStart() - s, x.GetDuration()) for x in (t.GetItemListInTrack(kind, k) or []) if x.GetName() != "Text+"]
            for kind in ("video", "audio") for k in range(1, t.GetTrackCount(kind) + 1)]


assert new.GetEndFrame() - new.GetStartFrame() == old.GetEndFrame() - old.GetStartFrame(), "length changed"
assert shape(new) == shape(old), "a non-caption item changed"
backup = NAME + " " + TAG  # noqa: F821
k = 2
while backup in tls:                        # a backup from an earlier pass already has the name (C03f, 10 Nov)
    backup = f"{NAME} {TAG}{k}"; k += 1  # noqa: F821
assert old.SetName(backup), "could not rename the old timeline"
assert new.SetName(NAME), "could not rename the import"  # noqa: F821
time.sleep(0.5)
bk = [f for f in home.GetSubFolderList() if f.GetName() == "Backup"]
bk = bk[0] if bk else mp.AddSubFolder(home, "Backup")
moved = mp.MoveClips([c for c in home.GetClipList() if c.GetName() == backup], bk)
project.SetCurrentTimeline(new)  # noqa: F821
pm.SaveProject()
result = {"swapped": NAME, "backup": backup, "moved": moved}  # noqa: F821
