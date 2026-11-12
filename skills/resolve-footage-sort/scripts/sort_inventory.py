#!/usr/bin/env python3
"""Footage sort, SKILL.md step 3: inventory, rerun state and roles by rule. Text only, no frames.

usage: python3 sort_inventory.py --project "Client" --bin "Month/Job/Shoot" \
           --fp-clips SCRATCH/clips.json --fp-selects SCRATCH/selects.json \
           [--shotlog "<shoot folder>/_shotlog/shotlog.json"] --out SCRATCH/manifest.json

Inputs
  --fp-clips    Footage Prep `clips(shoot, sort: timeline, limit: 200)` saved as JSON. Pass several files
                when it pages past 200 (--fp-clips p1.json p2.json).
  --fp-selects  Footage Prep `selects(shoot, order: timeline, without_flags: [shaky, whip, motion_blur,
                blocked], limit: 200)` saved as JSON (pages as above). Selects with those flags are dropped
                here too, so an unfiltered file works.
  --shotlog     the shoot's shot log (read only). Gives the rerun state and the missing list.

What it does
  Resolve (read only, one pass): every pool item in the shoot bin and its subfolders. Refuses when the
  open project is not --project. Never switches projects or timelines, never writes.
  Excluded and listed: timelines, multicam, compound and Fusion clips, subclips, Gyroflow renders,
  proxies, items in Selects, Original Clips or Proxy bins, and a second pool item for the same file.
  Sort copies (third-party metadata beon.sort_copy=1) are not rows: they mark their clip as settled
  and are listed under the clip's `copies`.
  Join key: absolute File Path. Footage Prep paths are relative to the shoot, so a clip joins when its
  File Path ends with /<FP path> (or its fp.clip metadata equals the FP path). Never by clip name.
  ffprobe: creation_time and duration per file (timeout per file). Online-only files are not probed,
  so nothing downloads.
  Rerun state: settled, moved_by_editor, missing or new (see SKILL.md step 3). The shot log's
  sort_copy.bin is relative to the shoot bin, so a renamed shoot bin does not break it.
  Roles: aroll (>= 60 s, locked or steady, speech-like audio), multicam_angle (another camera that
  overlaps an aroll clip by >= 30 s), audio (no video), junk_candidate (< 1.5 s, dark and silent, or
  reject with 0 selects), broll (the rest). The audio scan only runs on aroll and dark candidates.

Output: manifest.json (contract in SKILL.md). Prints a short summary. Writes only --out, and refuses a
path inside Dropbox, editor.json synced_folders or _shotlog."""
import argparse, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _sortlib as sl

SKIP_BINS = re.compile(r"select|original clips|proxy|gyroflow", re.I)
GYRO_FILE = re.compile(r"gyroflow|stabili[sz]|_gf_", re.I)
BAD_TYPES = re.compile(r"timeline|multicam|compound|fusion|generator|title", re.I)
AROLL_MIN_S, MULTICAM_MIN_S, JUNK_MAX_S = 60.0, 30.0, 1.5


def read_pool(mp, bin_path):
    """One read-only pass over the shoot bin. Returns a list of raw item dicts."""
    shoot = sl.find_folder(mp, bin_path)
    items = []
    for folder, path in sl.walk(shoot, "/".join(sl.bin_parts(bin_path))):
        skip = next((p for p in path.split("/")[len(sl.bin_parts(bin_path)):] if SKIP_BINS.search(p)), None)
        for c in folder.GetClipList() or []:
            p = c.GetClipProperty() or {}
            items.append({"name": p.get("Clip Name") or c.GetName(), "key": p.get("File Path") or "",
                          "type": p.get("Type") or "", "uid": c.GetUniqueId(), "folder": path, "skip_bin": skip,
                          "frames": int(p.get("Frames") or 0), "fps": float(p.get("FPS") or 0),
                          "camera": p.get("Camera Type") or "", "tpm": c.GetThirdPartyMetadata() or {}})
    return items


def probe(path, timeout):
    if not os.path.exists(path):
        return {"error": "file not found"}
    if sl.online_only(path):
        return {"error": "online-only file, not probed"}
    return sl.ffprobe(path, timeout)


