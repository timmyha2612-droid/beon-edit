---
name: learn-from-tim
description: "This skill should be used after Tim finishes or changes an edit Claude worked on, or when he asks to \"learn my edit\", \"learn my colour grading\", \"compare your version to mine\", \"analyse why I changed it\", or \"check what I did\". It reads Tim's version strictly read-only, measures the differences against Claude's version, asks Tim why, and updates the rules (project docs, memory, shot log, skills).\n"
metadata:
  version: "0.1.0"
---

# Learn from Tim

Read-only. Nothing in the project changes during this skill: no grade tweaks, no timeline edits, no playhead moves if avoidable. If Tim needs Resolve while this runs, stop all Resolve calls; the VM and cloud analysis can continue.

## 1. Snapshot Tim's version

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
- Motion cards (`broll-qaqc/scripts/motion_card.py`) on any shot Tim slipped or retimed, comparing Claude's window with his.
- Coverage %, on-camera stretches, break length and shots, outro.

Grade:
- `colour-grade/scripts/grade_read.py` for Temp, Tint, Global and changed nodes per clip; group shared grades (scene grading).
- Export per-clip LUTs and render frames through them (`colour-grade/scripts/meas.py`, `batch.py`) to measure where neutrals and the main white surface landed, before (template) and after (Tim).

Music and audio:
- Music clip In (DRT `<In>`) and `scripts/music_sections.py` for lifts and phrase dips; compare with story beats, the break and the end card.
- Dialogue track changes (enhanced file on A2, A1 off) and filenames.

## 3. Ask why

- Write the comparison first: what Tim kept, what he changed, and the likely reason for each, with numbers.
- Then ask about the uncertain reasons through the pop-up question tool (2–4 questions, suggested answers, recommended first). Don't ask what the data already answers.
- Separate what Tim said from what was inferred from one example.

## 4. Write it back

- Project doc: a lessons doc per concept or topic (e.g. "Tim edit lessons C7", "Tim colour grading lessons").
- Shot log: usage updated to Tim's final version (`status: final`), plus new `lessons`.
- The "Tim's Edit System" artifact page: add or adjust rules so Tim can mark them (`marks/<rule id>` and `additions/` collections are read back with ArtifactData).
- Client profile (client-styles `references/<client>.md`): add or adjust that client's rules with numbers from Tim's final, tagged [Tim] or [inferred] with the concept and date.
- Propose skill updates in this plugin when a rule is confirmed. Rules Tim marked "Change" use his note as the new rule; "Remove" means drop it, not invert it.
- Scratch images and data stay outside Dropbox; tell Tim where they are.
