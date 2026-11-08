---
name: broll-qaqc
description: "This skill should be used when adding, reviewing or fixing B-roll on a Beon Media concept edit in DaVinci Resolve: \"add B-roll\", \"pick shots for this line\", \"check the shaky shots\", \"use shots we haven't used\", \"fix this shot\", \"pacing pass\". Covers selection, placement, the pacing gate, the motion card, the fix ladder (re-pick, Gyroflow, Speed Warp, replace) and sign-off.\n"
metadata:
  version: "0.5.0"
---

# B-roll QA/QC (Tim, Beon Media)

Work in stages and stop at the gates. Never touch V1/A1 (interview), the music track, or anything Tim says he has placed. Stop all Resolve calls when Tim says he needs Resolve; analysis keeps running in the device VM.

## Stage 0. Footage Prep first, then the shot log [Tim, Mill site update, 9 Nov 2026]

Every shoot goes through Tim's Footage Prep app (the `footage-prep` MCP tools) before any B-roll is picked. Never pick B-roll from contact sheets or by eye alone: on The Mill (Nov C2) shots picked that way were shaky, didn't flow and were partly irrelevant, and the app had already scored several of them "reject" or "shaky".

1. `library_shoots` (query = client or shoot). If the folder isn't there, `inspect_folder` then `import` it (client name, `watch: false`) and wait on `progress` until analysis is done. Opening a shoot switches the app, so never pass `switch_shoot` unless Tim asked.
2. Pick only from the app's selects: `selects` with `without_flags: ["shaky","whip","motion_blur","blocked"]`, inside each select's `in_frame`/`out_frame`. Prefer `auto_tier`/Tim's tier `hero` and `metrics.stability` >= ~0.75; below ~0.65 only when it's the only shot for the line, and flag it. Skip clips the app rates `reject` (`clips` with `auto_tier`).
3. Match every shot to its line first (what's said on screen), then flow: similar moves and speeds in a run, never the same room twice in a row, settle before a cut back to camera.
4. Stabilisation renders are Tim's to start in the app; list the shots that need them.
5. Mention in the report which app selects (clip, frames, score, stability) were used.
6. Best stretch inside the select [Tim, Mill, 9 Nov 2026]: a select is 3-12 s but a slot uses ~2-3 s of it. Never start "about 1 s in": measure every window of the needed source length inside the select and take the smoothest. `scripts/select_window.py '<json [[slot, clip, need_src_frames, [[in,out],...]],...]>' out.json <clip folder>` (optical-flow jitter p90, speed evenness, reversals). At 48% the append needs `ceil(D*fps/24)` real-time source frames, so limit the search to windows that fit before the clip end.

## Stage 0b. What Tim expects of every B-roll shot [Tim, Mill, 9 Nov 2026]

- **Relevant to the words, literally.** "The finishes" = kitchen joinery, stone benchtop, tiles, tapware, not a toilet. Toilets only when the line is about bathrooms, and never as the first finishes shot.
- **Use the establishing shots.** When the shoot has building or street exteriors, use them: over the line that names the place ("we're standing in the display suite of The Mill"), on level or location changes ("we're at Level 5"), and as the closing wide into the end card. Don't leave the hero exteriors unused.
- **Flow.** Never the same room twice in a row; similar move speed through a run; cut on motion; settle before cutting back to camera.
- **Stabilise all handheld B-roll** with the Gyroflow Stabilize Flagged script (colour Orange, run it; headless driver pattern in house-rules/references/resolve-recipes.md), horizon lock on: clip-marker custom data `{"gyroflow": {"horizon": true, "horizon_amount": 100}}`. Drone shots are already gimbal-smooth; skip them.
- **Straight verticals, level floor.** After stabilising, export a still of every shot and run `scripts/level_check.py STILL...`: it measures the lean of door frames, walls and window mullions and prints the rotation that makes them vertical plus the **minimum** zoom that still covers the 9:16 frame after that rotation. Set `RotationAngle` and `ZoomX/ZoomY` to exactly that (never zoom more than the rotation needs), re-export and check again. Looking-up exteriors converge (keystone): level on the verticals nearest the centre of the frame.

Then read `<shoot>/_shotlog/shotlog.json` (shotlog skill). Reuse gyro windows, people windows, verified frames, tone tags, motion cards and transcripts; check `usage` (prefer unused windows); read `lessons`. Write back at the end.

## Stage 1. Select

- Cut inside the steadiest window: skip the first and last ~1 s, no focus pulls or exposure shifts, keep moves whole (start once underway, out before it eases).
- Fallback when no clean window or no other option: a shot outside the steadiest window can work if it's slowed to a suitable speed and gyro-stabilised. Use it only when necessary and flag it.
- Never use a videographer reset (camera drifting back to the start of a move). Find the clip's real move (longest run in a consistent gyro direction) and reject windows moving the opposite way or between passes.
- Re-score any hand-picked window (shake and direction) before placing.
- Fast window pick: `scripts/bestwin.py GYRO_DIR CLIP REC_SECONDS --speed 48 --avoid <used ranges>` ranks windows from the ingest gyro cache in milliseconds (shake tier, camera speed, uneven moves) and skips ranges already used in the series. Then confirm the winner with a motion card.
- 9:16 framing: `scripts/framing_sheet.py CLIP T OUT.jpg --pans a,b --x <subject x> --times <end of move>` draws the vertical windows and a Pan ruler on the full frame, at the start and end of a moving shot, and prints the Pan that centres a subject.
- 9:16 reframe sideways [Tim, 29 Oct 2026]: the vertical window only sees about a third of a 16:9 frame, so when the subject (the person, sign, door or feature the line is about) isn't in the middle, slide the window sideways with Pan to put it there. Never leave the subject cut by the window edge or sitting off to one side with empty wall in the middle. Moving shot: centre the subject mid-shot, then check the first and last frame still hold it. No single subject (empty room): frame the strongest feature or the leading lines. If the subject is beyond the slide limit, accept it off-centre or re-pick. Check every B-roll shot this way before the pacing gate, and verify with a rendered still.
- Pan units differ per timeline. Most 1080x1920 timelines take fill-space Pan ((0.5 - x) * 3413 for UHD at Zoom 1); some report scaleToFit and render fill and take fit-space Pan ((0.5 - x) * 1080; Green Oct 2026). `framing_sheet.py --space fit` prints fit-space values. Confirm with one rendered still per timeline before setting many. The readback can also differ from what a script wrote: on Green C3/C5 every Pan later read back as 1/4 of the value set while the picture stayed identical, so never infer framing changes from Pan numbers alone; compare stills.
- Matching: if there's an exact match for the line (what's named, the person talked about), use it. If not, use whatever fits the line without creating a misunderstanding (never a shot that implies something false). A line about a specific room or light must show that room if it's shown at all.
- People: confirm identity (shot log people registry). The first and last ~0.3 s must not freeze on a wide-open mouth or grimace; nudge up to ±0.5 s inside the steady window (`scripts/mouth_check.py`). Goofy or playful moments only where the concept allows it; ask in the opening grilling.
- Light spots: a small blown highlight is fine. Reject or shorten a shot when the hot spot is a significant part of the frame or the shot lingers on it (C7 R14).

