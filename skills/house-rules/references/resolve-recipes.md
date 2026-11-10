# Speed playbook and Resolve gotchas

Learned the hard way on Namir C6/C1/C7 and Arriva Oct C1/C3 (Oct 2026). Read before a big job.

## The fast path for a talking-head concept

| Step | Tool | Typical time |
|---|---|---|
| 1. Ingest the shoot once | `shotlog/scripts/ingest.py` (probe, gyro, keyframes, sheets; resumable) | ~2 s per clip |
| 2. Transcribe interviews | Resolve `MediaPoolItem.TranscribeAudio()` then `GetTranscription(True)` (word timings) → `_shotlog/transcripts/` | a minute or two per interview |
| 3. Pick the lines | read transcripts, beats from the brief, Tim's answers to the grilling | |
| 4. Cut the A-roll | `aroll-cut/scripts/cut_pieces.py plan.json` → sub-pieces + AppendToTimeline list | < 1 s |
| 5. Append | ONE `run_script` call that appends every item | seconds |
| 6. Self-review the joins | `aroll-cut/scripts/cut_review.py` → look at the sheets, fix flags | ~1 s per join |
| 7. B-roll windows | Footage Prep selects → `broll/scripts/broll_auto.py` (window, speed with its reason, Gyroflow preset, snippet); `framing_sheet.py` for 9:16 pans. No Footage Prep: `bestwin.py` (gyro cache) shortlists windows, then `broll_auto.py` still runs | ~3 s per slot |
| 8. Place B-roll | ONE `run_script` with the snippet: append real-time lengths, SetSpeed only on slowed shots, retime, names, colours, `why`; then `gyroflow_headless.py` and `broll_gate.py` PASS | seconds |
| 9. Motion cards | only on candidate windows before placing (placed shots: the qa-manager measures them); Gyroflow the flagged ones in one batch | ~10 s per shot |
| 10. Verify | subtitles on a duplicate timeline, `filler_scan.py` on the used ranges | |
| 11. Render check | `finish-pass/scripts/resolve_proxy_render.py` then `render_check.py` on the proxy | a minute or two |
| Changes after B-roll | `aroll-cut/scripts/resolve_snapshot.py` → `recut_plan.py` → `resolve_relay.py` (on a copy) | seconds |

On Arriva Oct C1 the hand-built A-roll took most of an hour; `cut_pieces.py` reproduced the same sub-pieces in 0.13 s and found the "family-based [uh] company" and "[uh] all the employees" fillers on its own.

## Device VM (where the footage is)

- 4 cores, ~3 GB RAM. Each `device_bash` call is a fresh shell with a short time limit (as low as 45 s on some connections, up to 180 s). Background jobs die when the call returns: run work in the foreground, time-budgeted and resumable, and just call again until it prints DONE.
- Decode in a 4-way thread pool (ffmpeg per frame); `-ss` before `-i` for fast seeks.
- `telemetry_parser` loads the whole file: skip gyro on clips over ~5 GB (8-min tripod interviews ran the VM out of memory). One clip at a time.
- OpenCV 5 has no `CascadeClassifier`; for Haar faces install `opencv-python-headless<5` into its own folder (`pip install --target ~/work/cv4`) and put it on PYTHONPATH.
- Hugging Face (and other model hosts and speech APIs) are blocked in both the VM and the cloud workspace; only package registries get through. Use Resolve's transcription, or a model folder Tim downloads into a connected folder (CrisperWhisper: `aroll-cut/scripts/verbatim.py`).
- The VM is aarch64: CTranslate2-based packages often ship x86_64 wheels only, and torch newer than 2.5.1 on aarch64 pulls several GB of CUDA libraries and fills the disk. Use `torch==2.5.1` in a venv with `--no-cache-dir`.
- The T7 is exFAT: macOS leaves `._NAME.MP4` AppleDouble files. Skip names starting with `._` in every glob.
- Keep scratch in `~/work/<shoot>`; put only what must be looked at (sheets) in a non-Dropbox connected folder and stage just those images. Pack many clips per image (8 per sheet, 6 joins per sheet).
- Moving files to the VM: `device_commit_files` with a `stagedPath` reuses a stale upload when the same staged path is committed twice. Give every new version a new file name, and don't `cp` and commit in the same tool block.

