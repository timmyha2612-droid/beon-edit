---
name: subtitles
description: "This skill should be used when the editor asks for subtitles or captions on a Beon Media video or short in DaVinci Resolve, or to fix, resync or restyle them after an edit: \"do the subtitles\", \"sub the shorts\", \"the sub is out of sync\", \"words pop up at once\", \"fix the sub after my trim\", \"install the title preset\". Covers finding each client's caption look (job card, profile, other timelines, the editor) and confirming it, the Fluid Reveal Words title, Auto/Resync Subtitles, hand clean-verbatim captions for batches, checks, and Resolve gotchas that crash or misplace titles."
metadata:
  version: "0.3.0"
---

# Subtitles (Fluid Reveal Words)

> **Job card first.** Before any work in this skill, make sure this job has a job card (house-rules, "Grill first"). No card: stop and run the grilling with the editor. The `job_guard` hook blocks Resolve edits without one.

Word-by-word subtitles that rise in as each word is spoken. Built on 28 Oct 2026 for the Beon SEO shorts (C2a approved by Bonnie, then 17 more shorts).

## What's here

| Path | What it is |
|---|---|
| `assets/Fluid Reveal Words.setting` | The word-by-word title (12 word layers, hidden `Main.WordTime1..12` for per-word timing, AE-style In/Out curves). Its defaults are the Beon SEO shorts look (Garet Book, C2a): other clients get their own look from Step 0. |
| `assets/Fluid Reveal.setting` | Letter-by-letter version of the same reveal. |
| `assets/Fluid Reveal Words Hook.setting` | Hook version of Fluid Reveal Words: same reveal and timing, plus a per-word highlight (accent colour, extra weight, pop). For video hooks only; normal subtitles stay on Fluid Reveal Words. |
| `assets/Fluid Reveal Words Kinetic.setting` | Kinetic (editorial) hook title: every word on its own layer in Libre Baskerville, key words in true italic, clean fade-rise-unblur reveal, no shadow [Tim, 3 Nov 2026]. Beon's preferred hook look. |
| `scripts/kinetic_layout.py`, `scripts/kinetic_apply.py` | Typeset Kinetic captions as stacked blocks in each shot's negative space (HarfBuzz, ink-aware italics) and push the layout into the titles. |
| `assets/Beon Name Title.setting` | Two-line name super: big Garet Book name over a small letter-spaced Garet Book role line (white, 85% opacity, no colour accent, no shadow), same clean fade-rise reveal; role follows the name by 6 frames. Controls: Name, Role, Position, Justify, sizes, Line Gap, In/Out. |
| `scripts/install.sh` | Copies all 5 titles above and the two Resolve scripts into Resolve (macOS). Run once per machine, then restart Resolve. |
| `scripts/subs_intake.py [--card CARD]` | Prints the job's intake values as JSON: `work` (scratch folder), `fps`, `width`/`height` (job card Delivery line, client profile `delivery`), `language` (`shoot.language`, client profile) and `whisper_model` (editor.json `tools.whisper.model`). The command-line scripts take `--card` and read it themselves; inject `WORK` and `FPS` from it into the scripts exec'd in Resolve. |
| `scripts/build_presets.py OUT_DIR` | Regenerates all 5 `.setting` files (fonts, default curves, write-on maths). Edit this, never the `.setting` by hand. |
| `scripts/Auto Subtitles.py` | Workspace > Scripts > Edit. One click: transcribe A1, caption, build, place on a new top track. |
| `scripts/Resync Subtitles.py` | Workspace > Scripts > Edit. After trims/retyping/re-cuts: re-times every title's words to the speech under it. Only sets values, never moves clips. |
| `scripts/export_words.py`, `show_words.py`, `plan_captions.py`, `build_lib.py`, `check_lib.py`, `sheet.sh`, `compare_whisper.py` | The hand-caption pipeline Claude drives for batches (clean verbatim, many shorts). |
| `scripts/export_state.py`, `timeline_audio.py`, `sync_captions.py`, `retime_captions_drt.py`, `swap_timeline.py`, `check_caption_starts.py` | Speech-sync check for plain Text+ captions on a finished timeline: rebuild its audio, find each caption's first word, retime, swap the timeline (see "Speech-sync check"). |
| `scripts/read_styles.py` | Read-only scan of the title looks on the project's other timelines (`scan()`), and `save_style()` to copy a confirmed one into `WORK/style.json` (a cache; the job card Subtitles line is the record). |
| `references/captions-example.py` | Format of hand-written captions, with real examples. |

