---
name: broll
description: "This skill should be used when adding or fixing B-roll on a Beon Media concept edit in DaVinci Resolve: \"add B-roll\", \"pick shots for this line\", \"use shots we haven't used\", \"fix this shot\", \"pacing pass\" (checking placed B-roll is the qa-loop skill and its qa-manager agent). Covers Beon's B-roll rulebook (speed and reasons, Gyroflow, movement flow, framing and zoom, placement), selection, placement, the hard gate, the pacing gate, handing to the qa-manager agent, and the fix ladder (re-pick, Gyroflow, slow down, replace) for its findings.\n"
metadata:
  version: "0.10.0"
---

# B-roll (Beon Media)

> **Job card first.** Before any work in this skill, make sure this job has a job card (house-rules, "Grill first"). No card: stop and run the grilling with the editor. The `job_guard` hook blocks Resolve edits without one.

## The B-roll rulebook

`references/broll-rulebook.md` is the one list of how Beon handles B-roll: speed and the valid reasons to slow, Gyroflow, movement flow, framing and the zoom limit, Dynamic Zoom on static shots, placement (speaker on screen max 4 s), matching the words. Read it before every B-roll pass. This skill is the how-to; the rulebook is the what. Where they disagree, the rulebook wins.

## What this skill reads from the intake files

The editor running the job decides everything here: they answer the grilling and approve every gate and exception. "Tim" below only marks where a rule came from.

- **Footage Prep**: `~/.beon-edit/editor.json` `tools.footage_prep.enabled` (off by default). Off or not reachable: say so in one line and use the fallback (Stage 0).
- **Gyroflow**: `editor.json` `tools.gyroflow.installed` and `stabilize_script`. Not installed: say so at the grilling (house-rules), because handheld shots then can't be stabilised and the gate wants each one slowed for a valid reason, replaced, or marked (plan `gyro_skip`). The scripts read the same field (`--no-gyroflow` forces it).
- **Delivery**: client profile `delivery` + job card `Delivery:` line (aspect, size, fps). Pass `--card <job card>` to the scripts; without it they use Beon's default, 9:16 1080x1920 24p. The 9:16 rules below (speaker centred with Pan, the vertical window, `framing_sheet.py`, the fit-space Pan formula) apply when the delivery aspect is 9:16. Other aspects: frame the subject in that window the same way and check a rendered still.
- **Cameras**: shot log `shoot.cameras[]` (`gyro`, `ext`, `name_pattern`). Gyro data is read from Sony rtmd tracks only; other bodies (`gyro: none`) never crash the scripts, they come out as "no gyro" and are listed for the editor.
- **People**: shot log `shoot.people` and the job card's `Goofy or playful people shots` and `On-camera holds` lines.
- **Run environment**: local Mac by default. If run_env is device-vm, long analysis runs there and keeps going while the editor has Resolve.
- Clip names in slots and scripts: a stem (`C0012`), a file name with any video extension (`.MP4`, `.mov`, any case) or a path relative to the shoot (`A001/C0012.MP4`).

## HARD GATE: every B-roll pass, no exceptions [Tim, Hired Home Nov S2 C2, 9 Nov 2026; speed rule 9 Nov 2026]

On Hired Home C2 this skill had been read and B-roll still went in with no Gyroflow and no window scoring. Tim: "make that apply to every single time". Do these five steps for every shot placed above V1, in order, and don't report the B-roll as done until step 5 prints PASS:

