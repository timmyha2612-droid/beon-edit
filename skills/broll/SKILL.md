---
name: broll
description: "This skill should be used when adding or fixing B-roll on a Beon Media concept edit in DaVinci Resolve: \"add B-roll\", \"pick shots for this line\", \"use shots we haven't used\", \"fix this shot\", \"pacing pass\" (checking placed B-roll is the qa-loop skill and its qa-manager agent). Covers Tim's B-roll rulebook (speed and reasons, Gyroflow, movement flow, framing and zoom, placement), selection, placement, the hard gate, the pacing gate, handing to the qa-manager agent, and the fix ladder (re-pick, Gyroflow, slow down, replace) for its findings.\n"
metadata:
  version: "0.9.0"
---

# B-roll (Tim, Beon Media)

> **Job card first.** Before any work in this skill, make sure this job has a job card (house-rules, "Grill first"). No card: stop and run the grilling with Tim. The `job_guard` hook blocks Resolve edits without one.

## The rules live in the rulebook

`references/broll-rulebook.md` is the one list of Tim's B-roll rules: speed and the valid reasons to slow, Gyroflow, movement flow, framing and the zoom limit, Dynamic Zoom on static shots, placement (speaker on screen max 4 s), matching the words. Read it before every B-roll pass. This skill is only the how-to (order, tools, recipes) and doesn't repeat the rules. Where anything here disagrees with the rulebook, the rulebook wins.

## HARD GATE: every B-roll pass, no exceptions [Tim, Hired Home Nov S2 C2, 9 Nov 2026; speed rule 9 Nov 2026]

On Hired Home C2 this skill had been read and B-roll still went in with no Gyroflow and no window scoring. Tim: "make that apply to every single time". Do these five steps for every shot placed above V1, in order, and don't report the B-roll as done until step 5 prints PASS:

