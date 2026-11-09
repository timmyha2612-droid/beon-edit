# beon-edit

Tim's editing system for Beon Media concept videos in DaVinci Resolve, packed as skills Claude loads on demand.

| Skill | What it covers |
|---|---|
| house-rules | Working agreement, the mandatory opening questions and job card, Footage Prep first (with fallback), Resolve etiquette, file rules, which skill to use when |
| client-styles | One style profile per client (Namir, Arriva, Green, Beon's own shorts so far): format, length, structure, A-roll, B-roll, audio, ending, grade, subtitle look, brand rules |
| shotlog | Per-shoot shot log: read first, analyse only what's missing, write back; merges Footage Prep's scores with Claude's analysis, holds the job cards |
| resolve-footage-sort | Sorting raws into numbered bins, logging audio and interviews |
| aroll-cut | Story beats, dialogue cutting, removing ums/uhs/stutters while keeping the speech flowing, air at joins, multicam, punch-ins, jump cuts, verification |
| broll | (was broll-qaqc) Tim's B-roll rulebook (speed 100% unless a valid reason, Gyroflow, movement flow, framing and zoom limit, Dynamic Zoom on static shots, speaker max 4 s), selection, placement, hard gate, motion cards, fix ladder, sign-off |
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
- colour-grade/scripts: drxlib.py, grade_read.py, drxw.py (writes grades), measnp.py and calib.py (measure in the device VM with numpy); meas.py and batch.py are legacy, don't run them inside Resolve
- learn-from-tim/scripts: jumpcut_check.py, music_sections.py, lessons.py (lessons inbox: add, list, propose, Tim's decisions, applied, repeats across client profiles)
- qa-loop/scripts: qa_round.py (files each QA round, compares rounds, 3-round limit, prints what to fix / verify / ask Tim, keeps qa-log.md)

Rules were learned from Namir Mikha C6, C1 and C7 and reviewed by Tim on the "Tim's Edit System" page (15 Oct 2026).

0.2.0 (15 Oct 2026, after Arriva Oct C1/C3): A-roll filler and stutter removal; colour grading rebuilt to stay light on Resolve (one DRX apply per clip, measuring outside Resolve, proven DRX writer).

0.3.0 (15 Oct 2026, self-assessment): speed pass. One-pass shoot ingest, automatic A-roll piece refinement with filler and stutter removal (reproduced the hand-built Arriva C1 cut in 0.13 s), join self-review sheets, instant B-roll window picks and 9:16 framing sheets, and a speed playbook with every VM and Resolve gotcha found so far (house-rules/references/resolve-recipes.md). Transcription moved to Resolve's word-timed TranscribeAudio.
0.4.0 (15 Oct 2026, after Tim's answers): client style profiles (Namir, Arriva), render check on a proxy render, recut-on-a-copy tools, CrisperWhisper verbatim transcription (installed in the VM; model and commercial licence pending), glued-filler cuts located by the change in the sound, clipped-audio warning with the safety channel.

0.5.0 (29 Oct 2026, Beon SEO shorts): subtitles skill. Fluid Reveal Words / Fluid Reveal titles, style test first (Tim styles one title, every caption copies it), never several words at once (4-frame min gap), no gaps, clean verbatim, Auto Subtitles now handles camera clips (source timecode, 25p on 24p) and waits for the playhead.
0.5.1 (29 Oct 2026): subtitles timeline keeps one video track (titles were landing on V2 when the source timeline had several tracks); tested style copy (Metropolis 0.06) on Green Oct2 C3.
0.5.2-0.5.3 (29 Oct 2026): subtitle check sheets follow moved subtitles; crash-safe insert pacing and compound-clip position notes.
0.6.0 (29 Oct 2026, Green C3): B-roll stabilisation measure-and-fix loop with a calibrated shake_check.py; Green rules (no pre-word breaths, tighter joins, levelling, stabilised over wide, Pan readback); Gyroflow notes.
0.6.1-0.6.3 (2 Nov 2026, Simone Nov C03): A-roll speaker centred in 9:16 with Pan; slow Dynamic Zoom adjustment clips on long holds; one Zoom/Pan/Tilt per framing for the whole setup.
0.7.0 (3 Nov 2026, C1 HERO v6): Fluid Reveal Words Hook (per-word highlight), Kinetic hook captions (Libre Baskerville, later Garet), Beon Name Title; two-tier Kinetic captions tried and reverted (Tim: looks worse); new-editor setup and marketplace file.
0.6.4 (3 Nov 2026, Simone Nov C03, committed after 0.7.0): caption changes land on the picture cut (plan_captions snaps within 6 frames).
0.8-0.12: not used (the version jumped to 0.13.0).
0.13.0 (9 Nov 2026, Mill site update): every shoot goes through Footage Prep first; B-roll only from its clean selects.
0.14.0-0.14.1 (9 Nov 2026, Mill): best window inside selects, literal relevance, establishing shots, Gyroflow on all handheld with horizon lock, straighten with minimum zoom, level_check --center; A-roll audio QC before handover.
0.15.0 (9 Nov 2026, Hired Home Nov S2 C2): B-roll hard gate. broll_auto.py picks the smoothest stretch of each Footage Prep select at the slot speed and the Gyroflow preset, with no frame reading. gyroflow_headless.py stabilises from Bash and broll_gate.py must PASS. A plugin hook (hooks/broll_guard.py) blocks Resolve scripts that place B-roll without speed, retime and a Gyroflow flag.
0.15.1-0.15.2 (9 Nov 2026): broll_auto only picks windows with the full real-time length + 1 s (Gyroflow renders with handles); --why prints the best window at every speed.

0.16.0 (10 Nov 2026, step 1 of the agent upgrade, Tim's answers 9 Nov): rules and gates.
- Opening grilling is mandatory: job card per concept (house-rules/references/job-card.md), checked by every stage skill and enforced by hooks/job_guard.py on Resolve edits.
- Footage Prep first on every footage task, with a one-line notice and the ingest.py fallback when it isn't reachable (house-rules/references/footage-prep.md); the shot log keeps Footage Prep's data and Claude's analysis side by side; its winners get a second look.
- Subtitles: the look comes from the client profile, then the project's other timelines (read_styles.py), then Tim, and is always confirmed with him; client profiles get a Subtitles section; new profile beon.md; Garet is the Beon shorts look, not the house default.
- Tim's B-roll rulebook (broll/references/broll-rulebook.md): speed 100% unless a valid reason (shake, match the neighbours' camera speed, stretch, hero) within floors (people talking 80%, moving 60%, others 48%); same room twice only from another angle; no jerky movement; never zoom into pixelation (UHD 1.25 / 1.4); slight Dynamic Zoom on every static shot; speaker on screen max 4 s; every shot records why.
- broll_auto.py, broll_gate.py and broll_guard.py rewritten to match (reasons, floors, zoom limit, Dynamic Zoom list, 4 s speaker and sliver checks).
- Housekeeping: changelog filled in, skill versions bumped, learn-from-tim no longer points at the legacy meas.py/batch.py.
- Not done yet: the QA agent (step 2) and the learning agent (step 3).

0.17.0 (10 Nov 2026, step 2 of the agent upgrade): QA manager.
- broll-qaqc split: the `broll` skill places and fixes; checking moves to a separate qa-manager agent (agents/qa-manager.md) that never edits.
- qa-loop skill: after every stage (aroll, broll, grade, subtitles) and a final pass on the render, qa-manager checks against per-stage checklists; judgement findings get an independent qa-verifier look (only agreed ones are fixed); hard findings always fixed; creative ones go to Tim; after 3 rounds anything still open is escalated (unattended: logged, moved on, reported).
- scripts/qa_round.py keeps the rounds honest: validates findings, compares rounds, carries confirmed verdicts, PASS / PARTIAL / FAIL / ESCALATE, qa-log.md.
- Calibration plan (qa-loop/references/calibration.md): run QA read-only on 2-3 of Tim's finals; until then the provisional thresholds only report.
- Until calibrated, QA runs in shadow mode: every finding goes to Tim, nothing is forced.
- Reviewed by three independent reviewers plus adversarial verification; 22 confirmed issues fixed before the PR.
- Not done yet: calibration run (needs Tim's Mac with Resolve) and the learning agent (step 3).

0.18.0 (10 Nov 2026, step 3 of the agent upgrade): learning agent.
- Always listening: during a job, the learn_listener hook reminds Claude on every message to log corrections and knowledge in the job's lessons inbox (lessons.py), sorted as general / client / concept / unsure.
- End of every job: the learner agent (agents/learner.md) compares Tim's finished version when there is one, checks each lesson against the existing rules, suggests client rules that repeat across clients as general rules, and drafts proposals plus at most 4 questions. It never edits anything.
- Tim approves, changes or drops each proposal; only then are the plugin files edited, versioned, committed and pushed (learn-from-tim/references/apply-rules.md). Concept lessons stay in the job card and shot log. Other editors' lessons wait for Tim (a pull request or pending-for-tim.md).
- Job card gains Editor, Client and Lessons inbox lines.
- Reviewed by three independent reviewers plus adversarial verification; 14 confirmed issues fixed before the PR (approval holes, the learner's proposals stored in the inbox so Tim approves exactly what changes, promotions through approval, Tim's page marks, safe push to main).

0.18.1 (10 Nov 2026): broll_auto trusts Footage Prep's gyro on still shots.
- Slots take `stability` (Footage Prep `metrics.stability`). A `locked`/`steady` shot at >= 0.95 is never slowed for `shake` and never rejected as uneven or reversing: the camera didn't move, so the optical-flow motion is the subject (Hired Home C0168, Nicole turning on a locked-off shot, was slowed to 48%). `hero` and `match` still apply. A locked/steady slot without `stability` that gets slowed for shake prints a warning.
- broll scripts need numpy, opencv-python-headless and scipy in the Python that runs them (`python3 -m pip install numpy opencv-python-headless scipy`).
