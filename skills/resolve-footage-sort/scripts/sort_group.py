#!/usr/bin/env python3
"""Footage sort, SKILL.md step 4: sessions, setups, take families, then frames and contact sheets.
usage: python3 sort_group.py SCRATCH/manifest.json --out SCRATCH/ [--jobs 5] [--timeout 90]
           [--prefer /Volumes/<drive>/Raws] [--all]

Reads manifest.json (from the manifest step) and writes, inside --out:
  groups.json            sessions, setups, sheets and strips (the groups.json contract), plus
                         clip_setup (per clip: session, setup, keyframe_s, d_prev, dup_of) and errors.
                         Old sheet_*, strips_* and strips/*.jpg in --out are cleared first.
  sheets/sheet_N.jpg     5x5 cells of 320x180, one frame per setup leader, strict manifest order,
                         a black cell at each session break; the cell number and camera clip number
                         are burned into the top left corner
  sheets/sheet_N.map.json  per cell: clip, File Path, frame time, setup, session, tier, movement, score
  sheets/strips_N.jpg    leaders that need 3 frames (select in, mid, out), one strip per row
  strips/<clip>.jpg      the single 3 frame strip of each of those leaders

Which clips: state "new", no excluded_reason and role not "audio" (--all takes every clip with video).
  Online-only (cloud placeholder) and missing files are skipped and listed in errors, so nothing downloads.
Sessions: an idle gap (start of a clip minus the end of the one before) over 300 s starts a new one.
Keyframe: middle of the best clean select (highest score with stability >= 0.75, else the best select),
  clip middle when there is no select.
Setups: 32x18 gray frame at the keyframe (area downscale and a blur first, so grain and small moves
  count less), z-normalised, mean absolute difference d to each of the last 3 clips in the session; the
  closest one counts. d < 0.35 and gap < 90 s = same setup (a member, never its own setup); 0.35 to 0.8
  (or d < 0.35 after a longer gap) = a new setup with band "maybe" and maybe_of = the closest setup, for
  Claude to merge or keep on the sheet; over 0.8 = band "new". FP duplicate_of joins the setup of that
  clip. A setup is a take family: leader = highest FP best_score, the rest dup_of it. On the test shoot
  true retakes measured 0.10 to 0.25, and other shots of the same thing (reframed, moved) 0.6 to 0.8,
  which overlaps different shots of one street (0.48 to 0.8). That is why the maybe band is wide.
Strips: FP movement pan, tilt, pan_tilt or gimbal, handheld with more than one movement chip (FP chips
  minus "shaky", for example locked_off plus handheld), or > 30 s. Up to 8 strips per strips_N sheet.
Sanity: the first and last cell of every sheet are cut back out and compared to their tiles. A mismatch
  regenerates the sheet once, then stops with an error.
Colour histograms are never used (useless on flat S-Log3). Stdlib python and plain ffmpeg only.
Source files are only read. Output paths inside Dropbox, editor.json synced_folders or _shotlog are refused."""
import argparse, math, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _sortlib as sl

SESSION_GAP_S = 300
SAME_D, NEW_D, SAME_GAP_S, LOOKBACK = 0.35, 0.8, 90, 3
CLEAN_STAB = 0.75
FP_W, FP_H = 32, 18
FP_FILTER = f"scale=128:72:flags=area,gblur=sigma=3,scale={FP_W}:{FP_H}:flags=area,format=gray"
TW, TH = 320, 180
COLS, ROWS = 5, 5
STRIPS_PER_SHEET = 8
STRIP_MOVES = {"pan", "tilt", "pan_tilt", "gimbal"}
LOOK = "eq=contrast=1.25:saturation=1.35"
FIT = f"scale={TW}:{TH}:force_original_aspect_ratio=decrease,pad={TW}:{TH}:(ow-iw)/2:(oh-ih)/2"


# ---------- timing, keyframes, distance ----------

def start_ts(c):
    try:
        return datetime.fromisoformat(c["recorded_at"]).timestamp()
    except (KeyError, TypeError, ValueError):
        return None


def best_select(c):
    sel = (c.get("fp") or {}).get("selects") or []
    clean = [s for s in sel if (s.get("stability") or 0) >= CLEAN_STAB]
    pool = clean or sel
    return max(pool, key=lambda s: s.get("score") or 0) if pool else None


def keyframe(c):
    dur = float(c.get("duration_s") or 0)
    s = best_select(c)
    t = (s["in_s"] + s["out_s"]) / 2 if s else dur / 2
    return round(max(0.0, min(t, dur - 0.1)), 3)


