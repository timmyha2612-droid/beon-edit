#!/usr/bin/env python3
"""QA loop bookkeeping (Tim, 9 Nov 2026): rounds, the 3-round limit, and what to do with each finding.

The qa-manager agent returns a findings JSON per stage and round; the qa-verifier agent returns verdicts
on the judgement findings; the editor running the job answers the creative questions. This script files all of it, compares
rounds by finding id, and prints the next actions, so the loop never depends on anyone's memory.

usage:
  qa_round.py record  QA_DIR findings.json [--extra]   file a qa-manager result, print the next actions
                                                       (--extra: a 4th+ round the editor asked for)
  qa_round.py verify  QA_DIR STAGE ROUND verdicts.json merge qa-verifier verdicts, print the next actions
  qa_round.py editor  QA_DIR STAGE answers.json         record the editor's answers to creative questions
                                                       (`tim` still works as an old name)
  qa_round.py status  QA_DIR                            one line per stage (reports, unattended logs, F-07)
  qa_round.py check   findings.json                     validate a findings file only

QA_DIR: <shoot>/_shotlog/qa/<concept>/ (small text only). Files: <stage>-r<N>.json, editor-answers.json, qa-log.md.
(Older jobs have tim-answers.json or approver-answers.json: still read, merged into editor-answers.json on the next write.)
Save raw agent outputs elsewhere (e.g. QA_DIR/raw/), not as <stage>-r*.json.

findings.json (what qa-manager returns):
  {"stage": "aroll|broll|grade|subtitles|final", "round": 1, "timeline": "C3 v2",
   "checked": ["B-01 gate PASS", ...],            every checklist id must appear in checked or not_checked
   "not_checked": ["B-05: no stills, editor in Resolve"],
   "findings": [{"id": "B-03-1", "kind": "hard|judgement|creative", "severity": "fix|check",
                 "where": "R4 0331, 00:00:12:05", "rule": "broll-rulebook 4 / B-03",
                 "evidence": "shake_check p90 2.4 px", "fix": "slide / Gyroflow / slow (shake)"}]}
verdicts.json (what qa-verifier returns):
  {"verdicts": [{"id": "B-20-1", "agree": true, "reason": "...", "reclassify": "creative"?}]}
answers.json (the editor's answers, written by Claude from what the editor said):
  {"answers": [{"id": "B-41-1", "answer": "keep Jay on camera", "editor_said": "their words"}]}
  (old files may say "tim_said": read the same way)

Verdicts:
  SHADOW    QA isn't calibrated yet (references/calibration.md): everything is reported to the editor,
            nothing is forced (Q25)
  VERIFY    judgement findings wait for the qa-verifier before anything else is decided
  FAIL      something to fix; fix it, then a fresh qa-manager runs the next round
  ESCALATE  round 3 (or later) still has something to fix: stop, show the editor (unattended: log, move on, report)
  PARTIAL   nothing to fix in what was checked, but some checks couldn't run: never report as passed
  PASS      nothing to fix; creative questions still open are listed (the stage waits on the editor for those)
Rules (Tim's answers, Q9-Q13):
  hard       a written rule broken, measured: always fixed, no need to ask (severity check: reported only)
  judgement  needs the qa-verifier's independent agreement, whatever its severity; only agreed ones count
  creative   taste (story, lines, joke on camera, music, the editor's placements, swapping a subject): never
             auto-fixed, never blocks the technical result, goes to the editor
"""
import json, os, re, sys

STAGES = ("aroll", "broll", "grade", "subtitles", "final")
KINDS = ("hard", "judgement", "creative")
MAX_ROUNDS = 3
ANSWERS = "editor-answers.json"
OLD_ANSWERS = ("tim-answers.json", "approver-answers.json")   # written by older versions; read, never written
HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(HERE, "..", "references")


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1)


def calibrated():
    try:
        txt = open(os.path.join(REFS, "calibration.md"), encoding="utf-8").read()
    except OSError:
        return False
    m = re.search(r"^Status:\s*(.*)$", txt, re.M)
    return bool(m and m.group(1).strip().lower().startswith("calibrated"))


