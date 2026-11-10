---
name: learn-from-tim
description: "This skill should be used during and after every Beon Media editing job to learn Tim's editing: when Tim (or the editor) corrects the edit or explains how something should be done mid-job (log it in the lessons inbox right away), at the end of every job (run the learner agent and put the rule proposals to Tim), after Tim finishes or changes an edit Claude worked on, or when he asks to \"learn my edit\", \"learn my colour grading\", \"compare your version to mine\", \"analyse why I changed it\", \"remember this for next time\", \"this is only for Namir\". Sorts each lesson into general / client / concept, and changes the plugin only after Tim's yes.\n"
metadata:
  version: "0.2.1"
---

# Learn from Tim (Tim, 9 Nov 2026)

Editing is a big skill, and Tim is the teacher. Two kinds of teaching reach us: what he **says** during a job
(corrections, how he wants something, why), and what he **does** to the edit afterwards. Both are written down
the moment they appear, sorted by who they apply to, and only become rules after Tim says yes.

## 0. Always listening (during every job)

- The `learn_listener` hook reminds you on every message while a job card is open. When a message corrects
  the edit, says how something should be done, or explains why, log it **before** acting on it:
  `python3 scripts/lessons.py add <inbox> --who "<editor>" --said "<their words>" --rule "<one-line rule>" --kind general|client|concept|unsure [--client <profile>] [--stage aroll|broll|grade|subtitles|final|footage|qa]`.
  The inbox path is on the job card (`Lessons inbox:`).
- Plain instructions for this edit alone ("move R4 two frames") are not lessons; don't log them. A reason or a
  "always / never / for this client" is.
- Sort it as you log it (Q6). When it isn't clear, use `unsure`; it becomes a question at the end of the job.

  | Kind | Applies to | Lands in (after Tim's yes) |
  |---|---|---|
  | general | every client | the stage skill, the B-roll rulebook, a QA checklist, or house-rules |
  | client | only this client | `client-styles/references/<client>.md` |
  | concept | only this video | the job card's concept-only notes and the shot log; never the plugin |

- Concept lessons apply straight away for this job (add them to the job card). General and client lessons
  apply to this job too when Tim gave them, but only become plugin rules through section 4.

## End of every job

Run sections 1-2 when Tim has finished his version (or asks to learn from it), then 3-5 every time.

## 1. Snapshot Tim's version

Read-only, and it needs no job card when Tim only asks to learn from a finished edit (it changes nothing). Nothing in the project changes: no grade tweaks, no timeline edits, no playhead moves if avoidable. If Tim needs Resolve while this runs, stop all Resolve calls; the VM and cloud analysis can continue.


- Export every relevant timeline: `timeline.Export('/tmp/claude_drx/<name>.drt', resolve.EXPORT_DRT)`. The DRT is a zip: `SeqContainer/<id>.xml` (largest one) holds every clip with Name, Start, Duration, In, MediaFilePath and the grade `<Body>`.
- Read the timeline items through the API: per track, start/end, source start/end seconds (`GetSourceStartTime` minus the clip's Start TC), Zoom/Pan/Tilt, clip colour, markers, audio tracks and enable states.
- Keep Claude's own version for comparison (build JSON, cut list, B-roll plan in the shot log `plans/` or the VM).
- Note the snapshot time: re-grades Tim makes afterwards won't be in it.

## 2. Measure the differences

A-roll:
- Map both cut lists onto the transcript (word timings) to see lines added, removed, split or trimmed.
- `aroll-cut/scripts/cut_air.py` on both lists: head air, tail air, join silence, inner pauses kept or removed.
- `scripts/jumpcut_check.py`: visibility of each same-framing cut (pixel difference, face shift %), and which ones Tim left uncovered.
- Running time, speech time, punch-in pattern.

B-roll:
- Shot list diff: removed, added, slipped (source in changed), retimed (source span ÷ duration = speed), re-ordered, zoomed.
- Motion cards (`broll/scripts/motion_card.py`) on any shot Tim slipped or retimed, comparing Claude's window with his.
- Coverage %, on-camera stretches, break length and shots, outro.

Grade:
- `colour-grade/scripts/grade_read.py` for Temp, Tint, Global and changed nodes per clip; group shared grades (scene grading).
- Export one LUT per grade group (never one per clip) and measure frames through them in the device VM with numpy (`colour-grade/scripts/measnp.py`, `calib.py`) to see where neutrals and the main white surface landed, before (template) and after (Tim).

Music and audio:
- Music clip In (DRT `<In>`) and `scripts/music_sections.py` for lifts and phrase dips; compare with story beats, the break and the end card.
- Dialogue track changes (enhanced file on A2, A1 off) and filenames.

## 3. Run the learner agent

Run `beon-edit:learner` (fresh agent) with: the job card path, the inbox path, the plugin folder (the git clone,
see `references/apply-rules.md`), the client profile, the QA folder, Claude's version (plans, cut list, timeline)
and Tim's finished timeline if there is one, and whether Tim is in Resolve. It compares, sorts, checks every
lesson against the existing rules, looks for client rules that repeat across clients (Q17), and returns proposals
and at most 4 questions. It stores each proposal in the inbox (`lessons.py revise`), so the table Tim approves is
exactly what would change. It changes nothing in the plugin or the edit.

## 4. Ask Tim, once, at the end

- Show the proposals as one short table: rule | kind | where it goes | evidence | Tim said or inferred
  (`lessons.py propose <inbox>` prints it). Promotions to general rules and duplicates get a line each.
- Ask the learner's questions (at most 4) with the pop-up question tool, suggested answers first (Q16).
  Nothing mid-flow unless it blocks the work.
- Tim answers each proposal: **approve**, **change** (his wording becomes the rule) or **drop**. Record it:
  `lessons.py decide <inbox> L-003 approve|change|drop --by "<editor>" [--rule "Tim's wording"]`. Unsure kinds:
  `decide <inbox> L-004 kind=client --client <profile> --by "<editor>"`.
- **Tim's marks on the "Tim's Edit System" page** (Q8; its link is `rules_page` in `~/.beon-edit/config.json`):
  read the `marks/<rule id>` and `additions/` collections with ArtifactData. Each mark is Tim's own decision:
  log it (`lessons.py add --who Tim --said "<his note>"`), have the learner `revise` it to the exact line, and record
  `decide ... --by Tim` ("Change" = his note becomes the rule; "Remove" = drop the rule, not invert it).
  After applying, update the page from the plugin (apply-rules step 8).

## 5. Write it into the plugin (only after Tim's yes)

- **The editor is Tim:** follow `references/apply-rules.md`: edit the plugin clone, bump the version, add a
  changelog line, commit and push; then `lessons.py applied <inbox> L-003 --file ... --commit ...` for each.
- **The editor isn't Tim** (Q1): only Tim turns lessons into general or client rules. Their decisions are stored as
  `pending-tim`. Follow `references/apply-rules.md` "Not Tim": a branch with the proposed changes and a pull
  request for Tim, or, without push access, `<shoot>/_shotlog/lessons/pending-for-tim.md`. Tell the editor
  where it went.
- Concept notes: into the job card's concept-only notes and the shot log `lessons`.
- Also write back to the shot log (not the plugin): usage updated to Tim's final (`status: final`) and new shot
  log `lessons`. Numbers from his final reach the client profile only as approved lessons.
- Scratch images and data stay outside Dropbox; tell Tim where they are.