def strip_times(c):
    dur = float(c.get("duration_s") or 0)
    s = best_select(c)
    a, b = (s["in_s"], s["out_s"]) if s else (dur * 0.1, dur * 0.9)
    a, b = a + 0.1, max(a + 0.1, b - 0.1)
    return [round(max(0.0, min(t, dur - 0.1)), 3) for t in (a, (a + b) / 2, b)]


def needs_strip(c):
    fp = c.get("fp") or {}
    mv = fp.get("movement") or ""
    chips = set(fp.get("chips") or []) - {"shaky"}
    return mv in STRIP_MOVES or (mv == "handheld" and len(chips) > 1) or float(c.get("duration_s") or 0) > 30


def znorm(px):
    n = len(px)
    m = sum(px) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in px) / n) or 1.0
    return [(v - m) / sd for v in px]


def dist(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


# ---------- ffmpeg ----------

def run(cmd, timeout):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else None
    except subprocess.TimeoutExpired:
        return None


def grab(src, t, tile_path, timeout):
    """One decode: 32x18 gray fingerprint to the pipe and a 320x180 rgb24 tile to a file."""
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", src,
           "-filter_complex", f"[0:v]split[a][b];[a]{FP_FILTER}[g];[b]{FIT},{LOOK},format=rgb24[t]",
           "-map", "[g]", "-frames:v", "1", "-f", "rawvideo", "pipe:1",
           "-map", "[t]", "-frames:v", "1", "-f", "rawvideo", tile_path]
    out = run(cmd, timeout)
    if not out or len(out) < FP_W * FP_H or not os.path.exists(tile_path):
        return None
    return znorm(list(out[:FP_W * FP_H]))


def grab_tile(src, t, tile_path, timeout):
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", src,
           "-vf", f"{FIT},{LOOK},format=rgb24", "-frames:v", "1", "-f", "rawvideo", tile_path]
    return run(cmd, timeout) is not None and os.path.getsize(tile_path) == TW * TH * 3


def decode_rgb(path, timeout=60):
    return run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"], timeout)


# ---------- tiles and labels ----------

FONT = {  # 3x5 pixel digits
    "0": "111101101101111", "1": "010110010010111", "2": "111001111100111", "3": "111001111001111",
    "4": "101101111001001", "5": "111100111001111", "6": "111100111101111", "7": "111001001001001",
    "8": "111101111101111", "9": "111101111001111", " ": "000000000000000"}


def burn(raw, text, scale=3):
    """Burn white digits on a black box in the top left corner of a 320x180 rgb24 tile."""
    buf = bytearray(raw)
    w, h = (4 * len(text) + 1) * scale, 7 * scale
    for y in range(h):
        for x in range(w):
            buf[(y * TW + x) * 3:(y * TW + x) * 3 + 3] = b"\x00\x00\x00"
    for i, ch in enumerate(text):
        bits = FONT.get(ch, FONT[" "])
        for r in range(5):
            for col in range(3):
                if bits[r * 3 + col] == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            x = (1 + i * 4 + col) * scale + dx
                            y = (1 + r) * scale + dy
                            buf[(y * TW + x) * 3:(y * TW + x) * 3 + 3] = b"\xff\xff\xff"
    return bytes(buf)


def write_ppm(path, raw, w=TW, h=TH):
    with open(path, "wb") as f:
        f.write(f"P6 {w} {h} 255\n".encode() + raw)


def clip_no(c):
    m = re.findall(r"\d+", os.path.splitext(c.get("name") or "")[0])
    return m[-1][-5:] if m else ""


def xstack(inputs, cols, rows, out, timeout):
    lay = "|".join(f"{(i % cols) * TW}_{(i // cols) * TH}" for i in range(cols * rows))
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y"]
    for p in inputs:
        cmd += ["-i", p]
    cmd += ["-filter_complex", "".join(f"[{i}:v]" for i in range(len(inputs))) +
            f"xstack=inputs={len(inputs)}:layout={lay}", "-frames:v", "1", "-q:v", "3", out]
    return run(cmd, timeout) is not None and os.path.exists(out)


