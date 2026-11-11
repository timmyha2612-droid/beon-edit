#!/usr/bin/env python3
"""Apply an approved footage sort plan in Resolve (archive method B: second copies). SKILL.md step 8.

usage:
  python3 sort_apply.py SCRATCH/plan.json                      # dry run (the default): print every action
  python3 sort_apply.py SCRATCH/plan.json --dry-run            # the same, said out loud
  python3 sort_apply.py SCRATCH/plan.json --apply --shotlog <shoot>/_shotlog/shotlog.json
  python3 sort_apply.py SCRATCH/plan.json --shotlog-only --shotlog <shoot>/_shotlog/shotlog.json [--apply]
  python3 sort_apply.py SCRATCH/plan.json --apply --test-bin _claude_sort_test --limit 3
  python3 sort_apply.py SCRATCH/plan.json --apply --test-bin _claude_sort_test --cleanup-test

Before anything (dry run too): the plan is checked (required keys, bin names `NN Title`, every copy
once, clip names ending in the camera clip number, no copy of a clip marked archive only or junk, no
`bin` or `sort_copy` in shotlog_updates), and --shotlog must exist and parse. Then Resolve is reached.

Bin layout: the shoot bin is the archive. Originals and rejects stay at its root under their own names.
The numbered bins are created inside it. Renaming the shoot bin (to `00 Archive - All Footage`) is not
possible from script; Tim does it by hand after the run, then the next inventory takes the new --bin.

What --apply does, in order:
  1. Makes the numbered bins inside the shoot bin (one at a time, checked by name first).
  2. For each copy: imports the clip's File Path again into its bin (a new pool clip, the original
     stays in the archive), tags it beon.sort_copy=1 and beon.sort_src=<original UniqueId>, sets the
     Clip Name (read back, the setter returns False even when it works), copies every marker and the
     Keywords from the original, and appends the sort keywords (place:, subject:, concept: ids and
     the primary role).
  3. Checks once: every planned copy exists once in its bin with its name, markers and sort_src, and
     the originals still have the same markers and keywords. No retry here: rerun to retry, it resumes.
  4. With --shotlog: re-reads the shot log and merges plan.shotlog_updates. Verified copies get
     `bin` (full path) and `sort_copy{bin, uid}` (bin relative to the shoot bin) and sort.approved.
     Clips marked sort.archive_only get sort.approved. Atomic write through a temp file.

--shotlog-only: the gate answer "Only write the shot log". No Resolve calls at all. Merges the content
fields with sort.approved false and no bin. Writes only with --apply.

Resumable: a bin that already holds a beon.sort_copy clip of that File Path is not imported again;
the existing copy is only topped up (name, missing markers, keywords).

--test-bin NAME puts every numbered bin inside <shoot bin>/NAME (NAME must be _claude_sort_test).
--cleanup-test deletes the copies in that bin and then the bin itself. Nothing else is ever deleted.
--limit N only does the first N copies (tests).

Never: CreateEmptyTimeline, SetSetting, project or timeline switches, clip colours. The open project
must be plan.project. Tim's current bin is restored at the end, also after errors.
Plan contract (plan.json): {project, shoot_bin, axis, archive:{rename_to}, bins:[{name, parent}],
copies:[{key, uid, bin, clip_name}], shotlog_updates:{<key>:{...}}}.
"""
import argparse, datetime, json, os, re, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _sortlib as sl

TEST_BIN = "_claude_sort_test"
TAG, SRC = sl.SORT_COPY_KEY, sl.SORT_SRC_KEY
BIN_NAME = re.compile(r"\d\d [A-Z0-9][^&/]{0,28}")
NO_UPDATE_KEYS = ("footage_prep", "bin", "sort_copy")   # never taken from shotlog_updates


def full(parts):
    return "/".join(["Master"] + parts)


def sub(folder, name):
    return next((s for s in (folder.GetSubFolderList() or []) if s.GetName() == name), None)


def clips_under(folder):
    for f, _ in sl.walk(folder, ""):
        yield from f.GetClipList() or []


def is_copy(clip):
    return (clip.GetThirdPartyMetadata(TAG) or "") == "1"