## Stage 2. Place

- Roughly 50/50 speaker and B-roll; walkthrough pieces can run heavier (C7 finished at 64%).
- Open each speaker turn on camera ~1.5–2 s; cover visible jump cuts (see aroll-cut for when a small one can stay); in long takes switch every ~4–6 s.
- Phrase-led rhythm: shots ~2–3 s, changing on sentence breaks.
- Open with 1–1.5 s of B-roll only before the first line.
- Breathing gap (hero property shots, music only) when the edit needs it: between two separate points or two answers, or when the speech has run continuous and fast for too long. Size it to the music once music is in.
- Speed: first try 50p empty-house shots at 48% and people at 50–60% (optical flow). If a shot still reads shaky, go slower (see fix ladder).
- B-roll is video only, hard cuts, on V2. Name items `<slot> <clip>` (e.g. `R4 0331`).
- Movement flow: no back-to-back opposite camera moves; similar speeds within a run; the last shot settles before cutting back to camera; cut on motion between moving shots.
- Outro and ending depend on the edit; Tim usually runs B-roll past the last word into the end card.

API: `AppendToTimeline` with source frames, length `ceil(D*fps/24)` (exclusive end), absolute `recordFrame`. Slow-mo: append real-time length then `SetSpeed({'Percentage': 48.0, 'RippleTimeline': False})`. Retime quality: `SetProperty('RetimeProcess', RETIME_OPTICAL_FLOW)`, `SetProperty('MotionEstimation', MOTION_EST_SPEED_WARP_BETTER)`.

