# beon-edit

Tim's editing system for Beon Media concept videos in DaVinci Resolve, packed as skills Claude loads on demand.

| Skill | What it covers |
|---|---|
| house-rules | Working agreement, the opening questions, Resolve etiquette, file rules, which skill to use when |
| client-styles | One style profile per client (Namir, Arriva so far): format, length, structure, A-roll, B-roll, audio, ending, grade, brand rules |
| shotlog | Per-shoot shot log: read first, analyse only what's missing, write back |
| resolve-footage-sort | Sorting raws into numbered bins, logging audio and interviews |
| aroll-cut | Story beats, dialogue cutting, removing ums/uhs/stutters while keeping the speech flowing, air at joins, multicam, punch-ins, jump cuts, verification |
| broll-qaqc | B-roll selection, placement, pacing gate, motion cards, fix ladder, sign-off |
| colour-grade | Tim's 9-node template, scope-led white balance and exposure, grading by scene, the light crash-safe grading method, reading/writing grades |
| subtitles | Style test with Tim, Fluid Reveal Words titles (word-by-word reveal), Auto/Resync Subtitles scripts, hand clean-verbatim captions for batches, checks and crash-safe Resolve recipes |
| finish-pass | What Tim does at the end, hand-over state, music and ending guidance, delivery checks |
| learn-from-tim | Read Tim's finished version, measure the differences, ask why, update the rules |

## New editor setup (subtitles for the Beon shorts)

1. Get access to this private repo from Tim, then clone it: `git clone https://github.com/timmyha2612-droid/beon-edit ~/code/beon-edit`
2. In Claude Code: `/plugin marketplace add ~/code/beon-edit`, then `/plugin install beon-edit@beon`. Update later with `git pull` and `/plugin marketplace update beon`.
3. Install the Garet font (Book and Heavy; one format only, .otf or .ttf, not both).
4. Run `bash ~/code/beon-edit/skills/subtitles/scripts/install.sh` (puts the Fluid Reveal titles and the Auto/Resync Subtitles scripts into Resolve), then restart DaVinci Resolve Studio.
5. Make sure Claude can reach Resolve (the DaVinci Resolve connector / MCP is enabled), then ask Claude to "sub the shorts" on your timelines. It follows skills/subtitles/SKILL.md: Tim's approved C2a look (Fluid Reveal Words defaults) and his caption rules.

Scripts (run in the device VM or on the Mac, never writing media into Dropbox):
- shotlog/scripts: ingest.py (one resumable pass per shoot: probe, gyro shake windows, keyframes, contact sheets)
- aroll-cut/scripts: verbatim.py (CrisperWhisper verbatim transcript with ums and uhs; needs Tim's model folder and licence), resolve_snapshot.py + recut_plan.py + resolve_relay.py (recut the A-roll on a copy and move everything else with it), cut_pieces.py (rough picks to clean sub-pieces and an AppendToTimeline list, removes isolated ums and stutters), cut_review.py (sheets of every join: edge frames, difference, waveform, jump size, air), cut_air.py, filler_scan.py
- subtitles/scripts: install.sh (titles + Resolve scripts), build_presets.py (regenerates the titles), Auto Subtitles.py / Resync Subtitles.py (Workspace > Scripts > Edit), export_words.py + show_words.py + plan_captions.py + build_lib.py + check_lib.py + sheet.sh + compare_whisper.py (hand-caption pipeline)
- finish-pass/scripts: resolve_proxy_render.py (small proxy render that restores Tim's render settings), render_check.py (checks the actual render: cuts, black/frozen frames, slivers, pops, level jumps, gaps, loudness)
- broll-qaqc/scripts: bestwin.py (steadiest unused window from the gyro cache), framing_sheet.py (9:16 Pan by eye), motion_card.py, mouth_check.py, intent_map2.py (paths inside are shoot-specific)
- colour-grade/scripts: drxlib.py, grade_read.py, drxw.py (writes grades), measnp.py and calib.py (measure in the device VM with numpy); meas.py and batch.py are legacy, don't run them inside Resolve
- learn-from-tim/scripts: jumpcut_check.py, music_sections.py

Rules were learned from Namir Mikha C6, C1 and C7 and reviewed by Tim on the "Tim's Edit System" page (15 Oct 2026).

0.2.0 (15 Oct 2026, after Arriva Oct C1/C3): A-roll filler and stutter removal; colour grading rebuilt to stay light on Resolve (one DRX apply per clip, measuring outside Resolve, proven DRX writer).

0.3.0 (15 Oct 2026, self-assessment): speed pass. One-pass shoot ingest, automatic A-roll piece refinement with filler and stutter removal (reproduced the hand-built Arriva C1 cut in 0.13 s), join self-review sheets, instant B-roll window picks and 9:16 framing sheets, and a speed playbook with every VM and Resolve gotcha found so far (house-rules/references/resolve-recipes.md). Transcription moved to Resolve's word-timed TranscribeAudio.
0.4.0 (15 Oct 2026, after Tim's answers): client style profiles (Namir, Arriva), render check on a proxy render, recut-on-a-copy tools, CrisperWhisper verbatim transcription (installed in the VM; model and commercial licence pending), glued-filler cuts located by the change in the sound, clipped-audio warning with the safety channel.

0.5.0 (29 Oct 2026, Beon SEO shorts): subtitles skill. Fluid Reveal Words / Fluid Reveal titles, style test first (Tim styles one title, every caption copies it), never several words at once (4-frame min gap), no gaps, clean verbatim, Auto Subtitles now handles camera clips (source timecode, 25p on 24p) and waits for the playhead.
0.5.1 (29 Oct 2026): subtitles timeline keeps one video track (titles were landing on V2 when the source timeline had several tracks); tested style copy (Metropolis 0.06) on Green Oct2 C3.
