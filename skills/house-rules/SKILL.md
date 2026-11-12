---
name: house-rules
description: "This skill should be used at the start of any Beon Media editing job (DaVinci Resolve concept videos, interviews, B-roll, colour grading, footage sorting, subtitles), when the editor says \"start the edit\", \"put together concept X\", \"help me with the A-roll / B-roll / grade\", \"learn my edit\", when deciding which Beon editing skill applies, when ~/.beon-edit/editor.json is missing (first use on a machine), or whenever any other beon-edit stage skill is about to start and no job card exists for this job yet. It holds the working agreement, the intake (editor setup, client profile, shoot, job card), the mandatory opening grilling and the map of the other skills.\n"
metadata:
  version: "0.9.0"
---

# Beon edit: house rules

How to work on any Beon edit. Read this first, then load the skill for the stage at hand.

Beon is the studio: its house rules, thresholds, looks and track layout are built into the skills and
are never asked. **The editor running the job decides everything else**: answers the grilling, approves
every gate, approves lessons. There is no separate approver. "The editor" is the `name` in
`~/.beon-edit/editor.json`; the job card's `Stages:` line says who does music, grade, subtitles and the
final pass. Tim is the plugin owner (he merges pull requests) and also an editor like anyone else.

The intake standard is `references/intake.md`: four files, read before every job, asked only once.
`scripts/beon_config.py` reads them (`python3 beon_config.py show --card <card>`).

## Skill map

