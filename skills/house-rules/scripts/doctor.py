#!/usr/bin/env python3
"""Check an editor's machine for the beon-edit skills (intake.md section 1).

Stdlib only. Only CHECKS and prints JSON: it never writes editor.json or anything else, never asks
questions, and always exits 0. Claude asks the editor the setup questions, runs this, then writes
~/.beon-edit/editor.json itself (using the `detected` block for the Resolve and Gyroflow fields).

    python3 doctor.py                      # check against ~/.beon-edit/editor.json (or defaults)
    python3 doctor.py --editor draft.json  # check a draft before writing it
    python3 doctor.py --footage-root "/Volumes/T7 Shield/Raws" --synced ~/Library/CloudStorage/Dropbox
    python3 doctor.py --text               # pass/warn list for people instead of JSON

Each check: {"name", "status": pass | warn | info, "detail"}. A warn says what is missing and what it
blocks; it never stops the editor from working.
"""
import argparse
import glob
import importlib.util
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import beon_config as bc  # noqa: E402

RESOLVE_APPS = ["/Applications/DaVinci Resolve/DaVinci Resolve.app",
                "/Applications/DaVinci Resolve Studio/DaVinci Resolve.app",
                "~/Applications/DaVinci Resolve/DaVinci Resolve.app"]
RESOLVE_LICENSE_DIR = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/.license"
RESOLVE_CONFIG = "~/Library/Preferences/Blackmagic Design/DaVinci Resolve/config.dat"
FUSION_SCRIPTS = "~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts"
GYROFLOW_APPS = ["/Applications/Gyroflow.app", "~/Applications/Gyroflow.app"]
FONT_DIRS = ["~/Library/Fonts", "/Library/Fonts", "/System/Library/Fonts"]  # last one: macOS built-ins
DEFAULT_FONTS = ["Garet Book"]  # Fluid Reveal Words defaults (Beon shorts look)
MIN_RESOLVE = (21, 1)
PY_PACKAGES = [("numpy", "numpy"), ("cv2", "opencv-python-headless"), ("scipy", "scipy"),
               ("zstandard", "zstandard")]

checks = []
detected = {}


def add(name, status, detail):
    checks.append({"name": name, "status": status, "detail": detail})


def x(p):
    return Path(os.path.expanduser(str(p))) if p else None


def vtuple(s):
    return tuple(int(n) for n in re.findall(r"\d+", s or "")[:3])


# ---------------------------------------------------------------- editor setup
def load(args):
    if args.editor:
        ed = json.loads(json.dumps(bc.EDITOR_DEFAULTS))
        try:
            ed.update(json.loads(x(args.editor).read_text()))
            add("editor.json", "info", f"checking draft {args.editor}")
        except (OSError, ValueError) as e:
            add("editor.json", "warn", f"can't read draft {args.editor}: {e}")
        ed["exists"] = True
    else:
        ed = bc.load_editor()
        p = bc.HOME / "editor.json"
        if ed.get("exists"):
            add("editor.json", "pass", f"{p} (editor: {ed.get('name') or 'no name'})")
        else:
            add("editor.json", "warn", f"{p} missing: Claude asks the setup questions (intake.md section 1) and writes it")
    if args.footage_root:
        ed["footage_roots"] = [{"path": r} for r in args.footage_root]
    if args.synced:
        ed["synced_folders"] = list(args.synced)
    if args.whisper_model:
        ed.setdefault("tools", {}).setdefault("whisper", {})["model"] = args.whisper_model
    if ed.get("exists") and not ed.get("name"):
        add("editor name", "warn", "editor.json has no name: it goes on every job card Editor line")
    return ed


