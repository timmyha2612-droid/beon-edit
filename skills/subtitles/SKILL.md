---
name: subtitles
description: "This skill should be used when Tim asks for subtitles or captions on a Beon Media video or short in DaVinci Resolve, or to fix, resync or restyle them after an edit: \"do the subtitles\", \"sub the shorts\", \"the sub is out of sync\", \"words pop up at once\", \"fix the sub after my trim\", \"install the title preset\". Covers the Fluid Reveal Words title, the style test with Tim, Auto/Resync Subtitles, hand clean-verbatim captions for batches, checks, and Resolve gotchas that crash or misplace titles."
metadata:
  version: "0.1.0"
---

# Subtitles (Fluid Reveal Words)

Word-by-word subtitles that rise in as each word is spoken. Built on 28 Oct 2026 for the Beon SEO shorts (C2a approved by Bonnie, then 17 more shorts).

## What's here

| Path | What it is |
|---|---|
| `assets/Fluid Reveal Words.setting` | The word-by-word title (12 word layers, Garet Book, hidden `Main.WordTime1..12` for per-word timing, AE-style In/Out curves). Approved C2a look as defaults. |
| `assets/Fluid Reveal.setting` | Letter-by-letter version of the same reveal. |
| `assets/Fluid Reveal Words Hook.setting` | Hook version of Fluid Reveal Words: same reveal and timing, plus a per-word highlight (accent colour, extra weight, pop). For video hooks only; normal subtitles stay on Fluid Reveal Words. |
| `assets/Fluid Reveal Words Kinetic.setting` | Kinetic (editorial) hook title: every word on its own layer in Libre Baskerville, key words in true italic, clean fade-rise-unblur reveal, soft shadow. Tim's preferred hook look. |
| `scripts/kinetic_layout.py`, `scripts/kinetic_apply.py` | Typeset Kinetic captions as stacked blocks in each shot's negative space (HarfBuzz, ink-aware italics) and push the layout into the titles. |
| `scripts/install.sh` | Copies both titles and the two Resolve scripts into Resolve. Run once per machine, then restart Resolve. |
| `scripts/build_presets.py OUT_DIR` | Regenerates both `.setting` files (fonts, default curves, write-on maths). Edit this, never the `.setting` by hand. |
| `scripts/Auto Subtitles.py` | Workspace > Scripts > Edit. One click: transcribe A1, caption, build, place on a new top track. |
| `scripts/Resync Subtitles.py` | Workspace > Scripts > Edit. After trims/retyping/re-cuts: re-times every title's words to the speech under it. Only sets values, never moves clips. |
| `scripts/export_words.py`, `show_words.py`, `plan_captions.py`, `build_lib.py`, `check_lib.py`, `sheet.sh`, `compare_whisper.py` | The hand-caption pipeline Claude drives for batches (clean verbatim, many shorts). |
| `references/captions-example.py` | Format of hand-written captions, with real examples. |

## Step 0: style test with Tim (always first, unless he says the defaults are fine)

1. Make sure the title is installed (`scripts/install.sh`). Ask Tim to drop one **Fluid Reveal Words** on his timeline, type a sample line and set the look himself: font, size, colour, position, tracking/line spacing, rise, blur, in/out curves and lengths.
2. Tim then either leaves that title **selected** and says so, or tells you the settings. Read the selected one with `build_lib.step_read_style(<timeline>)` (writes `WORK/style.json`) and read the values back to him in plain words (e.g. "Garet Book 0.07, white, 0.5/0.24") so he can confirm.
3. Every caption then copies that look (`build_lib.step_config` and Auto Subtitles both apply it). Per-caption values stay automatic: text, word times, in-duration, out-duration, and the last caption has no outro.
4. Curve *shapes* (the custom In/Out lookups) can't be copied by script. If Tim changed those, update `WORDS_IN_LUT`/`WORDS_OUT_LUT` in `build_presets.py`, regenerate, reinstall (he restarts Resolve), and commit.
5. If he wants the look as the new default for future jobs, put the values into `build_presets.py`, regenerate the assets, reinstall, bump the plugin version and push.

## Tim's rules (non-negotiable)

