# QA checklist: subtitles

Sources: subtitles skill (Tim's rules, gotchas), client profile Subtitles section, job card (the confirmed look).
Get: `plans.json` / `plan_captions.py` output, the subtitles timeline readback, `check_lib.stills` sheets,
optional whisper compare (`compare_whisper.py`).

| ID | Check | How | Kind | Pass when |
|---|---|---|---|---|
| S-01 | The look is the one Tim confirmed | read one title's style (font, size, colour, position, Tilt) vs the job card | hard | identical |
| S-02 | No gaps between captions | subtitle items start/end | hard | each ends exactly where the next starts; last runs to the end of speech |
| S-03 | Caption changes land on the picture cut | every caption start vs the V1/B-roll cut list | hard | no boundary 1-6 frames off a cut, except where the cut is more than 8 frames before or 6 after the caption's first word (speech wins, S-11) |
| S-04 | Never several words at once | WordTime gaps | hard | >= 4 frames between reveals |
| S-05 | Words reveal with the speech | WordTime vs word timings | hard | ~2 frames before each word (SyncOffset -2) |
| S-06 | Text complete, nothing clipped, lines balanced | stills sheet (`sheet.sh`) *(calibrating: line length)* | hard | every caption fully visible; <= 2 lines; ~24-28 chars per line |
| S-07 | Line breaks natural | caption text | judgement | no line ending on a/the/to/of/and/or; break at pauses and commas |
| S-08 | Clean verbatim and correct words | render each short's audio from the current timeline to scratch, `whisper-cli -m ~/whisper-models/ggml-large-v3.bin -oj -of WORK/verify/<tag> <wav>` (overwrite old ones), then `python3 compare_whisper.py WORK`; no Whisper: not_checked | judgement | differences are intentional clean-ups only; names and numbers right |
| S-09 | Not under the logo/end card | caption times vs end card | hard | none under it (or the report says so) |
| S-10 | Hook captions follow the hook rules | Kinetic/Hook look, one key word per caption, no yellow/pop/shadow unless the client says so | hard | as the client profile says |
| S-11 | Each caption goes up on its first spoken word [Tim, 4 Nov 2026] | rebuild the timeline's audio from the A1 source ranges, transcribe it, compare every caption start with its first word (subtitles skill, Speech-sync check: `timeline_audio.py` + `sync_captions.py` print every caption that would move; `check_caption_starts.py` finds any caption that goes up before its first word and confirms it by ear) | hard | start within 8 frames before to 6 frames after the word (Simone C03g was up to 35 frames off) |
