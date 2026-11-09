# How the checklists work

One file per stage: `aroll.md`, `broll.md`, `grade.md`, `subtitles.md`, `final.md`. The qa-manager agent
runs every item of its stage, from what is actually in the project and the renders, never from what the
editor says it did.

Each item: `ID` · what to check · how (tool or script) · kind · pass when.

- **kind** decides what happens to a finding (qa-loop skill, `scripts/qa_round.py`):
  - `hard`: measured against a written rule. Always fixed, no question.
  - `judgement`: needs a trained eye (relevance, flow, "sounds rushed"). Checked again by the qa-verifier
    agent; fixed only if both agree.
  - `creative`: a matter of taste. Never auto-fixed: it goes to Tim.
- **severity** `check` = worth a look, not a failure by itself (e.g. a zoom in the 1.25-1.4 range).
- Client profile and job card rules beat the house rules here, same as everywhere (client-styles).
- Until the calibration run on Tim's finals (`../calibration.md`) the whole loop runs in **shadow mode**:
  every finding is reported to Tim, nothing is forced (`qa_round.py` prints SHADOW). Items marked
  *(calibrating)* are the thresholds that calibration looks at first.
- Report every checklist id in `checked` or `not_checked` (or as a finding id like `B-03-1`): `qa_round.py`
  refuses a report that skips items.
- Keep a finding's id the same across rounds (same problem, same id), so rounds compare by id.
- If Tim already answered a creative question (`tim-answers.json` in the QA folder), don't raise it again.
- Anything you couldn't check (no render, no access, Resolve busy for Tim) goes in `not_checked`. Never
  mark it passed.
