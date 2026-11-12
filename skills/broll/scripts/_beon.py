"""Shared bits for the B-roll scripts: intake settings (house-rules/scripts/beon_config.py) and clip lookup.
Stdlib only, so every script's --help works on stock python3."""
import os, sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "house-rules" / "scripts"))
import beon_config as bc  # noqa: E402

VIDEO_EXT = (".mp4", ".mov", ".mxf", ".m4v", ".mts", ".avi", ".mkv")
FUSION_SCRIPTS = "~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts"


def add_delivery_args(ap, fps=True, size=True):
    """--card PATH (job card: client profile delivery + card Delivery line), --fps, --size WxH."""
    ap.add_argument("--card", help="job card; delivery size/fps from it (bc.delivery). Default 9:16 1080x1920 24p")
    if fps:
        ap.add_argument("--fps", type=float, help="timeline fps (overrides --card)")
    if size:
        ap.add_argument("--size", help="delivery WxH, e.g. 1080x1920 (overrides --card)")


def delivery(a):
    """{'width','height','fps','aspect'} from --card, then --size/--fps. Defaults: 1080x1920 24p (Beon)."""
    d = bc.delivery(getattr(a, "card", None)) if getattr(a, "card", None) else dict(bc.DEFAULT_DELIVERY)
    if getattr(a, "size", None):
        w, h = a.size.lower().replace("×", "x").split("x")
        d["width"], d["height"] = int(w), int(h)
    if getattr(a, "fps", None):
        d["fps"] = a.fps
    d["fps"] = float(d.get("fps") or 24)
    return d


def is_vertical_916(d):
    return d["width"] * 16 == d["height"] * 9


def _walk(root):
    for dp, dn, fn in os.walk(root):
        dn[:] = [x for x in dn if not x.startswith((".", "_claude", "_shotlog"))]
        for f in fn:
            if not f.startswith("._") and f.lower().endswith(VIDEO_EXT):
                yield os.path.join(dp, f)


_INDEX = {}


def find_clip(root, clip, prefix=""):
    """Path of a clip. Accepts an existing path, a path relative to the shoot or clip folder
    ('A001/C0012.MP4'), a file name with any video extension in any case, or a stem ('C0012',
    also found as '<prefix>C0012' or '<anything>_C0012' anywhere under root). Exits with a clear message."""
    clip = str(clip)
    for p in ([clip] + ([os.path.join(root, clip)] if root else [])):
        p = os.path.expanduser(p)
        if os.path.isfile(p):
            return p
    if not root:
        raise SystemExit(f"{clip}: not found (give the shoot or clip folder)")
    root = os.path.expanduser(root)
    stem = os.path.splitext(os.path.basename(clip))[0] if clip.lower().endswith(VIDEO_EXT) else os.path.basename(clip)
    sub = os.path.dirname(clip)
    base = os.path.join(root, sub) if sub else root
    if os.path.isdir(base):                                   # same folder, other extension or case
        for f in sorted(os.listdir(base)):
            s, e = os.path.splitext(f)
            if e.lower() in VIDEO_EXT and not f.startswith("._") and s.lower() in (stem.lower(), (prefix + stem).lower()):
                return os.path.join(base, f)
    if root not in _INDEX:
        _INDEX[root] = sorted(_walk(root))
    want = {stem.lower(), (prefix + stem).lower()}
    hits = [p for p in _INDEX[root] if os.path.splitext(os.path.basename(p))[0].lower() in want]
    if not hits and not prefix:
        hits = [p for p in _INDEX[root]
                if os.path.splitext(os.path.basename(p))[0].lower().endswith(("_" + stem.lower(), "." + stem.lower()))]
    if len(hits) > 1:
        raise SystemExit(f"{clip}: {len(hits)} files match under {root} ({', '.join(hits[:3])}...): "
                         "give the path relative to the shoot, e.g. A001/C0012.MP4")
    if not hits:
        raise SystemExit(f"{clip}: no video file under {root}")
    return hits[0]


def clip_stem(clip):
    b = os.path.basename(str(clip))
    return os.path.splitext(b)[0] if b.lower().endswith(VIDEO_EXT) else b


def gyroflow_installed(ed=None):
    """editor.json tools.gyroflow.installed; missing = installed (the owner's default setup)."""
    g = ((ed or bc.load_editor()).get("tools") or {}).get("gyroflow") or {}
    return g.get("installed", True) is not False


def footage_prep_enabled(ed=None):
    """editor.json tools.footage_prep.enabled; missing = off (intake.md default)."""
    f = ((ed or bc.load_editor()).get("tools") or {}).get("footage_prep") or {}
    return f.get("enabled") is True


def gyroflow_script(ed=None):
    g = ((ed or bc.load_editor()).get("tools") or {}).get("gyroflow") or {}
    p = g.get("stabilize_script") or "<Fusion Scripts>/Utility/Gyroflow Stabilize Flagged.py"
    return os.path.expanduser(p.replace("<Fusion Scripts>", FUSION_SCRIPTS))