## Step 0: find the look, the editor confirms it (always first) [Tim, 9 Nov 2026]

Font, size and colour change per client, so never assume them, not even the Garet defaults below. Those defaults are the Beon SEO shorts look (client profile `beon.md`), not a house style. The **job card Subtitles line** is the record of the look for this job; `WORK/style.json` is only a cache the scripts apply.

1. **Job card:** if the Subtitles line already holds a look confirmed by the editor, use it and skip to step 6.
2. **Client profile:** read `subtitles` in the front matter (look, title, font, reference timeline) and the Subtitles section of `client-styles/references/<client>.md`.
3. **Other timelines in the same project:** if the profile has no look (or says `ask`), scan what was already used, read-only: exec `scripts/read_styles.py` in `run_script_unsafe` and call `scan()` (or `scan(names=[...])`). It lists each distinct title look (font, size, colour, position), how often and where. Nothing is switched or edited.
4. **Ask the editor:** nothing found, or the finds disagree: ask with the pop-up question tool (suggest the most-used look first), or ask the editor to style one title: install the titles (`scripts/install.sh`), drop one **Fluid Reveal Words** on the timeline, type a sample line and set font, size, colour, position, tracking/line spacing, rise, blur, in/out curves and lengths. Leave it **selected**, and `build_lib.step_read_style(<timeline>)` reads it into `WORK/style.json`.
5. **Always confirm**, even when steps 2-3 found the look: read it back in plain words (e.g. "Garet Book 0.07, white, centred at 0.5/0.24, Tilt -450 on the subtitle track") and wait for the editor's yes. Write the confirmed look on the job card Subtitles line ("<look>, confirmed by the editor").
6. Found on another timeline and confirmed: `read_styles.save_style(<timeline>, <title item name>, WORK)` writes `WORK/style.json`. Every caption then copies it (`build_lib.step_config` and Auto Subtitles both apply it). Per-caption values stay automatic: text, word times, in-duration, out-duration, and the last caption has no outro. If `style.json` is missing or disagrees with the card, the card wins: rebuild the cache from it.
7. Curve *shapes* (the custom In/Out lookups) can't be copied by script. If the editor changed those, update `WORDS_IN_LUT`/`WORDS_OUT_LUT` in `build_presets.py`, regenerate, reinstall (restart Resolve), and send it as a general lesson (step 8).
8. New or changed look for this client: propose adding it to the client profile (front matter `subtitles` and the Subtitles section) through learn-from-tim, tagged with the editor's name, the concept and date. The editor approves it; the plugin owner commits it to `main`, other editors open a pull request that changes nothing until Tim merges it. A look for this concept only goes in the job card notes. Only change `build_presets.py` defaults when it should become the default for the Beon shorts (a general lesson, same route).

## Beon's caption rules (non-negotiable)