1. **Footage Prep picks the selects** (Stage 0) when it's on: `selects` without shaky/whip/motion_blur/blocked, stability >= ~0.75. Its gyro (rtmd) metrics score the whole select. Don't re-measure them by eye. Off or not reachable: tell the editor in one line and use the fallback (Stage 0, `house-rules/references/footage-prep.md`).
2. **`scripts/broll_auto.py SLOTS.json SHOOT_DIR -o plan.json --snippet apply.py --card <job card>`** finds the smoothest stretch of each select at the slot's length and picks the speed: **100% unless there's a valid reason** (shake, `match_v` = the neighbours' camera speed, stretch, `hero`), within the floors (people talking 80%, moving 60%, others 48%, 100 fps 25%). Give each slot `sel_frames`, `movement` and `stability` (`metrics.stability`) from Footage Prep (a locked/steady shot at >= 0.95 is never slowed for shake or rejected for uneven motion: what moves is the subject; without Footage Prep see Stage 0 for what fills these), plus `line`, `subject` and `people` ("talking"/"moving"). It also picks the Gyroflow preset, checks the zoom limit, lists static shots for Dynamic Zoom, and prints REJECT for reversals, focus pulls, exposure jumps, uneven moves and zoom that pixelates: re-pick those. Every row carries `why` (the reason record). About 3 s per slot. `--why` prints the best window at every speed. Don't read frames to judge motion; look only to check the subject, people and framing of the winner.
3. **Place with its snippet** (window, speed only when slowed, retime, Pan/Zoom, Orange + gyroflow marker, `why`). Confirm Pan with one still per timeline. Pan scales with zoom on 9:16 fit-space timelines: `(0.5 - x) * <delivery width> * Zoom` (1080 by default; the snippet's `PAN_W`). Add the Dynamic Zoom on static shots (rulebook section 5) and set `dynamic_zoom.applied` in the plan.
4. **`python3 scripts/gyroflow_headless.py --project P --timeline T`** stabilises every Orange clip (the Gyroflow Stabilize Flagged script, headless; path from `editor.json` `tools.gyroflow.stabilize_script`, `--script` overrides). Run it from Bash, not run_script. Gyroflow not installed: skip this step; nothing is flagged Orange.
5. **`python3 scripts/broll_gate.py --project P --timeline T --plan plan.json --card <job card>`** must print PASS: speed 100% or slowed with a valid reason above the floor, Optical Flow on slowed shots, stabilised (no gyro track: listed for the editor; Gyroflow not installed: slowed for a valid reason, camera-still, replaced or marked `gyro_skip`), zoom within the limit, Dynamic Zoom applied on static shots, the speaker never on screen more than 4 s (`--holds-ok` for the editor's exceptions, job card `On-camera holds`), no slivers under 1 s, no gaps. If the editor approves an exception, pass it with `--allow`.

A plugin hook (`hooks/broll_guard.py`) blocks any run_script that appends camera video above V1 without the `why` records, without a retime on slowed shots, or without an Orange gyroflow flag (`# broll-nogyro: <reason>` for drone or no-gyro shots). Titles, counters, logos and nested timelines need a `# broll-ok: <reason>` comment. Then hand the stage to QA (Stage 4), which measures the render.

Work in stages and stop at the gates. Never touch V1/A1 (interview), the music track, or anything the editor has placed (job card `Don't move`). Stop all Resolve calls when the editor says they need Resolve; analysis on files keeps running (in the device VM if run_env is device-vm).

## Stage 0. Footage Prep first (when it's on), then the shot log [Tim, Mill site update, 9 Nov 2026]

When `editor.json` `tools.footage_prep.enabled` is true, every shoot goes through the Footage Prep app (the `footage-prep` MCP tools) before any B-roll is picked (`house-rules/references/footage-prep.md`: reachability, fallback, priority, second look). Never pick B-roll from contact sheets or by eye alone: on The Mill (Nov C2) shots picked that way were shaky, didn't flow and were partly irrelevant, and the app had already scored several of them "reject" or "shaky".

1. `library_shoots` (query = client or shoot). If the folder isn't there, `inspect_folder` then `import` it (client name, `watch: false`) and wait on `progress` until analysis is done. Opening a shoot switches the app, so never pass `switch_shoot` unless the editor asked. If the shoot block names another editor in `prepped_by`, read their prep; don't re-prep.
2. Pick only from the app's selects: `selects` with `without_flags: ["shaky","whip","motion_blur","blocked"]`, inside each select's `in_frame`/`out_frame`. Prefer `auto_tier`/the editor's tier `hero` and `metrics.stability` >= ~0.75; below ~0.65 only when it's the only shot for the line, and flag it. Skip clips the app rates `reject` (`clips` with `auto_tier`).
3. Match every shot to its line first (what's said on screen), then flow: similar moves and speeds in a run (slow a faster shot to `match` its neighbours), the same room twice in a row only from a different angle, settle before a cut back to camera.
   - Read the sort keys in the shot log first (`scene`, `place`, `good_for`, `not_for`; shotlog skill) and match them to the line before looking at frames.
   - Reject two shots side by side when they share a `setup`, or a `take_family`, or both `scene` and `shot_size`. Reject any run of 3 or more with the same `place.id`.
   - Write `usage[].reason` for every shot placed: the line, then the same record the sort uses (e.g. "line 'the kitchen': place=kitchen scene=kitchen-1 setup=kitchen-1-s03 fp=hero stab 0.91").
4. Stabilisation renders are the editor's to start in the app; list the shots that need them.
5. Mention in the report which app selects (clip, frames, score, stability) were used.
6. Second look: Footage Prep's scorer chooses, but check its winner once more before placing (subject, people, framing for the delivery aspect, smoothness of the stretch actually used). Note it in the report.
7. Best stretch inside the select [Tim, Mill, 9 Nov 2026]: a select is 3-12 s but a slot uses ~2-3 s of it. Never start "about 1 s in": measure every window of the needed source length inside the select and take the smoothest. Use `scripts/broll_auto.py` (hard gate step 2: window + speed + Gyroflow preset in one pass). The older single-speed picker is `scripts/select_window.py '<json [[slot, clip, need_src_frames, [[in,out],...]],...]>' out.json <clip folder>` (optical-flow jitter p90, speed evenness, reversals). The append needs `ceil(D*fps/tl_fps)` real-time source frames (tl_fps = delivery fps, 24 by default), so limit the search to windows that fit before the clip end.

**Without Footage Prep** (off in `editor.json`, or not reachable): one line to the editor, then `shotlog/scripts/ingest.py` (gyro shake windows, keyframes, contact sheets) and Claude's own measures supply what Footage Prep would have given `broll_auto.py`:
- `sel` (seconds) instead of `sel_frames`: the steadiest gyro windows from `bestwin.py` on the ingest cache, or the whole clip minus ~1 s at each end. `broll_auto.py` still finds the smoothest stretch inside.
- `movement`: from a motion card (`motion_card.py`) or the shot log's move notes; leave it out when unsure (the preset then follows the measured move).
- `stability`: leave it out. Never invent one. Without it a locked shot isn't known to be camera-still, so a locked shot (tripod, no camera move) must not be slowed for shake. `broll_auto.py` warns on every shot it slows for `shake` without `stability`; check each one by eye: if only people or cars move, set the slot's `"speed": 100`.
- Non-Sony cameras have no gyro cache: rank them with a motion card or `broll_auto.py` alone.
Record `footage_prep.available: false` in the shoot block and the job card's `Footage Prep:` line.

## Stage 0b. What every B-roll shot needs [Tim, Mill, 9 Nov 2026]

- **Relevant to the words, literally.** "The finishes" = kitchen joinery, stone benchtop, tiles, tapware, not a toilet. Toilets only when the line is about bathrooms, and never as the first finishes shot.
- **Use the establishing shots.** When the shoot has building or street exteriors, use them: over the line that names the place ("we're standing in the display suite of The Mill"), on level or location changes ("we're at Level 5"), and as the closing wide into the end card. Don't leave the hero exteriors unused.
- **Flow.** The same room twice in a row only from a different angle; similar move speed through a run; cut on motion; settle before cutting back to camera; no jerky movement anywhere in the shot.
- **Stabilise all handheld B-roll** (when Gyroflow is installed) with the Gyroflow Stabilize Flagged script (colour Orange, run it; headless driver pattern in house-rules/references/resolve-recipes.md), horizon lock on: clip-marker custom data `{"gyroflow": {"horizon": true, "horizon_amount": 100}}`. Drone shots are already gimbal-smooth; skip them.
- **Straight verticals, level floor.** After stabilising, export a still of every shot and run `scripts/level_check.py --card <job card> STILL...`: it measures the lean of door frames, walls and window mullions and prints the rotation that makes them vertical plus the **minimum** zoom that still covers the delivery frame (9:16 by default) after that rotation. Set `RotationAngle` and `ZoomX/ZoomY` to exactly that (never zoom more than the rotation needs, and stay inside the rulebook's zoom limit so the picture never pixelates), re-export and check again. Looking-up exteriors converge (keystone): run `level_check.py --center` (verticals in the middle 40% only) or level by eye on something truly vertical (crane mast, building corner); leave strong keystone wides as shot. Measured on the Mill v2 (Resolve 21.1, 1080x1920): `RotationAngle` follows level_check's `rotate` value 1:1 (+2 set = +1.8 measured), zoom from `min_zoom(theta, cx=|Pan|*3.17)` +0.4%. Corrections were 0.3-2.2 deg with zoom 1.007-1.026. Re-export and confirm lean ~0 and no black corners.

Then read `<shoot>/_shotlog/shotlog.json` (shotlog skill). Reuse gyro windows, people windows, verified frames, tone tags, motion cards and transcripts; check `usage` (prefer unused windows); read `lessons`. Write back at the end.

## Stage 1. Select

- Cut inside the steadiest window: skip the first and last ~1 s, no focus pulls or exposure shifts, keep moves whole (start once underway, out before it eases).
- Fallback when no clean window or no other option: a shot outside the steadiest window can work if it's slowed to a suitable speed and gyro-stabilised. Use it only when necessary and flag it.
- Never use a videographer reset (camera drifting back to the start of a move). Find the clip's real move (longest run in a consistent gyro direction) and reject windows moving the opposite way or between passes.
- Re-score any hand-picked window (shake and direction) before placing.
- Fast window pick: `scripts/bestwin.py GYRO_DIR CLIP REC_SECONDS [--speed 48] --avoid <used ranges>` (`--speed` is the playback speed, default 100) ranks windows from the ingest gyro cache in milliseconds (shake tier, camera speed, uneven moves) and skips ranges already used in the series. Then confirm the winner with a motion card.
- 9:16 framing (9:16 deliveries): `scripts/framing_sheet.py CLIP T OUT.jpg --root SHOOT --card <job card> --pans a,b --x <subject x> --times <end of move>` draws the vertical windows and a Pan ruler on the full frame, at the start and end of a moving shot, and prints the Pan that centres a subject.
- 9:16 reframe sideways (9:16 deliveries) [Tim, 29 Oct 2026]: the vertical window only sees about a third of a 16:9 frame, so when the subject (the person, sign, door or feature the line is about) isn't in the middle, slide the window sideways with Pan to put it there. Never leave the subject cut by the window edge or sitting off to one side with empty wall in the middle. Moving shot: centre the subject mid-shot, then check the first and last frame still hold it. No single subject (empty room): frame the strongest feature or the leading lines. If the subject is beyond the slide limit, accept it off-centre or re-pick. Check every B-roll shot this way before the pacing gate, and verify with a rendered still.
- Pan units differ per timeline. Most 1080x1920 timelines take fill-space Pan ((0.5 - x) * 3413 for UHD at Zoom 1); some report scaleToFit and render fill and take fit-space Pan ((0.5 - x) * 1080; Green Oct 2026). `framing_sheet.py --space fit` prints fit-space values. Confirm with one rendered still per timeline before setting many. The readback can also differ from what a script wrote: on Green C3/C5 every Pan later read back as 1/4 of the value set while the picture stayed identical, so never infer framing changes from Pan numbers alone; compare stills.
- Matching: if there's an exact match for the line (what's named, the person talked about), use it. If not, use whatever fits the line without creating a misunderstanding (never a shot that implies something false). A line about a specific room or light must show that room if it's shown at all.
- People: confirm identity (shot log people registry). The first and last ~0.3 s must not freeze on a wide-open mouth or grimace; nudge up to ±0.5 s inside the steady window (`scripts/mouth_check.py CLIP T_IN DUR --dir SHOOT [--prefix <camera name prefix>]`). Goofy or playful moments only where the job card's `Goofy or playful people shots` line allows them.
- Light spots: a small blown highlight is fine. Reject or shorten a shot when the hot spot is a significant part of the frame or the shot lingers on it (C7 R14).

## Stage 2. Place

- The speaker stays on screen at most 4 s at a time [Tim, 9 Nov 2026] unless the B-roll is used up and already stretched and slowed; exceptions only for jokes the editor kept on camera (job card `Jokes or light moments`, `On-camera holds`) and the first introduction. (This replaces the old "about 50/50, switch every 4–6 s".)
- Open each speaker turn on camera ~1.5–2 s; cover visible jump cuts (see aroll-cut for when a small one can stay).
- Phrase-led rhythm: shots ~2–3 s, changing on sentence breaks.
- Open with 1–1.5 s of B-roll only before the first line.
- Breathing gap (hero property shots, music only) when the edit needs it: between two separate points or two answers, or when the speech has run continuous and fast for too long. Size it to the music once music is in.
- Speed: 100% unless there's a valid reason to slow (rulebook section 2: shake, match, stretch, hero), within the floors (people talking 80%, moving 60%, others 48%). Record the reason.
- Static shots: a slight Dynamic Zoom, 3–5%, in or out by the shot (rulebook section 5).
- B-roll is video only, hard cuts, on V2. Name items `<slot> <clip>` (e.g. `R4 0331`).
- Movement flow: no back-to-back opposite camera moves; similar speeds within a run; the last shot settles before cutting back to camera; cut on motion between moving shots.
- Outro and ending depend on the edit; Beon usually runs B-roll past the last word into the end card.

API: `AppendToTimeline` with source frames, length `ceil(D*fps/tl_fps)` (exclusive end; tl_fps = delivery fps, 24 by default), absolute `recordFrame`. Slow-mo: append real-time length then `SetSpeed({'Percentage': <speed>, 'RippleTimeline': False})`. Retime quality: `SetProperty('RetimeProcess', RETIME_OPTICAL_FLOW)`, `SetProperty('MotionEstimation', MOTION_EST_SPEED_WARP_BETTER)`.

## Stage 3. Pacing gate (the editor approves)

Report shot count, coverage %, shot lengths (flag < 1 s or > 4 s), speaker stretches over 4 s, speeds with their reasons, uncovered jump cuts, on-camera openings per turn. Wait for the editor's go.

Gap check before the gate [Tim, 29 Oct 2026; per item since Hired Home Nov S2 C4, 11 Nov 2026]: `broll_gate.py` now checks this per timeline item, never merging back-to-back pieces of the same camera clip (that merge hid a 1-frame flash of the speaker's close-up between two pieces). Every B-roll edge that meets an A-roll cut sits exactly on the cut frame. After any recut, re-place or 1-frame fix, run the gate again before reporting. walk the top visible layer frame by frame across V1, the angle track and B-roll. Nothing may show on screen for under ~1 s (24 frames) between two other shots: no 2-4 frame flash of the speaker between B-roll shots (Green C5 28:10, C6 16:10), no B-angle sliver before a B-roll shot. A B-roll shot that covers an A-roll cut must run to that cut frame or past it, never end a frame or two short (C6 32:05). Fix by trimming the neighbouring B-roll to meet exactly (head or tail), or move the shot when the clip has no handle. API: there's no trim call, so delete and re-append at the new range: append D frames at 100% (`endFrame = sf + ceil(D * fps / tl_fps)`), then `SetSpeed` (Resolve keeps the duration and trims the source), then re-apply Pan/Tilt/Zoom, retime, name, colour and markers.

## Stage 4. Hand to QA (the qa-manager agent checks, this skill fixes)

Since step 2 (v0.17), checking is not done by the same session that placed the shots. After the hard gate prints PASS and the editor has okayed the pacing (Stage 3), run the QA loop (skill `qa-loop`) for the stage `broll`. The qa-manager agent measures every shot with fresh eyes (motion cards, rendered shake check, framing and level stills, the rulebook) and returns findings. Fix them with the ladder below, then QA checks again. The measuring recipes (motion card, shake_check tiers, rendered stills) live in `qa-loop/references/checklists/broll.md`.

## Stage 5. Fix ladder (in order)

1. Slide to a steadier part of the same clip, or re-pick another window of the same subject; re-score it.
2. Stabilise with Gyroflow: colour the clip Orange and add a clip marker whose custom data is `{"gyroflow": {"smoothness": .., "horizon": .., "horizon_amount": .., "horizon_roll": .., "zoom_mode": "Dynamic", "zoom_window": 4, "max_zoom": ..}}`. Presets: static 0.3 + horizon lock; slow gimbal push/slide/orbit 0.5 + horizon lock; tilt reveals 0.5 + roll-only lock; handheld follow / walk-and-talk 0.8, no horizon lock. Run it headless with `scripts/gyroflow_headless.py --project P --timeline T`. The script (Workspace > Scripts > Utility > "Gyroflow Stabilize Flagged"; path in `editor.json` `tools.gyroflow.stabilize_script`) stabilises at 100%, re-applies speed and retime settings, renders next to the source clip, places it on a "Gyroflow" track, disables the original and colours the new clip Yellow.
   - `horizon_amount` is a percentage (100 = full lock; 1.0 means 1%, effectively off). `max_zoom` is a % limit the script only passes on above 50; use 0 for no limit.
   - Reframe first, Gyroflow second: the script copies Pan, Tilt, Zoom and crop onto the stabilised clip. It refuses camera files with no gyro data (REQUIRE_GYRO), so only flag shots whose file has motion data (Sony rtmd track; shot log `shoot.cameras[].gyro`) and list the rest for the editor. Gyroflow not installed: skip this rung and go to 3.
   - Check verticals after stabilising: horizon lock levels the gyro horizon, not the room, so a shot can still lean 1-1.5 deg. Level it with RotationAngle and the smallest zoom that hides the corners (Tim, Green C3: zoom 1.06-1.09 for 1.0-1.4 deg) [Tim, 29 Oct 2026].
   - After stabilising, re-check framing on every shot (orig vs stab 9:16 crop at first/mid/last): the stabilisation zoom shifts and tightens the frame, so re-centre with Pan on the stabilised clip; horizon lock can add roll to an already-level upward shot (re-render with horizon off); some clips crop ~1.4x whatever the settings: Beon still prefers the stabilised version over a wider shaky one (Green C3 C9995, 29 Oct 2026), so keep it and re-centre with Pan rather than reverting.
   - When the editor asks for Gyroflow on all B-roll, flag every gyro-capable B-roll shot Orange with a preset marker, not only the shaky ones.
3. If still shaky: slow down (reason `shake`) with Optical Flow, down to the floor: 48% for empty rooms (Speed Warp Better below 48% is only for 100 fps footage), 60% for people moving, 80% for people talking.
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

QA passes the stage (or the editor settles what it escalated), then set the shots Green and hand the editor the watch-down. Write the QA results, motion verdicts, usage and lessons back to the shot log.

## Clip colours (Beon convention)

Green pass, Yellow check or stabilised pending re-measure, Orange stabilise, Violet retime, Chocolate replace. A marker on each flagged shot with the QA finding id and reason.