def keywords(clip):
    return [k.strip() for k in (clip.GetMetadata("Keywords") or "").split(",") if k.strip()]


def archive_only(up):
    return bool((up.get("sort") or {}).get("archive_only"))


def validate(plan):
    """Exit with every problem found, before any Resolve call."""
    errs = [f"plan has no {k!r}" for k in ("project", "shoot_bin", "bins", "copies") if k not in plan]
    if errs:
        raise SystemExit("bad plan:\n  " + "\n  ".join(errs))
    if plan.get("axis") not in (None, "place", "subject", "concept"):
        errs.append(f"axis {plan['axis']!r} is not place, subject or concept")
    names = [b.get("name") or "" for b in plan["bins"]]
    for n in names:
        if not BIN_NAME.fullmatch(n):
            errs.append(f"bin {n!r} is not 'NN Title' (two digits, a space, at most 32 characters, no '&')")
    errs += [f"bin {n!r} is planned twice" for n in sorted({n for n in names if names.count(n) > 1})]
    ups = plan.get("shotlog_updates") or {}
    seen = set()
    for c in plan["copies"]:
        miss = [k for k in ("key", "uid", "bin", "clip_name") if not c.get(k)]
        if miss:
            errs.append(f"copy {c} has no {', '.join(miss)}")
            continue
        stem = os.path.splitext(os.path.basename(c["key"]))[0]
        if c["key"] in seen:
            errs.append(f"{stem} is copied twice")
        seen.add(c["key"])
        if c["bin"] not in names:
            errs.append(f"{stem} targets unknown bin {c['bin']!r}")
        if c["clip_name"].split()[-1] != stem:
            errs.append(f"{stem}: clip name {c['clip_name']!r} must end in the camera clip number {stem!r}")
        up = ups.get(c["key"], {})
        if archive_only(up) or (up.get("roles") or [None])[0] == "junk":
            errs.append(f"{stem} is marked archive only or junk: rejects and unsure clips get no copy")
    for k, up in ups.items():
        stem = os.path.splitext(os.path.basename(k))[0]
        bad = [x for x in ("bin", "sort_copy") if x in up]
        if bad:
            errs.append(f"{stem}: shotlog_updates carries {', '.join(bad)}; only a verified copy writes those")
        if k not in seen and not archive_only(up):
            errs.append(f"{stem} has no copy, so its update needs sort.archive_only: true (reject or unsure)")
    if errs:
        raise SystemExit("bad plan:\n  " + "\n  ".join(errs))


def read_shotlog(path):
    """The parsed shot log, or exit. Called before any Resolve change and again right before writing."""
    try:
        with open(os.path.expanduser(path)) as fh:
            log = json.load(fh)
    except OSError as e:
        raise SystemExit(f"shot log not readable: {path} ({e.strerror})")
    except ValueError as e:
        raise SystemExit(f"shot log is not valid JSON: {path} ({e})")
    if not isinstance(log, dict) or not isinstance(log.get("clips", []), list):
        raise SystemExit(f"shot log has no clips list: {path}")
    return log


def sort_keywords(plan, key):
    """Sort keywords from the shot log update: place/subject/concept ids and the primary role."""
    up = plan.get("shotlog_updates", {}).get(key, {})
    out = []
    for f in ("place", "subject", "concept"):
        v = up.get(f)
        v = v.get("id") if isinstance(v, dict) else v
        if v:
            out.append(f"{f}:{v}")
    roles = up.get("roles") or []
    if roles:
        out.append(roles[0])
    return out


def copy_in(folder, key):
    return [c for c in (folder.GetClipList() or []) if is_copy(c) and c.GetClipProperty("File Path") == key]


