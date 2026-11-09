---
name: qa-loop
description: "This skill should be used after every Beon Media edit stage (A-roll cut, B-roll placement, colour grade, subtitles) and before hand-over, to run Tim's quality loop: send the stage to the qa-manager agent, verify its judgement calls with the qa-verifier agent, fix what's confirmed, ask Tim the creative calls, and repeat up to 3 rounds. Also for \"QA this\", \"check the edit\", \"is it good to go\", \"run QA\", \"calibrate QA on my final\"."
metadata:
  version: "0.1.0"
---

# QA loop (Tim, 9 Nov 2026)

> **Job card first** (house-rules). QA reads the job card for the concept's own rules.

> **Calibrating QA on Tim's finished timelines** ("calibrate QA on my final"): follow `references/calibration.md` only. Read-only: no `qa_round.py` rounds, no fixes, nothing changes in Tim's project; findings go into its results table for Tim.

Tim's rule: nothing reaches him until a separate quality manager has checked it, the mistakes are fixed, and
anything that's taste is put to him. The editor (this session) never marks its own homework.

## Who does what

| Who | Does | Never |
|---|---|---|
| Editor (this session) | Builds the stage, runs the stage's own hard gate, calls QA, fixes findings, asks Tim the creative calls | Judges its own stage as passed |
| `beon-edit:qa-manager` agent | Checks the stage with fresh eyes against the checklist, returns findings JSON | Edits anything |
| `beon-edit:qa-verifier` agent | Second, independent look at the judgement findings; agrees or refutes | Edits anything |
| `scripts/qa_round.py` | Files each round, compares rounds, enforces the 3-round limit, prints the next actions | |

The agent names follow the plugin pattern `<plugin>:<name>`. If the Agent tool doesn't find
`beon-edit:qa-manager`, check the name in `/agents` and tell Tim.

## When

After each stage, before Tim sees it: `aroll` (after aroll-cut section 4), `broll` (after the hard gate PASS
and Tim's pacing okay), `grade`, `subtitles`, then `final` on the proxy render of the whole edit before
hand-over (finish-pass).

## The loop, per stage

QA folder: `<shoot>/_shotlog/qa/<concept>/` (small text only). Scratch images and renders: device VM or
`_claude_scratch/`, never Dropbox.

1. **Run the qa-manager** (a fresh agent every round; never reuse the previous round's agent). Prompt it with:
   stage, round, project, timeline, job card path, client profile path, QA folder, the stage files (plan
   JSON, cut list, WORK folder, proxy path) and whether Tim is in Resolve. Don't tell it what you think is
   wrong or what you already fixed: it re-measures the open findings from the QA folder itself.
2. Save its JSON under `QA_DIR/raw/` and **record it**: `python3 scripts/qa_round.py record QA_DIR raw/<stage>-r<N>.json`.
   It validates the format (every checklist item must be in checked or not_checked) and prints the next actions.
3. **Verify judgement findings** (`VERIFY`): run a fresh `qa-verifier` with the stage and only the judgement
   findings it lists, whatever their severity (id, where, rule, evidence, fix), plus project, timeline, job card,
   client profile and the still/render paths. Save its JSON under `QA_DIR/raw/` and run
   `qa_round.py verify QA_DIR STAGE ROUND raw/verdicts.json`. Refuted findings are dropped; findings it says are
   taste become creative questions for Tim (never dropped).
4. **Act on the printed list:**
   - `FIX`: hard findings and confirmed judgement findings. Fix them with the stage skill's own fix methods
     (broll: the fix ladder; aroll: section 2b; subtitles: Resync / rebuild; grade: one DRX apply per clip).
     Re-run the stage's own hard gate after fixing.
   - `ASK TIM`: creative findings. Never change these on your own. Put them to Tim in one batch with the
     pop-up question tool (suggested answers, recommended first), then record his answers:
     `qa_round.py tim QA_DIR STAGE answers.json` (`{"answers": [{"id", "answer", "tim_said"}]}`); the next
     qa-manager reads `tim-answers.json` and doesn't raise them again. Unattended: list them for the morning report.
   - `NOTE`: severity check items. Hard ones: mention them, fix only if cheap and clearly right. Judgement ones:
     never fix on your own view; only if Tim agrees.
5. **Next round**: run a new qa-manager with `round + 1`. Repeat until `PASS`.
6. **After round 3**, `qa_round.py` prints `ESCALATE`: stop fixing this stage. Show Tim what's still failing,
   with the evidence and what was tried. Unattended (Tim away): it's already in `qa-log.md`; move on to the
   next stage and put it at the top of the end-of-run report.
7. A stage is done when it prints `PASS` and its creative questions are answered (SETTLED). `PARTIAL` means nothing was wrong in what QA could check, but some checks couldn't run: run them in a new round when possible, or tell Tim exactly what wasn't checked. Only then hand it to Tim.

`qa_round.py status QA_DIR` prints one line per stage; use it in reports and in the final pass (F-07).

## Before calibration: shadow mode (Q25)

`references/calibration.md` says whether QA has been checked against Tim's own finished edits. Until its
Status says calibrated, `qa_round.py` prints `SHADOW`: run the qa-manager after every stage as usual, record
the round, and put every finding in front of Tim with the edit. Nothing is forced; fix a finding only if Tim
says so. The stage's own hard gates (broll_gate, render_check, ...) still apply as before. Tell Tim QA is
running in shadow mode until calibration is done.

## Reporting to Tim

Short table per stage: stage | rounds | result | fixed | asked Tim | escalated | not checked. Link the
`qa-log.md`. Never call a stage passed that QA didn't pass.