def audio_scan(path, timeout=180):
    """{'silence_pct', 'mean_db'} from silencedetect + volumedetect, or {'error'}."""
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-vn", "-i", path,
           "-af", "silencedetect=n=-40dB:d=0.5,volumedetect", "-f", "null", "-"]
    try:
        err = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stderr
    except subprocess.TimeoutExpired:
        return {"error": "audio scan timed out"}
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    total = int(dur[1]) * 3600 + int(dur[2]) * 60 + float(dur[3]) if dur else 0
    silent = sum(float(x) for x in re.findall(r"silence_duration: ([\d.]+)", err))
    starts = re.findall(r"silence_start: ([\d.]+)", err)
    if len(starts) > len(re.findall(r"silence_end", err)) and total:   # silence runs to the end
        silent += total - float(starts[-1])
    mean = re.search(r"mean_volume: (-?[\d.]+) dB", err)
    if not total or not mean:
        return {"error": "no audio"}
    return {"silence_pct": round(100 * silent / total, 1), "mean_db": float(mean[1])}


def fp_block(row, selects, drop):
    """The manifest fp block from one FP clips row and its selects."""
    clean = [s for s in selects if not set(s.get("flags") or []) & drop]
    fps = row.get("fps") or 1
    stab = [((s.get("metrics") or {}).get("stability")) for s in sorted(selects, key=lambda s: -(s.get("score") or 0))]
    return {"clip_path": row["path"], "tier": row.get("tier"), "auto_tier": row.get("auto_tier"),
            "movement": row.get("movement"), "chips": row.get("chips") or [], "stability": next((x for x in stab if x is not None), None),
            "shaky_frac": row.get("shaky_frac"), "best_score": row.get("best_score"), "flags": row.get("flags") or [],
            "n_selects": row.get("selects"),
            "selects": [{"in_s": round(s["in_frame"] / (s.get("fps") or fps), 3),
                         "out_s": round(s["out_frame"] / (s.get("fps") or fps), 3),
                         "score": round(s.get("score") or 0, 1),
                         "stability": round((s.get("metrics") or {}).get("stability") or 0, 3)} for s in clean],
            "duplicate_of": row.get("duplicate_of")}


def join_fp(keys, fp_rows, tpm_by_key):
    """{key: fp row}, plus FP rows that joined nothing. Suffix match on the FP relative path."""
    by_rel = {r["path"]: r for r in fp_rows}
    out, used = {}, set()
    for k in keys:
        rel = tpm_by_key.get(k, {}).get("fp.clip")
        hits = [rel] if rel in by_rel else [p for p in by_rel if k.endswith("/" + p)]
        if len(hits) > 1:   # same name on two cards: keep the longest (most specific) path
            hits = sorted(hits, key=len)[-1:]
        if hits and hits[0] not in used:
            out[k] = by_rel[hits[0]]
            used.add(hits[0])
    return out, [r for p, r in by_rel.items() if p not in used]


def shotlog_index(path):
    """{absolute file path: clip entry} from a shot log. Relative `file` values are under the shoot folder."""
    if not path:
        return {}
    log = sl.read_json(path, default={})
    root = os.path.dirname(os.path.dirname(os.path.abspath(path)))
    idx = {}
    for c in log.get("clips", []):
        f = c.get("file") or ""
        if f:
            idx[f if os.path.isabs(f) else os.path.join(root, f)] = c
    return idx


