---
name: finish-pass
description: "This skill should be used when an edit is nearing hand-off to Tim for his final pass, or when Tim asks about music placement, the break, the ending or delivery for a Beon Media concept: \"add the end card\", \"where should the music come in\", \"set it up for music\", \"is it ready to deliver\". Covers what Tim does himself, how to leave the edit ready for it, and the delivery checks.\n"
metadata:
  version: "0.1.0"
---

# Finish pass

> **Job card first.** Before any work in this skill, make sure this job has a job card (house-rules, "Grill first"). No card: stop and run the grilling with Tim. The `job_guard` hook blocks Resolve edits without one.

Tim does the final cut and music pass himself. Claude's job is to hand over an edit that's ready for it, and to help with music, the break and the ending when he asks.

## What Tim does himself (don't do these unless asked)

- Final cut adjustments and the music pass.
- Dialogue clean-up: he exports the dialogue, runs speech enhancement, brings it back on A2 and turns off A1. Don't touch A2 or re-enable A1 once he's done this.
- Grading sign-off.

## Hand-over state

- V1/A1 interview, V2 B-roll, A3 left free for music (or Tim's music untouched if he's already placed it).
- A1 enabled before hand-over (unless Tim has already moved dialogue to A2).
- A breathing break placed where the edit needs one (between two separate points or answers, or after a long fast stretch), marked with a Blue marker so Tim can size it to the music.
- Flagged shots coloured and marked (see broll-qaqc), plus a short note of anything borderline.
- No black frames or gaps; running time reported.

## Music (when Tim asks for help)

- Start the song so its lift (where the full band comes in) lands on a story beat. C7: the band enters at frame 290, beat 2 starts at 295.
- Put the break over a phrase change in the music, and size the break to fit the phrase (C7 break grew from 2.5 s to 4.4 s with 3 hero shots).
- Land the end card on a phrase start.
- Find lifts and phrase dips with `learn-from-tim/scripts/music_sections.py SONG.wav IN_FRAMES`.
- These three came from one edit (C7). Treat them as defaults and confirm with Tim when the music fights them.

## Ending

- The ending depends on the edit. Tim often lets B-roll carry past the last word (about 4 s over music) into the end card.
- Every Namir reel ends on the standard tail card `[03. Assets]/Logos/Namir Reel Tail_Standard.png`, 65 frames, with the music running about 0.6 s past it. Other clients: ask.

## Render check (Tim, 15 Oct 2026: check the actual render before handing over)

After the A-roll stage, after the B-roll stage, and before hand-over:
1. Only while Tim isn't using Resolve: `scripts/resolve_proxy_render.py` (run_script_unsafe) STEP "start" saves Tim's render settings as a temporary preset, renders a 540x960 H.264 proxy of the current timeline to the shoot's `_claude_scratch/proxy` (never Dropbox); "poll" until done; "restore" puts Tim's settings back and removes the job and the temporary preset.
2. `scripts/render_check.py PROXY.mp4 OUT_DIR --cuts <record frames of the edit points>` in the device VM: black and frozen frames, 1-2 frame slivers, pops and level jumps at cuts, long silences, overall loudness and true peak. Look at the cut sheets.
3. Fix, re-render, re-check. Report what was found and fixed.

## Delivery checks

- 1080x1920, 24p, vertical. Length per the brief (ask; it depends on the concept).
- Watch the joins at the break and the ending; check the end card is on V1 or V2 above everything and the music tail isn't cut mid-note.
- Leave the render settings as Tim set them; tell him if a capture or check changed anything (e.g. the render format).
