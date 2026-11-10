# beon-edit changelog

Newest at the bottom.

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

0.18.2 (10 Nov 2026): subtitles, speech comes first [Tim, 4 Nov 2026].
- A caption still goes up on its first spoken word. plan_captions.py snaps a start onto a picture cut only when the cut is up to 8 frames before the word or 6 frames after it (was ±6 either way); further off, the speech timing stays (Simone C03g had captions up to 35 frames off their words).
- QA: S-03 allows that exception; new S-11 checks every caption start against its first word on the timeline's own audio.

0.18.3-0.18.9 (10-11 Nov 2026, Simone Nov C03; from the commit messages, no changelog lines were written at the time):
- 0.18.3: subtitles speech-sync check for Text+ captions already on a timeline (QA S-02/S-03/S-11 tooling).
- 0.18.4: A-roll centring on the whole figure per shot; subtitles check every caption start against the speech.
- 0.18.5: check_caption_starts confirms late flags by ear and skips bleeped captions.
- 0.18.9: A-roll and subtitles: shared Pan on jump cuts, stray-clip check, zoom layer track, sentence and no-pause caption rules, stricter start check.

0.19.0 (11 Nov 2026, tidy-up on top of 0.18.9, no rule changed):
- The B-roll skill no longer repeats the rulebook: rules live only in broll/references/broll-rulebook.md (a few details that only lived in the skill moved there), the skill keeps the order, tools and recipes.
- Speed playbook fast path now matches the hard gate (Footage Prep selects, broll_auto.py, gate); bestwin.py is the no-Footage-Prep fallback and no longer suggests 48%.
- Removed legacy scripts nobody should run: colour-grade meas.py and batch.py, broll select_window.py.
- Job card: Progress lines (where the job stands, for the next session) and Kind: calibration (so the QA calibration proxy render isn't blocked).
- The per-message learning reminder is about half the length.
- Changelog moved out of the README into this file; tests/run_tests.py added.