def rerun_state(row, log, copies, shoot_bin):
    """settled | moved_by_editor | new, and where the clip is now. The editor always wins.
    Bins are compared relative to the shoot bin, so a renamed shoot bin keeps its clips settled."""
    sort = log.get("sort") or {}
    current = sort.get("v") == sl.SORT_V
    here = [c["folder"] for c in copies] or [row["folder"]]
    rel_here = [sl.rel_bin(f, shoot_bin) for f in here]
    want = (log.get("sort_copy") or {}).get("bin")          # the copy's bin, relative to the shoot bin
    if copies:
        return ("moved_by_editor", here) if want is not None and want not in rel_here else ("settled", here)
    if want is not None:                                      # the editor deleted the copy
        return "moved_by_editor", here
    if sort and log.get("bin") and sl.rel_bin(log["bin"], shoot_bin) != rel_here[0]:
        return "moved_by_editor", here                        # an older sort that moved the clip itself
    if current and (sort.get("approved") or sort.get("archive_only")):
        return "settled", here                                # a reject or unsure clip: archive only, no copy
    return "new", here


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project", required=True)
    ap.add_argument("--bin", required=True, help="shoot bin, Month/Job/Shoot (no Master/)")
    ap.add_argument("--fp-clips", nargs="+", required=True)
    ap.add_argument("--fp-selects", nargs="+", required=True)
    ap.add_argument("--shotlog")
    ap.add_argument("--out", required=True)
    ap.add_argument("--probe-timeout", type=float, default=15)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--no-audio", action="store_true", help="skip the aroll audio scan (aroll then stays unconfirmed)")
    a = ap.parse_args()
    out = sl.guard_scratch(a.out)
    bin_path = "/".join(sl.bin_parts(a.bin))

    fp_rows = sl.load_fp(a.fp_clips, "clips")
    sel_by = {}
    for s in sl.load_fp(a.fp_selects, "selects"):
        sel_by.setdefault(s["path"], []).append(s)
    if not fp_rows:
        print("Footage Prep clips file is empty: the fp blocks will be null", file=sys.stderr)

    # Resolve: one read pass, then no more calls.
    _, pj, mp = sl.connect(a.project)
    items = read_pool(mp, bin_path)

    excluded, copies, rows, seen = [], {}, [], {}
    for it in items:
        if it["skip_bin"]:
            excluded.append({"name": it["name"], "reason": f"in the {it['skip_bin']!r} bin"})
        elif BAD_TYPES.search(it["type"]) or not it["key"]:
            excluded.append({"name": it["name"], "reason": (it["type"] or "no file").lower()})
        elif str(it["tpm"].get(sl.SORT_COPY_KEY)) == "1":
            copies.setdefault(it["key"], []).append({"uid": it["uid"], "folder": it["folder"], "name": it["name"]})
        elif GYRO_FILE.search(os.path.basename(it["key"])) or "/gyroflow" in it["key"].lower():
            excluded.append({"name": it["name"], "reason": "Gyroflow render"})
        elif "/proxy/" in it["key"].lower():
            excluded.append({"name": it["name"], "reason": "proxy file"})
        elif it["key"] in seen:
            excluded.append({"name": it["name"], "reason": f"second pool item for {os.path.basename(it['key'])}"
                             " (subclip or duplicate import)"})
        else:
            seen[it["key"]] = it
            rows.append(it)

    for k, cs in copies.items():
        if k not in seen:
            excluded += [{"name": c["name"], "reason": f"sort copy in {c['folder']!r}, its original is not in the shoot bin"}
                         for c in cs]
    keys = [r["key"] for r in rows]
    with ThreadPoolExecutor(a.workers) as ex:
        probes = dict(zip(keys, ex.map(lambda k: probe(k, a.probe_timeout), keys)))

    # Subclips: the pool item is clearly shorter than its file.
    for r in list(rows):
        pd = probes[r["key"]].get("duration_s")
        if pd and r["fps"] and r["frames"] and r["frames"] / r["fps"] < pd - max(1.0, 0.05 * pd):
            excluded.append({"name": r["name"], "reason": f"subclip ({r['frames'] / r['fps']:.1f} s of a {pd:.1f} s file)"})
            rows.remove(r)

    fp_by_key, fp_orphans = join_fp([r["key"] for r in rows], fp_rows, {r["key"]: r["tpm"] for r in rows})
    log_idx = shotlog_index(a.shotlog)

    clips = []
    for r in rows:
        k, pr, fr = r["key"], probes[r["key"]], fp_by_key.get(r["key"])
        local = sl.parse_time(pr.get("created"))
        rec = (fr or {}).get("recorded_at") or (local.astimezone().isoformat(timespec="seconds") if local else None)
        dur = pr.get("duration_s") or (fr or {}).get("duration_s") or (round(r["frames"] / r["fps"], 3) if r["fps"] else None)
        state, here = rerun_state(r, log_idx.get(k, {}), copies.get(k, []), bin_path)
        clips.append({"key": k, "name": r["name"], "uid": r["uid"], "folder": r["folder"], "duration_s": dur,
                      "fps": pr.get("fps") or r["fps"] or (fr or {}).get("fps"), "recorded_at": rec,
                      "camera": (fr or {}).get("camera") or r["camera"] or None,
                      "fp": fp_block(fr, sel_by.get(fr["path"], []), set(sl.CLEAN_DROP)) if fr else None,
                      "state": state, "now_in": here if state == "moved_by_editor" else None,
                      "copies": copies.get(k, []), "probe_error": pr.get("error"),
                      "video": pr.get("video", True), "role": None, "audio": None, "excluded_reason": None})

    # Shot log clips that are gone from Resolve.
    present = {c["key"] for c in clips} | set(copies)
    for k, e in log_idx.items():
        if k not in present and (e.get("sort") or e.get("bin")):
            clips.append({"key": k, "name": e.get("clip") or os.path.basename(k), "uid": None, "folder": e.get("bin"),
                          "duration_s": e.get("duration_s"), "fps": None, "recorded_at": None, "camera": e.get("camera"),
                          "fp": None, "state": "missing", "now_in": None, "copies": [], "probe_error": None,
                          "video": True, "role": None, "audio": None, "excluded_reason": None})

    assign_roles([c for c in clips if c["state"] != "missing"], a)
    clips.sort(key=lambda c: (c["recorded_at"] or "9999", c["name"]))
    for c in clips:
        del c["video"]

    in_res_not_fp = [c["name"] for c in clips if c["fp"] is None and c["state"] != "missing"]
    manifest = {"shoot_bin": bin_path, "project": pj.GetName(), "generated_at": sl.now_iso(),
                "sort_v": sl.SORT_V, "clips": clips, "excluded": excluded,
                "mismatches": {"in_resolve_not_fp": in_res_not_fp,
                               "in_fp_not_resolve": [r["path"] for r in fp_orphans]}}
    sl.write_json(out, manifest)
    summary(manifest, out)


