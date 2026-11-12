#!/usr/bin/env python3
"""Lessons inbox (Tim, 9 Nov 2026): every correction or piece of knowledge, written down the moment it's given,
sorted into general / client / concept, and turned into rules only after the editor running the job says yes.

usage:
  lessons.py add INBOX --said "their words" --kind general|client|concept|unsure --rule "the rule, one line"
                 --who <editor> [--stage broll] [--where "R4 0331"] [--client namir-mikha]
                 [--source said|inferred] [--evidence "numbers / what changed"] [--promote-from arriva,namir-mikha]
  lessons.py revise INBOX ID --file F --section S --change add|replace|remove --new-line "- ..." [--old-line "- ..."]
                 [--kind K] [--client C] [--rule R] [--remove-lines "profile: line" ...]
                 the learner's proposal for a lesson: exactly what would change in the plugin (the editor approves THIS)
  lessons.py list INBOX [--status open]
  lessons.py propose INBOX            the end-of-job table for the editor, built from the stored proposals
  lessons.py decide INBOX ID approve|change|drop|kind=<general|client|concept> --by <who decided>
                 [--rule "the editor's version"] [--note "..."] [--client name] [--reopen]
  lessons.py ship INBOX [--repo PATH] [--body-out FILE]
                 prints the git / gh commands for the approved lessons: plugin owner -> commit + push to main;
                 any other editor -> branch lessons/<editor>-<concept>-<date> + pull request (never main)
  lessons.py applied INBOX ID --file skills/x/SKILL.md (--commit abc123 | --pr URL)
  lessons.py repeats PLUGIN_DIR        client rules that look alike across 2+ client profiles (Q17 candidates)

INBOX: <shoot>/_shotlog/lessons/<concept>.jsonl (small text). The job card's `Lessons inbox:` line names it.

Kinds (Q6):
  general  applies to every client          -> a stage skill, the B-roll rulebook, a QA checklist, house-rules
  client   only this client                 -> client-styles/references/<client>.md
  concept  only this concept                -> the job card's concept-only notes + shot log; never the plugin
  unsure   -> ask the editor which one before proposing
Statuses: open -> approved / changed (the editor's wording) / dropped -> in-pr (pull request open, waits for the
  plugin owner's merge) -> applied (in the plugin, with the commit).
  pending-approval: someone other than the editor running the job decided; it waits for the editor.
  (Old inboxes say pending-tim: read as pending-approval and written back with the new name.)
  Concept lessons go straight to `concept`.
The editor running the job approves their lessons. "The editor" = ~/.beon-edit/editor.json name / aliases
(skills/house-rules/references/intake.md). No editor.json yet: the old behaviour holds ("Tim", "Tim Ha" and
config.json tim_names are the editor; owner if config.json exists), with a note to write editor.json. Plugin owner
(editor.json plugin_owner: true) pushes approved general/client lessons to main; everyone else opens a pull request
that changes nothing until the owner merges it. Plugin clone: editor.json plugin_repo.
A kind change sends a lesson back to open: the editor approves the new placement again.
"""
import argparse, datetime, json, os, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "house-rules" / "scripts"))
import beon_config as bc  # noqa: E402

KINDS = ("general", "client", "concept", "unsure")
OLD_STATUS = {"pending-tim": "pending-approval"}
_ED = None


def editor():
    global _ED
    if _ED is None:
        _ED = bc.load_editor()
    return _ED


LEGACY_NAMES = {"tim", "tim ha"}                # before editor.json: Tim's machines answered to these


def legacy():
    """No editor.json yet: keep the old behaviour (Tim / Tim Ha + config.json tim_names; owner if config.json exists)."""
    return not editor().get("exists")


def is_editor(name):
    """The editor running the job (this machine's editor.json), the only one whose yes approves a lesson."""
    if not name:
        return False
    if legacy() and bc.norm_name(name) in LEGACY_NAMES:
        return True
    return bc.is_this_editor(name, editor())


def is_owner():
    if legacy():
        return (bc.HOME / "config.json").exists()
    return bc.is_plugin_owner(editor())