## Stage 3. Pacing gate (Tim approves)

Report shot count, coverage %, shot lengths (flag < 1 s or > 4 s), uncovered jump cuts, on-camera openings per turn. Wait for Tim's go.

Gap check before the gate [Tim, 29 Oct 2026]: walk the top visible layer frame by frame across V1, the angle track and B-roll. Nothing may show on screen for under ~1 s (24 frames) between two other shots: no 2-4 frame flash of the speaker between B-roll shots (Green C5 28:10, C6 16:10), no B-angle sliver before a B-roll shot. A B-roll shot that covers an A-roll cut must run to that cut frame or past it, never end a frame or two short (C6 32:05). Fix by trimming the neighbouring B-roll to meet exactly (head or tail), or move the shot when the clip has no handle. API: there's no trim call, so delete and re-append at the new range: append D frames at 100% (`endFrame = sf + ceil(D * fps / 24)`), then `SetSpeed` (Resolve keeps the duration and trims the source), then re-apply Pan/Tilt/Zoom, retime, name, colour and markers.

## Stage 4. Detail pass: read the motion

Stills hide motion. For every placed shot, render a motion card and read it:

`python3 scripts/motion_card.py CLIP T_IN SRC_DUR OUT.png --speed 48 --pan P --tilt T --zoom Z --label "R4 0331"`

The card shows a 6-frame filmstrip of the 9:16 window, a first/last onion skin, flow arrows mid-shot, the camera path (pan, tilt, zoom speed per frame) and jitter per output frame at 1080 wide. The JSON line gives the move, jitter p90/max and flags (mid-ease, uneven speed, per-axis slowing, direction reversal). Save cards outside Dropbox; stage them to look.

- Jitter tiers (provisional, calibrate against gyro): p90 < 1.0 px pass, 1.0–2.0 check, > 2.0 fix. Also keep the gyro tiers: pass < 0.35, check 0.35–0.6, fix > 0.6 deg/s.
- Flag jerky moves: speed varies > 30% inside the shot, or it starts or ends mid-ease; a reversal means a reset.
- Example: C7 R4 at 11.0 s @48% had jitter p90 0.85 px, max 1.46. Tim slid it to 11.56 s and slowed it to 30%: p90 0.38, max 0.71.
- Check the first and last frame of every shot (resets, moves ending on a blank wall, awkward faces) and the tone match.

## Stage 5. Fix ladder (in order)

1. Slide to a steadier part of the same clip, or re-pick another window of the same subject; re-score it.
2. Stabilise with Gyroflow: colour the clip Orange and add a clip marker whose custom data is `{"gyroflow": {"smoothness": .., "horizon": .., "horizon_amount": .., "horizon_roll": .., "zoom_mode": "Dynamic", "zoom_window": 4, "max_zoom": ..}}`. Presets: static 0.3 + horizon lock; slow gimbal push/slide/orbit 0.5 + horizon lock; tilt reveals 0.5 + roll-only lock; handheld follow / walk-and-talk 0.8, no horizon lock. Tim's script (Workspace > Scripts > Utility > "Gyroflow Stabilize Flagged") stabilises at 100%, re-applies speed and retime settings, renders next to the source clip, places it on a "Gyroflow" track, disables the original and colours the new clip Yellow.
   - `horizon_amount` is a percentage (100 = full lock; 1.0 means 1%, effectively off). `max_zoom` is a % limit the script only passes on above 50; use 0 for no limit.
   - Reframe first, Gyroflow second: the script copies Pan, Tilt, Zoom and crop onto the stabilised clip. It refuses camera files with no gyro data (REQUIRE_GYRO), so only flag shots whose file has motion data (Sony rtmd track) and list the rest for Tim.
   - Check verticals after stabilising: horizon lock levels the gyro horizon, not the room, so a shot can still lean 1-1.5 deg. Level it with RotationAngle and the smallest zoom that hides the corners (Tim, Green C3: zoom 1.06-1.09 for 1.0-1.4 deg) [Tim, 29 Oct 2026].
   - After stabilising, re-check framing on every shot (orig vs stab 9:16 crop at first/mid/last): the stabilisation zoom shifts and tightens the frame, so re-centre with Pan on the stabilised clip; horizon lock can add roll to an already-level upward shot (re-render with horizon off); some clips crop ~1.4x whatever the settings: Tim still prefers the stabilised version over a wider shaky one (Green C3 C9995, 29 Oct 2026), so keep it and re-centre with Pan rather than reverting.
   - When Tim asks for Gyroflow on all B-roll, flag every gyro-capable B-roll shot Orange with a preset marker, not only the shaky ones.