def assign_roles(clips, a):
    """Roles by rule, per clip. The audio scan only runs where it decides the role."""
    for c in clips:
        fp, dur = c["fp"] or {}, c["duration_s"] or 0
        c["_aroll_cand"] = dur >= AROLL_MIN_S and fp.get("movement") in ("locked", "steady")
        c["_dark"] = "dark" in (fp.get("flags") or [])
    scan = [c for c in clips if c["video"] and (c["_aroll_cand"] or c["_dark"]) and not a.no_audio]
    with ThreadPoolExecutor(min(4, a.workers)) as ex:
        for c, au in zip(scan, ex.map(lambda c: audio_scan(c["key"]), scan)):
            c["audio"] = au
    for c in clips:
        fp, dur, au = c["fp"] or {}, c["duration_s"] or 0, c["audio"] or {}
        speech = "silence_pct" in au and au["silence_pct"] < 40 and au["mean_db"] > -40
        silent = "error" in au or ("silence_pct" in au and (au["silence_pct"] > 90 or au["mean_db"] < -55))
        tier = fp.get("tier") or fp.get("auto_tier")
        if not c["video"]:
            c["role"] = "audio"
        elif c["_aroll_cand"] and speech:
            c["role"] = "aroll"
        elif dur and dur < JUNK_MAX_S:
            c["role"] = "junk_candidate"
        elif c["_dark"] and silent:
            c["role"] = "junk_candidate"
        elif tier == "reject" and not fp.get("selects") and fp.get("n_selects", 0) == 0:
            c["role"] = "junk_candidate"
        else:
            c["role"] = "broll"
    # multicam_angle: another camera overlapping an aroll clip by >= 30 s.
    span = {}
    for c in clips:
        t = sl.parse_time(c["recorded_at"])
        if t and c["duration_s"]:
            span[c["key"]] = (t.timestamp(), t.timestamp() + c["duration_s"])
    cam = lambda c: (c["camera"] or "", os.path.dirname(c["key"]))
    arolls = [c for c in clips if c["role"] == "aroll" and c["key"] in span]
    for c in clips:
        if c["role"] in ("aroll", "audio") or c["key"] not in span:
            continue
        s0, s1 = span[c["key"]]
        for ar in arolls:
            a0, a1 = span[ar["key"]]
            if cam(ar) != cam(c) and min(s1, a1) - max(s0, a0) >= MULTICAM_MIN_S:
                c["role"] = "multicam_angle"
                break
    for c in clips:
        c.pop("_aroll_cand"); c.pop("_dark")


def summary(m, out):
    from collections import Counter
    cl = m["clips"]
    print(f"{len(cl)} clips in {m['shoot_bin']} ({m['project']}), {len(m['excluded'])} excluded")
    print("state:", dict(Counter(c["state"] for c in cl)))
    print("role: ", dict(Counter(c["role"] for c in cl)))
    tiers = Counter(((c["fp"] or {}).get("tier") or (c["fp"] or {}).get("auto_tier") or "no fp") for c in cl)
    print("tier: ", dict(tiers))
    for e in m["excluded"]:
        print(f"  excluded: {e['name']} ({e['reason']})")
    for side, names in m["mismatches"].items():
        if names:
            print(f"  {side}: {len(names)}: {', '.join(names[:12])}{' ...' if len(names) > 12 else ''}")
    errs = [c["name"] for c in cl if c["probe_error"]]
    if errs:
        print(f"  ffprobe failed on {len(errs)}: {', '.join(errs[:12])}")
    if not any(c["state"] == "new" for c in cl):
        print("nothing to sort")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
