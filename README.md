# beon-edit

Tim's editing system for Beon Media concept videos in DaVinci Resolve, packed as skills Claude loads on demand.

| Skill | What it covers |
|---|---|
| house-rules | Working agreement, the mandatory opening questions and job card, Footage Prep first (with fallback), Resolve etiquette, file rules, which skill to use when |
| client-styles | One style profile per client (Namir, Arriva, Green, Beon's own shorts so far): format, length, structure, A-roll, B-roll, audio, ending, grade, subtitle look, brand rules |
| shotlog | Per-shoot shot log: read first, analyse only what's missing, write back; merges Footage Prep's scores with Claude's analysis, holds the job cards |
| resolve-footage-sort | Sorting raws into numbered bins, logging audio and interviews |
| aroll-cut | Story beats, dialogue cutting, removing ums/uhs/stutters while keeping the speech flowing, air at joins, multicam, punch-ins, jump cuts, verification |
| broll | Tim's B-roll rulebook (speed 100% unless a valid reason, Gyroflow, movement flow, framing and zoom limit, Dynamic Zoom on static shots, speaker max 4 s), selection, placement, hard gate, motion cards, fix ladder, sign-off |
| qa-loop | Tim's quality loop after every stage: the qa-manager agent checks with fresh eyes against per-stage checklists, the qa-verifier double-checks judgement calls, the editor fixes, creative calls go to Tim, max 3 rounds then escalate; calibration on Tim's finals |
| colour-grade | Tim's 9-node template, scope-led white balance and exposure, grading by scene, the light crash-safe grading method, reading/writing grades |
| subtitles | Each client's caption look (profile, other timelines in the project, or Tim) confirmed with Tim first, Fluid Reveal Words titles (word-by-word reveal), Auto/Resync Subtitles scripts, hand clean-verbatim captions for batches, checks and crash-safe Resolve recipes |
| finish-pass | What Tim does at the end, hand-over state, music and ending guidance, delivery checks |
| learn-from-tim | Always-on learning: every correction or piece of knowledge goes into the job's lessons inbox as general / client / concept; at the end of the job the learner agent proposes rules (and compares Tim's finished version), Tim approves, changes or drops each, then the plugin is updated and pushed; other editors' lessons wait for Tim |

## New editor setup (subtitles for the Beon shorts)

1. Get access to this private repo from Tim, then clone it: `git clone https://github.com/timmyha2612-droid/beon-edit ~/code/beon-edit`
2. In Claude Code: `/plugin marketplace add ~/code/beon-edit`, then `/plugin install beon-edit@beon`. Update later with `git pull` and `/plugin marketplace update beon`.
3. Install the Garet font (Book and Heavy; one format only, .otf or .ttf, not both).
4. Run `bash ~/code/beon-edit/skills/subtitles/scripts/install.sh` (puts the Fluid Reveal titles and the Auto/Resync Subtitles scripts into Resolve), then restart DaVinci Resolve Studio.
5. Make sure Claude can reach Resolve (the DaVinci Resolve connector / MCP is enabled), then ask Claude to "sub the shorts" on your timelines. It follows skills/subtitles/SKILL.md: it finds the client's caption look (client profile, other timelines in the project, or Tim), confirms it with Tim, then applies his caption rules. The Fluid Reveal Words defaults are the Beon shorts look (C2a).

Agents (agents/, called as `beon-edit:<name>`):
- qa-manager: read-only quality manager; checks a stage against skills/qa-loop/references/checklists/<stage>.md and returns findings JSON (hard / judgement / creative).
- qa-verifier: read-only second look at the judgement findings; only what it agrees with gets fixed.
- learner: end of every job; sorts the lessons inbox and Tim's changes into general / client / concept, checks them against the existing rules, spots client rules that repeat across clients, and drafts proposals plus at most 4 questions. Proposes only.

Hooks (PreToolUse, on the DaVinci Resolve MCP tools):
- hooks/job_guard.py: blocks Resolve edits until this session has a job card from the opening grilling (house-rules/references/job-card.md). Reads are never blocked.
- hooks/broll_guard.py: blocks scripts that place B-roll on V2+ without a reason per shot, a retime on slowed shots and a Gyroflow flag.
- hooks/learn_listener.py (UserPromptSubmit): while a job card is open, reminds Claude on every message to log corrections and knowledge in the lessons inbox.

Scripts (run in the device VM or on the Mac, never writing media into Dropbox):
- shotlog/scripts: ingest.py (one resumable pass per shoot: probe, gyro shake windows, keyframes, contact sheets)
- aroll-cut/scripts: verbatim.py (CrisperWhisper verbatim transcript with ums and uhs; needs Tim's model folder and licence), resolve_snapshot.py + recut_plan.py + resolve_relay.py (recut the A-roll on a copy and move everything else with it), cut_pieces.py (rough picks to clean sub-pieces and an AppendToTimeline list, removes isolated ums and stutters), cut_review.py (sheets of every join: edge frames, difference, waveform, jump size, air), cut_air.py, filler_scan.py
- subtitles/scripts: install.sh (titles + Resolve scripts), build_presets.py (regenerates the titles), Auto Subtitles.py / Resync Subtitles.py (Workspace > Scripts > Edit), export_words.py + show_words.py + plan_captions.py + build_lib.py + check_lib.py + sheet.sh + compare_whisper.py (hand-caption pipeline), read_styles.py (read-only scan of the caption looks on the project's other timelines)
- finish-pass/scripts: resolve_proxy_render.py (small proxy render that restores Tim's render settings), render_check.py (checks the actual render: cuts, black/frozen frames, slivers, pops, level jumps, gaps, loudness)
- broll/scripts: broll_auto.py (smoothest window, speed with its reason, Gyroflow preset, zoom check and Dynamic Zoom list per slot from Footage Prep selects; writes the placement snippet), gyroflow_headless.py (runs Gyroflow Stabilize Flagged from Bash), broll_gate.py (PASS/FAIL: speed reasons and floors, retime, stabilised, zoom limit, Dynamic Zoom, speaker max 4 s, slivers, gaps), bestwin.py (steadiest unused window from the gyro cache), framing_sheet.py (9:16 Pan by eye), motion_card.py, mouth_check.py, intent_map2.py (paths inside are shoot-specific)
- colour-grade/scripts: drxlib.py, grade_read.py, drxw.py (writes grades), measnp.py and calib.py (measure in the device VM with numpy)
- learn-from-tim/scripts: jumpcut_check.py, music_sections.py, lessons.py (lessons inbox: add, list, propose, Tim's decisions, applied, repeats across client profiles)
- tests/run_tests.py: quick self-test of the hooks, the QA and lessons bookkeeping, and every file the skills point to (`python3 tests/run_tests.py`)
- qa-loop/scripts: qa_round.py (files each QA round, compares rounds, 3-round limit, prints what to fix / verify / ask Tim, keeps qa-log.md)

History and what changed in each version: [CHANGELOG.md](CHANGELOG.md).