def fill_copy(cp, orig, cinfo, extra_kw, log):
    """Name, markers, keywords on a copy. Safe to run again on a half-done copy."""
    want = cinfo["clip_name"]
    if cp.GetName() != want:
        cp.SetClipProperty("Clip Name", want)          # returns False even on success
        if cp.GetName() != want:
            cp.SetName(want)
        if cp.GetName() != want:
            log.append(f"name not set on {want!r} (reads {cp.GetName()!r})")
    have = {int(f) for f in (cp.GetMarkers() or {})}
    for f, m in sorted((orig.GetMarkers() or {}).items()):
        if int(f) in have:
            continue
        ok = cp.AddMarker(int(f), m.get("color", "Blue"), m.get("name", ""), m.get("note", ""),
                          int(m.get("duration", 1)), m.get("customData", "") or "")
        if not ok:
            log.append(f"{want}: marker at {int(f)} ({m.get('color')}) not added")
    kw = keywords(cp)
    for k in keywords(orig) + extra_kw:
        if k not in kw:
            kw.append(k)
    if kw != keywords(cp):
        cp.SetMetadata({"Keywords": ",".join(kw)})
        if keywords(cp) != kw:
            log.append(f"{want}: keywords not set")


def write_shotlog(path, plan, verified, approve_archive):
    """Merge plan.shotlog_updates into shotlog.json (re-read first). Never touches footage_prep.
    verified: {key: {"bin": full path, "rel": bin relative to the shoot bin, "uid": copy UniqueId}}.
    approve_archive False is the shot-log-only mode: sort.approved false, no bin. Atomic write."""
    log = read_shotlog(path)
    clips = log.setdefault("clips", [])
    today = datetime.date.today().isoformat()
    n = 0
    for key, up in plan.get("shotlog_updates", {}).items():
        e = next((c for c in clips if c.get("file") and (c["file"] == key or key.endswith("/" + c["file"]))), None)
        if e is None:
            e = {"clip": os.path.splitext(os.path.basename(key))[0], "file": key}
            clips.append(e)
        for k, v in up.items():
            if k in NO_UPDATE_KEYS:
                continue
            if k == "sort" and isinstance(v, dict):
                e.setdefault("sort", {}).update(v)
            else:
                e[k] = v
        s = e.setdefault("sort", {})
        s.update({"v": sl.SORT_V, "axis": plan.get("axis") or s.get("axis"), "at": s.get("at") or today})
        s.setdefault("tim", [])
        if key in verified:
            e["bin"] = verified[key]["bin"]
            e["sort_copy"] = {"bin": verified[key]["rel"], "uid": verified[key]["uid"]}
            s.update({"approved": True, "bin_verified": today})
        elif archive_only(up) and approve_archive:
            s["approved"] = True
        else:
            s.setdefault("approved", False)
        n += 1
    log["updated"] = today
    p = os.path.abspath(os.path.expanduser(path))
    fd, tmp = tempfile.mkstemp(prefix=".shotlog.", suffix=".tmp", dir=os.path.dirname(p))
    with os.fdopen(fd, "w") as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False)
    os.replace(tmp, p)
    return n


