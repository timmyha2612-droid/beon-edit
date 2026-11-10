#!/usr/bin/env python3
"""Quick self-test for the beon-edit plugin. No Resolve, no footage, no network: `python3 tests/run_tests.py`.

Checks:
  1. every Python script compiles, every JSON file parses, every skill and agent has a name and description
  2. every script or reference file a skill, agent, checklist or hook message points to really exists
  3. plugin version: plugin.json and the last CHANGELOG entry agree
  4. hooks: job_guard (blocks edits without a card, lets reads through), broll_guard, learn_listener
  5. lessons.py: add -> revise -> decide -> propose; a non-Tim decision waits for Tim
  6. qa_round.py: refuses a report that skips checklist items; shadow mode while not calibrated
  7. broll_gate.py pure checks: zoom limit, speed reasons and floors, speaker over 4 s, slivers, gaps
Exit code 0 = all passed."""
import glob, importlib.util, json, os, py_compile, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails, passed = [], 0


def ok(name, cond, detail=""):
    global passed
    if cond:
        passed += 1
    else:
        fails.append(f"{name}: {detail}")
        print(f"FAIL  {name}  {detail}")


def run(args, stdin=None, env=None):
    e = dict(os.environ)
    e.update(env or {})
    p = subprocess.run([sys.executable] + args, input=stdin, capture_output=True, text=True, env=e, timeout=60)
    return p.returncode, p.stdout, p.stderr


def hook(name, payload, env=None):
    return run([os.path.join(ROOT, "hooks", name)], json.dumps(payload), env)


# ---- 1. files are well-formed
for f in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True):
    if "/references/" in f:           # example snippets, not runnable on their own
        continue
    try:
        py_compile.compile(f, doraise=True, cfile=os.path.join(tempfile.gettempdir(), "beon_test.pyc"))
        ok("compile", True)
    except Exception as e:
        ok("compile", False, f"{os.path.relpath(f, ROOT)}: {e}")
for f in glob.glob(os.path.join(ROOT, "**", "*.json"), recursive=True) + glob.glob(os.path.join(ROOT, ".claude-plugin", "*.json")):
    try:
        json.load(open(f, encoding="utf-8"))
        ok("json", True)
    except Exception as e:
        ok("json", False, f"{os.path.relpath(f, ROOT)}: {e}")
docs = glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")) + glob.glob(os.path.join(ROOT, "agents", "*.md"))
for f in docs:
    head = open(f, encoding="utf-8").read().split("---")
    fm = head[1] if len(head) > 2 else ""
    ok("frontmatter", re.search(r"^name:\s*\S", fm, re.M) and re.search(r"^description:\s*\S", fm, re.M),
       os.path.relpath(f, ROOT))

# ---- 2. every file the docs point to exists
SKILLS = os.path.join(ROOT, "skills")
names = {}
for f in glob.glob(os.path.join(SKILLS, "*", "scripts", "*")) + glob.glob(os.path.join(SKILLS, "*", "references", "**", "*"), recursive=True):
    names.setdefault(os.path.basename(f), []).append(f)
texts = glob.glob(os.path.join(ROOT, "skills", "**", "*.md"), recursive=True) + glob.glob(os.path.join(ROOT, "agents", "*.md")) \
    + glob.glob(os.path.join(ROOT, "hooks", "*.py")) + [os.path.join(ROOT, "README.md")]
EXTERNAL = {"Auto Subtitles.py", "Resync Subtitles.py", "shotlog.json", "plan.json", "apply.py", "snapshot.json",
            "edits.json", "answers.json", "verdicts.json", "tim-answers.json", "qa-log.md", "config.json",
            "pending-for-tim.md", "plans.json", "findings.json", "SLOTS.json", "SHOTS.json", "CUT.json",
            "TRANSCRIPT.json", "out.json", "README.md", "CHANGELOG.md", "SKILL.md", "MEMORY.md", "hooks.json",
            "plugin.json", "marketplace.json", "file.md"}
