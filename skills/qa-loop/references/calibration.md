# QA calibration on finished edits

Status: not calibrated (built 10 Nov 2026; run this before trusting the *(calibrating)* thresholds)

Calibration is per studio, and the studio is Beon: the thresholds are calibrated on Tim's finished timelines,
because Beon's house rules are his. Any Beon editor's approved finals can be added to the set later; each one
is checked the same way.

The rule (Tim, Q25, 9 Nov 2026): before QA goes live, run it read-only on 2-3 finished timelines. A final the
editor signed off is correct by definition. A rule or threshold that fails it is wrong or too strict, and gets
fixed before QA can force fixes.

## Which timelines

Pick finals that cover different clients and stages, e.g. Tim's:
- Namir Mikha C7 (A-roll, B-roll, grade, ending)
- Simone Nov C03 (A-roll framing, Dynamic Zoom holds, subtitles on the cut)
- Hired Home Nov S2 C2 (B-roll speed and Gyroflow)
Confirm the list and the exact timeline names with the editor whose finals they are.

## How

1. Only when that editor isn't using Resolve. Nothing in their project changes: the qa-manager is read-only,
   proxy renders restore their settings.
2. For each timeline and each stage it has: run the qa-manager with `calibration: true`, round 1, a QA folder
   outside the job (e.g. `<shoot>/_shotlog/qa/calibration-<timeline>/`). No plan JSON exists for a hand-made
   B-roll, so the reason checks (B-02, B-08) are expected in `not_checked`.
3. Collect every finding. For each: is the rule wrong, the threshold too tight, the script measuring badly, or
   is it a real slip in the final (rare; ask the editor whose final it is)?
4. Write the results table below, then propose the changes (thresholds, rule wording, scripts) to the editor
   running the calibration. What they approve is a general lesson: the plugin owner (editor.json
   `plugin_owner: true`) commits and pushes it; any other editor opens a pull request, which changes nothing
   until Tim merges it.
5. When a full run on all chosen finals comes back with no hard or judgement findings (or each one explained
   and accepted), set Status to `calibrated (<date>, <timelines>)`, bump the plugin version, and say so. This
   is a general change too (owner pushes, others send a pull request). Until then `qa_round.py` runs the loop
   in shadow mode (reports, forces nothing).

## Known to watch

- B-04 jitter thresholds were tuned when shots were measured at 48%. At 100% the camera moves further per
  frame: check whether Tim's 100% shots read as "shake" and adjust broll_auto.py's `clean()` and the motion card tiers.
- A-06 air: client profiles differ (Green runs tighter).
- G-03 neutral target (Cb -5, Cr +5) came from Namir; Arriva moves per concept.

## Results

| Date | Editor | Timeline | Stage | Finding | Measured | Rule / threshold | Verdict (rule wrong / threshold / script / real slip) | Change made |
|---|---|---|---|---|---|---|---|---|