def cleanup_test(mp, shoot):
    tb = sub(shoot, TEST_BIN)
    if tb is None:
        print(f"no {TEST_BIN} bin, nothing to clean")
        return
    assert tb.GetName() == TEST_BIN
    items = list(clips_under(tb))
    bad = [c.GetName() for c in items if not is_copy(c)]
    if bad:
        raise SystemExit(f"{TEST_BIN} holds clips that are not sort copies, not deleting: {bad}")
    if items and not mp.DeleteClips(items):
        raise SystemExit("DeleteClips failed")
    if not mp.DeleteFolders([tb]):
        raise SystemExit("DeleteFolders failed")
    print(f"deleted {len(items)} copies and the {TEST_BIN} bin")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--apply", action="store_true", help="execute (default is a dry run)")
    ap.add_argument("--dry-run", action="store_true", help="print only (the default, never with --apply)")
    ap.add_argument("--shotlog", help="shotlog.json to update (checked in a dry run, written with --apply)")
    ap.add_argument("--shotlog-only", action="store_true", help="only merge the shot log, no Resolve calls")
    ap.add_argument("--test-bin", help=f"put numbered bins inside <shoot bin>/{TEST_BIN}")
    ap.add_argument("--limit", type=int, help="only the first N copies (tests)")
    ap.add_argument("--cleanup-test", action="store_true", help=f"delete the {TEST_BIN} bin and its copies")
    a = ap.parse_args()

    if a.apply and a.dry_run:
        raise SystemExit("--dry-run and --apply together: pick one")
    plan = sl.read_json(a.plan)
    if a.test_bin and a.test_bin != TEST_BIN:
        raise SystemExit(f"--test-bin must be {TEST_BIN}")
    if a.cleanup_test and not a.test_bin:
        raise SystemExit("--cleanup-test needs --test-bin")
    if a.shotlog_only and not a.shotlog:
        raise SystemExit("--shotlog-only needs --shotlog")
    if a.shotlog_only and (a.test_bin or a.cleanup_test):
        raise SystemExit("--shotlog-only makes no Resolve calls: no --test-bin or --cleanup-test")
    if a.test_bin and a.shotlog and "Dropbox" in os.path.realpath(os.path.expanduser(a.shotlog)):
        raise SystemExit("test mode never writes a shot log in Dropbox")
    if not a.cleanup_test:
        validate(plan)
    if a.shotlog:
        n_log = len(read_shotlog(a.shotlog).get("clips", []))
        print(f"shotlog ok: {a.shotlog} ({n_log} clips)")
    mode = "APPLY" if a.apply else "DRY RUN"

    if a.shotlog_only:
        ups = plan.get("shotlog_updates", {})
        if a.apply:
            n = write_shotlog(a.shotlog, plan, {}, approve_archive=False)
            print(f"{mode} shotlog only: {n} clips merged, sort.approved false, no bins -> {a.shotlog}")
        else:
            print(f"{mode} shotlog only: would merge {len(ups)} clips, sort.approved false, no bins")
        return

    shoot_parts = sl.bin_parts(plan["shoot_bin"])
    bins = {b["name"]: sl.bin_parts(b.get("parent") or plan["shoot_bin"]) + [b["name"]] for b in plan["bins"]}
    if a.test_bin:   # same bins, one level down inside the test bin
        bins = {n: shoot_parts + [TEST_BIN] + p[len(shoot_parts):] if p[:len(shoot_parts)] == shoot_parts
                else shoot_parts + [TEST_BIN, n] for n, p in bins.items()}
    copies = plan["copies"][: a.limit] if a.limit else plan["copies"]

    resolve, pj, mp = sl.connect(plan["project"])
    shoot = sl.find_folder(mp, shoot_parts)
    tim_folder = mp.GetCurrentFolder()
    tim_id = tim_folder.GetUniqueId() if tim_folder else None
    print(f"{mode}: {pj.GetName()} / {full(shoot_parts)}, {len(copies)} copies into {len(set(c['bin'] for c in copies))} bins")

    problems, verified = [], {}
    try:
        if a.cleanup_test:
            if a.apply:
                cleanup_test(mp, shoot)
            else:
                tb = sub(shoot, TEST_BIN)
                print(f"would delete {len(list(clips_under(tb))) if tb else 0} copies and the {TEST_BIN} bin")
            return

        # originals: every untagged clip under the shoot bin, by UniqueId
        originals = {c.GetUniqueId(): c for c in clips_under(shoot) if not is_copy(c)}
        before = {}
        for c in copies:
            o = originals.get(c["uid"])
            if o is None or o.GetClipProperty("File Path") != c["key"]:
                o = next((x for x in originals.values() if x.GetClipProperty("File Path") == c["key"]), None)
            if o is None:
                problems.append(f"{c['clip_name']}: original not found ({c['key']})")
                continue
            c["_orig"] = o
            before[c["key"]] = (len(o.GetMarkers() or {}), keywords(o))

        # 1. bins, one at a time
        if a.test_bin and sub(shoot, TEST_BIN) is None:
            print(f"bin  + {full(shoot_parts + [TEST_BIN])}")
            if a.apply:
                mp.SetCurrentFolder(shoot)
                mp.AddSubFolder(shoot, TEST_BIN)
                if sub(shoot, TEST_BIN) is None:
                    raise SystemExit(f"{TEST_BIN} did not land in the shoot bin")
        folders = {}
        for name in dict.fromkeys(c["bin"] for c in copies):
            parts = bins[name]
            parent = sl.find_folder(mp, parts[:-1], required=False)
            f = sub(parent, name) if parent else None
            if f is None:
                print(f"bin  + {full(parts)}")
                if a.apply:
                    if parent is None:
                        raise SystemExit(f"parent bin missing: {full(parts[:-1])}")
                    mp.SetCurrentFolder(parent)
                    mp.AddSubFolder(parent, name)
                    f = sub(parent, name)
                    if f is None:
                        raise SystemExit(f"bin {name!r} did not land in {full(parts[:-1])}: check the pool")
            else:
                print(f"bin  = {full(parts)} (exists)")
            folders[name] = f

        # 2. copies
        for c in copies:
            if "_orig" not in c:
                continue
            f, extra = folders.get(c["bin"]), sort_keywords(plan, c["key"])
            have = copy_in(f, c["key"]) if f else []
            if have:
                print(f"skip {c['clip_name']}: copy already in {c['bin']}, topping up")
                cp = have[0]
            else:
                print(f"copy {os.path.basename(c['key'])} -> {c['bin']} as {c['clip_name']!r}, "
                      f"{before[c['key']][0]} markers, keywords +{extra}")
                if not a.apply:
                    continue
                mp.SetCurrentFolder(f)
                new = mp.ImportMedia([c["key"]]) or []
                cp = next((x for x in new if x.GetUniqueId() != c["_orig"].GetUniqueId()), None)
                if cp is None:
                    problems.append(f"{c['clip_name']}: ImportMedia gave no new clip")
                    continue
                cp.SetThirdPartyMetadata({TAG: "1", SRC: c["_orig"].GetUniqueId()})
            if a.apply:
                fill_copy(cp, c["_orig"], c, extra, problems)
        archive = [k for k, up in plan.get("shotlog_updates", {}).items() if archive_only(up)]
        print(f"archive only (no copy, stay in {full(shoot_parts)}): {len(archive)}")

        # 3. verify (once; a rerun resumes and retries what is missing)
        if a.apply:
            for c in copies:
                if "_orig" not in c:
                    continue
                got = copy_in(folders[c["bin"]], c["key"])
                o = c["_orig"]
                now = (len(o.GetMarkers() or {}), keywords(o))
                if len(got) != 1:
                    problems.append(f"{c['clip_name']}: {len(got)} copies in {c['bin']}, expected 1")
                elif got[0].GetName() != c["clip_name"]:
                    problems.append(f"{c['clip_name']}: copy is named {got[0].GetName()!r}")
                elif len(got[0].GetMarkers() or {}) < now[0]:
                    problems.append(f"{c['clip_name']}: copy has fewer markers than the original")
                elif (got[0].GetThirdPartyMetadata(SRC) or "") != o.GetUniqueId():
                    problems.append(f"{c['clip_name']}: beon.sort_src does not match the original")
                else:
                    path = bins[c["bin"]]
                    verified[c["key"]] = {"bin": full(path), "rel": "/".join(path[len(shoot_parts):]),
                                          "uid": got[0].GetUniqueId()}
                if now != before[c["key"]]:
                    problems.append(f"{c['clip_name']}: ORIGINAL changed (markers/keywords {before[c['key']]} -> {now})")
            print(f"verify: {len(verified)}/{len(copies)} copies ok, originals checked")
    finally:
        # DeleteFolders and SetCurrentFolder move the current bin: put Tim's back (shoot bin if it's gone)
        if not (tim_folder and mp.SetCurrentFolder(tim_folder) and mp.GetCurrentFolder().GetUniqueId() == tim_id):
            mp.SetCurrentFolder(sl.find_folder(mp, shoot_parts, required=False) or mp.GetRootFolder())
        print(f"current bin restored: {mp.GetCurrentFolder().GetName()}")

    # 4. shot log (no more Resolve calls)
    if a.shotlog:
        if a.apply:
            n = write_shotlog(a.shotlog, plan, verified, approve_archive=True)
            print(f"shotlog: {n} clips updated, {len(verified)} with a verified copy -> {a.shotlog}")
        else:
            print(f"shotlog: would update {len(plan.get('shotlog_updates', {}))} clips in {a.shotlog}")
    rename = (plan.get("archive") or {}).get("rename_to")
    if rename:
        print(f"archive rename: Tim renames {full(shoot_parts)} to {rename!r} by hand (no Folder rename in the API),"
              " then the next inventory takes the new --bin")

    for p in problems:
        print("PROBLEM", p)
    print("DONE" if not problems else f"DONE with {len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
