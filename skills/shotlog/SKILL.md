---
name: shotlog
description: "This skill should be used for any footage task on a Beon Media shoot (sorting, selects, B-roll, interview cuts, grading) to read and keep the per-shoot shot log (_shotlog/ in each shoot folder), including its shoot block (cameras, audio, multicam, people). Read it first, analyse only what's missing, write back after. Triggers: \"use the shot log\", \"which clips are steady\", \"what did we use in C6\", \"log this shoot\".\n"
metadata:
  version: "0.6.0"
---

# Shot log (Beon Media shoots)

Goal: never analyse the same footage twice. Every shoot folder gets a `_shotlog/` with what is known about each clip, and every job reads it first and writes back what it learned.

## Location

- `<shoot folder>/_shotlog/`, next to the camera cards (e.g. `<footage root>/<Client>/<Shoot>/_shotlog/`). Some clients keep raws in a synced folder (client profile `footage.write_protected`); the shot log still goes there, media never does.
- Small text only: `jobs/` (one job card per concept, house-rules), `lessons/` (one lessons inbox per concept, learn-from-tim), `qa/` (QA rounds per concept, qa-loop), `shotlog.json` (source of truth, schema `beon-shotlog/1`), `shotlog.csv` (one row per clip), `README.md`, `transcripts/` (word-timed JSON), `plans/` (concept cut plans), `tools/` (analysis scripts used).
- Never put media, thumbnails, motion cards or renders here (they sync to the team). Images go in the job's scratch folder (`<scratch_root>/<client>-<shoot>/<concept>/`, editor.json `scratch_root`), never in a folder listed in editor.json `synced_folders` or in Dropbox. If run_env is device-vm, they go in the VM scratch, or a non-synced connected folder when they must be staged to view.

## Before any footage task

