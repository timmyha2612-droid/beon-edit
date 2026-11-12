---
name: learn-from-tim
description: "This skill should be used during and after every Beon Media editing job to learn the editor's editing (Tim's or any editor running a Beon job): when the editor corrects the edit or explains how something should be done mid-job (log it in the lessons inbox right away), at the end of every job (run the learner agent and put the rule proposals to the editor), after the editor finishes or changes an edit Claude worked on, or when they ask to \"learn my edit\", \"learn my colour grading\", \"compare your version to mine\", \"analyse why I changed it\", \"remember this for next time\", \"this is only for Namir\". Sorts each lesson into general / client / concept, and changes the plugin only after the editor's yes (the plugin owner pushes it; other editors send a pull request).\n"
metadata:
  version: "0.3.0"
---

# Learn from the editor (Tim, 9 Nov 2026)

Editing is a big skill, and the editor running the job is the teacher (Tim or any editor on a Beon job; the job
card's `Editor:` line). Two kinds of teaching reach us: what they **say** during a job (corrections, how they want
something, why), and what they **do** to the edit afterwards. Both are written down the moment they appear, sorted
by who they apply to, and only become rules after the editor says yes. There is no separate approver.

## 0. Always listening (during every job)

- The `learn_listener` hook reminds you on every message while a job card is open. When a message corrects
  the edit, says how something should be done, or explains why, log it **before** acting on it:
  `python3 scripts/lessons.py add <inbox> --who "<editor>" --said "<their words>" --rule "<one-line rule>" --kind general|client|concept|unsure [--client <profile>] [--stage aroll|broll|grade|subtitles|final|footage|qa]`.
  The inbox path is on the job card (`Lessons inbox:`).
- Plain instructions for this edit alone ("move R4 two frames") are not lessons; don't log them. A reason or a
  "always / never / for this client" is.
- Sort it as you log it (Q6). When it isn't clear, use `unsure`; it becomes a question at the end of the job.

  | Kind | Applies to | Lands in (after the editor's yes) |
  |---|---|---|
  | general | every client | the stage skill, the B-roll rulebook, a QA checklist, or house-rules |
  | client | only this client | `client-styles/references/<client>.md` |
  | concept | only this video | the job card's concept-only notes and the shot log; never the plugin |

- Concept lessons apply straight away for this job (add them to the job card). General and client lessons
  apply to this job too when the editor gave them, but only become plugin rules through section 5.

## End of every job

Run sections 1-2 when the editor has finished their version (or asks to learn from it), then 3-5 every time.

## 1. Snapshot the editor's version

Read-only, and it needs no job card when the editor only asks to learn from a finished edit (it changes nothing). Nothing in the project changes: no grade tweaks, no timeline edits, no playhead moves if avoidable. If the editor needs Resolve while this runs, stop all Resolve calls; file analysis (and the device VM, if run_env is device-vm) can continue.

- Ask the editor for their finished timeline name (never guess it).
- Export every relevant timeline: `timeline.Export('<scratch>/<name>.drt', resolve.EXPORT_DRT)`, where `<scratch>` is `beon_config.scratch_dir(client, shoot, concept)` (editor.json `scratch_root`). The DRT is a zip: `SeqContainer/<id>.xml` (largest one) holds every clip with Name, Start, Duration, In, MediaFilePath and the grade `<Body>`.
- Read the timeline items through the API: per track, start/end, source start/end seconds (`GetSourceStartTime` minus the clip's Start TC), Zoom/Pan/Tilt, clip colour, markers, audio tracks and enable states.
- Keep Claude's own version for comparison (build JSON, cut list, B-roll plan in the shot log `plans/` or the job's scratch folder, `editor.json` `scratch_root`).
- Note the snapshot time: re-grades the editor makes afterwards won't be in it.

## 2. Measure the differences

A-roll:
- Map both cut lists onto the transcript (word timings) to see lines added, removed, split or trimmed.
- `aroll-cut/scripts/cut_air.py` on both lists: head air, tail air, join silence, inner pauses kept or removed.
- `scripts/jumpcut_check.py CLIP PIECES.json --card <job card>`: visibility of each same-framing cut (pixel difference, face shift %), and which ones the editor left uncovered. `--card` takes the timeline size from the Delivery line.
- Running time, speech time, punch-in pattern.

B-roll:
- Shot list diff: removed, added, slipped (source in changed), retimed (source span ÷ duration = speed), re-ordered, zoomed.
- Motion cards (`broll/scripts/motion_card.py`) on any shot the editor slipped or retimed, comparing Claude's window with theirs.
- Coverage %, on-camera stretches, break length and shots, outro.

Grade:
- `colour-grade/scripts/grade_read.py` for Temp, Tint, Global and changed nodes per clip; group shared grades (scene grading).
- Export one LUT per grade group (never one per clip) and measure frames through them with numpy (`colour-grade/scripts/measnp.py`, `calib.py`; in the device VM if run_env is device-vm) to see where neutrals and the main white surface landed, before (template) and after (the editor). `meas.py` and `batch.py` are legacy: never run them inside Resolve (colour-grade, "Keep Resolve light").

Music and audio:
- Music clip In (DRT `<In>`) and `scripts/music_sections.py SONG.wav IN_FRAMES <fps from the job card Delivery line>` for lifts and phrase dips; compare with story beats, the break and the end card.
- Dialogue track changes (enhanced file on A2, A1 off) and filenames.

Footage sort: count `sort.editor_changes` in the shot log (older logs: `sort.tim`) per field and per
client, so repeated corrections to the sort become proposals too.

## 3. Run the learner agent

Run `beon-edit:learner` (fresh agent) with: the job card path, the inbox path, the plugin folder (`editor.json`
`plugin_repo`, see `references/apply-rules.md`), the client profile, the QA folder, Claude's version (plans, cut
list, timeline) and the editor's finished timeline if there is one, whether the editor is in Resolve, and whether
this editor is the plugin owner (`editor.json` `plugin_owner`). It compares, sorts, checks every lesson against the
existing rules, looks for client rules that repeat across clients (Q17), and returns proposals and at most 4
questions. It stores each proposal in the inbox (`lessons.py revise`), so the table the editor approves is exactly
what would change. It changes nothing in the plugin or the edit, and decides nothing.