for t in texts:
    body = open(t, encoding="utf-8").read()
    for m in re.finditer(r"(?<![\w<>*])((?:[\w.-]+/)*)([A-Za-z_][\w-]*\.(?:py|sh|md|json))\b", body):
        path, base = m.group(1), m.group(2)
        if base in EXTERNAL or base.startswith(("<", "_claude")) or "<" in path:
            continue
        if path.startswith(("~", "/", "WORK/", "tests/", "code/")) or "_shotlog" in path or "work/" in path or base == "Subtitles.py":
            continue
        if path.startswith("hooks/") or (not path and os.path.exists(os.path.join(ROOT, "hooks", base))):
            ok("ref", os.path.exists(os.path.join(ROOT, "hooks", base)), f"{os.path.relpath(t, ROOT)} -> hooks/{base}")
            continue
        rel = os.path.relpath(t, SKILLS).split(os.sep)
        own = os.path.join(SKILLS, rel[0]) if not rel[0].startswith("..") else None
        if own and path.startswith(("scripts/", "references/")):      # a skill's own folder
            ok("ref", os.path.exists(os.path.join(own, path, base)), f"{os.path.relpath(t, ROOT)} -> {path}{base} is not in this skill")
            continue
        if own and path.startswith(("../", "checklists/")):          # relative to the file itself
            ok("ref", os.path.exists(os.path.normpath(os.path.join(os.path.dirname(t), path, base)))
               or os.path.exists(os.path.join(own, "references", path, base)), f"{os.path.relpath(t, ROOT)} -> {path}{base}")
            continue
        if base in names:
            if path and not path.startswith(("scripts/", "references/", "../", "checklists/")):
                want = path.replace("skills/", "").rstrip("/")
                hit = any(want in os.path.relpath(c, SKILLS) for c in names[base])
                ok("ref", hit, f"{os.path.relpath(t, ROOT)} -> {path}{base} (found only in {[os.path.relpath(c, SKILLS) for c in names[base]]})")
            else:
                ok("ref", True)
        elif base.endswith((".py", ".sh")) or "references/" in path or "checklists/" in path:
            ok("ref", False, f"{os.path.relpath(t, ROOT)} -> {path}{base} does not exist")

# ---- 3. version
ver = json.load(open(os.path.join(ROOT, ".claude-plugin", "plugin.json")))["version"]
log = open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
last = re.findall(r"^(?:\d+\.\d+\.\d+-)?(\d+\.\d+\.\d+)[ (]", log, re.M)
ok("version", last and last[-1] == ver, f"plugin.json {ver} vs last CHANGELOG entry {last[-1] if last else None}")

# ---- 4. hooks
with tempfile.TemporaryDirectory() as jobs:
    env = {"BEON_JOBS_DIR": jobs, "CLAUDE_PLUGIN_ROOT": ROOT}
    write = {"session_id": "s1", "tool_name": "mcp__davinci-resolve__run_script",
             "tool_input": {"script": "item.SetProperty('ZoomX', 1.2)"}}
    read = {"session_id": "s1", "tool_name": "mcp__davinci-resolve__run_script",
            "tool_input": {"script": "print(tl.GetItemListInTrack('video', 1))"}}
    rc, _, err = hook("job_guard.py", write, env)
    ok("job_guard blocks an edit with no card", rc == 2 and "s1.md" in err, f"rc={rc}")
    ok("job_guard lets reads through", hook("job_guard.py", read, env)[0] == 0)
    ok("job_guard blocks a write-named tool", hook("job_guard.py", {"session_id": "s1", "tool_name": "mcp__resolve__timeline_item", "tool_input": {"action": "set_property"}}, env)[0] == 2)
    ok("job_guard lets navigation through", hook("job_guard.py", {"session_id": "s1", "tool_name": "mcp__resolve__timeline", "tool_input": {"action": "set_current_timeline"}}, env)[0] == 0)
    card = os.path.join(jobs, "s1.md")
    open(card, "w").write("# Job\nKind: concept\nEditor: Tim\nClient: namir-mikha\nLessons inbox: /x/_shotlog/lessons/c8.jsonl\n"
                          "Grilling: done with Tim\n\n## Answers\n- Concept and goal: \n- Target length: 45 s\n")
    ok("job_guard blocks an unfinished card", hook("job_guard.py", write, env)[0] == 2)
    full = open(card).read().replace("Concept and goal: ", "Concept and goal: sell the reno")
    open(card, "w").write(full)
    ok("job_guard passes a full card", hook("job_guard.py", write, env)[0] == 0)
    open(os.path.join(jobs, "s2.md"), "w").write("# Job\nKind: calibration\nGrilling: done with Tim\n")
    w2 = dict(write, session_id="s2", tool_input={"script": "project.AddRenderJob()"})
    ok("job_guard lets a calibration card render the proxy", hook("job_guard.py", w2, env)[0] == 0)
    open(os.path.join(jobs, "s4.md"), "w").write("# Job\nKind: calibration\n")
    ok("job_guard blocks a card with no Grilling line", hook("job_guard.py", dict(w2, session_id="s4"), env)[0] == 2)
    open(os.path.join(jobs, "s3.md"), "w").write("# Job\nKind: fix\nGrilling: skipped (Tim said \"just do it\")\n")
    ok("job_guard passes a skipped card", hook("job_guard.py", dict(write, session_id="s3"), env)[0] == 0)

    rc, out, _ = hook("learn_listener.py", {"session_id": "s1", "prompt": "slow that one down"}, env)
    ok("learn_listener reminds during a job", rc == 0 and "lessons.py" in out and "c8.jsonl" in out and '--who "Tim"' in out and "namir-mikha" in out, out[:200])
    ok("learn_listener reminder stays short", len(out.split()) < 75, f"{len(out.split())} words")
    rc, out, _ = hook("learn_listener.py", {"session_id": "nojob", "prompt": "hi"}, env)
    ok("learn_listener silent without a job", rc == 0 and not out.strip())

    place = "mp.AppendToTimeline([{'mediaPoolItem': c, 'trackIndex': 2, 'mediaType': 1, 'startFrame': 0, 'endFrame': 50}])\n"
    b = lambda s: hook("broll_guard.py", {"tool_name": "mcp__resolve__run_script", "tool_input": {"script": s}})[0]
    ok("broll_guard blocks bare B-roll", b(place) == 2)
    good = place + "rows=[{'why': {'line': 'x'}}]\nit.SetClipColor('Orange'); it.AddMarker(0,'Blue','gyroflow','',1,'{}')\n"
    ok("broll_guard passes reasons + gyro flag", b(good) == 0)
    ok("broll_guard wants a retime on slowed shots", b(good + "it.SetSpeed({'Percentage': 60})\n") == 2)
    ok("broll_guard passes slowed + retime", b(good + "it.SetSpeed({'Percentage': 60}); it.SetProperty('RetimeProcess', 3)\n") == 0)
    ok("broll_guard passes broll-ok", b("# broll-ok: logo\n" + place) == 0)
    ok("broll_guard ignores V1", b(place.replace("'trackIndex': 2", "'trackIndex': 1")) == 0)