0. Footage Prep first [Tim, 9 Nov 2026], when editor.json `tools.footage_prep.enabled` is true: follow `house-rules/references/footage-prep.md`. Reachable: make sure the shoot is in the app and analysed (by the editor in `shoot.prepped_by` only; others read, don't re-prep), then copy its scores, flags, movement and selects into each clip's `footage_prep` block. Not enabled or not reachable: tell the editor in one line, use the fallback (step 6) and set `footage_prep.available: false`. Its scorer is the first source for picks; Claude's own analysis adds what it doesn't cover (content, people, transcripts, motion at the slot's speed).
1. Find and read `_shotlog/shotlog.json`. If none exists, create one at the end of the job. Read its `shoot` block (below); if it is missing or has gaps the job needs, fill it now.
2. Use what's there: content and people, gyro windows, people windows (face_x for 9:16 pan), verified frames, transcripts, interview best lines and `avoid` lists, `lessons`.
3. Check `usage` so a series of concepts doesn't reuse a clip window (same clip + overlapping source range in another concept = repeat). Prefer unused shots; reuse only when it's the only option.
4. Respect the people registry (`shoot.people`). Confirm identities with the editor before using a person to illustrate a line (e.g. the stylist is not a vendor). Never guess a name.
5. Only analyse clips that are missing or flagged stale.
6. New shoot (fallback, or when Footage Prep is off): run `scripts/ingest.py SHOOT_DIR <scratch>/ingest <scratch>/sheets` (scratch = `<scratch_root>/<client>-<shoot>`). Locally it runs to the end in one call. If run_env is device-vm, pass the budget from the Mac's editor.json (the VM usually has none): `--budget <run_env.shell_budget_s - 20>`, or `--budget 160` when that isn't set; it stops there, so repeat the call until it prints DONE. One pass gives probe data, gyro shake windows, 4 keyframes per clip, contact sheets (8 clips per sheet, labelled with duration, fps, shake and time of day) and `cameras_suggested.json` for the shoot block. Look at the sheets, then write content, people and moves into the log. Test: 4 clips in 9 s.

## Shoot block (shotlog.json > shoot)

The shoot facts every job reads (intake standard section 3, `house-rules/references/intake.md`). Fill it on the first footage task on a shoot (sort, ingest, A-roll, B-roll or grade, whichever comes first), then only add what a later job needs.

```json
"shoot": {
  "shoot_folder": "<footage root>/<Client>/<Shoot>/", "client": "<slug>", "shoot": "<Shoot>",
  "location": "<plain words>", "days": ["<YYYY-MM-DD>"],
  "cameras": [{"folder": "<card folder>", "role": "A", "model": "FX3", "fps": 25, "res": "3840x2160",
               "codec": "h264", "log": "S-Log3", "gyro": "sony-rtmd", "ext": ".MP4", "name_pattern": "C*"}],
  "audio": {"mic_camera": "A", "mic_channel": 2, "safety_channel": 1, "safety_offset_db": -6},
  "multicam": {"exists": true, "clip": "<Name> Multicam", "audio_ref_camera": "A", "angle_offsets_s": {"B": 11.0}},
  "people": {"<Name>": "<role>"},
  "language": "en",
  "resolve_bin": {"path": "<Month>/<Job>/<Shoot>", "sorted_bins": []},
  "footage_prep": {"shoot": "<app shoot name>", "available": true},
  "prepped_by": {"editor": "<editor.json name>", "machine": "<computer>", "date": "<YYYY-MM-DD>"}
}
```

How to fill it:
1. Probe, don't ask, what the files say. `ingest.py` writes `cameras_suggested.json` (per card folder: fps, res, codec, ext, name pattern, model and log profile from the Sony XML sidecar when there is one, whether gyro was found). Without ingest, run `ffprobe` on one clip per card folder. Footage Prep's `shoot_summary` covers the rest when it is on.
2. Ask the editor only the gaps, in one question: which folder is A/B, which camera and channel carry the clean mic (`audio.mic_camera`, `audio.mic_channel`), the multicam clip and its audio reference camera, who is who (`people`), the Resolve bin. Defaults come from the client profile (`language`, `people`).
3. Write it, then read it back. Never overwrite a field that is already set: a value the editor confirmed beats a new probe. If a probe disagrees with what is there, say so and ask.

Rules:
- `people` is the only source of names. Keep the old top-level `people` in step with it (older skills and Footage Prep read that one).
- `cameras[].gyro`: `sony-rtmd` for Sony bodies with gyro, `none` for anything else (Gyroflow can't stabilise it from metadata).
- `prepped_by`: one prepper per shoot. Set it when Footage Prep analyses the shoot. Other editors read the app's results and never re-prep.
- Older logs have a top-level `shoot` that is a plain name string (Footage Prep writes it that way). When writing the block, replace the string with the object and keep the old text in `shoot.label`. Footage Prep never writes `shoot` after creating the log, so this is safe.
- Old top-level `client`, `days`, `footage_prep` stay where they are. Footage Prep owns the top-level `footage_prep`; the block's `footage_prep` only names the app shoot.

## Per-clip entry (shotlog.json > clips[])

Each clip keeps what came from where. `footage_prep{tier, auto_tier, flags[], movement, metrics{stability, jitter, shaky_frac, ...}, selects[{in_frame, out_frame, score}], synced}` is copied from the app as-is, never edited by hand. Claude's analysis goes in the fields below. When the two disagree, keep both and add a `verified_frames` note or a `warning` saying which one held up on the second look.

`clip, file, camera, log_profile, fps, duration_s, bin, content, people, shot_move, notes, gyro{shake_med, shake_p90, speed_med, windows{1.0,2.0,3.0: [{t, shake, move, steady}]}, shake_1s[]}, audio{mean_db, max_db, silence_pct, flags}, people_windows[{t, len, people_avg, faces_avg, face_x}], verified_frames[{t, note}], motion[{t_in, dur, speed, move, jitter_p90_px, flags}], transcript{file, words, engine}, usage[{concept, timeline, slot, src_in, src_out, rec_frames, speed, line, role, reason, status: placed|planned|final, warning}]`. `reason` is one plain line on why the clip went in (or was dropped): the line it matches, and for B-roll the place, scene, setup, Footage Prep tier and stability.

### Sort keys (owned by resolve-footage-sort)

The footage sort writes these per clip. Other skills read them, only the sort (or the editor) changes them:

- `sort{v, axis, at, approved, archive_only, bin_verified, editor_changes[]}`: sort version (must be "0.3", the inventory treats any other v as not sorted), axis (place, subject or concept), when, whether the editor approved it at the gate (false after "Only write the shot log"), archive only (a reject or unsure clip with no copy), the day the copy was verified, and `editor_changes`, the list of the editor's changes `{field, from, to, date, editor}` (taxonomy section 7). Older logs call it `tim`: read both, write `editor_changes`.
- `scene`, `setup`, `take_family`, `dup_of`: which scene and camera setup the clip belongs to, its group of takes, and the clip it duplicates.
- `place{id, family, inferred}`, `subject`, `concept`: what and where. All three are kept whatever axis the bins use.
- `shot_size`, `angle`, `light`, `people_detail{count, role, faces, names, minors_visible}`, `roles` (taxonomy list: aroll, establishing, place, people, detail, transition, junk), `good_for`, `not_for`, `vertical`, `subject_x` (0-1, for 9:16 Pan), `confidence`.
- `sort_role`: the rule role from the inventory (aroll, multicam_angle, audio, broll, junk_candidate).
- `sort_copy{bin, uid}`: the copy's bin relative to the shoot bin (`01 Park`) and its Resolve UniqueId. sort_apply writes it only after a verified copy. `bin` then holds the copy's full bin path. The original stays at the root of the shoot bin, which is the archive.

Technical state (tier, flags, movement, stability, selects) is read live from Footage Prep when needed, never copied into the sort keys.

Top level: `schema, updated, client, shoot{...} (the shoot block above; a name string in older logs), property, footage_prep{available, shoot, imported, synced}, jobs[] (job card paths), days, people{name: description}, conventions, interviews[{clip, transcript, source_files, best_lines, avoid, usage}], lessons[]`.

## After any footage task (write back)

- Add or refresh entries for clips analysed (gyro, audio, people windows, transcripts, motion cards).
- Add `verified_frames` for every moment actually looked at, with a plain description.
- Add `usage` for every placement or plan. After the editor finishes a concept, update usage to their final version (`status: final`): their slips, retimes and removals matter for the next concept.
- Add a `warning` when something needs fixing (wrong person, repeat, shaky).
- Add new `lessons` learned on this shoot. Fill any shoot block gap the job found (never overwrite a set field).
- Update `updated`, regenerate `shotlog.csv`, save plans to `plans/`.
- When Resolve is free (never while the editor needs it): mirror key fields into the media pool clip metadata (Comments = content + people + notes, Keywords = room/people/flags) so the editor sees them in Resolve.

## Tools

- Gyro: `telemetry_parser` (pip) on Sony FX3 / A7S III files; jitter RMS deg/s, tiers pass < 0.35, check 0.35–0.6, fix > 0.6.
- Motion card per shot window: `broll/scripts/motion_card.py` (filmstrip, camera path, jitter at output resolution). Run on candidate windows before placing; placed shots are measured by the qa-manager agent (qa-loop).
- Intent map (whole-clip optical-flow move map, finds resets and the real move): only on demand, when the editor asks or a clip's move is unclear. Script: `broll/scripts/intent_map2.py CLIP... --dir <shoot.shoot_folder> --prefix <shoot.cameras[].name_pattern without *>`.
- Transcripts: Resolve `MediaPoolItem.TranscribeAudio()` then `GetTranscription(True)` for word timings, saved to `transcripts/`, or whisper when editor.json `tools.whisper` is set (if run_env is device-vm, Hugging Face is blocked, so Resolve only). Use `shoot.language`. Word timings drift up to 0.3 s and fillers are usually missing; `aroll-cut/scripts/cut_pieces.py` handles both. Take audio from `shoot.audio.mic_camera` / `mic_channel`.
- People: OpenCV 4.x (`pip install "opencv-python-headless<5"`, HOG + Haar faces) on keyframes, then verify by eye. Mouth edges: `broll/scripts/mouth_check.py` (mediapipe 0.10.14).
- Copies of the scripts used live in `_shotlog/tools/`.
