"""Shared reader for the beon-edit intake files (skills/house-rules/references/intake.md).

Stdlib only, so hooks and scripts on stock python3 can import it. Never writes anything.

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "house-rules" / "scripts"))
    import beon_config as bc

Files:
  1. editor setup   ~/.beon-edit/editor.json   (BEON_HOME overrides ~/.beon-edit; old config.json is read as a fallback)
  2. client profile skills/client-styles/references/<slug>.md, YAML front matter
  3. shoot          <shoot>/_shotlog/shotlog.json, top-level "shoot" block
  4. job card       <shoot>/_shotlog/jobs/<concept>.md (session copy in ~/.beon-edit/jobs/<session_id>.md)

CLI:  python3 beon_config.py show [--card PATH] [--client SLUG] [--shoot FOLDER]
"""
import json
import os
import re
import sys
from pathlib import Path

HOME = Path(os.path.expanduser(os.environ.get("BEON_HOME", "~/.beon-edit")))
JOBS = Path(os.path.expanduser(os.environ.get("BEON_JOBS_DIR", str(HOME / "jobs"))))
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
PROFILES = PLUGIN_ROOT / "skills" / "client-styles" / "references"

DEFAULT_DELIVERY = {"aspect": "9:16", "width": 1080, "height": 1920, "fps": 24,
                    "loudness_lufs": None, "true_peak_db": None}

EDITOR_DEFAULTS = {
    "name": None, "aliases": [], "plugin_owner": False, "plugin_repo": "~/code/beon-edit",
    "footage_roots": [], "synced_folders": [], "scratch_root": "~/work",
    "run_env": {"mode": "local"}, "resolve": {}, "tools": {}, "rules_page": None,
}

# Card lines the hook requires, per Kind (intake.md section 4).
REQUIRED = {
    "concept": ["Editor", "Client", "Shoot", "Concept", "Resolve project", "Timelines", "Grilling",
                "Brief", "Concept and goal", "Target length", "Story beats / answers to use",
                "Speakers", "Stages", "Delivery"],
    "montage": ["Editor", "Client", "Shoot", "Concept", "Resolve project", "Timelines", "Grilling",
                "Brief", "Concept and goal", "Target length", "Stages", "Delivery"],
}
REQUIRED_OTHER = ["Editor", "Client", "Shoot", "Resolve project", "Grilling"]
KINDS = ("concept", "montage", "footage-sort", "subtitles-only", "grade-only", "fix")


# ---------------------------------------------------------------- editor setup
def load_editor():
    """editor.json merged over defaults. Falls back to the old config.json (repo, tim_names, rules_page)."""
    ed = json.loads(json.dumps(EDITOR_DEFAULTS))
    old = HOME / "config.json"
    if old.exists():
        try:
            c = json.loads(old.read_text())
            if c.get("repo"):
                ed["plugin_repo"] = c["repo"]
            if c.get("tim_names"):
                ed["aliases"] = list(c["tim_names"])
            if c.get("rules_page"):
                ed["rules_page"] = c["rules_page"]
        except (OSError, ValueError):
            pass
    p = HOME / "editor.json"
    if p.exists():
        try:
            ed.update(json.loads(p.read_text()))
        except (OSError, ValueError) as e:
            sys.stderr.write(f"beon_config: can't read {p}: {e}\n")
    ed["exists"] = p.exists()
    return ed


def norm_name(s):
    return " ".join((s or "").lower().split())


def editor_names(ed=None):
    ed = ed or load_editor()
    names = {norm_name(n) for n in ed.get("aliases") or []}
    if ed.get("name"):
        names.add(norm_name(ed["name"]))
    return names


def is_this_editor(name, ed=None):
    return norm_name(name) in editor_names(ed)


def is_plugin_owner(ed=None):
    return bool((ed or load_editor()).get("plugin_owner"))


def expand(p):
    return Path(os.path.expanduser(str(p))) if p else None


def in_synced_folder(path, ed=None):
    """True if path is inside one of the editor's synced folders (never write media there).
    Dropbox is always refused, whatever editor.json says."""
    ed = ed or load_editor()
    s = str(Path(os.path.expanduser(str(path))).resolve()) if path else ""
    if "dropbox" in s.lower():
        return True
    for f in ed.get("synced_folders") or []:
        fp = str(expand(f).resolve())
        if s == fp or s.startswith(fp.rstrip("/") + "/"):
            return True
    return False


# ---------------------------------------------------------------- tiny YAML (front matter only)
def _scalar(v):
    v = v.strip()
    if v == "":
        return None
    if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    low = v.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~"):
        return None
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d*", v):
        return float(v)
    return v


def _split_top(s, sep=","):
    out, depth, cur, q = [], 0, "", None
    for ch in s:
        if q:
            cur += ch
            if ch == q:
                q = None
            continue
        if ch in "\"'":
            q = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        if ch == sep and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


def _value(v):
    v = v.strip()
    if v.startswith("{") and v.endswith("}"):
        d = {}
        for part in _split_top(v[1:-1]):
            k, _, val = part.partition(":")
            d[k.strip().strip("\"'")] = _value(val)
        return d
    if v.startswith("[") and v.endswith("]"):
        return [_value(x) for x in _split_top(v[1:-1])]
    return _scalar(v)


