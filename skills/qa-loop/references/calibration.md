# QA calibration on Tim's finished edits

Status: not calibrated (built 10 Nov 2026; run this before trusting the *(calibrating)* thresholds)

Tim's rule (Q25, 9 Nov 2026): before QA goes live, run it read-only on 2-3 of his finished timelines. His finals
are correct by definition. A rule or threshold that fails his own edit is wrong or too strict, and gets fixed
(with Tim's okay) before QA can force fixes.

## Which timelines

Pick finals that cover different clients and stages, e.g.:
- Namir Mikha C7 (A-roll, B-roll, grade, ending)
- Simone Nov C03 (A-roll framing, Dynamic Zoom holds, subtitles on the cut)
- Hired Home Nov S2 C2 (B-roll speed and Gyroflow)
Confirm the list and the exact timeline names with Tim first.

## How

0. Write a job card with `Kind: calibration`, every line filled (n/a where it doesn't apply), `Grilling: done with Tim`
   (he confirmed the timelines), and its session copy (house-rules job card). Without it the `job_guard` hook blocks
   the proxy render.
1. Only when Tim isn't using Resolve. Nothing in his project changes: the qa-manager is read-only, proxy
   renders restore his settings.
2. For each timeline and each stage it has: run the qa-manager with `calibration: true`, round 1, a QA folder
   outside the job (e.g. `<shoot>/_shotlog/qa/calibration-<timeline>/`). No plan JSON exists for Tim's own
   B-roll, so the reason checks (B-02, B-08) are expected in `not_checked`.
3. Collect every finding. For each: is the rule wrong, the threshold too tight, the script measuring badly, or
   is it a real slip in the final (rare; ask Tim)?
4. Write the results table below, then propose the changes to Tim (thresholds, rule wording, scripts). Apply
   only what he approves (learning agent rules: nothing goes into the plugin without his yes).
5. When a full run on all chosen finals comes back with no hard or judgement findings (or each one explained
   and accepted by Tim), and Tim says yes, set Status to `calibrated (<date>, <timelines>)`, bump the plugin
   version, and tell Tim. Until then `qa_round.py` runs the loop in shadow mode (reports, forces nothing).

## Known to watch

- B-04 jitter thresholds were tuned when shots were measured at 48%. At 100% the camera moves further per
  frame: check whether Tim's 100% shots read as "shake" and adjust broll_auto.py's `clean()` and the motion card tiers.
- A-06 air: client profiles differ (Green runs tighter).
- G-03 neutral target (Cb -5, Cr +5) came from Namir; Arriva moves per concept.

## Results

| Date | Timeline | Stage | Finding | Measured | Rule / threshold | Verdict (rule wrong / threshold / script / real slip) | Change made |
|---|---|---|---|---|---|---|---|