# ---------------------------------------------------------------- Resolve
def check_resolve(ed):
    app = next((x(a) for a in RESOLVE_APPS if x(a).exists()), None)
    if not app:
        add("Resolve", "warn", "DaVinci Resolve not found in /Applications: install Resolve Studio 21.1 or later")
        return
    version = None
    try:
        with open(app / "Contents" / "Info.plist", "rb") as f:
            version = plistlib.load(f).get("CFBundleShortVersionString")
    except (OSError, plistlib.InvalidFileException):
        pass
    lic = glob.glob(os.path.join(RESOLVE_LICENSE_DIR, "*studio*")) + glob.glob(os.path.join(RESOLVE_LICENSE_DIR, ".*studio*"))
    edition = "studio" if lic else "unknown"
    detected["resolve"] = {"edition": edition, "version": version}
    if version and vtuple(version)[:2] < MIN_RESOLVE:
        add("Resolve", "warn", f"{app} version {version}: the skills need Studio 21.1 or later")
    else:
        add("Resolve", "pass", f"{app} version {version or 'unknown'}")
    if edition == "studio":
        add("Resolve Studio", "pass", "Studio licence file found")
    else:
        add("Resolve Studio", "warn", "no Studio licence file found: the free edition has no scripting on 21.1+; confirm with the editor")
    cfg = x(RESOLVE_CONFIG)
    mode = None
    try:
        m = re.search(rb"System\.Scripting\.Mode\s*=\s*(\d+)", cfg.read_bytes())
        mode = int(m.group(1)) if m else None
    except OSError:
        pass
    if mode is None:
        add("External scripting", "warn", "can't read the setting: set Preferences > System > General > External scripting using: Local")
    elif mode == 0:
        detected["resolve"]["external_scripting_local"] = False
        add("External scripting", "warn", "off: set Preferences > System > General > External scripting using: Local, then restart Resolve")
    else:
        detected["resolve"]["external_scripting_local"] = mode == 1
        add("External scripting", "pass" if mode == 1 else "info",
            f"System.Scripting.Mode = {mode} ({'Local' if mode == 1 else 'not Local; Local is the tested setting'})")
    fs = x(FUSION_SCRIPTS)
    if fs.is_dir():
        subs = (fs / "Edit" / "Auto Subtitles.py").exists()
        add("Fusion Scripts", "pass" if subs else "warn",
            f"{fs}" + ("" if subs else ": Auto Subtitles not installed; run skills/subtitles/scripts/install.sh and restart Resolve"))
    else:
        add("Fusion Scripts", "warn", f"{fs} missing: open Resolve once, then run skills/subtitles/scripts/install.sh")


# ---------------------------------------------------------------- command-line tools and Python
def check_cli():
    for tool in ("ffmpeg", "ffprobe"):
        p = shutil.which(tool)
        if p:
            add(tool, "pass", p)
        else:
            alt = next((a for a in (f"/opt/homebrew/bin/{tool}", f"/usr/local/bin/{tool}") if os.path.exists(a)), None)
            add(tool, "warn", f"not on PATH (found {alt}; add its folder to PATH)" if alt else "not found: brew install ffmpeg")
    for mod, pkg in PY_PACKAGES:
        ok = importlib.util.find_spec(mod) is not None
        add(f"python {mod}", "pass" if ok else "warn",
            f"importable in {sys.executable}" if ok else f"missing in {sys.executable}: python3 -m pip install {pkg}")
    gh = shutil.which("gh")
    add("gh", "pass" if gh else "info", gh or "not found: needed only to open pull requests with lessons (brew install gh)")


# ---------------------------------------------------------------- tools from editor.json
def check_tools(ed):
    tools = ed.get("tools") or {}
    gyro = next((x(a) for a in GYROFLOW_APPS if x(a).exists()), None)
    detected["gyroflow_installed"] = bool(gyro)
    if gyro:
        add("Gyroflow", "pass", str(gyro))
    else:
        add("Gyroflow", "warn", "not in /Applications: handheld B-roll can't pass the broll gate without it (https://gyroflow.xyz)")
    script = (tools.get("gyroflow") or {}).get("stabilize_script")
    if script and "<" not in script:
        add("Gyroflow script", "pass" if x(script).exists() else "warn",
            script if x(script).exists() else f"{script} not found")
    else:
        found = glob.glob(os.path.join(x(FUSION_SCRIPTS), "**", "Gyroflow Stabilize Flagged.py"), recursive=True)
        if found:
            detected["gyroflow_stabilize_script"] = found[0]
        add("Gyroflow script", "info", found[0] if found else "Gyroflow Stabilize Flagged.py not found in Fusion Scripts")
    fp = (tools.get("footage_prep") or {}).get("enabled")
    add("Footage Prep", "info", "enabled in editor.json (the app's MCP is checked at the first footage task)" if fp
        else "off: footage tasks use the fallback (ingest.py + contact sheets)")
    w = tools.get("whisper") or {}
    for key in ("model", "cli"):
        if w.get(key):
            ok = x(w[key]).exists()
            add(f"whisper {key}", "pass" if ok else "warn", w[key] if ok else f"{w[key]} not found")
    cw = tools.get("crisperwhisper") or {}
    for key in ("python", "model_dir"):
        if cw.get(key) and "<" not in str(cw[key]):
            ok = x(cw[key]).exists()
            add(f"crisperwhisper {key}", "pass" if ok else "warn", cw[key] if ok else f"{cw[key]} not found")