- **No gaps:** each caption ends exactly where the next starts. The last one runs to the end of the speech, and the outro (`OutDur 0`) only applies when the logo or end card isn't covering it.
- **New sentence = new caption.** Natural breaks: at most 2 lines of about 24–28 characters, break at pauses and commas, never end a line on a/the/to/of. Proper punctuation and capitals, with numbers as written ("$10 million", "3 months").
- **Words reveal at speech rate:** LEAD 2 frames before the word is spoken.
- **Never several words at once:** at least 4 frames between word reveals (`MIN_GAP`). Too short a caption spreads evenly, and the last word may land up to 2 frames before the exit. Tim: "we dont ever want that happen as it looks bad and clumsy".
- **Clean verbatim:** drop ums, stutters and false starts. Drop the other person's one-word reactions ("Yeah.", "Wow.", "Right."); the previous caption holds over them.
- **Never crash Resolve** (see gotchas). **Easy to fix after edits:** Resync Subtitles.
- Defaults: IN_DUR 18, OUT_DUR 4, OutBlur 6, OutLift 0.015, SyncOffset -2.

## Route A: quick (one timeline, verbatim is fine)

Tim selects his styled title (optional) and runs **Auto Subtitles**. It transcribes A1 with Resolve's TranscribeAudio, maps words through the cuts (source timecode and 25p→24p handled), splits the captions, builds them on a "<timeline> Subtitles" duplicate and places that on a new top track. Tim decomposes it if he wants. Check the results, then fix wording by retyping the title text and running Resync.

To drive it yourself: `exec` the script in `run_script_unsafe` with `{"resolve": resolve, "__name__": "lib"}`. First call `run(dry_run=True)` to see the plan, with nothing built. Building many captions can exceed the 60 s call limit, so for long timelines use Route B.

## Route B: hand clean-verbatim captions (batches, client deliverables)

