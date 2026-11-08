---
name: house-rules
description: "This skill should be used at the start of any editing job for Tim at Beon Media (DaVinci Resolve concept videos, interviews, B-roll, colour grading, footage sorting), when Tim says \"start the edit\", \"put together concept X\", \"help me with the A-roll / B-roll / grade\", \"learn my edit\", or when deciding which Beon editing skill applies. It holds the working agreement, the opening grilling checklist and the map of the other skills.\n"
metadata:
  version: "0.3.0"
---

# Beon edit: house rules

How to work with Tim on any edit. Read this first, then load the skill for the stage at hand.

## Skill map

| Stage | Skill | Use when |
|---|---|---|
| 0 | house-rules | Every job: working agreement, grilling, routing |
| 0 | client-styles | Every client job: read the client's profile before grilling |
| 1 | resolve-footage-sort | Sorting raws into bins, logging audio and interviews |
| 1 | Footage Prep app (`footage-prep` MCP) | Every shoot, before any B-roll pick: import, analyse, pick from its selects (broll-qaqc Stage 0) |
| 1 | shotlog | Any footage task: read the shoot's log first, write back after |
| 2 | aroll-cut | Story beats and the interview cut (the "meat") |
| 3–5 | broll-qaqc | Picking, placing, measuring and fixing B-roll |
| 6 | colour-grade | Grading with Tim's template and the scopes |
| 7 | subtitles | Captions: style test with Tim first, then Fluid Reveal Words subs, resync after edits |
| 7 | finish-pass | What Tim does at the end, and how to set the edit up for it |
| 8 | learn-from-tim | After Tim finishes or asks to "learn": read his version, compare, ask why |

Typical order: brief → client profile → grill → ingest/shot log → A-roll → Tim reviews → B-roll select and place → pacing gate → QC and fixes → Tim watch-down → grade → Tim's finish → learn.

## Grill before touching the edit

Read the client's profile first (client-styles) and skip what its [Tim] rules already answer. Ask clarifying questions before any hands-on work, through the pop-up question tool, with suggested answers (recommended first). Keep it to what the brief doesn't answer. Always cover these, because Tim decides them per concept:

- Target length (it depends on the case; no default).
- Story beats and which answers to use if the brief is loose.
- Jokes or light moments: keep the speaker on camera, or allow B-roll?
- Goofy or playful people shots: allowed under this concept's tone?
- Which camera or multicam to cut from (default: Tim's multicam, A cam only unless told).
- Music: will Tim add it (usual), and is there a break planned?
- Anything Tim has already placed that must not move.

## Resolve etiquette

- Work in Resolve freely during a job, but the moment Tim says he needs it (a quick revision mid-run, "can I chime in"), stop every Resolve call, reads included, until he says it's free.
- Finished timelines (e.g. a delivered concept) are for learning from: read them, never edit them unless Tim asks.
- A "learn" or "just read" request is strictly read-only: no adjustments of any kind, not even a playhead move if it can be avoided. Prefer exports (DRT, LUT) to the viewer.
- Before handing over, check track enable states on the current timeline (A1 has been found disabled on an empty timeline Tim created).
- Never delete Tim's timelines. For risky changes, duplicate the timeline first as a backup.

## Files

- Never write media (frames, renders, thumbnails, audio) into Dropbox. Only small text goes in a shoot's `_shotlog/` folder. Scratch images go in the device VM home, or a non-Dropbox connected folder when they must be staged for viewing.
- Exception that is Tim's, not Claude's: his Gyroflow script renders stabilised clips next to the source clip.
- Deletion is off on connected folders; leave scratch for Tim to clear and say where it is.

## Long or unattended runs

- When Tim leaves a job running, loop check-and-fix until the edit is smooth, keep a progress log, and schedule resume reminders (scheduled tasks) in case the session limit hits. Delete the reminders when finished.
- Go fast: drop steps that don't add quality, split independent analysis across agents, reuse the shot log instead of re-analysing. Follow the fast path and the VM and API gotchas in `references/resolve-recipes.md` (ingest once, `cut_pieces.py`, one `run_script` per stage, measure outside Resolve).

## Learning

- Keep learning Tim's style and apply it to every future edit. After each job, run learn-from-tim.
- Rules confirmed by Tim beat rules inferred from one example. When a rule was inferred from a single case, treat it as a default and ask when it matters.
- The full rulebook with Tim's marks lives on the "Tim's Edit System" artifact page and in the project docs.