def no_setup_note():
    if legacy():
        return " (no editor set up: write ~/.beon-edit/editor.json first, house-rules references/intake.md)"
    return ""


def editor_name():
    """The editor's real name, or None when editor.json has none."""
    if editor().get("name"):
        return editor()["name"]
    if legacy() and (bc.HOME / "config.json").exists():
        return "Tim"
    return None


def editor_label():
    return editor_name() or "the editor"


def read(inbox):
    if not os.path.exists(inbox):
        return []
    out = []
    with open(inbox, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    it = json.loads(line)
                except json.JSONDecodeError as e:
                    sys.exit(f"{inbox} line {n} is not valid JSON: {e}")
                it["status"] = OLD_STATUS.get(it.get("status"), it.get("status"))
                out.append(it)
    return out


def write(inbox, items):
    os.makedirs(os.path.dirname(os.path.abspath(inbox)), exist_ok=True)
    tmp = inbox + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    os.replace(tmp, inbox)


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def one_line(s):
    return " ".join(str(s or "").split())


def cell(s):
    return one_line(s).replace("|", "\\|")


def target(it):
    p = it.get("proposal") or {}
    if p.get("file"):
        return p["file"] + (f" > {p['section']}" if p.get("section") else "")
    k = it["kind"]
    if k == "client":
        return f"skills/client-styles/references/{it.get('client') or '<client>'}.md"
    if k == "general":
        return {"aroll": "skills/aroll-cut/SKILL.md", "broll": "skills/broll/references/broll-rulebook.md",
                "grade": "skills/colour-grade/SKILL.md", "subtitles": "skills/subtitles/SKILL.md",
                "final": "skills/finish-pass/SKILL.md", "footage": "skills/shotlog/SKILL.md",
                "qa": "skills/qa-loop/references/checklists/"}.get(it.get("stage") or "",
                                                                    "skills/house-rules/SKILL.md (or the stage skill)")
    if k == "concept":
        return "job card (Concept-only notes) + shot log lessons"
    return "ask the editor which kind first"


def find(items, lid):
    for it in items:
        if it["id"] == lid:
            return it
    sys.exit(f"no lesson {lid}")


def history(it, **entry):
    entry["at"] = now()
    it.setdefault("history", []).append(entry)


def cmd_add(a):
    items = read(a.inbox)
    if a.kind == "client" and not a.client:
        sys.exit("--client is required for a client lesson (the profile file name, e.g. namir-mikha)")
    if not one_line(a.said) or not one_line(a.rule):
        sys.exit("--said and --rule must not be empty")
    n = max([int(re.sub(r"\D", "", it["id"]) or 0) for it in items] + [0]) + 1
    it = dict(id=f"L-{n:03d}", at=now(), who=one_line(a.who), said=a.said.strip(), rule=one_line(a.rule),
              kind=a.kind, client=a.client, stage=a.stage, where=a.where, source=a.source, evidence=a.evidence,
              status="concept" if a.kind == "concept" else "open")
    if a.promote_from:
        if a.kind != "general":
            sys.exit("--promote-from is for a general rule built from client rules")
        it["promote_from"] = [p.strip() for p in a.promote_from.split(",") if p.strip()]
    items.append(it)
    write(a.inbox, items)
    print(f"{it['id']} [{it['kind']}] {it['rule']}  -> {target(it)}")
    if a.kind == "concept":
        print("  concept-only: also add it to the job card's 'Concept-only notes' (never into the plugin)")
    if a.kind == "unsure":
        print("  unsure: ask the editor whether this is for every client, this client, or this concept only")


def cmd_revise(a):
    items = read(a.inbox)
    it = find(items, a.id)
    if it["status"] in ("applied", "concept"):
        sys.exit(f"{a.id} is {it['status']}: nothing to propose")
    if a.kind and a.kind != it["kind"]:
        if a.kind == "client" and not (a.client or it.get("client")):
            sys.exit("--client is required for a client lesson")
        history(it, by="learner", event=f"kind {it['kind']} -> {a.kind} (proposed)")
        it["kind"] = a.kind
        if a.kind == "concept":
            it["status"] = "concept"
    if a.client:
        it["client"] = a.client
    if a.rule:
        it["rule"] = one_line(a.rule)
    if a.change in ("replace", "remove") and not a.old_line:
        sys.exit("--old-line is required for replace and remove")
    it["proposal"] = dict(file=a.file, section=a.section, change=a.change, old_line=a.old_line,
                          new_line=one_line(a.new_line), remove_lines=a.remove_lines or [])
    if it["status"] in ("approved", "changed", "pending-approval", "in-pr"):
        history(it, by="learner", event=f"proposal revised after '{it['status']}': back to open")
        it["status"] = "open"
    write(a.inbox, items)
    print(f"{it['id']} proposal stored: {a.change} in {target(it)}")


def cmd_list(a):
    want = OLD_STATUS.get(a.status, a.status)
    for it in read(a.inbox):
        if want and it["status"] != want:
            continue
        dec = it.get("decision") or {}
        extra = f" ({dec.get('by')}: {dec.get('decision')})" if it["status"] == "pending-approval" else \
            f" ({(it.get('pr') or {}).get('url')})" if it["status"] == "in-pr" else ""
        print(f"{it['id']} {it['status']:<16}{extra} [{it['kind']}{'/' + it['client'] if it.get('client') else ''}] "
              f"{it['rule']}  ({it['who']}: \"{one_line(it['said'])[:80]}\")")


def route(it):
    if it["kind"] == "concept":
        return "job card"
    if it["kind"] == "unsure":
        return "kind first"
    return "push to main" if is_owner() else "pull request (owner merges)"


def cmd_propose(a):
    items = [it for it in read(a.inbox) if it["status"] in ("open", "pending-approval")]
    if not items:
        print("nothing to propose")
        return
    ask = [it for it in items if it["kind"] == "unsure"]
    rules = [it for it in items if it["kind"] in ("general", "client")]
    print("| # | Rule (exact line) | Kind | Goes to | Route | Evidence | Source | Note |\n"
          "|---|---|---|---|---|---|---|---|")
    for it in rules:
        p = it.get("proposal") or {}
        line = p.get("new_line") or it["rule"]
        if p.get("change") == "replace":
            line = f"{line} (replaces: {p.get('old_line')})"
        if p.get("change") == "remove":
            line = f"remove: {p.get('old_line')}"
        src = "repeated in client profiles" if it.get("promote_from") else \
              f"{it['who']} said" if it.get("source") == "said" else f"inferred ({it['who']})"
        notes = []
        if not p:
            notes.append("no learner proposal yet")
        if it.get("promote_from"):
            notes.append("promotion from " + ", ".join(it["promote_from"])
                         + ("; removes: " + " / ".join(p.get("remove_lines") or []) if p.get("remove_lines") else ""))
        if it["status"] == "pending-approval":
            dec = it.get("decision") or {}
            notes.append(f"{dec.get('by')} said {dec.get('decision')}"
                         + (f" ({dec.get('note')})" if dec.get("note") else ""))
        print(f"| {it['id']} | {cell(line)} | {it['kind']}{' (' + it['client'] + ')' if it.get('client') else ''} | "
              f"`{cell(target(it))}` | {route(it)} | {cell(it.get('evidence') or it['said'])} | {cell(src)} | "
              f"{cell('; '.join(notes))} |")
    for it in ask:
        print(f"\nASK which kind: {it['id']} \"{it['rule']}\" (every client / this client / this concept only?)")
    how = "commit + push to main" if is_owner() else "a pull request that changes nothing until the plugin owner merges it"
    print(f"\n{len(rules)} to approve, change or drop; {len(ask)} need a kind first. "
          f"Nothing goes into the plugin without {editor_label()}'s yes; approved rules go in as {how}."
          + no_setup_note())


def cmd_decide(a):
    items = read(a.inbox)
    it = find(items, a.id)
    by_editor = is_editor(a.by)
    if it["status"] == "applied" and not a.reopen:
        sys.exit(f"{a.id} is already applied ({(it.get('applied') or {}).get('commit')}); pass --reopen to change it")
    prev = it.get("decision") or {}
    if not by_editor and prev and is_editor(prev.get("by")):
        sys.exit(f"{a.id} was decided by {prev.get('by')} ({prev.get('decision')}), the editor running the job; "
                 "only they can change that")
    wait = (f"waits for {editor_name()}, the editor running the job" if editor_name()
            else "waits for the editor running the job") + no_setup_note()
    if a.decision.startswith("kind="):
        k = a.decision.split("=", 1)[1]
        if k not in KINDS[:3]:
            sys.exit("kind must be general, client or concept")
        if k == "client" and not (a.client or it.get("client")):
            sys.exit("--client is required when making it a client lesson")
        if not by_editor:
            it["status"] = "pending-approval"
            it["decision"] = dict(by=a.by, at=now(), decision=f"kind={k}", note=a.note, client=a.client)
            history(it, **it["decision"])
            print(f"{it['id']} -> pending-approval ({a.by} suggests {k}; {wait})")
        else:
            history(it, by=a.by, event=f"kind {it['kind']} -> {k}")
            it["kind"] = k
            if k != "general":
                it.pop("promote_from", None)
            if a.client:
                it["client"] = a.client
            it.pop("proposal", None)                 # the placement changed: the learner proposes again
            it["status"] = "concept" if k == "concept" else "open"
            it.pop("decision", None)
            print(f"{it['id']} is now {k} -> {target(it)}"
                  + ("" if k == "concept" else " (open again: propose its exact line, then the editor approves)"))
    else:
        if it["kind"] == "unsure":
            sys.exit("ask the editor which kind first (decide ID kind=general|client|concept)")
        if it["kind"] == "concept":
            sys.exit("concept lessons never go into the plugin")
        if a.decision == "change" and not a.rule:
            sys.exit("change needs --rule with the editor's version")
        dec = dict(by=a.by, at=now(), decision=a.decision, note=a.note, rule=a.rule)
        history(it, **dec)
        it["decision"] = dec
        if not by_editor:
            it["status"] = "pending-approval"
            print(f"{it['id']} -> pending-approval ({a.by}: {a.decision}; {wait})")
        else:
            if a.decision == "change":
                it["rule_before"] = it["rule"]
                it["rule"] = one_line(a.rule)
                if it.get("proposal"):
                    it["proposal"]["new_line"] = one_line(a.rule)
            it["status"] = {"approve": "approved", "change": "changed", "drop": "dropped"}[a.decision]
            it.pop("pr", None)
            print(f"{it['id']} -> {it['status']}"
                  + (f" (goes in as {route(it)})" if it["status"] != "dropped" else ""))
    write(a.inbox, items)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "editor"


def cmd_ship(a):
    """Print (never run) the commands that put the approved lessons into the plugin."""
    items = read(a.inbox)
    ready = [it for it in items if it["status"] in ("approved", "changed") and it["kind"] in ("general", "client")]
    dropped = [it for it in items if it["status"] == "dropped"]
    concept = os.path.splitext(os.path.basename(a.inbox))[0]
    repo = os.path.expanduser(a.repo or editor().get("plugin_repo") or "~/code/beon-edit")
    day = datetime.date.today().isoformat()
    if not ready:
        print("nothing approved to ship (lessons.py list INBOX --status approved / changed)")
        return
    if not os.path.isdir(os.path.join(repo, ".git")):
        print(f"WARNING: {repo} is not a git clone; set plugin_repo in ~/.beon-edit/editor.json")
    ids = ", ".join(it["id"] for it in ready)
    msg = f"Learn from {concept}: {ready[0]['rule'][:60]}" + (f" (+{len(ready) - 1} more)" if len(ready) > 1 else "")
    body = [f"Lessons from {concept}, approved by {editor_label()} ({day}). Changes nothing until the plugin owner merges.",
            "", "| # | Rule | Kind | File | Who / evidence |", "|---|---|---|---|---|"]
    for it in ready:
        p = it.get("proposal") or {}
        body.append(f"| {it['id']} | {cell(p.get('new_line') or it['rule'])} | {it['kind']} | `{cell(target(it))}` | "
                    f"{cell(it['who'])}: {cell(it.get('evidence') or it['said'])} |")
    if dropped:
        body += ["", "Dropped by the editor (listed so the owner can overrule):"]
        body += [f"- {it['id']} {it['rule']}" for it in dropped]
    body_txt = "\n".join(body) + "\n"
    q = lambda s: "'" + s.replace("'", "'\\''") + "'"
    print(f"# {len(ready)} lesson(s): {ids}   plugin clone: {repo}")
    if is_owner():
        print("# plugin owner: commit + push to main (apply-rules.md 'Plugin owner')")
        print(f"git -C {q(repo)} switch main && git -C {q(repo)} pull --ff-only")
        print("# ... make exactly the stored proposals, bump versions, changelog line, show the diff ...")
        print(f"git -C {q(repo)} pull --ff-only")
        print(f"git -C {q(repo)} add -A && git -C {q(repo)} commit -m {q(msg)}")
        print(f"git -C {q(repo)} push origin main")
        print(f"# then for each: lessons.py applied {a.inbox} <id> --file <path> --commit <sha>")
        return
    if not editor_name():
        sys.exit("no editor name for the branch: write ~/.beon-edit/editor.json (name) first, "
                 "house-rules references/intake.md")
    branch = f"lessons/{slug(editor_name())}-{slug(concept)}-{day}"
    body_file = a.body_out or os.path.join(os.path.dirname(os.path.abspath(a.inbox)), f"{concept}-pr.md")
    with open(body_file, "w", encoding="utf-8") as f:
        f.write(body_txt)
    print("# not the plugin owner: branch + pull request, never main (apply-rules.md 'Other editors')")
    print(f"git -C {q(repo)} fetch origin")
    print(f"git -C {q(repo)} switch -c {q(branch)} origin/main")
    print("# ... make exactly the stored proposals (no version bump, no changelog: the owner does those on merge) ...")
    print(f"git -C {q(repo)} add -A && git -C {q(repo)} commit -m {q(msg)}")
    print(f"git -C {q(repo)} push -u origin {q(branch)}")
    print("# push refused (no write access): fork once, then push the branch to the fork")
    print(f"#   (cd {q(repo)} && gh repo fork --remote --remote-name fork) && git -C {q(repo)} push -u fork {q(branch)}")
    print(f"(cd {q(repo)} && gh pr create --base main --head {q(branch)} --title {q(msg)} --body-file {q(body_file)})")
    print(f"#   from a fork: --head <your-github-user>:{branch}")
    print(f"git -C {q(repo)} switch main")
    print(f"# then for each: lessons.py applied {a.inbox} <id> --file <path> --pr <url>")
    print(f"# PR body written to {body_file}")


def cmd_applied(a):
    items = read(a.inbox)
    it = find(items, a.id)
    if it["status"] not in ("approved", "changed", "in-pr"):
        sys.exit(f"{a.id} is {it['status']}: only lessons the editor approved or changed can be applied")
    if not (it.get("decision") or {}).get("by"):
        sys.exit(f"{a.id} has no recorded decision")
    if a.pr:
        it["status"] = "in-pr"
        it["pr"] = dict(url=a.pr, file=a.file, at=now())
        history(it, by="apply", event=f"pull request {a.pr} ({a.file})")
        write(a.inbox, items)
        print(f"{a.id} in-pr: {a.pr} (changes nothing until the plugin owner merges; then --commit <merge sha>)")
        return
    if not a.commit:
        sys.exit("pass --commit <sha> (pushed to main / merged) or --pr <url> (pull request opened)")
    if it["status"] != "in-pr" and not is_owner():
        sys.exit(f"{a.id}: only the plugin owner pushes to main. Open a pull request (lessons.py ship), record it "
                 "with --pr <url>, and pass --commit once it is merged")
    it["status"] = "applied"
    it["applied"] = dict(file=a.file, commit=a.commit, at=now())
    history(it, by="apply", event=f"applied in {a.file} ({a.commit})")
    write(a.inbox, items)
    print(f"{a.id} applied in {a.file} ({a.commit})")


STOP = set("a an the and or of to in on at for with is are be it its as by from this that than then when "
           "into per each every not no only".split())


def words(line):
    line = re.sub(r"\[(?:Tim|inferred)[^\]]*\]|\[[^\]]*\b20\d\d\b[^\]]*\]|\([^)]*20\d\d[^)]*\)", " ", line)
    return {w for w in re.sub(r"[^a-z0-9%.]+", " ", line.lower()).split() if w not in STOP and len(w) > 1}


def cmd_repeats(a):
    d = os.path.join(a.plugin_dir, "skills", "client-styles", "references")
    profiles = {}
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".md") or fn.startswith("_"):
            continue
        for line in open(os.path.join(d, fn), encoding="utf-8"):
            if not line.startswith("- "):
                continue
            body = line[2:].strip()
            if re.search(r":\s*ask\b", body, re.I) or body.lower().startswith("ask"):
                continue
            for sent in re.split(r"(?<=[.;])\s+", body):         # bullets often hold several rules
                w = words(sent)
                if len(w) >= 3:
                    profiles.setdefault(fn[:-3], []).append((sent, w))
    names = sorted(profiles)
    hits = 0
    for i, p in enumerate(names):
        for q in names[i + 1:]:
            for la, wa in profiles[p]:
                for lb, wb in profiles[q]:
                    j = len(wa & wb) / len(wa | wb)
                    if j >= a.min_overlap:
                        hits += 1
                        print(f"{j:.2f}\n  {p}: {la}\n  {q}: {lb}")
    print(f"{hits} candidate pair(s). The learner agent judges them: same rule, no counter-example in another "
          "profile -> add it as a general lesson with --promote-from (the editor decides).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("add"); p.add_argument("inbox")
    p.add_argument("--said", required=True); p.add_argument("--rule", required=True)
    p.add_argument("--kind", required=True, choices=KINDS)
    p.add_argument("--who", required=True, help="who said it (the editor on the job card, or who taught it)")
    p.add_argument("--stage"); p.add_argument("--where"); p.add_argument("--client")
    p.add_argument("--source", default="said", choices=("said", "inferred")); p.add_argument("--evidence")
    p.add_argument("--promote-from")
    p = sp.add_parser("revise"); p.add_argument("inbox"); p.add_argument("id")
    p.add_argument("--file", required=True); p.add_argument("--section", default="")
    p.add_argument("--change", required=True, choices=("add", "replace", "remove"))
    p.add_argument("--new-line", default=""); p.add_argument("--old-line")
    p.add_argument("--kind", choices=KINDS[:3]); p.add_argument("--client"); p.add_argument("--rule")
    p.add_argument("--remove-lines", nargs="*")
    p = sp.add_parser("list"); p.add_argument("inbox"); p.add_argument("--status")
    p = sp.add_parser("propose"); p.add_argument("inbox")
    p = sp.add_parser("decide"); p.add_argument("inbox"); p.add_argument("id"); p.add_argument("decision")
    p.add_argument("--rule"); p.add_argument("--by", required=True, help="who decided: the editor named on the job card")
    p.add_argument("--note"); p.add_argument("--client"); p.add_argument("--reopen", action="store_true")
    p = sp.add_parser("ship"); p.add_argument("inbox")
    p.add_argument("--repo", help="plugin clone (default: editor.json plugin_repo)")
    p.add_argument("--body-out", help="write the pull request body here")
    p = sp.add_parser("applied"); p.add_argument("inbox"); p.add_argument("id")
    p.add_argument("--file", required=True); p.add_argument("--commit"); p.add_argument("--pr")
    p = sp.add_parser("repeats"); p.add_argument("plugin_dir"); p.add_argument("--min-overlap", type=float, default=0.5)
    a = ap.parse_args()
    if a.cmd == "decide" and not (a.decision in ("approve", "change", "drop") or a.decision.startswith("kind=")):
        sys.exit("decision must be approve, change, drop or kind=<general|client|concept>")
    if a.cmd == "revise" and a.change != "remove" and not one_line(a.new_line):
        sys.exit("--new-line is required for add and replace")
    {"add": cmd_add, "revise": cmd_revise, "list": cmd_list, "propose": cmd_propose, "decide": cmd_decide,
     "ship": cmd_ship, "applied": cmd_applied, "repeats": cmd_repeats}[a.cmd](a)


if __name__ == "__main__":
    main()