def parse_front_matter(text):
    """Front matter of the shapes intake.md uses: `key: scalar|{flow map}|[flow list]` and
    `key:` followed by `  - item` lines. Returns ({}, text) when there is none."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    block, body = text[3:end], text[end + 4:]
    data, key = {}, None
    for raw in block.splitlines():
        line = raw.split(" #")[0].rstrip() if " #" in raw and "\"" not in raw else raw.rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith("- ") and key:
            if not isinstance(data.get(key), list):
                data[key] = []
            data[key].append(_value(line.lstrip()[2:]))
            continue
        if not line.startswith(" ") and ":" in line:
            k, _, v = line.partition(":")
            key = k.strip()
            data[key] = _value(v) if v.strip() else None
    return data, body


# ---------------------------------------------------------------- client profile
def profile_path(slug):
    return PROFILES / f"{slug}.md"


def load_client(slug):
    p = profile_path(slug)
    if not slug or not p.exists():
        return {}
    data, _ = parse_front_matter(p.read_text())
    return data


# ---------------------------------------------------------------- shoot
def load_shoot(shoot_folder):
    if not shoot_folder:
        return {}
    p = expand(shoot_folder) / "_shotlog" / "shotlog.json"
    try:
        return json.loads(p.read_text()).get("shoot", {}) or {}
    except (OSError, ValueError):
        return {}


# ---------------------------------------------------------------- job card
LINE = re.compile(r"^\s*(?:[-*]\s+)?\*{0,2}([A-Za-z][A-Za-z /&()-]*?)\*{0,2}\s*:\s*(.*)$")


def parse_card(text):
    """Every `Key: value` and `- Key: value` line, keys as written (first wins)."""
    out = {}
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        m = LINE.match(line)
        if m:
            out.setdefault(m.group(1).strip(), m.group(2).strip())
    return out


def load_card(path):
    p = expand(path)
    return parse_card(p.read_text()) if p and p.exists() else {}


def session_card_path(session_id):
    return JOBS / f"{session_id}.md"


def unfilled(value):
    """Empty, a `<placeholder>` anywhere, or a template option list (`a | b`) left as is."""
    v = (value or "").strip()
    return v == "" or bool(re.search(r"<[^>]+>", v)) or " | " in v


def missing_lines(card):
    """Required lines that are absent or still a placeholder. `n/a` counts as filled."""
    kind = (card.get("Kind") or "").split("|")[0].strip().lower()
    need = REQUIRED.get(kind, REQUIRED_OTHER)
    return [k for k in need if unfilled(card.get(k))]


# ---------------------------------------------------------------- delivery
def _parse_delivery_line(s):
    out = {}
    if not s or s.strip().lower().startswith("as client"):
        return out
    m = re.search(r"(\d+)\s*:\s*(\d+)", s)
    if m:
        out["aspect"] = f"{m.group(1)}:{m.group(2)}"
    m = re.search(r"(\d{3,4})\s*[x×]\s*(\d{3,4})", s)
    if m:
        out["width"], out["height"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d{2}(?:\.\d+)?)\s*(?:p|fps)\b", s)
    if m:
        out["fps"] = float(m.group(1)) if "." in m.group(1) else int(m.group(1))
    m = re.search(r"(-\d+(?:\.\d+)?)\s*LUFS", s, re.I)
    if m:
        out["loudness_lufs"] = float(m.group(1))
    return out


def delivery(card=None, client=None):
    """Plugin default < client profile `delivery` < job card `Delivery:` line."""
    d = dict(DEFAULT_DELIVERY)
    if isinstance(card, (str, Path)):
        card = load_card(card)
    card = card or {}
    slug = client or card.get("Client")
    prof = load_client(slug) if slug else {}
    pd = prof.get("delivery") or {}
    if isinstance(pd, dict):
        for k in ("aspect", "fps", "loudness_lufs", "true_peak_db"):
            if pd.get(k) not in (None, "ask"):
                d[k] = pd[k]
        res = pd.get("resolution")
        if isinstance(res, str) and "x" in res:
            w, h = res.lower().split("x")
            d["width"], d["height"] = int(w), int(h)
    line = _parse_delivery_line(card.get("Delivery"))
    d.update(line)
    if "aspect" in line and "width" not in line:
        # Aspect without a size: 1080 on the short side (1:1 -> 1080x1080, 16:9 -> 1920x1080).
        a, b = (int(x) for x in line["aspect"].split(":"))
        if a >= b:
            d["width"], d["height"] = round(1080 * a / b / 2) * 2, 1080
        else:
            d["width"], d["height"] = 1080, round(1080 * b / a / 2) * 2
    return d


def scratch_dir(client, shoot, concept=None, ed=None):
    ed = ed or load_editor()
    base = expand(ed.get("scratch_root") or "~/work") / f"{client}-{shoot}".replace("/", "-")
    return base / concept if concept else base


# ---------------------------------------------------------------- CLI
def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["show"])
    ap.add_argument("--card")
    ap.add_argument("--client")
    ap.add_argument("--shoot")
    a = ap.parse_args(argv)
    card = load_card(a.card) if a.card else {}
    client = a.client or card.get("Client")
    shoot = a.shoot or card.get("Shoot")
    out = {"editor": load_editor(), "client": load_client(client) if client else {},
           "shoot": load_shoot(shoot), "card": card,
           "card_missing": missing_lines(card) if card else None,
           "delivery": delivery(card, client)}
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main(sys.argv[1:])
