---
name: shotlog
description: "This skill should be used for any footage task on a Beon Media shoot (sorting, selects, B-roll, interview cuts, grading) to read and keep Tim's per-shoot shot log (_shotlog/ in each shoot folder). Read it first, analyse only what's missing, write back after. Triggers: \"use the shot log\", \"which clips are steady\", \"what did we use in C6\", \"log this shoot\".\n"
metadata:
  version: "0.4.0"
---

# Shot log (Beon Media shoots)

Goal: never analyse the same footage twice. Every shoot folder gets a `_shotlog/` with what is known about each clip, and every job reads it first and writes back what it learned.

## Location

- `<shoot folder>/_shotlog/` inside Tim's Dropbox (e.g. `Namir Mikha/[01. Content]/Videography/1. SHOOTS/2026/Shoot 16. Bishop St/_shotlog/`).
- Small text only: `jobs/` (one job card per concept, house-rules), `shotlog.json` (source of truth, schema `beon-shotlog/1`), `shotlog.csv` (one row per clip), `README.md`, `transcripts/` (word-timed JSON), `plans/` (concept cut plans), `tools/` (analysis scripts used).
- Never put media, thumbnails, motion cards or renders here (they sync to the team). Images go in the device VM scratch, or a non-Dropbox connected folder when they must be staged to view.

## Before any footage task

0. Footage Prep first [Tim, 9 Nov 2026]: follow `house-rules/references/footage-prep.md`. Reachable: make sure the shoot is in the app and analysed, then copy its scores, flags, movement and selects into each clip's `footage_prep` block. Not reachable: tell Tim in one line, use the fallback (step 6) and set `footage_prep.available: false`. Its scorer is the first source for picks; Claude's own analysis adds what it doesn't cover (content, people, transcripts, motion at the slot's speed).
1. Find and read `_shotlog/shotlog.json`. If none exists, create one at the end of the job.
2. Use what's there: content and people, gyro windows, people windows (face_x for 9:16 pan), verified frames, transcripts, interview best lines and `avoid` lists, `lessons`.
3. Check `usage` so a series of concepts doesn't reuse a clip window (same clip + overlapping source range in another concept = repeat). Prefer unused shots; reuse only when it's the only option.
4. Respect the `people` registry. Confirm identities with Tim before using a person to illustrate a line (e.g. Molly is the stylist, not a vendor).
5. Only analyse clips that are missing or flagged stale.
6. New shoot: run `scripts/ingest.py SHOOT_DIR ~/work/<shoot> <non-Dropbox sheet folder>` in the device VM, repeating the call until it prints DONE. One pass gives probe data, gyro shake windows, 4 keyframes per clip and contact sheets (8 clips per sheet, labelled with duration, fps, shake and time of day). Look at the sheets, then write content, people and moves into the log. Arriva test: 4 clips in 9 s.

## Per-clip entry (shotlog.json > clips[])

Each clip keeps what came from where. `footage_prep{tier, auto_tier, flags[], movement, metrics{stability, jitter, shaky_frac, ...}, selects[{in_frame, out_frame, score}], synced}` is copied from the app as-is, never edited by hand. Claude's analysis goes in the fields below. When the two disagree, keep both and add a `verified_frames` note or a `warning` saying which one held up on the second look.

`clip, file, camera, log_profile, fps, duration_s, bin, content, people, shot_move, notes, gyro{shake_med, shake_p90, speed_med, windows{1.0,2.0,3.0: [{t, shake, move, steady}]}, shake_1s[]}, audio{mean_db, max_db, silence_pct, flags}, people_windows[{t, len, people_avg, faces_avg, face_x}], verified_frames[{t, note}], motion[{t_in, dur, speed, move, jitter_p90_px, flags}], transcript{file, words, engine}, usage[{concept, timeline, slot, src_in, src_out, rec_frames, speed, line, role, status: placed|planned|final, warning}]`.

Top level: `schema, updated, client, shoot, property, footage_prep{available, shoot, imported, synced}, jobs[] (job card paths), days, people{name: description}, conventions, interviews[{clip, transcript, source_files, best_lines, avoid, usage}], lessons[]`.

## After any footage task (write back)

- Add or refresh entries for clips analysed (gyro, audio, people windows, transcripts, motion cards).
- Add `verified_frames` for every moment actually looked at, with a plain description.
- Add `usage` for every placement or plan. After Tim finishes a concept, update usage to his final version (`status: final`): his slips, retimes and removals matter for the next concept.
- Add a `warning` when something needs fixing (wrong person, repeat, shaky).
- Add new `lessons` learned on this shoot.
- Update `updated`, regenerate `shotlog.csv`, save plans to `plans/`.
- When Resolve is free (never while Tim needs it): mirror key fields into the media pool clip metadata (Comments = content + people + notes, Keywords = room/people/flags) so Tim sees them in Resolve.

## Tools (device VM)

- Gyro: `telemetry_parser` (pip) on Sony FX3 / A7S III files; jitter RMS deg/s, tiers pass < 0.35, check 0.35–0.6, fix > 0.6.
- Motion card per shot window: `broll/scripts/motion_card.py` (filmstrip, camera path, jitter at output resolution). Run on candidate windows before placing; placed shots are measured by the qa-manager agent (qa-loop).
- Intent map (whole-clip optical-flow move map, finds resets and the real move): only on demand, when Tim asks or a clip's move is unclear. Script: `broll/scripts/intent_map2.py` (paths inside are shoot-specific; adapt).
- Transcripts: Resolve `MediaPoolItem.TranscribeAudio()` then `GetTranscription(True)` for word timings, saved to `transcripts/` (Hugging Face is blocked in the VM, so no whisper models). Word timings drift up to 0.3 s and fillers are usually missing; `aroll-cut/scripts/cut_pieces.py` handles both.
- People: OpenCV 4.x (`pip install "opencv-python-headless<5"`, HOG + Haar faces) on keyframes, then verify by eye. Mouth edges: `broll/scripts/mouth_check.py` (mediapipe 0.10.14).
- Copies of the scripts used live in `_shotlog/tools/`.