## Inside Resolve (keep it light)

- Never measure inside Resolve's Python (no numpy, 60 s limit, and it slows the UI Tim is using). Export (LUT, DRT, FCPXML, stills) and measure in the VM.
- Batch: one `run_script` per stage with every item in it, not dozens of single MCP calls.
- Stop all Resolve calls the moment Tim needs it. Never delete Tim's timelines; duplicate before risky changes.

### Editing API

- `MediaPool.AppendToTimeline([{mediaPoolItem, startFrame, endFrame, recordFrame, trackIndex}])`: integer source frames in the clip's own fps; `endFrame = startFrame + ceil(D_timeline_frames * src_fps / tl_fps)`. Float ends leave gaps.
- Multicam clips run at the timeline rate (24) with the angle offset baked in: source frame = `round((A_cam_seconds + offset) * 24)` (Arriva Azar: offset 11/12 s). Find the offset in an FCPXML export (`mc-angle`).
- `CreateMulticamClip([A, B], {"angleSyncMode": MULTICAM_ANGLE_SYNC_AUDIO, "multicamAudioMode": MULTICAM_AUDIO_REFERENCE})` with the mic camera first puts its audio on every angle. Sources move to an "Original Clips" bin. No API switches angles on a timeline item: put B-angle pieces on a named track above V1. (`PerformMulticamSmartSwitch` exists in 21.x: untested.)
- `SetSpeed` keeps the item's duration and shortens the source: append the full real-time record length first, then `SetSpeed({'Percentage': <speed>, 'RippleTimeline': False})` (only on shots slowed for a valid reason, broll rulebook section 2). Then `RetimeProcess` = optical flow; `MotionEstimation` = speed warp better only below 48%.
- `TimelineItem.AddMarker` fails on retimed items: add markers before the retime, or pass Gyroflow settings straight to the runner.
- `AddSubFolder` can return None and land the bin elsewhere: check with `GetSubFolderList`.
- `GetIsTrackEnabled` is only reliable on the current timeline: `SetCurrentTimeline` first.
- 9:16 from UHD/HD 16:9 on a 1080x1920 timeline (scale to fill): `Pan = (0.5 - subject_x) * W * 1920/H * zoom`, i.e. `(0.5 - x) * 3413` at Zoom 1. The window slides about ±1166 before it leaves the frame.
- Smooth Cut / Cross Fade: `TimelineItem.AddTransition` (21.1); read back the real span, Resolve needs handles on both sides.

### Transcripts

- Resolve word times drift up to ~0.3 s, and ums/uhs are usually missing. Never cut on word times alone: snap to energy gaps (`cut_pieces.py` does this) and scan the audio for hidden fillers.

### Stabilising

- Gyroflow: colour the clip Orange with the settings in a clip marker, then Tim's "Gyroflow Stabilize Flagged" script. Run headless via its Runner; the first run can report a false "render failed" (output mtime check). Run it again: it reuses the cached render (`~/Movies/Gyroflow Cache/<Project>/`) and places it on the "Gyroflow" track.

### Grading

- `ApplyGradeFromDRX` once per fresh clip, never twice on the same clip (that crashed Resolve). `ResetAllGrades` is a separate step. See colour-grade.

## Not tried yet (worth a test on a scratch timeline)

- davinci-resolve MCP `edit_engine` (plan_tighten, plan_silence_ripple, selects, swap) and `media_analysis` vision: could replace some of the scripts above.
- Resolve 20/21 AI tools: IntelliScript (builds a timeline from a script), SmartSwitch (multicam angle switching on who's talking), IntelliCut, Audio Assistant, Dialogue Matcher.