# ---------------------------------------------------------------- fonts from client profiles
def profile_fonts():
    fonts = {}
    for p in sorted(bc.PROFILES.glob("*.md")):
        if p.name.startswith("_"):
            continue
        try:
            fm, _ = bc.parse_front_matter(p.read_text())
        except OSError:
            continue
        sub = fm.get("subtitles")
        font = sub.get("font") if isinstance(sub, dict) else None
        if isinstance(font, str) and font.lower() not in ("ask", "") and "<" not in font:
            fonts.setdefault(font, []).append(p.stem)
    for f in DEFAULT_FONTS:
        fonts.setdefault(f, []).append("Fluid Reveal Words default")
    return fonts


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def check_fonts():
    files = []
    for d in FONT_DIRS:
        files += [f for f in glob.glob(os.path.join(x(d), "**", "*"), recursive=True)
                  if f.lower().endswith((".otf", ".ttf", ".ttc", ".otc"))]
    for font, users in profile_fonts().items():
        key = norm(re.sub(r"\s+regular$", "", font, flags=re.I))  # "Times New Roman Regular" -> file "Times New Roman"
        exact = [f for f in files if norm(Path(f).stem) in (key, key + "regular")]
        family = [f for f in files if key in norm(Path(f).stem)]
        hits = exact or family
        who = ", ".join(users)
        if not hits:
            add(f"font {font}", "warn", f"not in ~/Library/Fonts, /Library/Fonts or the system fonts (used by {who})")
            continue
        if not exact:  # only other styles of the family, e.g. "Garet Book Italic" for "Garet Book"
            add(f"font {font}", "info", f"family found ({Path(hits[0]).name}), style {font} not confirmed (used by {who})")
            continue
        exts = {Path(f).suffix.lower() for f in hits}
        if {".otf", ".ttf"} <= exts:
            add(f"font {font}", "warn", f"installed as both .otf and .ttf: keep one format (used by {who})")
        else:
            add(f"font {font}", "pass", f"{Path(hits[0]).name} (used by {who})")


# ---------------------------------------------------------------- folders
def check_folders(ed):
    roots = ed.get("footage_roots") or []
    if not roots:
        add("footage roots", "warn", "none set: ask the editor where the raws live")
    for r in roots:
        path = r.get("path") if isinstance(r, dict) else r
        p = x(path)
        if p and p.exists():
            fs = ""
            try:
                mount = p.resolve()
                while not os.path.ismount(mount) and mount != mount.parent:
                    mount = mount.parent
                out = subprocess.run(["diskutil", "info", str(mount)], capture_output=True, text=True, timeout=10).stdout
                m = re.search(r"Type \(Bundle\):\s*(\S+)", out)
                fs = m.group(1) if m else ""
            except (OSError, subprocess.SubprocessError):
                pass
            if fs:
                detected.setdefault("footage_root_fs", {})[path] = fs
            add(f"footage root {path}", "pass", f"mounted{f' ({fs})' if fs else ''}")
        else:
            add(f"footage root {path}", "warn", "not mounted or missing: plug in the drive before a footage task")
    synced = ed.get("synced_folders") or []
    if not synced:
        add("synced folders", "info", "none set (Dropbox is always refused anyway)")
    for s in synced:
        add(f"synced folder {s}", "pass" if x(s).exists() else "info",
            "exists (no media, renders or scratch go here)" if x(s).exists() else "not found on this Mac (still refused)")
    scratch = ed.get("scratch_root") or "~/work"
    if bc.in_synced_folder(scratch, ed):
        add("scratch root", "warn", f"{scratch} is inside a synced folder: pick a local folder")
    else:
        add("scratch root", "pass" if x(scratch).exists() else "info",
            scratch if x(scratch).exists() else f"{scratch} (created on first use)")
    repo = ed.get("plugin_repo")
    if repo:
        ok = (x(repo) / ".git").exists()
        need = ed.get("plugin_owner")
        add("plugin repo", "pass" if ok else ("warn" if need else "info"),
            f"{repo} (git clone)" if ok else f"{repo} is not a git clone: needed to push lessons (owner) or open pull requests")
    mode = (ed.get("run_env") or {}).get("mode", "local")
    add("run_env", "info", f"{mode}" + (" (device-VM notes in resolve-recipes.md apply)" if mode == "device-vm" else ""))


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--editor", help="draft editor.json to check instead of ~/.beon-edit/editor.json")
    ap.add_argument("--footage-root", action="append", help="footage root to check (repeatable; overrides editor.json)")
    ap.add_argument("--synced", action="append", help="synced folder to check (repeatable; overrides editor.json)")
    ap.add_argument("--whisper-model", help="whisper model path to check")
    ap.add_argument("--text", action="store_true", help="print a pass/warn list instead of JSON")
    a = ap.parse_args(argv)
    ed = load(a)
    for fn in (lambda: check_resolve(ed), check_cli, lambda: check_tools(ed), check_fonts, lambda: check_folders(ed)):
        try:
            fn()
        except Exception as e:  # a broken check must never stop the others
            add("doctor", "warn", f"a check failed: {e!r}")
    warns = [c for c in checks if c["status"] == "warn"]
    out = {"ok": not warns, "warnings": len(warns), "checks": checks, "detected": detected}
    if a.text:
        for c in checks:
            print(f"[{c['status'].upper():4}] {c['name']}: {c['detail']}")
        print(f"\n{len(warns)} warning(s)")
    else:
        print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except SystemExit:  # argparse --help / bad flags: still exit 0
        pass
    except Exception as e:
        print(json.dumps({"ok": False, "checks": [{"name": "doctor", "status": "warn", "detail": repr(e)}]}))
    sys.exit(0)