# ---- 5. lessons.py
L = os.path.join(SKILLS, "learn-from-tim", "scripts", "lessons.py")
with tempfile.TemporaryDirectory() as d:
    inbox = os.path.join(d, "c8.jsonl")
    env = {"HOME": d}
    rc, out, err = run([L, "add", inbox, "--said", "never slow talking people below 80", "--kind", "general",
                        "--rule", "People talking: no slower than 80%", "--who", "Tim", "--stage", "broll"], env=env)
    ok("lessons add", rc == 0 and "L-001" in out + err, (out + err)[:200])
    rc, out, err = run([L, "revise", inbox, "L-001", "--file", "skills/broll/references/broll-rulebook.md", "--section",
                        "2. Speed", "--change", "add", "--new-line", "- People talking: no slower than 80% [Tim, C8]"], env=env)
    ok("lessons revise", rc == 0, (out + err)[:200])
    rc, out, err = run([L, "propose", inbox], env=env)
    ok("lessons propose shows the stored line", rc == 0 and "no slower than 80%" in out, (out + err)[:200])
    rc, out, err = run([L, "decide", inbox, "L-001", "approve", "--by", "Sam"], env=env)
    rc2, out2, _ = run([L, "list", inbox, "--status", "pending-tim"], env=env)
    ok("a non-Tim decision waits for Tim", "L-001" in out2, (out + err + out2)[:200])
    rc, out, err = run([L, "decide", inbox, "L-001", "approve", "--by", "Tim"], env=env)
    rc2, out2, _ = run([L, "list", inbox, "--status", "approved"], env=env)
    ok("Tim's yes approves", rc == 0 and "L-001" in out2, (out + err + out2)[:200])
    rc, out, err = run([L, "repeats", ROOT], env=env)
    ok("lessons repeats runs on the plugin", rc == 0, err[:200])