## 4. Ask the editor, once, at the end

- Show the proposals as one short table: rule | kind | where it goes | route | evidence | said or inferred
  (`lessons.py propose <inbox>` prints it; route is "push to main" for the plugin owner, "pull request" for
  everyone else). Promotions to general rules and duplicates get a line each.
- Ask the learner's questions (at most 4) with the pop-up question tool, suggested answers first (Q16).
  Nothing mid-flow unless it blocks the work.
- The editor answers each proposal: **approve**, **change** (their wording becomes the rule) or **drop**. Record it:
  `lessons.py decide <inbox> L-003 approve|change|drop --by "<editor>" [--rule "the editor's wording"]`. Unsure
  kinds: `decide <inbox> L-004 kind=client --client <profile> --by "<editor>"`. `--by` must be the editor in
  `editor.json` (name or alias); anyone else's decision is stored as `pending-approval` and waits for the editor.
- **The rules page** (Q8, owner only): if `editor.json` `rules_page` is set and this editor is the plugin owner,
  read its `marks/<rule id>` and `additions/` collections with ArtifactData. Each mark is the owner's own decision:
  log it (`lessons.py add --who "<owner>" --said "<their note>"`), have the learner `revise` it to the exact line, and
  record `decide ... --by "<owner>"` ("Change" = the note becomes the rule; "Remove" = drop the rule, not invert it).
  After applying, update the page from the plugin (apply-rules step 8). `rules_page` unset, or not the owner: skip
  this step and say nothing about it.

## 5. Write it into the plugin (only after the editor's yes)

`lessons.py ship <inbox>` prints the exact commands for this editor; it runs nothing.
- **Plugin owner** (`editor.json` `plugin_owner: true`): follow `references/apply-rules.md` "Plugin owner": edit
  the plugin clone, bump the version, add a changelog line, commit and push to main; then
  `lessons.py applied <inbox> L-003 --file ... --commit ...` for each.
- **Any other editor:** follow `references/apply-rules.md` "Other editors": a branch
  `lessons/<editor>-<concept>-<date>`, one commit, and a pull request with `gh`. Never push to main. Record it with
  `lessons.py applied <inbox> L-003 --file ... --pr <url>` (status `in-pr`). The pull request changes nothing until
  Tim (the plugin owner) merges it; tell the editor the link.
- Concept notes: into the job card's concept-only notes and the shot log `lessons`. Same for every editor.
- Also write back to the shot log (not the plugin): usage updated to the editor's final (`status: final`) and new
  shot log `lessons`. Numbers from their final reach the client profile only as approved lessons.
- Scratch images and data stay out of synced folders (`editor.json` `synced_folders`; never Dropbox); tell the
  editor where they are.