| Stage | Skill | Use when |
|---|---|---|
| 0 | house-rules | Every job: intake, grilling and job card (hard rule), routing |
| 0 | client-styles | Every client job: the client profile (intake §2) is read and completed before grilling |
| 1 | Footage Prep app (`footage-prep` MCP) | Every footage task, first, if editor.json `tools.footage_prep.enabled`. Off or not reachable: one-line notice and the fallback (`references/footage-prep.md`) |
| 1 | resolve-footage-sort | Every edit job, at the start, before B-roll: sort raws into bins, log audio and interviews, write the sort keys to the shot log |
| 1 | shotlog | Any footage task: read the shoot's log first (it merges Footage Prep with Claude's analysis and holds the `shoot` block), write back after |
| 2 | aroll-cut | Story beats and the interview cut (the "meat") |
| 3–5 | broll | Picking, placing and fixing B-roll by the B-roll rulebook (`broll/references/broll-rulebook.md`). Its HARD GATE runs on every pass: broll_auto.py → snippet → gyroflow_headless.py → broll_gate.py PASS (no Gyroflow: broll_auto/broll_gate read `tools.gyroflow.installed: false` and skip the Gyroflow step) |
| after each stage | qa-loop + `beon-edit:qa-manager` / `beon-edit:qa-verifier` agents | Every stage is checked by a separate quality manager before the editor sees it; mistakes fixed, judgement calls double-checked, creative calls to the editor, max 3 rounds then escalate |
| 6 | colour-grade | Grading with the Beon template and the scopes |
| 7 | subtitles | Captions: style test with the editor first, then Fluid Reveal Words subs, resync after edits |
| 7 | finish-pass | The final pass (whoever the card's Stages line names), and how to set the edit up for it |
| all, then 8 | learn-from-tim + `beon-edit:learner` agent | Always on: log every correction and piece of knowledge in the lessons inbox as it's given; at the end of every job the learner proposes rules, the editor approves, then the plugin is updated (owner) or a pull request is opened (everyone else) |

Typical order: editor setup (once) → brief → client profile → shoot block → grill → job card → Footage
Prep → shot log → footage sort → A-roll → QA → editor reviews → B-roll select and place → pacing gate →
QA → editor watch-down → grade → QA → subtitles → QA → final QA on the render → final pass → learn.

## Intake and grilling, every job, no exceptions [Tim, 9 Nov 2026]

Every concept is different, and jobs have started without anyone being asked. So the intake is a hard
rule, and every stage skill checks for the job card before it works. Ask everything through the pop-up
question tool, with suggested answers (recommended first). The editor answers everything.

**Compulsory, and in one go** [Tim, 12 Nov 2026, Simone 1 Arthur St C5: "this step must be compulsory
and need to be done in one go"]. On that job the questions came out in pieces between footage searches
and transcription, and the card was only written after Tim asked when the grilling would start.

1. **Prep (reads only).** Read the brief, editor.json, the client profile, the shoot block and the card.
   Find the footage and do only the reading the questions need: list clips, transcribe to find the
   takes, a contact sheet. Build nothing yet: no cut planning past naming the candidates, no B-roll
   picks, no Resolve writes.
2. **Say it starts.** One line: "Starting the grilling: N questions in M pop-ups."
3. **Ask everything in one block.** Ask all of §1-§3 back to back (4 questions per pop-up, the next pop-up
   straight after, no other tool calls between). That covers the client-profile `ask` fields and open
   questions, the shoot block, and every job-card line the files don't answer: length, beats or takes,
   speakers, stages, delivery, framing, timeline name, subtitles, music, end card, B-roll scope.
   Every concept in the request gets its block before any of them is built.
4. **Write the card at once** (real card plus session copy), then start stage work.
5. **No questions in drips afterwards.** After the card, ask only stage-time questions (intake §6) or
   things the footage turned up that the grilling couldn't know (say which). Something that belonged in
   the grilling and was missed: say so, ask it, and add it to the card.

### 0. Editor setup (once per person and computer)

If `~/.beon-edit/editor.json` is missing (`beon_config.load_editor()["exists"]` is false):

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/skills/house-rules/scripts/doctor.py"` (or
   `~/code/beon-edit/skills/house-rules/scripts/doctor.py` in a clone). It only checks and prints JSON;
   its `detected` block fills the Resolve and Gyroflow fields.
2. Ask the intake §1 questions: name and aliases, footage roots (and whether deleting is allowed there),
   synced folders (Dropbox, iCloud, Google Drive), scratch root, run environment (local Mac, or the
   device VM), Footage Prep on or off, Whisper / CrisperWhisper paths if any, and the plugin clone if
   they will send lessons. `plugin_owner` is `true` only for Tim; never ask anyone else.
3. Run doctor again with the answers (`--footage-root`, `--synced`, or `--editor <draft>`) and tell the
   editor each warning and what it blocks.
4. Write `~/.beon-edit/editor.json` (intake §1 shape). Doctor never writes it; Claude does.

### 1. Client profile

Read `client-styles/references/<slug>.md` (no profile yet: client-styles makes one from `_template.md`).
Ask every front-matter field set to `ask` and every `open_questions` item, then write the answers back
into the front matter and remove the answered questions. Skip what its tagged rules already answer;
confirm `[inferred]` rules that matter for this concept.

### 2. Shoot block

Read `<shoot>/_shotlog/shotlog.json` → `shoot` (shotlog skill). Fill what's missing by probing the
footage (`ffprobe`, card folder names): `cameras[]`, `audio` (mic camera and channel), `multicam`,
`people`, `language`. Confirm with the editor anything probed but not certain (which channel is the lav,
who a person is, the multicam audio reference), then write the block back. Never guess a person's name.

### 3. Job card

Grill per intake §4 and write the card (`references/job-card.md` for where it goes). The required lines
depend on `Kind:` (`beon_config.REQUIRED` / `REQUIRED_OTHER`). On a concept that means: target length
(no default), story beats and which answers to use, speakers, stages (who does A-roll, B-roll, grade,
subs, music, final), delivery (client default or an override), jokes and goofy shots, camera or
multicam, cut style, music break, subtitle look (subtitles Step 0; never assume font, size or colour),
and anything the editor already placed that must not move. Ask only what the files above don't answer.

Only then touch Resolve. The `job_guard` hook blocks any Resolve call that changes the project until the
session copy exists and its required lines are filled; reads are never blocked.

- The editor says "skip the questions" (or the job is a tiny fix): write a card with
  `Grilling: skipped ("<editor's words>")`. Never skip on your own judgement. The Kind's required lines
  still apply (intake §4): fill what you know and write `n/a` on the rest, or use `Kind: fix` for a tiny
  fix (header lines only).
- B-roll in scope and editor.json `tools.gyroflow.installed: false`: tell the editor handheld B-roll can't
  be stabilised, so the gate will want those shots slowed for a valid reason, replaced or marked
  `gyro_skip`. `tools.footage_prep.enabled` false: one-line notice that the fallback (ingest.py + contact
  sheets) is used.
- Second job on the same card, or a new session: read the card, ask "anything changed since <Date>?",
  update it, write the session copy. Don't re-run the full grilling.
- Any stage skill loaded without a job card: stop and run this section first, even if the request named
  the stage directly ("add B-roll to C3").

## Resolve etiquette

- Work in Resolve freely during a job, but the moment the editor says they need it (a quick revision
  mid-run, "can I chime in"), stop every Resolve call, reads included, until they say it's free.
- Finished timelines (e.g. a delivered concept) are for learning from: read them, never edit them unless
  the editor asks.
- A "learn" or "just read" request is strictly read-only: no adjustments of any kind, not even a playhead
  move if it can be avoided. Prefer exports (DRT, LUT) to the viewer.
- Before handing over, check track enable states on the current timeline (A1 has been found disabled on
  an empty timeline the editor created).
- Never delete the editor's timelines. For risky changes, duplicate the timeline first as a backup.

## Files

- Never write media (frames, renders, thumbnails, audio) into a synced folder (editor.json
  `synced_folders`; Dropbox is always refused, `beon_config.in_synced_folder`). Only small text goes in
  a shoot's `_shotlog/` folder. Scratch goes in `<scratch_root>/<client>-<shoot>/<concept>/`
  (`beon_config.scratch_dir`). If run_env is device-vm, scratch lives in the VM home and only sheets are
  staged in a non-synced connected folder.
- Exception that is the editor's, not Claude's: the Gyroflow script renders stabilised clips next to the
  source clip.
- Deleting is off on footage roots unless editor.json `footage_roots[].delete_allowed` is `true`; leave
  scratch for the editor to clear and say where it is.

## Long or unattended runs

- When the editor leaves a job running, run the QA loop (qa-loop) on every stage until it passes or
  escalates after 3 rounds, keep a progress log, and schedule resume reminders (scheduled tasks) in case
  the session limit hits. Delete the reminders when finished.
- Go fast: drop steps that don't add quality, split independent analysis across agents, reuse the shot
  log instead of re-analysing. Follow the fast path and the API gotchas in `references/resolve-recipes.md`
  (ingest once, `cut_pieces.py`, one `run_script` per stage, measure outside Resolve).

## Learning (always on) [Tim, 9 Nov 2026]

- Every job keeps a lessons inbox (job card `Lessons inbox:`). While a job is open, the `learn_listener`
  hook reminds you on every message: when the editor corrects the edit, says how something should be
  done, or explains why, log it right away with its kind: general (every client), client (only this
  client), concept (only this video, never the plugin), or unsure (ask at the end). learn-from-tim
  section 0.
- At the end of every job: the `beon-edit:learner` agent turns the inbox and the editor's finished
  version into proposals; the editor approves, changes or drops each one (at most 4 questions, batched
  at the end). learn-from-tim sections 3-5.
- Where approved lessons go (intake §5): concept → the job card's "Concept-only notes". Client and
  general → the plugin: the plugin owner (editor.json `plugin_owner: true`) commits and pushes to
  `main`; every other editor opens a pull request (`gh`), which changes nothing until Tim merges it.
- Rules confirmed by an editor beat rules inferred from one example. When a rule was inferred from a
  single case, treat it as a default and ask when it matters.
- The plugin is the only real copy of the rules. Owner only (editor.json `rules_page`): the "Tim's Edit
  System" artifact page shows them and collects marks, which come back through learn-from-tim.
