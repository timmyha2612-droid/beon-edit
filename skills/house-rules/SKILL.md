---
name: house-rules
description: "This skill should be used at the start of any editing job for Tim at Beon Media (DaVinci Resolve concept videos, interviews, B-roll, colour grading, footage sorting), when Tim says \"start the edit\", \"put together concept X\", \"help me with the A-roll / B-roll / grade\", \"learn my edit\", when deciding which Beon editing skill applies, or whenever any other beon-edit stage skill is about to start and no job card exists for this job yet. It holds the working agreement, the mandatory opening grilling and job card, and the map of the other skills.\n"
metadata:
  version: "0.6.1"
---

# Beon edit: house rules

How to work with Tim on any edit. Read this first, then load the skill for the stage at hand.

## Skill map

| Stage | Skill | Use when |
|---|---|---|
| 0 | house-rules | Every job: working agreement, grilling and job card (hard rule), routing |
| 0 | client-styles | Every client job: read the client's profile before grilling |
| 1 | Footage Prep app (`footage-prep` MCP) | Every footage task, first: import, analyse, use its scores and selects. Not reachable: tell Tim in one line and fall back (`references/footage-prep.md`) |
| 1 | resolve-footage-sort | Sorting raws into bins, logging audio and interviews |
| 1 | shotlog | Any footage task: read the shoot's log first (it merges Footage Prep with Claude's analysis), write back after |
| 2 | aroll-cut | Story beats and the interview cut (the "meat") |
| 3–5 | broll | Picking, placing and fixing B-roll by Tim's B-roll rulebook (`broll/references/broll-rulebook.md`). Its HARD GATE runs on every pass: broll_auto.py → snippet → gyroflow_headless.py → broll_gate.py PASS |
| after each stage | qa-loop + `beon-edit:qa-manager` / `beon-edit:qa-verifier` agents | Every stage is checked by a separate quality manager before Tim sees it; mistakes fixed, judgement calls double-checked, creative calls to Tim, max 3 rounds then escalate |
| 6 | colour-grade | Grading with Tim's template and the scopes |
| 7 | subtitles | Captions: style test with Tim first, then Fluid Reveal Words subs, resync after edits |
| 7 | finish-pass | What Tim does at the end, and how to set the edit up for it |
| all, then 8 | learn-from-tim + `beon-edit:learner` agent | Always on: log every correction and piece of knowledge in the lessons inbox as it's given; at the end of every job, the learner proposes rules, Tim approves, then the plugin is updated |

Typical order: brief → client profile → grill → job card → Footage Prep → ingest/shot log → A-roll → QA → Tim reviews → B-roll select and place → pacing gate → QA → Tim watch-down → grade → QA → subtitles → QA → final QA on the render → Tim's finish → learn.

## Grill first, every job, no exceptions [Tim, 9 Nov 2026]

Tim: every concept is different, and jobs have started without him being asked. So the opening questions are a hard rule, not a suggestion, and every stage skill checks for the job card before it works.

1. Read the client's profile (client-styles). Skip what its [Tim] rules already answer; confirm [inferred] rules that matter for this concept.
2. Ask Tim the open questions before any hands-on work, through the pop-up question tool, with suggested answers (recommended first). Always cover these, because Tim decides them per concept:
   - Target length (it depends on the case; no default).
   - Story beats and which answers to use if the brief is loose.
   - Jokes or light moments: keep the speaker on camera, or allow B-roll?
   - Goofy or playful people shots: allowed under this concept's tone?
   - Which camera or multicam to cut from (default: Tim's multicam, A cam only unless told).
   - Music: will Tim add it (usual), and is there a break planned?
   - Subtitles: which look (see subtitles Step 0; never assume the font, size or colour).
   - Anything Tim has already placed that must not move.
3. Write the answers into the job card (`references/job-card.md`): the real card in `<shoot>/_shotlog/jobs/`, and the session copy the hook reads.
4. Only then touch Resolve. The `job_guard` hook blocks any Resolve call that changes the project until the session copy exists; reads are never blocked.

- Tim says "skip the questions" (or the job is a tiny fix): write a card with `Grilling: skipped (Tim said "...")`. Never skip on your own judgement.
- New session on a job that already has a card: read it, ask "anything changed since <date>?", update it, link it; its Progress lines say where the job stands.
- After every stage (built, QA result, waiting on Tim) and before stopping, add a Progress line to the real card.
- Any stage skill loaded without a job card: stop and run this section first, even if the request named the stage directly ("add B-roll to C3").

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

- When Tim leaves a job running, run the QA loop (qa-loop) on every stage until it passes or escalates after 3 rounds, keep a progress log, and schedule resume reminders (scheduled tasks) in case the session limit hits. Delete the reminders when finished.
- Go fast: drop steps that don't add quality, split independent analysis across agents, reuse the shot log instead of re-analysing. Follow the fast path and the VM and API gotchas in `references/resolve-recipes.md` (ingest once, `cut_pieces.py`, one `run_script` per stage, measure outside Resolve).

## Learning (always on) [Tim, 9 Nov 2026]

- Every job keeps a lessons inbox (job card `Lessons inbox:`). While a job is open, the `learn_listener` hook reminds you on every message: when Tim (or the editor) corrects the edit, says how something should be done, or explains why, log it right away with its kind: general (every client), client (only this client), concept (only this video, never the plugin), or unsure (ask at the end). learn-from-tim section 0.
- At the end of every job: the `beon-edit:learner` agent turns the inbox and Tim's finished version into proposals; Tim approves, changes or drops each one (at most 4 questions, batched at the end); only then is the plugin changed, versioned and pushed. learn-from-tim sections 3-5.
- Only Tim turns a lesson into a general or client rule. Other editors' lessons wait for him (a pull request or `pending-for-tim.md`).
- Rules confirmed by Tim beat rules inferred from one example. When a rule was inferred from a single case, treat it as a default and ask when it matters.
- The plugin is the only real copy of the rules. The "Tim's Edit System" artifact page shows them and collects Tim's marks, which come back through learn-from-tim.