1. **Footage Prep picks the selects** (Stage 0, `house-rules/references/footage-prep.md`). Its gyro (rtmd) metrics score the whole select; don't re-measure them by eye. Not reachable: tell Tim in one line and use the fallback.
2. **`scripts/broll_auto.py SLOTS.json CLIP_DIR -o plan.json --snippet apply.py`** finds the smoothest stretch of each select at the slot's length and picks the speed by rulebook section 2 (100% unless a valid reason, within the floors). Give each slot `sel_frames`, `movement` and `stability` (`metrics.stability`) from Footage Prep (a locked/steady shot at >= 0.95 is never slowed for shake or rejected for uneven motion: what moves is the subject), plus `line`, `subject` and `people` ("talking"/"moving"). Optional: `match_v` (the neighbours' camera speed in px/frame, for the reason `match`) and `hero: true` (a shot that should breathe). It also picks the Gyroflow preset, checks the zoom limit, lists static shots for Dynamic Zoom, and prints REJECT for reversals, focus pulls, exposure jumps, uneven moves and zoom that pixelates: re-pick those. Every row carries `why` (the reason record). About 3 s per slot. `--why` prints the best window at every speed. Don't read frames to judge motion; look only to check the subject, people and framing of the winner.
3. **Place with its snippet** (window, speed only when slowed, retime, Pan/Zoom, Orange + gyroflow marker, `why`). Confirm Pan with one still per timeline. Pan scales with zoom on 9:16 fit-space timelines: `(0.5 - x) * 1080 * Zoom`. Add the Dynamic Zoom on static shots (rulebook section 5) and set `dynamic_zoom.applied` in the plan.
4. **`python3 scripts/gyroflow_headless.py --project P --timeline T`** stabilises every Orange clip (Tim's script, headless). Run it from Bash, not run_script.
5. **`python3 scripts/broll_gate.py --project P --timeline T --plan plan.json`** must print PASS: speed 100% or slowed with a valid reason above the floor, Optical Flow on slowed shots, stabilised (no gyro track: listed for Tim), zoom within the limit, Dynamic Zoom applied on static shots, the speaker never on screen more than 4 s (`--holds-ok` for Tim's exceptions), no slivers under 1 s, no gaps. If Tim approves an exception, pass it with `--allow`.

A plugin hook (`hooks/broll_guard.py`) blocks any run_script that appends camera video above V1 without the `why` records, without a retime on slowed shots, or without an Orange gyroflow flag (`# broll-nogyro: <reason>` for drone or no-gyro shots). Titles, counters, logos and nested timelines need a `# broll-ok: <reason>` comment. Then hand the stage to QA (Stage 4), which measures the render.

Work in stages and stop at the gates. Never touch V1/A1 (interview), the music track, or anything Tim says he has placed. Stop all Resolve calls when Tim says he needs Resolve; analysis keeps running in the device VM.

## Stage 0. Footage Prep first, then the shot log [Tim, Mill site update, 9 Nov 2026]

Never pick B-roll from contact sheets or by eye alone: on The Mill (Nov C2) shots picked that way were shaky, didn't flow and were partly irrelevant, and the app had already scored several of them "reject" or "shaky".

1. Follow `house-rules/references/footage-prep.md`: is the app reachable, get the shoot in and analysed, which selects and tiers to take, the second look at its winners, the fallback, and what to report (clip, frames, score, stability, anything overridden).
2. Best stretch inside the select [Tim, Mill, 9 Nov 2026]: a select is 3-12 s but a slot uses ~2-3 s of it. Never start "about 1 s in": `scripts/broll_auto.py` (hard gate step 2) measures every window of the needed source length inside the select and takes the smoothest. The append needs `ceil(D*fps/24)` real-time source frames, so it only searches windows that fit before the clip end.
3. Read `<shoot>/_shotlog/shotlog.json` (shotlog skill). Reuse gyro windows, people windows, verified frames, tone tags, motion cards and transcripts; check `usage` (prefer unused windows); read `lessons`. Write back at the end.

## Stage 1. Select (how to apply rulebook sections 4, 5 and 7)

- Match the shot to its line first, then flow through the run.
- The clip's real move is the longest run in a consistent gyro direction; reject windows moving the opposite way or between passes (videographer resets).
- Fallback when there's no clean window and no other shot: a stretch outside the steadiest window can work if it's slowed to a suitable speed (reason `shake`) and gyro-stabilised. Only when necessary, and flag it.
- Re-score any hand-picked window (shake and direction) before placing.
- Footage Prep not reachable: `scripts/bestwin.py GYRO_DIR CLIP REC_SECONDS --avoid <used ranges>` shortlists candidate windows from the ingest gyro cache in milliseconds (shake tier, camera speed, uneven moves) and skips ranges already used in the series. `broll_auto.py` still runs on the shortlist (leave out `sel_frames`: it searches the whole clip minus 1 s at each end) and writes the `why` records the gate and the hook need.
- 9:16 framing: `scripts/framing_sheet.py CLIP T OUT.jpg --pans a,b --x <subject x> --times <end of move>` draws the vertical windows and a Pan ruler on the full frame, at the start and end of a moving shot, and prints the Pan that centres a subject. Subject beyond the slide limit: accept it off-centre or re-pick. Check every shot before the pacing gate, with a rendered still.
- Pan units differ per timeline. Most 1080x1920 timelines take fill-space Pan ((0.5 - x) * 3413 for UHD at Zoom 1); some report scaleToFit and render fill and take fit-space Pan ((0.5 - x) * 1080; Green Oct 2026). `framing_sheet.py --space fit` prints fit-space values. Confirm with one rendered still per timeline before setting many. The readback can also differ from what a script wrote: on Green C3/C5 every Pan later read back as 1/4 of the value set while the picture stayed identical, so never infer framing changes from Pan numbers alone; compare stills.
- People: nudge the window up to ±0.5 s inside the steady stretch so the first and last ~0.3 s don't land on an open mouth or grimace (`scripts/mouth_check.py`).

## Stage 2. Place

Place by rulebook section 6 (placement, speaker max 4 s), section 2 (speed and its reason) and section 5 (Dynamic Zoom on static shots), using the snippet from the hard gate.

After stabilising (hard gate step 4), straighten verticals and level the floor: export a still of every shot and run `scripts/level_check.py STILL...`: it measures the lean of door frames, walls and window mullions and prints the rotation that makes them vertical plus the **minimum** zoom that still covers the 9:16 frame after that rotation. Set `RotationAngle` and `ZoomX/ZoomY` to exactly that, re-export and check again (lean ~0, no black corners). Looking-up exteriors converge (keystone): run `level_check.py --center` (verticals in the middle 40% only) or level by eye on something truly vertical (crane mast, building corner). Measured on the Mill v2 (Resolve 21.1, 1080x1920): `RotationAngle` follows level_check's `rotate` value 1:1 (+2 set = +1.8 measured), zoom from `min_zoom(theta, cx=|Pan|*3.17)` +0.4%. Corrections were 0.3-2.2 deg with zoom 1.007-1.026.

API: `AppendToTimeline` with source frames, length `ceil(D*fps/24)` (exclusive end), absolute `recordFrame`. Slow-mo: append real-time length then `SetSpeed({'Percentage': <speed>, 'RippleTimeline': False})`. Slowed shots only: `SetProperty('RetimeProcess', RETIME_OPTICAL_FLOW)`; `SetProperty('MotionEstimation', MOTION_EST_SPEED_WARP_BETTER)` only below 48%.

## Stage 3. Pacing gate (Tim approves)

Report shot count, coverage %, shot lengths (flag < 1 s or > 4 s), speaker stretches over 4 s, speeds with their reasons, uncovered jump cuts, on-camera openings per turn. Wait for Tim's go.

Gap check before the gate [Tim, 29 Oct 2026]: walk the top visible layer frame by frame across V1, the angle track and B-roll. Nothing may show on screen for under ~1 s (24 frames) between two other shots: no 2-4 frame flash of the speaker between B-roll shots (Green C5 28:10, C6 16:10), no B-angle sliver before a B-roll shot. A B-roll shot that covers an A-roll cut must run to that cut frame or past it, never end a frame or two short (C6 32:05). Fix by trimming the neighbouring B-roll to meet exactly (head or tail), or move the shot when the clip has no handle. API: there's no trim call, so delete and re-append at the new range: append D frames at 100% (`endFrame = sf + ceil(D * fps / 24)`), then `SetSpeed` (Resolve keeps the duration and trims the source), then re-apply Pan/Tilt/Zoom, retime, name, colour and markers.

## Stage 4. Hand to QA (the qa-manager agent checks, this skill fixes)

Checking is never done by the session that placed the shots. After the hard gate prints PASS and Tim has okayed the pacing (Stage 3), run the QA loop (skill `qa-loop`) for the stage `broll`. The qa-manager agent measures every shot with fresh eyes (motion cards, rendered shake check, framing and level stills, the rulebook) and returns findings. Fix them with the ladder below, then QA checks again. The measuring recipes (motion card, shake_check tiers, rendered stills) live in `qa-loop/references/checklists/broll.md`.

## Stage 5. Fix ladder (in order)

1. Slide to a steadier part of the same clip, or re-pick another window of the same subject; re-score it.
2. Stabilise with Gyroflow: colour the clip Orange and add a clip marker whose custom data is `{"gyroflow": {"smoothness": .., "horizon": .., "horizon_amount": .., "horizon_roll": .., "zoom_mode": "Dynamic", "zoom_window": 4, "max_zoom": ..}}`. Presets by move: rulebook section 3. Run it headless with `scripts/gyroflow_headless.py --project P --timeline T`. Tim's script (Workspace > Scripts > Utility > "Gyroflow Stabilize Flagged") stabilises at 100%, re-applies speed and retime settings, renders next to the source clip, places it on a "Gyroflow" track, disables the original and colours the new clip Yellow.
   - `horizon_amount` is a percentage (100 = full lock; 1.0 means 1%, effectively off). `max_zoom` is a % limit the script only passes on above 50; use 0 for no limit.
   - Reframe first, Gyroflow second: the script copies Pan, Tilt, Zoom and crop onto the stabilised clip. It refuses camera files with no gyro data (REQUIRE_GYRO), so only flag shots whose file has motion data (Sony rtmd track) and list the rest for Tim.
   - Check verticals after stabilising: horizon lock levels the gyro horizon, not the room, so a shot can still lean 1-1.5 deg. Level it with RotationAngle and the smallest zoom that hides the corners (Tim, Green C3: zoom 1.06-1.09 for 1.0-1.4 deg) [Tim, 29 Oct 2026].
   - After stabilising, re-check framing on every shot (orig vs stab 9:16 crop at first/mid/last): the stabilisation zoom shifts and tightens the frame, so re-centre with Pan on the stabilised clip; horizon lock can add roll to an already-level upward shot (re-render with horizon off); some clips crop ~1.4x whatever the settings: Tim still prefers the stabilised version over a wider shaky one (Green C3 C9995, 29 Oct 2026), so keep it and re-centre with Pan rather than reverting.
   - When Tim asks for Gyroflow on all B-roll, flag every gyro-capable B-roll shot Orange with a preset marker, not only the shaky ones.
3. If still shaky: slow down (reason `shake`) with Optical Flow, down to the floor for what's in the shot (rulebook section 2).
4. Replace with a different clip.

## Stage 5b. Fixes that worked (for QA findings)

What fixed shots on Green C5/C7 (29 Oct 2026):
- Gyroflow can ADD shake on clips that already had in-body/lens stabilisation (C1345: camera 0.2 px, Gyroflow render 2.7 px). Compare the render with the camera file; if the original is steadier, use the original.
- 25p clips at 100% on a 24p timeline drop one frame a second (visible hitch on moves): set 96% with Retime Nearest so every frame plays once.
- Speed Warp smears hands crossing the frame or touching the face: slip the window past the hand rather than changing the retime.
- Residual low-frequency sway: re-render Gyroflow at smoothness 0.8-0.9 + horizon lock (C7 2474: 1.75 -> 0.2 px).
- Walking bob (camera translation) and roll that horizon lock won't hold can't be fixed by Gyroflow: re-pick a calmer window (100 fps clips can drop to ~25% with no invented frames) or replace the shot with a static/tripod one that fits the line.
- Resolve's TimelineItem.Stabilize() runs from scripts but uses the clip's Inspector settings (mode/smooth/strength are not scriptable); at defaults it added nothing measurable on top of Gyroflow.
- Rebuilding a clip (no trim API): read Pan/Tilt/Zoom/Rotation, re-append, re-apply, then confirm framing with a still; Pan readback has been inconsistent between clips and timelines. ExportCurrentFrameAsStill fails on the Deliver page (OpenPage('edit') first).

## Stage 6. Sign-off

QA passes the stage (or Tim settles what it escalated), then set the shots Green and hand Tim the watch-down. Write the QA results, motion verdicts, usage and lessons back to the shot log.

## Clip colours (Tim's convention)

Green pass, Yellow check or stabilised pending re-measure, Orange stabilise, Violet retime, Chocolate replace. A marker on each flagged shot with the QA finding id and reason.