- **No gaps:** each caption ends exactly where the next starts. The last one runs to the end of the speech, and the outro (`OutDur 0`) only applies when the logo or end card isn't covering it.
- **Caption changes land on the picture cut** [Tim, Simone Nov C03, 3 Nov 2026]: when a caption boundary falls near a cut in the edit (angle change, shot size change, jump cut, B-roll in or out), move the boundary onto the cut so the text and the picture change on the same frame. A caption switching a few frames before or after a cut looks messy. `plan_captions.py` snaps a start onto a cut up to `SNAP_BEFORE` (8) frames before or `SNAP_AFTER` (6) frames after its first word; check by reading back every subtitle item's start against the V1 cut list (offsets of 1-6 frames are the miss). Speech comes first [Tim, 4 Nov 2026]: a caption must still go up on its first spoken word. Only snap when the cut falls up to 8 frames before the word or 6 frames after it; otherwise keep the speech timing. Verify against the timeline's own audio (rebuild it from the A1 source ranges, transcribe it, compare each caption's start with its first word); Simone C03g had captions up to 35 frames off their words.
- **New sentence = new caption**, even a one-word one: Tim split "Wild. We are salespeople." back into "Wild." and "We are salespeople." (Simone C03c, 10 Nov 2026). Never merge across a sentence end to avoid a short caption; a short one-sentence caption (24 frames for "Wild.") is fine. Natural breaks: at most 2 lines of about 24–28 characters, break at pauses and commas, never end a line on a/the/to/of. Proper punctuation and capitals, with numbers as written ("$10 million", "3 months").
- **Words reveal at speech rate:** LEAD 2 frames before the word is spoken.
- **Never several words at once:** at least 4 frames between word reveals (`MIN_GAP`). Too short a caption spreads evenly, and the last word may land up to 2 frames before the exit. [Tim]: "we dont ever want that happen as it looks bad and clumsy".
- **Clean verbatim** (unless the job card Cut style line says verbatim): drop ums, stutters and false starts. Drop the other speakers' one-word reactions (the job card Speakers line names the primary speaker and the others) ("Yeah.", "Wow.", "Right."); the previous caption holds over them.
- **Never crash Resolve** (see gotchas). **Easy to fix after edits:** Resync Subtitles.
- Timing defaults (all clients): IN_DUR 18, OUT_DUR 4, OutBlur 6, OutLift 0.015, SyncOffset -2. Font, size, colour and position come from Step 0. Frame rate comes from the timeline (job card Delivery line).

## Route A: quick (one timeline, verbatim is fine)

The editor selects a styled title (optional) and runs **Auto Subtitles**. It transcribes A1 with Resolve's TranscribeAudio, maps words through the cuts (source timecode and camera fps → timeline fps handled, e.g. 25p→24p), splits the captions, builds them on a "<timeline> Subtitles" duplicate and places that on a new top track. The editor decomposes it if wanted. Check the results, then fix wording by retyping the title text and running Resync.

To drive it yourself: `exec` the script in `run_script_unsafe` with `{"resolve": resolve, "__name__": "lib"}`. First call `run(dry_run=True)` to see the plan, with nothing built. Building many captions can exceed the 60 s call limit, so for long timelines use Route B.

## Route B: hand clean-verbatim captions (batches, client deliverables)

Work in a folder (`WORK`): `python3 scripts/subs_intake.py --card <job card>` gives the job's scratch folder (`<scratch_root>/<client>-<shoot>/<concept>/subs`) and its `fps`. Never a synced folder (editor.json `synced_folders`; Dropbox is always refused). All Resolve calls go through `run_script_unsafe`, `exec`-ing the script with `resolve`, `project`, `WORK` and `FPS` injected, and stay under 60 s each.

1. **Words:** run `export_words.py`'s `export("<path to Auto Subtitles.py>")` with `NAMES=[timeline prefixes]`. It writes `WORK/words.json` (frames relative to timeline start, plus A1 cuts).
2. **Read:** `python3 show_words.py WORK C5b` prints `index:word@frame`, with `‖` at cuts and `|n` at pauses.
3. **Write captions** in `WORK/captions.py` (format in `references/captions-example.py`): `(first word index, "Line one\nline two")`. Keep the indices increasing. Hand-write the clean text and fix the transcript's mishearings.
4. **Plan:** `python3 plan_captions.py WORK` (or `--card <job card>`) writes `plans.json` (start/end/times/in/out per caption) and prints problems: too wide, too many words, more than 118 frames, words that don't match. Fix and rerun until clean.
5. **Build**, per timeline, each step its own call (`build_lib.py`):
   - `step_dup(name)`: duplicate the timeline as "<name> Subtitles", then empty it.
   - `step_insert(name, a, b)`: insert in chunks of about 8. It waits for the playhead and asserts each landing frame.
   - `step_trim(name)`: must return `match: true`.
   - `step_config(name, a, b)`: text, timing, style and names ("Sub 01"…).
   - `step_place(name)`: new top track named Subtitles, nested clip at 0.
   - If anything lands wrong: `step_reset`, then insert again.
6. **Check:** `check_lib.stills(name, a, b, tag)` exports one still per caption just before it exits. Run `WORK=… [WIDTH=<delivery width>] [HEIGHT=<delivery height>] [CROP_Y=<band top>] sheet.sh tag` (set CROP_Y for non-9:16 frames) and look at the sheet: text complete, nothing clipped, lines balanced.
7. **Verify words** (optional, batches): render each short's audio, then `whisper-cli -m <editor.json tools.whisper.model> -l <language> -oj -of WORK/verify/<tag> <wav>` (`subs_intake.py` prints both), then `python3 compare_whisper.py WORK --card <job card>`. No Whisper installed: skip this step and say so. Review each difference; most are intentional clean-ups.
8. Run the QA loop (qa-loop skill, stage `subtitles`) before the editor signs them off.
9. Write a proofreading list for the editor (caption number, text) next to the edit notes.

## Hook captions (Fluid Reveal Words Hook)

For the opening hook of a video (built 3 Nov 2026 on C1 HERO v6): the strong word or phrase in each caption pops in the accent colour.

- **How it works:** same group name (`FluidRevealWords`), `Main` node and `WordTime1..12` as Fluid Reveal Words, so build_lib, Resync and the planner work unchanged. Every word layer (`W1..W12`) is an instance of a hidden template `Txt1`, so a highlighted word can change colour without touching the base colour.
- **Per-word switch:** `Main.Hi1..12` (also on the title's Highlight page): 0 off, 1 highlight, 2 slam (double pop, for the one payoff word, e.g. "MORE important").
- **Highlight look:** accent colour = `Main.TopLeftRed/Green/Blue` (Highlight Color picker, default white 1/1/1: never yellow in subtitles [Tim, 3 Nov 2026]; a client accent comes from the job card Subtitles line), extra weight = outline in the same colour (`HiWeight` 0.02, it never shifts the layout, unlike a Garet Heavy swap), pop = Text+ word transform from 1+Hi*PopAmount back to 1 over PopDur, and highlighted words snap in faster (`HiSnap` 1.5) so the pop reads as a punch, not a blur.
- **Defaults:** PopAmount 0.10, PopDur 6. At 0.18/10, a highlighted word revealed late in a short caption was still enlarged at the exit and ate the space before it ("not foreverybody").
- **Building:** exec build_lib as usual and set `ns["TITLE"] = "Fluid Reveal Words Hook"` before step_insert/step_trim. After step_config, set per caption: `Hi{k}` (display token numbers, 1-based), speaker colour per person on the job card Speakers line (e.g. Bonnie cream 0.93/0.90/0.84, Jordan white on the Beon SEO job), and for 16:9 Size 0.06, Position (0.5, 0.2). Keep the highlights and speakers in a side file (e.g. `WORK/hook_extra.json`).
- **Hook only:** cap the last caption at the end of the hook speech (copy words.json with `end` = start + hook frames before planning), or the planner runs it to the end of the long-form.
- **Rules:** one strong word or phrase per caption, never more than one slam per hook, and the 4-frame reveal gap still applies.
- **Gotchas found building it:** `comp.Execute()` runs Lua asynchronously, so read results back after a sleep. Pasting a macro into a timeline title's comp from a script doesn't stick; install the .setting and use `InsertFusionTitleIntoTimeline` instead. Resolve picked up a newly installed title without a restart. A Text+ shading element switched on by script has `Size2 = 0` and draws nothing, so set Size/SizeX/SizeY to 1.

## Kinetic hook captions (Fluid Reveal Words Kinetic)

Beon's preferred hook look [Tim, built 3 Nov 2026 on C1 HERO v6]: white Libre Baskerville, sentence case, key words in true italic, 1-3 word captions stacked on up to 2 lines in the negative space beside the speaker. Reference: "Is your business *keeping up?*". **Never yellow**, **no bounce/pop** and **no shadow**: Tim rejected both ("dont use yellow", "i dont like that pop up ... apple clean style").

- **Why per-word layers:** Character Level Styling (italic on some words of one Text+) can't be scripted (`CharacterLevelStyling` reads back as a string, table writes are ignored). So each `W{k}` has its own StyledText / Style / Center, and `kinetic_layout.py` sets them from the font's real metrics.
- **Reveal:** each word fades in over `SnapIn` (Fade In, 8 frames) with an ease-out cubic, rises `Rise` 0.01 and clears `InBlur` 6. `Bounce` > 0 brings the CapCut spring back if ever wanted (default 0). Captions hard-swap (OutDur 0). Key-word colour defaults to white.
- **Calibration (Resolve 21.1):** 1 em = Text+ Size x frame width x 0.6451; Text+ centres the advance box; its centre sits 0.35 em above the baseline (Regular and Italic share hhea metrics). Italic is ~11% narrower, and its overhang closes up the next space ("for*everybody*"), so spacing is ink-aware (`MIN_INK_GAP` 0.22 em).
- **Placement:** first pick one framing per angle for the whole hook (Zoom/Pan on the V2 shots and the V1 multicam under any gap; Pan is in px of a 3840 frame, positive moves the picture right, max pan = (zoom-1) x 1920). C1 HERO: zoom 1.25 on all, Jordan pan +400 (text on the left wall), Bonnie pan -450 (text on the wall behind her, right-aligned), wide pan 0 (text centred above their heads). Punch in on the wide to lose the softboxes [Tim, C1 HERO].
- **Workflow:** (1) build titles with build_lib, `ns["TITLE"] = "Fluid Reveal Words Kinetic"`, `subs_name = n + " Kinetic Subtitles"`. (2) `WORK/captions.py` holds `CAPTIONS` plus `KEYS = {caption index: {token number: 1 italic | 2 italic slam}}`; `WORK/blocks.py` holds `BLOCKS = {name: [(start, end, x, y, align, max_width), ...]}` per stretch of the edit (C1: Jordan (0.07, 0.56, left, 0.34), Bonnie (0.93, 0.56, right, 0.30), wide (0.5, 0.72, center, 0.5)). (3) `hb/bin/python kinetic_layout.py WORK` (venv with uharfbuzz + fonttools). (4) with the subtitle timeline current, exec `kinetic_apply.py` with `SCRIPTS` (this skill's scripts folder), `WORK`, `NAME`, `A`, `B`, about 8 titles per call. (5) stills of every caption fully revealed + contact sheet.
- **Not two-tier:** a small lead-in + big italic highlight layout (Tim's "Search is / *changing.*" reference) was built and applied on 3 Nov, and Tim rejected it on screen ("it looks worse"). Keep key words italic at the same size.
- **Garet captions (C1 HERO hook, 3 Nov):** Tim switched the hook to Garet Book for every word (he rejected Heavy key words: "looks bad"); only the slam word ("more") stands out, by size. `kinetic_layout.py --font garet`; kinetic_apply sets Txt1 Font/Style from the layout. Text+ sizes a font by its full hhea height, so Garet reads ~22% smaller than Libre Baskerville at the same Size (bump Txt1 Size to ~0.09 to match).
- **Empty word layers in Garet blank the caption:** an empty (or whitespace-only) Text+ in Garet returns no image, which breaks the WordMerge chain and the whole caption renders blank (Libre returns an empty image and is fine). kinetic_apply passes unused WordMerge{k} through (`TOOLB_PassThrough`). Probe with `tool.Output[t].DataWindow` (None = valid full frame, null = failed).
- **Line breaks (Tim, 3 Nov: "the way you break ... look strange and weird to follow"):** one line whenever it fits, or fits after a shrink of up to 10%; otherwise one break at the most natural point (after punctuation, never ending a line on a clingy word like a/the/to/not/and/or, never a lone short word). Keep every caption the same size: widen the block instead of shrinking (Bonnie's C1 block is 0.37 wide). No size slam either: he found the bigger "more" weird.
- **Captions crossing a cut** take the block covering most of their time and are gated to that shot (`show` window), so text never lands on the wrong angle; it leaves at the cut.
- **Gotchas:** never put an expression on a W layer's `Size` (instanced from Txt1): it loops and the whole nested frame renders black. Scale slam / shrink-to-fit words through `WordSizeX/Y`. `GetInput` on an expression-driven input returns None; verify with stills, not read-backs. `SetInput` on an instanced input is ignored. Resolve crashes if Fusion edits are sent as parallel calls.

## Name supers (Beon Name Title)

C1 HERO v6 (3 Nov 2026): "Bonnie / FOUNDER & CEO" over her first post-hook shot (927-982), "Jordan / SEO MANAGER" over his (982-1014), each in the open wall beside them (Bonnie name at (0.56, 0.62), Jordan at (0.07, 0.62), left-justified, Name Size 0.11). [Tim]: no shadow, name not Heavy (only Book and Heavy are installed), no company name on the role line. Names and roles come from the job card Speakers line (supers) and `shoot.people`; never guess a person. Build like the subtitles: duplicate the long-form with build_lib `step_dup` (subs_name = n + " Name Titles"), insert one title per shot at the cut frames (insert one more at the last cut and delete it, to trim), set `Name`/`Role` StyledText and `Name.Center`, then AppendToTimeline the nested timeline onto a free stretch of the subtitles track. Short shots: drop OutDur to ~6 so the title holds long enough.

## Speech-sync check (plain Text+ captions already on a timeline)

QA checks S-02, S-03 and S-11 for a timeline whose captions are one Text+ each (Simone Nov C03 look), and the fix when they fail. Built 10 Nov 2026 on Simone C03a-h.

1. exec `export_state.py` (read-only) with `WORK` and `NAMES`, call `export()`: cuts, A1 source ranges and every Text+ per timeline.
2. `python3 timeline_audio.py WORK/<name>_state.json WORK/<name> --card <job card>` (Whisper model from editor.json, language from the shoot / client): A1 rebuilt as it plays and transcribed, so word times are timeline frames.
3. `python3 sync_captions.py WORK/<name>_state.json WORK/<name>/tl.json WORK/<name>_plan.json WORK/<name>/tl.wav`: applies the cut rule above to each caption's first word, moves a word whisper placed inside a pause onto the real speech onset, and merges a caption that would show for under 14 frames into a neighbour. It only touches the lowest Text+ track (a Text+ question card stays). Check any move over ~10 frames against the audio level.
3b. **New captions from scratch on a re-cut** [Simone C03 v2, 11 Nov 2026]: long-form whisper word times drifted up to 40 frames on these timelines. Plan from whisper run in ~10 s overlapping chunks, snap each start to the audio onset, and for every start whose window doesn't open on its first word, scan the boundary every 2 frames with short windows (small.en), confirming with large-v3. Finish with step 4, then an independent re-listen of every caption: on C03c it caught a caption 25 frames early that step 4 had passed, plus a wrong word ("and" for "or"). Build with the DRT route: clone the client's Text+ caption from an exported timeline onto the empty Subtitles track, then run swap_timeline.py. Resolve stills (ExportCurrentFrameAsStill) don't include titles, so they can't check caption layout.
4. **Check every start against the audio, always last** [Simone C03b, 10 Nov 2026: "Like, it's marketing 101." went up 9 frames early over "essential", because a re-split took whisper's word time; the plan checker only checked words, gaps and line lengths, so it passed]: `python3 check_caption_starts.py WORK/<name>_state.json WORK/<name>/tl.wav --fix WORK/<name>_starts.json --card <job card>`. It finds captions that go up before the speaker starts their first word (measured from the pauses, not whisper), confirms each by transcribing the stretch in question, and writes a plan that moves only the confirmed ones. A muted or beeped word reads as a pause, so a flag on a bleeped line needs a listen. Run it after any caption timing change: a re-split, a retime, or the editor's own edits. It can't judge a break with no pause in front of it: there, whisper often puts the next word a syllable early (C03c: "Our" landed on the "-ple" of "salespeople", 6 frames before the speaker says it; Tim moved it to the last dip before the word). List those no-pause breaks and listen to them, starting each caption on the last dip before its first word.
5. Nothing to change: done. Otherwise export the timeline as DRT, `python3 retime_captions_drt.py IN.drt OUT.drt WORK/<name>_plan.json --fps <fps>` (timeline start 1 h at that fps; or `--start FRAME`), then exec `swap_timeline.py` with `NAME` and `DRT` (Resolve can't trim titles by script; the old timeline goes to a Backup bin, nothing is deleted).

## After the editor edits

- Small trims, retyped words or re-cut audio: **Resync Subtitles** (or exec its `run()`). It reports titles whose words don't match the transcript.
- A new opening, or a big re-cut that moves every caption: re-export words, remap the caption indices onto the new words (difflib on the normalised words), re-plan, rebuild the subtitles timeline (`step_reset` then insert/trim/config), then replace the nested clip on the main timeline (delete the old one and append the new one at 0). C5b on 29 Oct needed this: the new opening shifted everything by about 20 frames.
- Captions under the logo or end card: leave them out, and say so.

## Gotchas (each one cost a crash or a rebuild)

- **Never `CreateEmptyTimeline` or `SetSetting` from a script.** They deadlock Resolve 21.1 (SyncProjectSettings). Always `DuplicateTimeline`, then delete the clips.
- `InsertFusionTitleIntoTimeline` is a ripple insert at the playhead on V1: it splits the previous title and pushes its tail along. Delete the tails after each insert, and trim the end by inserting one more title at the end and deleting it.
- **The playhead lags** `SetCurrentTimecode`, worst right after switching timelines. Set it, poll `GetCurrentTimecode` until it matches, and assert where each title landed. C4a was built in the wrong places before this rule.
- The duplicated subtitles timeline must keep **one video track**: with several, Resolve's track targeting drops the titles on V2 and the tail clean-up misses them (Green Oct2 C3). `step_dup` and Auto Subtitles delete the extra tracks.
- Resolve crashed once mid-insert (Green C6, 29 Oct) after about 14 quick inserts in a row. Insert in chunks of 5 to 7 per call with about 1 s between inserts. If it goes down, wait for the editor to restart it, check the subtitles timeline (autosave kept every title already placed), and carry on from the next caption; don't redo the ones already placed.
- Editors lower the subtitles by setting the compound clip's Tilt (Tim, C3/C6: -450). Copy it onto new shorts with `SetProperty("Tilt", …)`, and use `CROP_Y=1250` for the check sheet.
- Wait after `SetCurrentTimeline` until `GetCurrentTimeline()` reports the new one.
- `AppendToTimeline` startFrame/endFrame are frames *inside the subtitles timeline* (0..length); recordFrame is the main timeline's start.
- Transcript words carry the **clip's own timecode**: subtract the clip's Start TC, and scale by timeline fps / clip fps (25p camera on a 24p timeline).
- Text+ write-on per word: letters are counted without "\n", but the totals include it. A word's start skips newlines, while its end and the total include them. Pad by ±0.3 characters or float rounding drops first letters. An empty layer is (N/N, N/N). The generator does this; don't hand-edit.
- `WordTime` values are comp frames (`COMPN_RenderStart` + offset), so head-trims shift them. Resync handles it. -1 means even stagger.
- Fusion: Follower ignores expressions (use Expression modifiers), `exp()` isn't supported (use `^`), and StyledText arrays can't be set by expression, Fuse or Lua (why the highlight feature was dropped).
- Resolve can't select MP3 in the render API. For audio-only deliveries, render the "Audio Only" preset (WAV), then `ffmpeg -i x.wav -c:a libmp3lame -b:a 320k -ar 48000 x.mp3`.
