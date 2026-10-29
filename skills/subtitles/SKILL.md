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

## After Tim edits

- Small trims, retyped words or re-cut audio: **Resync Subtitles** (or exec its `run()`). It reports titles whose words don't match the transcript.
- A new opening, or a big re-cut that moves every caption: re-export words, remap the caption indices onto the new words (difflib on the normalised words), re-plan, rebuild the subtitles timeline (`step_reset` then insert/trim/config), then replace the nested clip on the main timeline (delete the old one and append the new one at 0). C5b on 29 Oct needed this: the new opening shifted everything by about 20 frames.
- Captions under the logo or end card: leave them out, and say so.

## Gotchas (each one cost a crash or a rebuild)

- **Never `CreateEmptyTimeline` or `SetSetting` from a script.** They deadlock Resolve 21.1 (SyncProjectSettings). Always `DuplicateTimeline`, then delete the clips.
- `InsertFusionTitleIntoTimeline` is a ripple insert at the playhead on V1: it splits the previous title and pushes its tail along. Delete the tails after each insert, and trim the end by inserting one more title at the end and deleting it.
- **The playhead lags** `SetCurrentTimecode`, worst right after switching timelines. Set it, poll `GetCurrentTimecode` until it matches, and assert where each title landed. C4a was built in the wrong places before this rule.
- Wait after `SetCurrentTimeline` until `GetCurrentTimeline()` reports the new one.
- `AppendToTimeline` startFrame/endFrame are frames *inside the subtitles timeline* (0..length); recordFrame is the main timeline's start.
- Transcript words carry the **clip's own timecode**: subtract the clip's Start TC, and scale by timeline fps / clip fps (25p camera on a 24p timeline).
- Text+ write-on per word: letters are counted without "\n", but the totals include it. A word's start skips newlines, while its end and the total include them. Pad by ±0.3 characters or float rounding drops first letters. An empty layer is (N/N, N/N). The generator does this; don't hand-edit.
- `WordTime` values are comp frames (`COMPN_RenderStart` + offset), so head-trims shift them. Resync handles it. -1 means even stagger.
- Fusion: Follower ignores expressions (use Expression modifiers), `exp()` isn't supported (use `^`), and StyledText arrays can't be set by expression, Fuse or Lua (why the highlight feature was dropped).
- Resolve can't select MP3 in the render API. For audio-only deliveries, render the "Audio Only" preset (WAV), then `ffmpeg -i x.wav -c:a libmp3lame -b:a 320k -ar 48000 x.mp3`.
