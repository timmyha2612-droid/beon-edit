---
name: "resolve-footage-sort"
description: "Sort a DaVinci Resolve bin of raw footage into numbered content bins and log audio and interviews, using the davinci-resolve MCP plus local ffmpeg."
---

# Resolve footage sort

Use when Tim asks to sort, organise or log raws in a Resolve project (Beon Media client shoots).

## 1. Scope
- Ask which project and bin, and confirm the project is open in Resolve. If Tim is actively editing, avoid switching timelines.
- Read the clips with `folder.get_clips` and get one clip's `File Path` via `media_pool_item.get_clip_property` to find the source folder.
- Raws usually live on the T7 drive (`/Volumes/T7 Shield/Raws/<Client>/<Month>/...`) or in Dropbox. Prefer the T7 copy. If a Dropbox path can't be requested, ask Tim to add the folder with Add folder.

## 2. Look at the shots (cheap)
- Run `shotlog/scripts/ingest.py` in device_bash (probe, gyro, 4 keyframes per clip, contact sheets of 8 clips) with the sheets going to `_claude_thumbs/` inside a connected T7 folder (never inside Dropbox, so nothing syncs to the team). Repeat the call until it prints DONE.
- Stage only the sheets and read them. The same pass seeds the shot log, so nothing gets decoded twice.

## 3. Bins
- Default system: bins by shot content, numbered `01`, `02` and so on, e.g. Interviews, Team Moments, Office Floor, Branding & Reception, Audio & Music, Timelines & Subtitles. Adapt the names to the shoot (e.g. Arrival & Lift, Kitchen & Coffee, Meeting Room).
- Create bins one at a time: `media_pool.set_current_folder` with path `<Bin>` (no `Master/` prefix), then `add_subfolder` with no parent, and repeat. Parallel creates fail, and `parent_path` can land the bin in Master. Check with `get_subfolders` and fix with `move_folders`.
- Move clips with `media_pool.move_clips` (`target_path` = `Master/<Bin>/<Sub>`). Afterwards, check that the parent bin is empty.

## 4. Audio pass (free, local)
- In device_bash, run `ffmpeg -vn -af silencedetect=n=-40dB:d=0.5,volumedetect` per clip and save a CSV to $HOME.
- Flag clips with no sound (mean around -67 dB, 100% silence), clipping (peak 0.0 dB) and clips under 1 second.

## 5. Interviews
- Hugging Face is blocked, so don't use whisper models in the VM.
- Preferred: `MediaPoolItem.TranscribeAudio()` on each interview clip, then `GetTranscription(True)` for word-timed segments; save as JSON in the shot log `transcripts/` (the format `aroll-cut/scripts/cut_pieces.py` and `filler_scan.py` read).
- Fallback: a scratch timeline from `create_timeline_from_clips` (`clip_infos` start_frame 0 to the full length, so in/out marks are ignored), then `timeline_ai.create_subtitles`. The call may time out but still finish, so check the subtitle track count, then read the subtitle items into a clip-relative `[mm:ss] text` transcript.
- Analyse the transcript: speakers and roles, best soundbites with timecodes, hooks, sections to avoid (setup, jokes the speakers asked to cut, swearing), and claims to verify with the client (e.g. growth percentages).

## 6. Report
- Give a table of bin, contents and clip count, plus judgement calls, junk clips, audio warnings and cleanup notes (the `_claude_thumbs` folder and any scratch timelines).
- Keep it short and avoid em dashes.