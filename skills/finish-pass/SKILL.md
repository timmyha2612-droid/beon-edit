---
name: finish-pass
description: "This skill should be used when an edit is nearing hand-off for the final pass (music, grade, final cut by whoever the job card's Stages line names), or when the editor asks about music placement, the break, the ending or delivery for a Beon Media concept: \"add the end card\", \"where should the music come in\", \"set it up for music\", \"is it ready to deliver\". Covers what the editor does themselves, how to leave the edit ready for it, and the delivery checks.\n"
metadata:
  version: "0.2.0"
---

# Finish pass

> **Job card first.** Before any work in this skill, make sure this job has a job card (house-rules, "Grill first"). No card: stop and run the grilling with the editor. The `job_guard` hook blocks Resolve edits without one.

Who does the final cut, music and grade is on the job card Stages line (`music`, `grade`, `final`). At Beon
that is usually the editor themselves. Claude's job is to hand over an edit that's ready for it, and to help
with music, the break and the ending when asked.

## What the editor does themselves (don't do these unless asked)

Whatever the Stages line gives to the editor, typically:
- Final cut adjustments and the music pass.
- Dialogue clean-up: they export the dialogue, run speech enhancement (client profile `audio.dialogue_enhance`), bring it back on A2 and turn off A1. Don't touch A2 or re-enable A1 once that's done.
- Grading sign-off.

If the Stages line gives one of these to Claude, do it and run its QA stage like any other.

## Hand-over state

- V1/A1 interview, V2 B-roll, A3 left free for music (or the editor's music untouched if it's already placed).
- A1 enabled before hand-over (unless the editor has already moved dialogue to A2).
- A breathing break placed where the edit needs one (between two separate points or answers, or after a long fast stretch), marked with a Blue marker so the editor can size it to the music.
- Flagged shots coloured and marked (see broll), plus a short note of anything borderline.
- No black frames or gaps; running time reported.

## Music (when the editor asks for help)

- Start the song so its lift (where the full band comes in) lands on a story beat. C7: the band enters at frame 290, beat 2 starts at 295.
- Put the break over a phrase change in the music, and size the break to fit the phrase (C7 break grew from 2.5 s to 4.4 s with 3 hero shots).
- Land the end card on a phrase start.
- Find lifts and phrase dips with `learn-from-tim/scripts/music_sections.py SONG.wav IN_FRAMES`.
- These three came from one edit (C7). Treat them as defaults and confirm with the editor when the music fights them.

## Ending

- The ending depends on the edit. Beon edits often let B-roll carry past the last word (about 4 s over music) into the end card.
- The end card comes from the client profile `end_card`: `kind` (file or compound), `asset`, `length_f`, `music_tail_s`. Any field `ask` or missing: ask the editor and write the answer back into the profile front matter, so the next job doesn't ask. (Namir, for example: `Namir Reel Tail_Standard.png`, 65 frames, music about 0.6 s past it.)

## Render check (Tim, 15 Oct 2026: check the actual render before handing over)

After the A-roll stage, after the B-roll stage, and before hand-over:
1. Only while the editor isn't using Resolve: `scripts/resolve_proxy_render.py` (run_script_unsafe) STEP "start" saves the editor's render settings as a temporary preset, renders a half-size H.264 proxy of the current timeline (half the delivery size: 540x960 for 9:16 1080x1920) to the shoot's `_claude_scratch/proxy` (never a synced folder from editor.json, never Dropbox); "poll" until done; "restore" puts the editor's settings back and removes the job and the temporary preset. Set `OUT_DIR` and the proxy size in the script before running.
2. `scripts/render_check.py PROXY.mp4 OUT_DIR --cuts <record frames of the edit points> --card <job card>`: black and frozen frames, 1-2 frame slivers, pops and level jumps at cuts, long silences, overall loudness and true peak against the delivery target, and the proxy's aspect and fps against delivery. Look at the cut sheets. It needs a Python with numpy and opencv-python (a venv, or the VM if run_env is device-vm).
3. Fix, re-render, re-check. Report what was found and fixed.
4. Before hand-over, the QA loop's `final` stage (qa-loop skill) runs on this render: the qa-manager checks the whole edit and that every stage passed QA.

## Delivery checks

- Format from the client profile `delivery` and the job card Delivery line (`beon_config.delivery(card)`, the card wins). Beon default: 9:16, 1080x1920, 24p. Loudness and true peak from the same place; `ask` means ask the editor and write the answer back to the profile.
- Length per the job card Target length.
- Watch the joins at the break and the ending; check the end card is on V1 or V2 above everything and the music tail isn't cut mid-note.
- Leave the render settings as the editor set them; say so if a capture or check changed anything (e.g. the render format).
