"""Shared helpers for the footage sort scripts (sort_inventory.py, sort_group.py, sort_apply.py).

Import it from a script in the same folder:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _sortlib as sl

What is here:
- guard_scratch(path): refuse to write inside Dropbox or a shot log folder, symlinks resolved.
  Every scratch output goes through it.
- read_json / write_json: small JSON io. write_json is atomic (temp file, then rename) and guarded.
- load_fp(paths, key): read saved Footage Prep MCP output (clips or selects), one or more pages.
- connect(project): reach the running Resolve from an external python, refuse a different project.
  It never switches projects or timelines.
- find_folder / walk / rel_bin: find a bin by "Month/Job/Shoot", walk it, and give a bin path
  relative to the shoot bin (what the shot log stores in sort_copy.bin).
- online_only(path): True for a cloud placeholder file (reading it would download it).
- ffprobe(path): creation_time, duration, fps and stream kinds, with a timeout.
- now_iso() and parse_time(text) for ISO times.

Stdlib only (plus ffprobe on PATH)."""
import csv, io, json, math, os, subprocess, sys, tempfile
from datetime import datetime, timezone

SORT_V = "0.3"                 # sort block version in the shot log
SORT_COPY_KEY = "beon.sort_copy"  # third-party metadata set on every copy in a sorted bin
SORT_SRC_KEY = "beon.sort_src"    # on a copy: the UniqueId of its original in the archive (shoot) bin
REFUSE = ("CloudStorage/Dropbox", "/Dropbox", "_shotlog")
CLEAN_DROP = ("shaky", "whip", "motion_blur", "blocked")  # select flags that make a select unclean


# ---------- paths and json ----------
def guard_scratch(path):
    """Return the absolute path, or exit if it points into Dropbox or a _shotlog folder.
    Symlinks are resolved first (realpath), so a link in scratch that points into Dropbox is refused too."""
    p = os.path.abspath(os.path.expanduser(str(path)))
    for q in (p, os.path.realpath(p)):
        for bad in REFUSE:
            if bad in q:
                raise SystemExit(f"refusing to write {q!r}: scratch output never goes in Dropbox or _shotlog")
    return p


def read_json(path, default=None):
    """Read JSON, or return default when the file is missing (default None means the file must exist)."""
    if not os.path.exists(path):
        if default is not None:
            return default
        raise SystemExit(f"missing {path}")
    with open(path) as f:
        return json.load(f)