def checklist_ids(stage):
    try:
        txt = open(os.path.join(REFS, "checklists", f"{stage}.md"), encoding="utf-8").read()
    except OSError:
        return []
    return re.findall(r"^\|\s*([A-Z]-\d\d)\s*\|", txt, re.M)


def validate(d):
    errs = []
    if d.get("stage") not in STAGES:
        errs.append(f"stage must be one of {STAGES}")
    if not isinstance(d.get("round"), int) or d["round"] < 1:
        errs.append("round must be an integer >= 1")
    if not isinstance(d.get("findings"), list):
        errs.append("findings must be a list")
    if not isinstance(d.get("checked"), list) or not d.get("checked"):
        errs.append("checked must be a non-empty list of what was actually checked")
    if not isinstance(d.get("not_checked"), list):
        errs.append("not_checked must be a list (what couldn't be checked, and why; [] if nothing)")
    ids = set()
    for i, f in enumerate(d.get("findings") or []):
        for k in ("id", "kind", "where", "rule", "evidence", "fix"):
            if not str(f.get(k, "")).strip():
                errs.append(f"finding {i}: '{k}' is empty")
        if f.get("kind") not in KINDS:
            errs.append(f"finding {f.get('id', i)}: kind must be one of {KINDS}")
        if f.get("severity", "fix") not in ("fix", "check"):
            errs.append(f"finding {f.get('id', i)}: severity must be fix or check")
        if f.get("id") in ids:
            errs.append(f"duplicate id {f.get('id')}")
        ids.add(f.get("id"))
    if d.get("stage") in STAGES and isinstance(d.get("checked"), list) and isinstance(d.get("not_checked"), list):
        text = " ".join(str(x) for x in d["checked"] + d["not_checked"])
        found = " ".join(str(f.get("id", "")) for f in d.get("findings") or [])
        missing = [c for c in checklist_ids(d["stage"])
                   if not re.search(rf"\b{re.escape(c)}\b", text) and not re.search(rf"\b{re.escape(c)}-", found)]
        if missing:
            errs.append("checklist items neither checked nor listed in not_checked: " + ", ".join(missing))
    return errs


def rpath(qa_dir, stage, rnd):
    return os.path.join(qa_dir, f"{stage}-r{rnd}.json")


def rounds_of(qa_dir, stage):
    pat = re.compile(rf"^{stage}-r(\d+)\.json$")
    return sorted(int(m.group(1)) for n in os.listdir(qa_dir) for m in [pat.match(n)] if m)


def all_answers(qa_dir):
    """Every stage's answers: the old files first, editor-answers.json last (it wins)."""
    out = {}
    for n in OLD_ANSWERS + (ANSWERS,):
        p = os.path.join(qa_dir, n)
        if os.path.exists(p):
            for st, ans in (load(p) or {}).items():
                out.setdefault(st, {}).update(ans or {})
    return out


def editor_answers(qa_dir, stage):
    return all_answers(qa_dir).get(stage) or {}


def counts(f):
    """Does this finding have to be fixed (live mode)?"""
    if f.get("dropped") or f["kind"] == "creative":
        return False
    if f["kind"] == "judgement" and f.get("verified") is not True:
        return False
    return f.get("severity", "fix") == "fix"