3. If still shaky: slow to ~50% with Optical Flow + Speed Warp Better.
4. If still shaky: ~30%, only if the subject doesn't move strangely.
5. Replace with a different clip.

## Stage 5b. Measure the rendered result (stabilisation loop)

Judge what the viewer sees: render the timeline at 1080x1920 H.264 to the shoot's `_claude_scratch/proxy` (save Tim's render settings as a temporary preset first, restore and delete it after, and delete your jobs), then run `scripts/shake_check.py RENDER.mp4 SHOTS.json OUT` (SHOTS = [{"shot", "start", "dur"}] in timeline frames).
- Calibrated on synthetic shake (Green, 29 Oct 2026): floor ~0.2 px p90 at 1080 wide; +1 px random shake reads ~1.6; +2 px ~3.2; an accelerating pan stays ~0.2. Tiers: < 1.0 pass, 1.0-1.6 check, >= 1.6 fix.
- It tracks only low-change background (moving people masked) with a Savitzky-Golay (9/2) detrend. Hands or bodies filling the frame can still inflate it: confirm every fix/check by eye (flipbooks with a fixed grid, 2x crops, slit-scans of a static column, hand-tracked background points), with an independent second look.
- Also read the frame-difference spikes: one-frame lighting jumps (a light switching on), dropped frames, held first frames.

What fixed shots on Green C5/C7 (29 Oct 2026):
- Gyroflow can ADD shake on clips that already had in-body/lens stabilisation (C1345: camera 0.2 px, Gyroflow render 2.7 px). Compare the render with the camera file; if the original is steadier, use the original.
- 25p clips at 100% on a 24p timeline drop one frame a second (visible hitch on moves): set 96% with Retime Nearest so every frame plays once.
- Speed Warp smears hands crossing the frame or touching the face: slip the window past the hand rather than changing the retime.
- Residual low-frequency sway: re-render Gyroflow at smoothness 0.8-0.9 + horizon lock (C7 2474: 1.75 -> 0.2 px).
- Walking bob (camera translation) and roll that horizon lock won't hold can't be fixed by Gyroflow: re-pick a calmer window (100 fps clips can drop to ~25% with no invented frames) or replace the shot with a static/tripod one that fits the line.
- Resolve's TimelineItem.Stabilize() runs from scripts but uses the clip's Inspector settings (mode/smooth/strength are not scriptable); at defaults it added nothing measurable on top of Gyroflow.
- Rebuilding a clip (no trim API): read Pan/Tilt/Zoom/Rotation, re-append, re-apply, then confirm framing with a still; Pan readback has been inconsistent between clips and timelines. ExportCurrentFrameAsStill fails on the Deliver page (OpenPage('edit') first).

## Stage 6. Re-measure and sign-off

Re-run the motion card on fixed shots, check first and last frames, run the proxy render check (finish-pass), set Green, then Tim's watch-down. Write QC results, motion verdicts, usage and lessons back to the shot log.

## QC reporting

Clip colours: Green pass, Yellow check or stabilised pending re-measure, Orange stabilise, Violet retime, Chocolate replace. A marker on each flagged shot with score and reason. Short chat table: shot | clip | window | jitter | move flags | face/tone | action | status.