def write_json(path, obj):
    """Atomic, guarded JSON write. Creates the folder."""
    p = guard_scratch(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
    os.replace(tmp, p)
    return p


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_fp(paths, key):
    """Rows from saved Footage Prep output. key is 'clips' or 'selects'.
    Accepts the MCP result object ({key: [...]}), a bare list, or several pages (list of paths)."""
    if isinstance(paths, str):
        paths = [paths]
    rows = []
    for p in paths:
        d = read_json(p)
        if isinstance(d, dict) and "structuredContent" in d:
            d = d["structuredContent"]
        rows += d.get(key, []) if isinstance(d, dict) else d
    return rows


# ---------- Resolve ----------
API = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting"
LIB = "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"


def connect(project):
    """(resolve, project, media_pool). Refuses when the open project is not `project`. Never switches."""
    os.environ.setdefault("RESOLVE_SCRIPT_API", API)
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", LIB)
    if API + "/Modules" not in sys.path:
        sys.path.append(API + "/Modules")
    import DaVinciResolveScript as dvr
    resolve = dvr.scriptapp("Resolve")
    if not resolve:
        raise SystemExit("cannot reach Resolve (Studio running? Preferences > General > External scripting = Local)")
    pj = resolve.GetProjectManager().GetCurrentProject()
    if not pj or pj.GetName() != project:
        raise SystemExit(f"open project is {pj.GetName() if pj else None!r}, expected {project!r}: stopping")
    return resolve, pj, pj.GetMediaPool()


def bin_parts(bin_path):
    """'Master/Month/Job/Shoot' or 'Month/Job/Shoot' -> ['Month', 'Job', 'Shoot']."""
    parts = [p for p in bin_path.strip("/").split("/") if p]
    return parts[1:] if parts and parts[0] == "Master" else parts


def find_folder(media_pool, bin_path, required=True):
    """The Folder at bin_path under Master. Missing: exit, or None when required is False."""
    f = media_pool.GetRootFolder()
    for name in bin_parts(bin_path) if isinstance(bin_path, str) else bin_path:
        hit = [s for s in (f.GetSubFolderList() or []) if s.GetName() == name]
        if not hit:
            if not required:
                return None
            raise SystemExit(f"no bin {name!r} under {f.GetName()!r} (looking for {bin_path!r})")
        f = hit[0]
    return f


def walk(folder, path):
    """Yield (folder, path) for folder and every subfolder, depth first. path has no 'Master/'."""
    yield folder, path
    for s in folder.GetSubFolderList() or []:
        yield from walk(s, f"{path}/{s.GetName()}")


def rel_bin(path, shoot_bin):
    """A bin path relative to the shoot bin: 'Month/Job/Shoot/01 Park' -> '01 Park', the shoot bin -> ''.
    A path outside the shoot bin comes back whole (below Master)."""
    p, s = "/".join(bin_parts(path or "")), "/".join(bin_parts(shoot_bin))
    if p == s:
        return ""
    return p[len(s) + 1:] if p.startswith(s + "/") else p


# ---------- media ----------
def online_only(path):
    """True when the file is a cloud placeholder (reading it would download it)."""
    try:
        st = os.stat(path)
        return st.st_size > 1_000_000 and st.st_blocks * 512 < st.st_size * 0.5
    except OSError:
        return False


def ffprobe(path, timeout=15):
    """{'created', 'duration_s', 'fps', 'video', 'audio'} or {'error': text}. Never raises."""
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
                           capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        j = json.loads(r.stdout or "{}")
    except subprocess.TimeoutExpired:
        return {"error": f"ffprobe timed out after {timeout} s"}
    except (OSError, ValueError) as e:
        return {"error": str(e)}
    if not j:
        return {"error": (r.stderr or "no ffprobe output").strip()[:200]}
    fmt, streams = j.get("format", {}), j.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    fps = None
    if v and v.get("r_frame_rate", "0/0") != "0/0":
        n, d = v["r_frame_rate"].split("/")
        fps = round(float(n) / max(1.0, float(d)), 3)
    created = (fmt.get("tags") or {}).get("creation_time") or (v or {}).get("tags", {}).get("creation_time")
    return {"created": created, "duration_s": round(float(fmt.get("duration") or 0), 3) or None, "fps": fps,
            "video": v is not None, "audio": any(s.get("codec_type") == "audio" for s in streams)}


def parse_time(s):
    """ISO time (with Z or offset) -> aware datetime, or None."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


# ---- shotlog.csv (same bytes as Footage Prep's fp-shotlog csv.rs: 8 skill columns, then fp_*) ----
CSV_HEADER = ["clip", "camera", "fps", "duration_s", "content", "people", "notes", "usage",
              "fp_tier", "fp_score", "fp_move", "fp_stab", "fp_selects"]


def _cell(v):
    if v is None:
        return ""
    if v is True:
        return "True"
    if v is False:
        return "False"
    if isinstance(v, float) and not math.isfinite(v):
        return "NaN" if v != v else ("Infinity" if v > 0 else "-Infinity")
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, list):
        return ", ".join(_cell(x) for x in v)
    if isinstance(v, dict):
        return json.dumps(v, indent=1)
    return str(v)


def _sel_time(x):
    return str(int(x)) if float(x).is_integer() and abs(x) < 1e16 else repr(float(x))


def _truthy(v):
    return v is not None and v != ""


def csv_text(log):
    """shotlog.json -> shotlog.csv text: Python csv excel dialect, CRLF, minimal quoting."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")
    w.writerow(CSV_HEADER)
    for e in log.get("clips") or []:
        usage = "; ".join(f"{_cell(u.get('timeline'))} {_cell(u.get('slot'))} {_cell(u.get('src_in'))}-{_cell(u.get('src_out'))}"
                          for u in (e.get("usage") or []) if isinstance(u, dict))
        fp = e.get("footage_prep") or {}
        stab = fp.get("stab") or {}
        stab_text = next((_cell(stab[k]) for k in ("status", "mode") if isinstance(stab, dict) and _truthy(stab.get(k))), "")
        sels = "; ".join(f"{_sel_time(s['in']) if isinstance(s.get('in'), (int, float)) else ''}-"
                         f"{_sel_time(s['out']) if isinstance(s.get('out'), (int, float)) else ''} "
                         f"{next((_cell(s[k]) for k in ('tier', 'kind') if _truthy(s.get(k))), '')}"
                         for s in (fp.get("segments") or []))
        w.writerow([_cell(e.get(k)) for k in ("clip", "camera", "fps", "duration_s", "content", "people", "notes")]
                   + [usage, _cell(fp.get("tier")), _cell(fp.get("score")), _cell(fp.get("move")), stab_text, sels])
    return buf.getvalue()


def write_csv_next_to(shotlog_path):
    """Regenerate shotlog.csv beside shotlog.json, atomically. Returns the csv path."""
    p = os.path.abspath(os.path.expanduser(shotlog_path))
    with open(p) as fh:
        log = json.load(fh)
    out = os.path.join(os.path.dirname(p), "shotlog.csv")
    fd, tmp = tempfile.mkstemp(prefix=".shotlog.", suffix=".csv.tmp", dir=os.path.dirname(p))
    with os.fdopen(fd, "w", newline="") as fh:
        fh.write(csv_text(log))
    os.replace(tmp, out)
    return out