def plan(qa_dir, d):
    """Return (verdict, lines) for the next step of this stage."""
    stage, rnd = d["stage"], d["round"]
    live = calibrated()
    answers = editor_answers(qa_dir, stage)
    fs = [f for f in d["findings"] if not f.get("dropped")]
    creative = [f for f in fs if f["kind"] == "creative"]
    ask = [f for f in creative if f["id"] not in answers]
    settled = [f for f in creative if f["id"] in answers]
    unverified = [f for f in fs if f["kind"] == "judgement" and "verified" not in f]
    to_fix = [f for f in fs if counts(f)]
    notes = [f for f in fs if f["kind"] != "creative" and not counts(f) and f not in unverified
             and (f["kind"] == "hard" or f.get("verified") is True)]
    lines = []
    prev_p = rpath(qa_dir, stage, rnd - 1)
    if rnd > 1 and os.path.exists(prev_p):
        before = {f["id"] for f in load(prev_p)["findings"] if counts(f)}
        now = {f["id"] for f in to_fix} | {f["id"] for f in unverified}
        lines.append(f"since round {rnd - 1}: {len(before - now)} fixed, {len(before & now)} still open, "
                     f"{len(now - before)} new or not yet verified")
    if not live:
        verdict = "SHADOW"
    elif unverified:
        verdict = "VERIFY"
    elif to_fix:
        verdict = "ESCALATE" if rnd >= MAX_ROUNDS else "FAIL"
    else:
        verdict = "PARTIAL" if d.get("not_checked") else "PASS"
    head = f"{stage} round {rnd}: {verdict}"
    if ask:
        head += f" ({len(ask)} question{'s' if len(ask) > 1 else ''} for the editor)"
    lines.append(head)
    if not live:
        lines.append("QA isn't calibrated yet (references/calibration.md): report every finding "
                     "to the editor with the edit; nothing is forced. Fix one only if the editor says so.")
        for f in fs:
            if f["kind"] != "creative":
                lines.append(f"  REPORT {f['id']} [{f['kind']}/{f.get('severity', 'fix')}] {f['where']}: "
                             f"{f['evidence']} -> {f['fix']} ({f['rule']})")
    else:
        if unverified:
            lines.append(f"VERIFY first: run a fresh qa-verifier on " + ", ".join(f["id"] for f in unverified)
                         + f", then: qa_round.py verify QA_DIR {stage} {rnd} verdicts.json")
        for f in to_fix:
            tag = "ESCALATE to editor" if verdict == "ESCALATE" else "FIX"
            lines.append(f"  {tag} {f['id']} [{f['kind']}] {f['where']}: {f['evidence']} -> {f['fix']} ({f['rule']})")
        for f in notes:
            allow = " (fix only if cheap and clearly right)" if f["kind"] == "hard" else " (verified; fix only if the editor agrees)"
            lines.append(f"  NOTE {f['id']} [{f['kind']}/check] {f['where']}: {f['evidence']}{allow}")
    for f in ask:
        lines.append(f"  ASK EDITOR {f['id']} [creative] {f['where']}: {f['evidence']} (suggestion: {f['fix']})")
    for f in settled:
        lines.append(f"  SETTLED {f['id']}: the editor said {answers[f['id']].get('answer', '')!r}")
    for f in [f for f in d["findings"] if f.get("dropped")]:
        lines.append(f"  DROPPED {f['id']}: the verifier disagreed ({f.get('verifier_reason', '')})")
    if d.get("not_checked"):
        lines.append("  NOT CHECKED: " + "; ".join(str(x) for x in d["not_checked"]))
    nxt = {
        "SHADOW": "next: put the report in front of the editor; continue only as they say",
        "VERIFY": "next: the verifier decides the judgement findings, then this prints the real verdict",
        "FAIL": f"next: fix, then run a fresh qa-manager as round {rnd + 1} (same stage)",
        "ESCALATE": "next: stop fixing this stage. Show the editor what's still failing, the evidence and what was tried "
                    "(unattended: it's in qa-log.md; move on and put it at the top of the end-of-run report)",
        "PARTIAL": "next: nothing to fix in what was checked, but some checks couldn't run (above). Run them in a "
                   "new round when possible, or tell the editor exactly what wasn't checked; never report it as passed",
        "PASS": "next: stage passed; continue to the next stage",
    }[verdict]
    lines.append(nxt)
    if ask and verdict in ("PASS", "PARTIAL", "FAIL", "ESCALATE"):
        lines.append("  the creative questions go to the editor (one batch, pop-up questions); record the answers with: "
                     f"qa_round.py editor QA_DIR {stage} answers.json")
    return verdict, lines


def log(qa_dir, d, verdict, lines, what):
    with open(os.path.join(qa_dir, "qa-log.md"), "a", encoding="utf-8") as f:
        f.write(f"\n## {d['stage']} round {d['round']} ({d.get('timeline', '')}), after {what}: {verdict}\n")
        for ln in lines:
            f.write(f"- {ln.strip()}\n")