# ---- 6. qa_round.py
Q = os.path.join(SKILLS, "qa-loop", "scripts", "qa_round.py")
ids = re.findall(r"^\| (F-\d+) ", open(os.path.join(SKILLS, "qa-loop", "references", "checklists", "final.md")).read(), re.M)
ok("final checklist has ids", len(ids) >= 5, str(ids))
with tempfile.TemporaryDirectory() as d:
    bad = os.path.join(d, "bad.json")
    json.dump({"stage": "final", "round": 1, "timeline": "T", "checked": ["F-01 none"], "not_checked": [], "findings": []}, open(bad, "w"))
    rc, out, err = run([Q, "check", bad])
    ok("qa_round refuses a report that skips items", rc != 0, (out + err)[:200])
    good = os.path.join(d, "good.json")
    json.dump({"stage": "final", "round": 1, "timeline": "T", "checked": [f"{i} fine" for i in ids[1:]], "not_checked": [],
               "findings": [{"id": ids[0] + "-1", "kind": "hard", "severity": "fix", "where": "00:00:03:00",
                             "rule": "final " + ids[0], "evidence": "2 black frames", "fix": "close the gap"}]}, open(good, "w"))
    rc, out, err = run([Q, "check", good])
    ok("qa_round accepts a complete report", rc == 0, (out + err)[:300])
    qa = os.path.join(d, "qa"); os.makedirs(qa)
    rc, out, err = run([Q, "record", qa, good])
    cal = open(os.path.join(SKILLS, "qa-loop", "references", "calibration.md")).read()
    calibrated = bool(re.search(r"^Status:\s*calibrated", cal, re.M))
    ok("qa_round record gives the right verdict", rc == 0 and (("FAIL" in out) if calibrated else ("SHADOW" in out)), (out + err)[:300])
    rc, out, err = run([Q, "status", qa])
    ok("qa_round status", rc == 0 and "final" in out, (out + err)[:200])

# ---- 7. broll_gate pure checks
spec = importlib.util.spec_from_file_location("broll_gate", os.path.join(SKILLS, "broll", "scripts", "broll_gate.py"))
try:
    g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
    ok("zoom tier UHD 1.2 fine", g.zoom_tier(1.2, 2160) == "ok", str(g.zoom_tier(1.2, 2160)))
    ok("zoom tier UHD 1.3 check", g.zoom_tier(1.3, 2160) == "check")
    ok("zoom tier UHD 1.5 fails", g.zoom_tier(1.5, 2160) == "fail")
    ok("zoom tier 1080 1.2 fails", g.zoom_tier(1.2, 1080) == "fail")
    shot = dict(name="R1 0001", speed=100.0, retime=None, stabilised=True, colour="Yellow", has_gyro=True, zoom=1.0, height=2160, fps=50)
    row = {"why": {"speed_reason": None}}
    ok("100% stabilised shot passes", g.check_shot(shot, row, set())[0] == [], str(g.check_shot(shot, row, set())))
    slow = dict(shot, speed=60.0, retime="optical_flow")
    ok("slowed with no reason fails", any("no valid reason" in p for p in g.check_shot(slow, row, set())[0]))
    ok("slowed for a valid reason passes", g.check_shot(slow, {"why": {"speed_reason": "match"}}, set())[0] == [])
    ok("slowed without Optical Flow fails", any("Optical Flow" in p for p in g.check_shot(dict(slow, retime=None), {"why": {"speed_reason": "match"}}, set())[0]))
    ok("talking people below 80% fails", any("floor" in p for p in g.check_shot(slow, {"why": {"speed_reason": "shake"}, "people": "talking"}, set())[0]))
    ok("below 48% fails on 50 fps", any("floor" in p for p in g.check_shot(dict(slow, speed=40.0), {"why": {"speed_reason": "shake"}}, set())[0]))
    ok("unstabilised gyro shot fails", any("not stabilised" in p for p in g.check_shot(dict(shot, stabilised=False, colour="Blue"), row, set())[0]))
    ok("zoom past the limit fails", any("pixelates" in p for p in g.check_shot(dict(shot, zoom=1.5), row, set())[0]))
    ok("Tim's exception is allowed", g.check_shot(dict(slow, speed=30.0), None, {"R1 0001"})[0] == [])
    items = [dict(track=1, start=0, end=300, speaker=True, name="A"), dict(track=2, start=0, end=30, speaker=False, name="R1"),
             dict(track=2, start=150, end=200, speaker=False, name="R2"), dict(track=2, start=212, end=260, speaker=False, name="R3")]
    runs = g.merge_speaker(g.top_layer(items, 0, 300))
    probs = g.check_timeline(runs, 24, [])
    ok("speaker over 4 s is caught", any("speaker on screen 5.0 s" in p for p in probs), str(probs))
    ok("a 12-frame sliver is caught", any("only 12 frames" in p for p in probs), str(probs))
    ok("Tim's allowed hold passes", not any("speaker on screen" in p for p in g.check_timeline(runs, 24, [(30, 150)])))
    ok("a gap is caught", any("gap" in p for p in g.check_timeline(g.top_layer(items[1:], 0, 60), 24, [])))
except Exception as e:
    ok("broll_gate imports without Resolve", False, repr(e))

print(f"\n{passed} passed, {len(fails)} failed")
sys.exit(1 if fails else 0)