Work in a folder (`WORK`, e.g. the shoot's `_claude_scratch/subs`, never Dropbox). All Resolve calls go through `run_script_unsafe`, `exec`-ing the script with `resolve`, `project` and `WORK` injected, and stay under 60 s each.

1. **Words:** run `export_words.py`'s `export("<path to Auto Subtitles.py>")` with `NAMES=[timeline prefixes]`. It writes `WORK/words.json` (frames relative to timeline start, plus A1 cuts).
2. **Read:** `python3 show_words.py WORK C5b` prints `index:word@frame`, with `‖` at cuts and `|n` at pauses.
3. **Write captions** in `WORK/captions.py` (format in `references/captions-example.py`): `(first word index, "Line one\nline two")`. Keep the indices increasing. Hand-write the clean text and fix the transcript's mishearings.
4. **Plan:** `python3 plan_captions.py WORK` writes `plans.json` (start/end/times/in/out per caption) and prints problems: too wide, too many words, more than 118 frames, words that don't match. Fix and rerun until clean.
5. **Build**, per timeline, each step its own call (`build_lib.py`):
   - `step_dup(name)`: duplicate the timeline as "<name> Subtitles", then empty it.
   - `step_insert(name, a, b)`: insert in chunks of about 8. It waits for the playhead and asserts each landing frame.
   - `step_trim(name)`: must return `match: true`.
   - `step_config(name, a, b)`: text, timing, style and names ("Sub 01"…).
   - `step_place(name)`: new top track named Subtitles, nested clip at 0.
   - If anything lands wrong: `step_reset`, then insert again.
6. **Check:** `check_lib.stills(name, a, b, tag)` exports one still per caption just before it exits. Run `WORK=… sheet.sh tag` and look at the sheet: text complete, nothing clipped, lines balanced.
7. **Verify words** (optional, batches): render each short's audio, then `whisper-cli -m ~/whisper-models/ggml-large-v3.bin -oj -of WORK/verify/<tag> <wav>`, then `python3 compare_whisper.py WORK`. Review each difference; most are intentional clean-ups.
8. Write a proofreading list for Tim (caption number, text) next to the edit notes.

## Hook captions (Fluid Reveal Words Hook)

For the opening hook of a video (built 3 Nov 2026 on C1 HERO v6): the strong word or phrase in each caption pops in the accent colour.

- **How it works:** same group name (`FluidRevealWords`), `Main` node and `WordTime1..12` as Fluid Reveal Words, so build_lib, Resync and the planner work unchanged. Every word layer (`W1..W12`) is an instance of a hidden template `Txt1`, so a highlighted word can change colour without touching the base colour.
- **Per-word switch:** `Main.Hi1..12` (also on the title's Highlight page): 0 off, 1 highlight, 2 slam (double pop, for the one payoff word, e.g. "MORE important").
- **Highlight look:** accent colour = `Main.TopLeftRed/Green/Blue` (Highlight Color picker, default warm yellow 1/0.82/0.25), extra weight = outline in the same colour (`HiWeight` 0.02, it never shifts the layout, unlike a Garet Heavy swap), pop = Text+ word transform from 1+Hi*PopAmount back to 1 over PopDur, and highlighted words snap in faster (`HiSnap` 1.5) so the pop reads as a punch, not a blur.
- **Defaults:** PopAmount 0.10, PopDur 6. At 0.18/10, a highlighted word revealed late in a short caption was still enlarged at the exit and ate the space before it ("not foreverybody").
- **Building:** exec build_lib as usual and set `ns["TITLE"] = "Fluid Reveal Words Hook"` before step_insert/step_trim. After step_config, set per caption: `Hi{k}` (display token numbers, 1-based), speaker colour (Bonnie cream 0.93/0.90/0.84, Jordan white on the Beon SEO job), and for 16:9 Size 0.06, Position (0.5, 0.2). Keep the highlights and speakers in a side file (e.g. `WORK/hook_extra.json`).
- **Hook only:** cap the last caption at the end of the hook speech (copy words.json with `end` = start + hook frames before planning), or the planner runs it to the end of the long-form.
- **Rules:** one strong word or phrase per caption, never more than one slam per hook, and Tim's 4-frame reveal gap still applies.
- **Gotchas found building it:** `comp.Execute()` runs Lua asynchronously, so read results back after a sleep. Pasting a macro into a timeline title's comp from a script doesn't stick; install the .setting and use `InsertFusionTitleIntoTimeline` instead. Resolve picked up a newly installed title without a restart. A Text+ shading element switched on by script has `Size2 = 0` and draws nothing, so set Size/SizeX/SizeY to 1.

## Kinetic hook captions (Fluid Reveal Words Kinetic)

Tim's preferred hook look (built 3 Nov 2026 on C1 HERO v6): white Libre Baskerville, sentence case, key words in true italic, 1-3 word captions stacked on up to 2 lines in the negative space beside the speaker. Reference: "Is your business *keeping up?*". **Never yellow** and **no bounce/pop**: he rejected both ("dont use yellow", "i dont like that pop up ... apple clean style").

- **Why per-word layers:** Character Level Styling (italic on some words of one Text+) can't be scripted (`CharacterLevelStyling` reads back as a string, table writes are ignored). So each `W{k}` has its own StyledText / Style / Center, and `kinetic_layout.py` sets them from the font's real metrics.
- **Reveal:** each word fades in over `SnapIn` (Fade In, 8 frames) with an ease-out cubic, rises `Rise` 0.01 and clears `InBlur` 6. `Bounce` > 0 brings the CapCut spring back if ever wanted (default 0). Captions hard-swap (OutDur 0). Key-word colour defaults to white.
- **Calibration (Resolve 21.1):** 1 em = Text+ Size x frame width x 0.6451; Text+ centres the advance box; its centre sits 0.35 em above the baseline (Regular and Italic share hhea metrics). Italic is ~11% narrower, and its overhang closes up the next space ("for*everybody*"), so spacing is ink-aware (`MIN_INK_GAP` 0.22 em).
- **Placement:** first pick one framing per angle for the whole hook (Zoom/Pan on the V2 shots and the V1 multicam under any gap; Pan is in px of a 3840 frame, positive moves the picture right, max pan = (zoom-1) x 1920). C1 HERO: zoom 1.25 on all, Jordan pan +400 (text on the left wall), Bonnie pan -450 (text on the wall behind her, right-aligned), wide pan 0 (text centred above their heads). Tim prefers punch-in on the wide to lose the softboxes.
- **Workflow:** (1) build titles with build_lib, `ns["TITLE"] = "Fluid Reveal Words Kinetic"`, `subs_name = n + " Kinetic Subtitles"`. (2) `WORK/captions.py` holds `CAPTIONS` plus `KEYS = {caption index: {token number: 1 italic | 2 italic slam}}`; `WORK/blocks.py` holds `BLOCKS = {name: [(start, end, x, y, align, max_width), ...]}` per stretch of the edit (C1: Jordan (0.07, 0.56, left, 0.34), Bonnie (0.93, 0.56, right, 0.30), wide (0.5, 0.72, center, 0.5)). (3) `hb/bin/python kinetic_layout.py WORK` (venv with uharfbuzz + fonttools). (4) with the subtitle timeline current, exec `kinetic_apply.py` with `NAME`, `A`, `B`, about 8 titles per call. (5) stills of every caption fully revealed + contact sheet.
- **Captions crossing a cut** take the block covering most of their time and are gated to that shot (`show` window), so text never lands on the wrong angle; it leaves at the cut.
- **Gotchas:** never put an expression on a W layer's `Size` (instanced from Txt1): it loops and the whole nested frame renders black. Scale slam / shrink-to-fit words through `WordSizeX/Y`. `GetInput` on an expression-driven input returns None; verify with stills, not read-backs. `SetInput` on an instanced input is ignored. Resolve crashes if Fusion edits are sent as parallel calls.

## After Tim edits

- Small trims, retyped words or re-cut audio: **Resync Subtitles** (or exec its `run()`). It reports titles whose words don't match the transcript.
- A new opening, or a big re-cut that moves every caption: re-export words, remap the caption indices onto the new words (difflib on the normalised words), re-plan, rebuild the subtitles timeline (`step_reset` then insert/trim/config), then replace the nested clip on the main timeline (delete the old one and append the new one at 0). C5b on 29 Oct needed this: the new opening shifted everything by about 20 frames.
- Captions under the logo or end card: leave them out, and say so.

## Gotchas (each one cost a crash or a rebuild)

- **Never `CreateEmptyTimeline` or `SetSetting` from a script.** They deadlock Resolve 21.1 (SyncProjectSettings). Always `DuplicateTimeline`, then delete the clips.
- `InsertFusionTitleIntoTimeline` is a ripple insert at the playhead on V1: it splits the previous title and pushes its tail along. Delete the tails after each insert, and trim the end by inserting one more title at the end and deleting it.
- **The playhead lags** `SetCurrentTimecode`, worst right after switching timelines. Set it, poll `GetCurrentTimecode` until it matches, and assert where each title landed. C4a was built in the wrong places before this rule.
- The duplicated subtitles timeline must keep **one video track**: with several, Resolve's track targeting drops the titles on V2 and the tail clean-up misses them (Green Oct2 C3). `step_dup` and Auto Subtitles delete the extra tracks.
- Resolve crashed once mid-insert (Green C6, 29 Oct) after about 14 quick inserts in a row. Insert in chunks of 5 to 7 per call with about 1 s between inserts. If it goes down, wait for Tim to restart it, check the subtitles timeline (autosave kept every title already placed), and carry on from the next caption; don't redo the ones already placed.
- Tim lowers the subtitles by setting the compound clip's Tilt (C3/C6: -450). Copy it onto new shorts with `SetProperty("Tilt", …)`, and use `CROP_Y=1250` for the check sheet.
- Wait after `SetCurrentTimeline` until `GetCurrentTimeline()` reports the new one.
- `AppendToTimeline` startFrame/endFrame are frames *inside the subtitles timeline* (0..length); recordFrame is the main timeline's start.
- Transcript words carry the **clip's own timecode**: subtract the clip's Start TC, and scale by timeline fps / clip fps (25p camera on a 24p timeline).
- Text+ write-on per word: letters are counted without "\n", but the totals include it. A word's start skips newlines, while its end and the total include them. Pad by ±0.3 characters or float rounding drops first letters. An empty layer is (N/N, N/N). The generator does this; don't hand-edit.
- `WordTime` values are comp frames (`COMPN_RenderStart` + offset), so head-trims shift them. Resync handles it. -1 means even stagger.
- Fusion: Follower ignores expressions (use Expression modifiers), `exp()` isn't supported (use `^`), and StyledText arrays can't be set by expression, Fuse or Lua (why the highlight feature was dropped).
- Resolve can't select MP3 in the render API. For audio-only deliveries, render the "Audio Only" preset (WAV), then `ffmpeg -i x.wav -c:a libmp3lame -b:a 320k -ar 48000 x.mp3`.