def main():
    argv = [a for a in sys.argv[1:] if a != "--extra"]
    extra = "--extra" in sys.argv
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return
    if len(argv) < 2:
        sys.exit(__doc__)
    cmd = argv[0]
    if cmd == "check":
        errs = validate(load(argv[1]))
        print("ok" if not errs else "\n".join(errs))
        sys.exit(1 if errs else 0)
    qa_dir = argv[1]
    if cmd == "status":
        if not os.path.isdir(qa_dir):
            sys.exit(f"no QA folder at {qa_dir}")
        any_ = False
        for st in STAGES:
            rs = rounds_of(qa_dir, st)
            if rs:
                any_ = True
                v, lines = plan(qa_dir, load(rpath(qa_dir, st, rs[-1])))
                print(f"{st:<10} " + next(l for l in lines if l.startswith(st)).split(" ", 1)[1])
        if not any_:
            print("no QA rounds recorded here yet")
        return
    os.makedirs(qa_dir, exist_ok=True)
    if cmd == "record":
        d = load(argv[2])
        errs = validate(d)
        if errs:
            sys.exit("findings file is not valid:\n" + "\n".join(errs))
        stage, rnd = d["stage"], d["round"]
        out = rpath(qa_dir, stage, rnd)
        if os.path.exists(out):
            sys.exit(f"{out} already exists: this round was recorded. Use round {rnd + 1} for a new check.")
        if rnd > 1 and not os.path.exists(rpath(qa_dir, stage, rnd - 1)):
            sys.exit(f"round {rnd - 1} of {stage} was never recorded")
        if rnd > MAX_ROUNDS and not extra:
            sys.exit(f"{stage} already had {MAX_ROUNDS} rounds: escalate to the editor. "
                     "Record another round only if the editor asked for it (--extra).")
        prev_p = rpath(qa_dir, stage, rnd - 1)
        if rnd > 1 and os.path.exists(prev_p):        # the same finding id, already confirmed: no second verify
            confirmed = {f["id"]: f for f in load(prev_p)["findings"]
                         if f.get("verified") is True and f["kind"] == "judgement"}
            for f in d["findings"]:
                if f["kind"] == "judgement" and f["id"] in confirmed and "verified" not in f:
                    f["verified"] = True
                    f["verifier_reason"] = f"confirmed in round {rnd - 1}"
        save(out, d)
        what = "qa-manager"
    elif cmd == "verify":
        stage, rnd, vfile = argv[2], int(argv[3]), argv[4]
        out = rpath(qa_dir, stage, rnd)
        if not os.path.exists(out):
            sys.exit(f"record round {rnd} of {stage} first")
        d = load(out)
        verdicts = {v["id"]: v for v in load(vfile).get("verdicts", [])}
        for f in d["findings"]:
            v = verdicts.get(f["id"])
            if f["kind"] != "judgement" or not v:
                continue
            f["verifier_reason"] = v.get("reason", "")
            if v.get("reclassify") == "creative":
                f["kind"] = "creative"                # taste, not a mistake: it goes to the editor, never dropped
                f["reclassified_by_verifier"] = True
            else:
                f["verified"] = bool(v.get("agree"))
                if not f["verified"]:
                    f["dropped"] = True
        missing = [f["id"] for f in d["findings"] if f["kind"] == "judgement" and "verified" not in f]
        if missing:
            print("no verdict yet for: " + ", ".join(missing))
        save(out, d)
        what = "qa-verifier"
    elif cmd in ("editor", "tim"):
        stage, afile = argv[2], argv[3]
        p = os.path.join(qa_dir, ANSWERS)
        allans = all_answers(qa_dir)                  # carries old tim-/approver-answers.json over
        for a in load(afile).get("answers", []):
            allans.setdefault(stage, {})[a["id"]] = {k: v for k, v in a.items() if k != "id"}
        save(p, allans)
        rs = rounds_of(qa_dir, stage)
        if not rs:
            print("answers saved; no round recorded for this stage yet")
            return
        d = load(rpath(qa_dir, stage, rs[-1]))
        what = "the editor's answers"
    else:
        sys.exit(__doc__)
    verdict, lines = plan(qa_dir, d)
    log(qa_dir, d, verdict, lines, what)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