def cell_rgb(sheet_raw, cols, i):
    sw = cols * TW
    x0, y0 = (i % cols) * TW, (i // cols) * TH
    return b"".join(sheet_raw[((y0 + y) * sw + x0) * 3:((y0 + y) * sw + x0 + TW) * 3] for y in range(TH))


def rgb_diff(a, b, step=37):
    n = min(len(a), len(b))
    idx = range(0, n, step)
    return sum(abs(a[i] - b[i]) for i in idx) / max(1, len(idx))


def sanity(sheet, tiles, cols, rows):
    """First and last real cell must match their own tile better than any other tile on the sheet."""
    raw = decode_rgb(sheet)
    if not raw or len(raw) != cols * TW * rows * TH * 3:
        return False
    real = [i for i, t in enumerate(tiles) if t is not None]
    for i in {real[0], real[-1]} if real else ():
        got = cell_rgb(raw, cols, i)
        own = rgb_diff(got, tiles[i])
        if own > 12 or any(rgb_diff(got, tiles[j]) < own for j in real if j != i):
            return False
    return True


def build_sheet(path, cells, tmp, cols, rows, timeout):
    """cells: list of raw rgb24 tiles (None = black). Writes PPMs, xstacks, checks, retries once."""
    black = bytes(TW * TH * 3)
    inputs = []
    for i in range(cols * rows):
        p = os.path.join(tmp, f"{os.path.basename(path)}.{i:02d}.ppm")
        write_ppm(p, cells[i] if i < len(cells) and cells[i] is not None else black)
        inputs.append(p)
    tiles = [cells[i] if i < len(cells) else None for i in range(cols * rows)]
    for _ in range(2):
        if xstack(inputs, cols, rows, path, timeout) and sanity(path, tiles, cols, rows):
            for p in inputs:
                os.remove(p)
            return True
    return False


# ---------- main ----------

def prefer_index(dirs):
    idx = {}
    for d in dirs:
        for root, _, files in os.walk(d):
            for f in files:
                if f.lower().endswith((".mp4", ".mov", ".mxf")):
                    p = os.path.join(root, f)
                    try:
                        idx.setdefault((f, os.path.getsize(p)), p)
                    except OSError:
                        pass
    return idx


def source(c, idx):
    k = c["key"]
    try:
        alt = idx.get((os.path.basename(k), os.path.getsize(k)))
    except OSError:
        alt = None
    return alt or k


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest")
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=5, help="parallel ffmpeg (4 to 6)")
    ap.add_argument("--timeout", type=int, default=90, help="seconds per ffmpeg call")
    ap.add_argument("--prefer", action="append", default=[], help="folder with local copies (same name and size)")
    ap.add_argument("--all", action="store_true", help="take settled and moved clips too")
    a = ap.parse_args()
    jobs = max(4, min(6, a.jobs))

    out = sl.guard_scratch(a.out)
    sheets_dir, strips_dir, tmp = (sl.guard_scratch(os.path.join(out, d)) for d in ("sheets", "strips", "_tiles"))
    for d in (out, sheets_dir, strips_dir, tmp):
        os.makedirs(d, exist_ok=True)
    for d, pat in ((sheets_dir, r"(sheet|strips)_\d+\.(jpg|map\.json)$"), (strips_dir, r"\.jpg$"), (tmp, r".")):
        for f in os.listdir(d):   # a rerun with fewer setups must not leave old sheets behind
            if re.search(pat, f):
                os.remove(os.path.join(d, f))

    man = sl.read_json(a.manifest)
    errors = []
    clips = []
    for c in man["clips"]:
        if c.get("role") == "audio" or c.get("excluded_reason") or not (a.all or c.get("state", "new") == "new"):
            continue
        if c.get("state") == "missing" or not os.path.exists(c["key"]):
            errors.append({"clip_key": c["key"], "error": "file not found, skipped"})
        elif "online-only" in (c.get("probe_error") or "") or sl.online_only(c["key"]):
            errors.append({"clip_key": c["key"], "error": "online-only file, skipped (make it available offline)"})
        else:
            clips.append(c)
    order = {c["key"]: i for i, c in enumerate(man["clips"])}
    clips.sort(key=lambda c: (start_ts(c) is None, start_ts(c) or 0, order[c["key"]]))
    if not clips:
        print("nothing to group")
        return
    idx = prefer_index(a.prefer)

    # sessions
    sessions, prev_end, gaps = [], None, {}
    for c in clips:
        st = start_ts(c)
        gap = None if st is None or prev_end is None else st - prev_end
        gaps[c["key"]] = gap
        if not sessions or (gap is not None and gap > SESSION_GAP_S):
            sessions.append({"id": f"sess-{len(sessions) + 1:02d}", "clip_keys": []})
        sessions[-1]["clip_keys"].append(c["key"])
        if st is not None:
            prev_end = max(prev_end or 0, st + float(c.get("duration_s") or 0))
    sess_of = {k: s["id"] for s in sessions for k in s["clip_keys"]}

    # fingerprints and tiles, one decode per clip
    kf = {c["key"]: keyframe(c) for c in clips}
    tile_path = {c["key"]: os.path.join(tmp, f"{i:04d}.rgb") for i, c in enumerate(clips)}

    def fp_job(c):
        return grab(source(c, idx), kf[c["key"]], tile_path[c["key"]], a.timeout)

    with ThreadPoolExecutor(jobs) as ex:
        prints = dict(zip((c["key"] for c in clips), ex.map(fp_job, clips)))
    for c in clips:
        if prints[c["key"]] is None:
            errors.append({"clip_key": c["key"], "error": "frame grab failed or timed out"})

    # setups
    by_name = {}
    for c in clips:
        for n in (c.get("name"), (c.get("fp") or {}).get("clip_path"), os.path.basename(c["key"])):
            if n:
                by_name.setdefault(n, c["key"])
    setups, setup_of, d_prev = [], {}, {}
    for i, c in enumerate(clips):
        k = c["key"]
        prev = clips[i - 1]["key"] if i else None
        # closest of the last LOOKBACK clips in the same session (a retake can come after another shot)
        back = [clips[j]["key"] for j in range(max(0, i - LOOKBACK), i) if sess_of[clips[j]["key"]] == sess_of[k]]
        cand = [(round(dist(prints[k], prints[b]), 3), b) for b in back if prints[k] is not None and prints[b] is not None]
        d, near = min(cand) if cand else (None, None)
        d_prev[k] = d
        gap = gaps[k]
        dup = (c.get("fp") or {}).get("duplicate_of")
        join = None
        if dup and by_name.get(dup) in setup_of and sess_of[by_name[dup]] == sess_of[k]:
            join = setup_of[by_name[dup]]
        elif d is not None and d < SAME_D and (gap is None or gap < SAME_GAP_S):
            join = setup_of[near]
        if join is not None:
            setups[join]["member_keys"].append(k)
        else:
            maybe = d is not None and d <= NEW_D
            setups.append({"id": f"setup-{len(setups) + 1:03d}", "session": sess_of[k], "leader_key": k,
                           "member_keys": [k], "keyframe_s": kf[k], "d_prev": d, "band": "maybe" if maybe else "new",
                           "maybe_of": setups[setup_of[near]]["id"] if maybe else None})
            join = len(setups) - 1
        setup_of[k] = join
    by_key = {c["key"]: c for c in clips}
    for s in setups:
        lead = max(s["member_keys"], key=lambda k: (by_key[k].get("fp") or {}).get("best_score") or 0)
        s["leader_key"], s["keyframe_s"] = lead, kf[lead]
    clip_setup = {}
    for c in clips:
        s = setups[setup_of[c["key"]]]
        clip_setup[c["key"]] = {"session": s["session"], "setup": s["id"], "keyframe_s": kf[c["key"]],
                                "d_prev": d_prev[c["key"]], "gap_s": None if gaps[c["key"]] is None else round(gaps[c["key"]], 1),
                                "dup_of": None if c["key"] == s["leader_key"] else s["leader_key"]}

    # contact sheets of setup leaders, black cell at each session break
    seq, last_sess = [], None
    for s in setups:
        if last_sess is not None and s["session"] != last_sess:
            seq.append(None)
        seq.append(s)
        last_sess = s["session"]
    per = COLS * ROWS
    pages = [seq[i:i + per] for i in range(0, len(seq), per)]
    sheets = []
    for n, page in enumerate(pages, 1):
        while page and page[0] is None:  # a break cell never opens a sheet
            page = page[1:]
        if not page:
            continue
        cells, cmap = [], []
        for ci, s in enumerate(page):
            if s is None:
                cells.append(None)
                cmap.append({"cell": ci + 1, "black": True, "note": "session break"})
                continue
            c = by_key[s["leader_key"]]
            fp = c.get("fp") or {}
            raw = None
            if os.path.exists(tile_path[c["key"]]) and os.path.getsize(tile_path[c["key"]]) == TW * TH * 3:
                raw = burn(open(tile_path[c["key"]], "rb").read(), f"{ci + 1:02d} {clip_no(c)}")
            cells.append(raw)
            bs = best_select(c)
            cmap.append({"cell": ci + 1, "clip": c.get("name"), "key": c["key"], "uid": c.get("uid"),
                         "frame_s": s["keyframe_s"], "setup": s["id"], "session": s["session"],
                         "members": len(s["member_keys"]), "band": s["band"], "maybe_of": s["maybe_of"],
                         "d_prev": s["d_prev"],
                         "role": c.get("role"), "tier": fp.get("tier") or fp.get("auto_tier"),
                         "movement": fp.get("movement"), "select_score": bs and round(bs.get("score") or 0, 1),
                         "flags": fp.get("flags") or [], "missing_frame": raw is None})
        rows = math.ceil(len(page) / COLS)
        f = os.path.join(sheets_dir, f"sheet_{n}.jpg")
        if not build_sheet(f, cells, tmp, COLS, rows, a.timeout):
            sys.exit(f"sheet {f} failed its first/last cell check twice; nothing more written")
        mf = os.path.join(sheets_dir, f"sheet_{n}.map.json")
        sl.write_json(mf, {"sheet": f, "cols": COLS, "rows": rows, "cell_px": [TW, TH], "cells": cmap})
        sheets.append({"file": f, "map_file": mf})

    # strips: 3 frames of each leader that moves or runs long
    want = [by_key[s["leader_key"]] for s in setups if needs_strip(by_key[s["leader_key"]])]

    def strip_job(c):
        ts = strip_times(c)
        paths = [f"{tile_path[c['key']]}.s{j}" for j in range(3)]
        ok = all(grab_tile(source(c, idx), t, p, a.timeout) for t, p in zip(ts, paths))
        return c, ts, (paths if ok else None)

    strips, strip_rows = [], []
    with ThreadPoolExecutor(jobs) as ex:
        for c, ts, paths in ex.map(strip_job, want):
            if not paths:
                errors.append({"clip_key": c["key"], "error": "strip grab failed or timed out"})
                continue
            raws = [open(p, "rb").read() for p in paths]
            stem = re.sub(r"[^\w.-]+", "_", os.path.splitext(c.get("name") or "clip")[0])
            f = os.path.join(strips_dir, f"{stem}.jpg")
            if build_sheet(f, raws, tmp, 3, 1, a.timeout):
                strips.append({"clip_key": c["key"], "file": f})
                strip_rows.append((c, ts, raws))
            else:
                errors.append({"clip_key": c["key"], "error": "strip failed its check"})
    for n in range(0, len(strip_rows), STRIPS_PER_SHEET):
        chunk = strip_rows[n:n + STRIPS_PER_SHEET]
        cells, cmap = [], []
        for r, (c, ts, raws) in enumerate(chunk):
            for j in range(3):
                cells.append(burn(raws[j], f"{r + 1:02d} {clip_no(c)}") if j == 0 else raws[j])
            s = setups[setup_of[c["key"]]]
            cmap.append({"row": r + 1, "clip": c.get("name"), "key": c["key"], "uid": c.get("uid"), "frames_s": ts,
                         "setup": s["id"], "session": s["session"], "role": c.get("role"),
                         "tier": (c.get("fp") or {}).get("tier") or (c.get("fp") or {}).get("auto_tier"),
                         "movement": (c.get("fp") or {}).get("movement")})
        k = n // STRIPS_PER_SHEET + 1
        f = os.path.join(sheets_dir, f"strips_{k}.jpg")
        if not build_sheet(f, cells, tmp, 3, len(chunk), a.timeout):
            sys.exit(f"strip sheet {f} failed its first/last cell check twice")
        mf = os.path.join(sheets_dir, f"strips_{k}.map.json")
        sl.write_json(mf, {"sheet": f, "cols": 3, "rows": len(chunk), "cell_px": [TW, TH], "rows_map": cmap})
        sheets.append({"file": f, "map_file": mf})

    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    groups = {"sessions": sessions, "setups": setups, "sheets": sheets, "strips": strips,
              "clip_setup": clip_setup, "errors": errors,
              "thresholds": {"session_gap_s": SESSION_GAP_S, "same_d": SAME_D, "new_d": NEW_D,
                             "same_gap_s": SAME_GAP_S, "lookback": LOOKBACK}}
    gp = sl.write_json(os.path.join(out, "groups.json"), groups)
    bands = {b: sum(s["band"] == b for s in setups) for b in ("new", "maybe")}
    print(f"{len(clips)} clips, {len(sessions)} sessions, {len(setups)} setups ({bands['maybe']} maybe), "
          f"{len(sheets)} sheets, {len(strips)} strips, {len(errors)} errors -> {gp}")


if __name__ == "__main__":
    main()
