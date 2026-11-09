# QA checklist: B-roll

Sources: `broll/references/broll-rulebook.md` (the rules), broll skill, client profile, job card.
Get: `broll_gate.py --plan` output, the plan rows (`why` per shot), timeline readback, a 1080x1920 proxy
render, Footage Prep scores in the shot log.

## Hard checks (scripts)

| ID | Check | How | Kind | Pass when |
|---|---|---|---|---|
| B-01 | Gate | `broll/scripts/broll_gate.py --project P --timeline T --plan plan.json` | hard | prints PASS |
| B-02 | Every shot has a reason record | plan rows `why` (line, move, speed, gyro, pan) | hard | none missing |
| B-03 | Shake on what the viewer sees | `broll/scripts/shake_check.py RENDER.mp4 SHOTS.json OUT` on the 1080x1920 proxy; SHOTS.json = `[{"shot": "R4 0331", "start": <frame>, "dur": <frames>}]`, frames counted from the render's first frame *(calibrating)* | hard | p90 < 1.0 px; 1.0-1.6 = severity check; >= 1.6 fix |
| B-04 | No jerky moves | `broll/scripts/motion_card.py CLIP T_IN SRC_DUR OUT.png --speed S --pan P --tilt T --zoom Z` per shot | hard | no `uneven` (speed varies > 30%), `mid-ease` or `reversal` flag; jitter p90 < 1.0 px (1.0-2.0 check) *(calibrating at 100%)* |
| B-05 | Verticals level | still per shot, `broll/scripts/level_check.py` (`--center` on looking-up exteriors) | hard | lean ~0 deg, no black corners; strong keystone exteriors stay as shot |
| B-06 | Zoom doesn't pixelate | gate zoom tier + a rendered still for anything over 1.25x (UHD) / 1.0x (1080) | hard | rulebook section 5 limits; stills sharp |
| B-07 | Speaker max 4 s, no slivers, no gaps | gate timeline section | hard | none, except the rulebook's exceptions: jokes Tim kept on camera and the first introduction (job card), and holds where the B-roll is used up and already stretched and slowed. A hold over 4 s that can't be covered is a creative finding (ASK TIM), not a fix |
| B-08 | Speed reasons hold up | each slowed shot's reason vs its neighbours (match: camera speeds close; shake: faster speed really was rough) | hard | reason true on the numbers |
| B-09 | Footage Prep: no rejected or flagged clips, scores used | shot log `footage_prep` blocks vs placed clips | hard | no `reject` tier, no shaky/whip/blur/blocked select |
| B-10 | Stabilised shots not worse than the camera file | the original: `motion_card.py CLIP T_IN SRC_DUR OUT.png --speed S --pan P --tilt T --zoom Z` (jitter at 1080 wide) or the Footage Prep / `bestwin.py` gyro score; the stabilised: B-03's shake_check on the render, same 1080-wide pixel scale | hard | stabilised <= original (else use the original) |

## Judgement checks (second look by qa-verifier)

| ID | Check | How | Kind | Pass when |
|---|---|---|---|---|
| B-20 | Shot matches the words literally | line (why.line) vs a mid still | judgement | what's named is shown; nothing implies something false; toilets only for bathroom lines |
| B-21 | Subject centred in 9:16 | first/mid/last stills | judgement | subject not cut by the edge; strongest feature framed in empty rooms |
| B-22 | Flow through a run | sequence of moves and camera speeds (motion cards) | judgement | no opposite moves back to back; similar speeds; cut on motion; settles before the speaker |
| B-23 | Same room twice in a row | consecutive shots' rooms | judgement | only from a different angle |
| B-24 | People | first/last 0.3 s stills, shot log people registry | judgement | right person; no open mouth or grimace on the edges; no slowed talking that looks odd |
| B-25 | Establishing shots used | place names, level changes, closing wide | judgement | hero exteriors used where the rulebook says |
| B-26 | Static shots move | Dynamic Zoom present and its direction fits the line | judgement | 3-5%, in on a detail, out on a reveal/list |
| B-27 | Light spots | stills | judgement | no big blown area held on screen |

## Creative (to Tim, never auto-fixed)

| ID | Check | Kind |
|---|---|---|
| B-40 | A shot would need a different subject than the plan (no exact match exists) | creative |
| B-41 | Goofy or playful shots, jokes covered by B-roll, against the job card's tone answer | creative |
