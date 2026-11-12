---
name: aroll-cut
description: "This skill should be used when building or tightening the interview (A-roll) cut of a Beon Media concept video in DaVinci Resolve: \"put together the A-roll\", \"cut the interview\", \"build the meat first\", \"tighten the pauses\", \"take out the ums\", \"remove the stutters\", \"follow this story\", or fixing cuts that sound rough or clipped. Covers story beats, dialogue cutting, removing fillers and stutters while keeping the speech flowing, air at joins, multicam, punch-ins, jump cuts and verification.\n"
metadata:
  version: "0.5.0"
---

# A-roll cut (Beon method)

> **Job card first.** Before any work in this skill, make sure this job has a job card (house-rules, "Grill first"). No card: stop and run the grilling with the editor. The `job_guard` hook blocks Resolve edits without one.

Build the spoken spine first. The editor reviews it before any B-roll goes on. The editor running the job decides every open call in this skill.

## 1. Brief to beats

- Run the house-rules grilling first. Read from the job card: Target length, Story beats, Speakers (primary speaker; drop the others' backchannels), Camera / multicam, Jokes, On-camera holds and Cut style. Names come only from the Speakers line and `shoot.people`; never guess who someone is.
- Turn the brief into story beats (e.g. C7: "the first step was…" → approach and outcome → materials, finishes, design decisions → conclusion).
- Use the strongest answers. When the speaker repeats himself, use the final version (usually the cleanest).
- **Context before hooks** [Simone Nov C03, 11 Nov 2026: the client couldn't follow v1s built from cold mid-answer hooks and lines spliced from different minutes]. Each short must make sense to a stranger with the sound on: start on the answer's setup line, play it in source order, and reorder only whole thoughts when that is clearer. Check every "it", "that", "because", "so" and callback ("25 years ago", "marketing 101") points at something the viewer has heard. Don't open on a teaser that repeats the ending. Before building, run a cold-listener check: transcribe the simulated cut and have a reviewer with no context flag anything that doesn't follow.
- Cut from the multicam when it exists (`shoot.multicam.clip`, angles from the job card Camera / multicam line); otherwise the mic camera (`shoot.audio.mic_camera`) only unless told. Single-cam interviews use punch-ins (below).
- Read the shot log `interviews` entry for transcripts, best lines and `avoid` lists. Transcribe if missing.
- Find interview clips and angles by their `sort_role` in the shot log: `aroll` for the main take, `multicam_angle` for other angles.
- **No reuse across concepts** [Tim, Hired Home Nov S2 C4, 11 Nov 2026: "some a roll is overlapping or already used in concept 2"]: concepts from one shoot share clips. Before cutting, run `scripts/reuse_check.py` (run_script, read-only; `PLANNED` takes the ranges you're about to cut) against the project's other timelines, and again before hand-over. Never reuse an A-roll take another concept already uses without the editor's yes; the job card Timelines line says which versions don't count (ask if it doesn't: a superseded, never-delivered version may not), and offer the other take of the same answer. Report B-roll clips used elsewhere (same window = reuse).
- Every take or line cut in or dropped gets a `usage[].reason` in the shot log (e.g. "dropped: repeats line 4, cleaner take at 3:12").
- Show the editor the beat list and lines (pop-up questions with suggested choices) before cutting when the brief leaves choices open. Size the cut to the job card Target length.

## 2. Cutting rules

The aim above everything: the speech flows smoothly and sounds natural, not rushed. The rules below serve that.

- Never clip a word at the start or end of a piece. Whisper word times drift up to 0.3 s: snap every edge to a real energy gap between words.
- Tone: don't end a piece on a still-talking (rising or level) tone when the next piece starts a new thought. A continuing tone is fine when the next piece carries on the same sentence (C7: "dramatically | light-filled, | large living areas").
- Remove silent mid-sentence gaps of about 0.3 s or more (hesitations). Keep pauses that read as natural phrasing (commas, sentence ends). On C7 Tim removed 8 gaps of 0.17–0.42 s; speech went from 80.1 s to 74.0 s.
- Start on the word, not the breath [Tim, Green Oct C3, 29 Oct 2026]: an in-breath, mouth click or breathy "I" before the first word is not air. Cut it and start ~0.05 s before the word (C3: 158.6-159.2 s click+breath, 176.0-176.3 s breathy "I"). Energy-threshold air checks count breaths as speech, so look at the contour: a low separate blob before the word is a breath.
- Air at joins (house default; some clients run tighter, see the client profile): about 0.10 s before the first word and 0.15 s after the last, about 0.28 s of silence across a join.
- Jokes: follow what the grilling decided. Default when unsure: keep the speaker on camera across the joke.
- Measure with `scripts/cut_air.py` (head/tail air and inner pauses per piece) and fix outliers before handing over.

### Fast path: `scripts/cut_pieces.py`

Write the picks as rough source ranges (transcript times are fine) in a plan JSON and run `cut_pieces.py plan.json --card <job card>`. The card and its shoot give the timeline fps (Delivery line), the source fps (`shoot.multicam`, `shoot.cameras`), the safety-channel advice (`shoot.audio`) and the filler language (`shoot.language`); values in the plan win. In one pass it snaps every in and out to a real silence (never inside a word), sets the air, trims hesitations by punctuation (0.22 s mid-sentence, 0.35 s after a comma, 0.45 s after a full stop), finds untranscribed ums and uhs with the steadiness test, removes isolated ones and "and and" stutters on function words (`"fillers": "cut"`, or as the job card Cut style line says), and prints the AppendToTimeline items laid end to end (multicam: `src_fps` = timeline fps plus the angle offset from `shoot.multicam.angle_offsets_s`). Glued fillers ("is-uhh", "uh-making") and fillers inside continuous speech are only flagged with a suggested cut: decide those by the rules in 2b and tell the editor about the ones left in. Treat its output as the first cut, not the final word: read every flag.

## 2a. Audio QC before any handover [Tim, Mill Nov C2, 9 Nov 2026]

Tim on the first Mill cut: "why the audio of Jay is so bad, like a lot of stutter and everything doesnt flow smooth?" and "the uhmm stutter where I just highlighted ... why dont you take it out?". Plain whisper on a whole line printed "The finishes is actually..." while the piece started with a 0.43 s "um" (C1568 15.42-15.85).
- Never trust a transcript of a whole piece to prove it is clean. Read the 10 ms energy envelope of the first and last ~0.8 s of every piece and of every inner pause: any separate voiced blob before the first word or after the last is a filler or breath. Confirm with a tiny-window transcript (it says "Um,").
- Run the full section 2b scan on every used range, measure the F0 of each piece's tail, and simulate the whole cut (concatenate the ranges) and transcribe it before touching Resolve.
- Multi-take Q&A: when a piece needs several cuts to be clean, prefer another take of the same answer.

## 2b. Remove ums, uhs and stutters (Tim, 15 Oct 2026)

House rule for every talking-head A-roll: take out the fillers and stutters (or only flag them, if the job card Cut style says so), but the speech must still flow and sound smooth after they're gone. Flow beats purity. If a removal makes a line sound clipped, rushed or stitched together, put a little air back, try another take of the line, or leave that one in and tell the editor.

What to remove (English words below; for another language the scripts read `shoot.language` or `--lang`, and their word lists are keyed by language):
- Fillers: um, uh, er, ah, erm, mm, including when they're glued to a word ("is-uhh", "and-uhh").
- Stutters and repeats: "the the", "I I", "we take, we take pride".
- False starts and restarts: keep the final complete version of the phrase.
- Self-corrections, "sorry", and crew voices inside the answer.
- "You know" at the start of a sentence, after a pause (Tim cut these on Simone C03a/C03b, 11 Nov 2026). Keep mid-phrase ones with no gap ("presenting, you know, a suggested"): cutting them would clip the line. If removing one leaves no air at a sentence break, keep it.
- A "possible um" you flagged but weren't sure of: Tim cut it (Simone C03a, before "more nightmares"). Listen, and cut it when it is a separate blob in a pause.

Joins after removals [Tim, Simone C03, 11 Nov 2026]: put a 4-frame Cross Fade 0 dB on A1 at any tight join (little or no air), and leave about 0.4 s of tail after the last word before the end card. On a single-camera short, don't trim pauses under ~0.9 s or tiny hesitations just to tidy: each trim is a jump cut (Tim: "too jumpy"). Change shot size only where motivated: at real audio cuts, plus at most one change inside a stretch over ~20 s on a new idea.

How to find them (transcripts usually drop fillers, so don't trust the text alone):
- Best: a verbatim transcript of the ranges you plan to use. `scripts/verbatim.py` runs CrisperWhisper 2.0 and writes "[um]"/"[uh]" with ~30-40 ms word times, which `cut_pieces.py` then cuts precisely (isolated, glued or run-in). It uses editor.json `tools.crisperwhisper` (run it with its `python`; MODEL_DIR `auto` reads `model_dir`). Needs the model folder and, for client work, Nyra's commercial licence (`tools.crisperwhisper.licence: true`): the weights are non-commercial. If run_env is device-vm, download the model on the Mac (Hugging Face is blocked in the VM). Setup notes are in the script header (aarch64: torch 2.5.1, transformers backend).
- Without it (no `tools.crisperwhisper` in editor.json), use the audio checks below.
- Run `scripts/filler_scan.py TRANSCRIPT.json AUDIO.wav A-B ...` over the source ranges you plan to use (`--card` or `--shoot` picks the filler language). It flags:
  - transcribed fillers;
  - speech that falls outside every transcribed word (checked for "steadiness": an "uh" is one held voiced vowel, centroid variation < 0.3);
  - words held far too long (a drawn-out "aaand" often hides an "uh");
  - repeated words and phrases;
  - mid-sentence pauses ≥ 0.3 s.
- Treat every flag as a candidate. On Arriva Oct C1 the scan found the "family-based [uh] company" filler (405.76–406.42) and four more that the first cut had kept: "is [uh] seeing", "[uh] making life", "[uh] all the employees" and "it feels [uh] really good".
- When in doubt, look at the energy contour around the spot. A separate low, steady blob between two words is a filler. A blob that runs straight into the next word is probably the word itself, because word times drift.

How to cut one out so the speech still flows:
- Cut from about 0.10–0.12 s after the last clean word to about 0.10 s before the next one, snapped to real energy gaps. That gives roughly 0.22–0.28 s of silence across the join, the same as any other join.
- Audio safety channel: `cut_pieces.py` reports clipped samples per answer, and with `--card`/`--shoot` names the dialogue and safety channels from `shoot.audio` (`mic_camera`, `mic_channel`, `safety_channel`, `safety_offset_db`). Example: Sony XLR setups record ch2 about 6 dB lower; on Arriva Oct (Azar, LIAM 0925) ch1 clipped in every answer (300+ samples in Q5) while ch2 never did. Tell the editor, work from the clean channel, and record it in `shoot.audio` if it isn't there.
- Never cut into a word. When the filler is glued to a word ("sooo-uh"), only trim the held tail if the word still ends naturally; otherwise keep the word and cut after it.
- Mind the melody: the word before the cut should lead naturally into the word after it (same sentence, compatible pitch and loudness). If the pitch jumps, or he takes a breath right at the cut, keep the breath or use the other take.
- Don't stack removals so tightly that he sounds like he never breathes. Keep natural phrasing pauses at commas and sentence ends.
- Glued fillers: `cut_pieces.py` finds where the word ends or starts by the change in the sound (e.g. the /z/ of "is" into the "uhh", the "umm" into the /m/ of "making") and puts all the join's air on the side that has silence. Arriva C1 check: it matched the hand-picked cut points within 0.05 s.
- Every removal is a jump cut in the picture. Cover it with B-roll or an angle change (see section 3), or stitch it with a Smooth Cut.
- **Smooth Cut (Tim: often works really well after removing an um or stutter):**
  - Use it when the speaker stays on camera across the removal and the head barely moves (same framing, small gap). That's typical of a short filler or stutter cut.
  - Tim's own Arriva timelines (C2 Amrita, C4) use a 4-frame Smooth Cut centred on the V1 join, with a matching 4-frame Cross Fade 0 dB on A1.
  - Skip it when the head, hands or body move a lot across the cut; it warps. Use B-roll or the other angle instead.
  - Check each Smooth Cut by eye for morphing artefacts around the face and mouth.
  - Apply it with the 21.1 transition API on the item after the join (`TimelineItem.AddTransition` / the MCP `timeline_item add_transition`). Read back the actual span, because Resolve needs a few frames of handle on both sides.
- List each removal in the A-roll report (source time and what was removed) so the editor can spot-check it, and re-run `cut_air.py` on the final pieces.

## 3. Picture on the A-roll

- Single-camera interviews alternate Zoom 1.0 and 1.35 (with pan and tilt to keep the face placed) on the visible pieces, so cuts read as angle changes. Land the conclusion in the close-up. C7 framing: medium Zoom 1.0 Pan −40; close-up Zoom 1.35 Pan −54 Tilt −150.
- Centre the speaker in every shot [Tim, Simone Nov C03, 10 Nov 2026]: slide each A-roll clip left or right with Pan so the whole person sits in the middle of the delivery frame (9:16 by default; job card Delivery line), in the wides and the close-ups. "Whole person" means the centre of mass of everything that isn't wall (hair, top, hands, jeans, crossed legs, stool), not the face: with crossed legs the head sits a little left of centre, and that's right (Tim's C03b shot 2, Pan 0). Same rule as B-roll reframing in broll.
  - Zoom and Tilt stay the same for every clip at one framing level (Simone C03: wide Zoom 1.0 Tilt 0, close Zoom 1.44 Tilt −200); only Pan changes from clip to clip, and only as far as she has actually moved. Leave a clip alone when she's already within 1% of centre, so cuts between clips at the same zoom don't nudge sideways for nothing [Tim, 2 Nov 2026]. Back-to-back clips at the same zoom (a jump cut, no framing change between them) always share one Pan, centred on the run together (duration-weighted): centring each on its own shifts her sideways across the cut [Tim, Simone C03c shots 1-2, 10 Nov 2026: Pan 0 and 7.6]. Each clip in the run stays within ~2% of centre.
  - Measure on what the viewer sees: export one still from the middle of each clip (`ExportCurrentFrameAsStill`), find the person as the largest blob that differs from the wall colour, take its column centre of mass, and correct Pan by (0.5 − x) × delivery width (1080 by default) / units-per-px. Re-export and confirm every clip lands within 1% (Simone C03, 110 clips: 49.1–50.9%).
  - Pan units are not pixels and differ per timeline: set a test Pan on one wide and one close clip, export a still each, and measure how far she moved. Simone (UHD 25p on 1080x1920): 1 Pan unit = 2.28 px at Zoom 1.0 and 3.1 px at Zoom 1.44.
- Speaker on screen max 4 s [Tim, 9 Nov 2026]: plan the cut so B-roll can cover the speaker every 4 s or less (broll rulebook section 6). Long holds only happen when the B-roll is used up, or for the exceptions in the job card On-camera holds line (a joke kept on camera, the first introduction).
- Slow Dynamic Zoom on long holds [Tim, Simone Nov C03, 2 Nov 2026], the fallback for those: an Adjustment Clip on V2 over a hold of about 6.5 s or more, Dynamic Zoom linear, about 6% over 7.4 s (Tim's C03a: 1.0 to 0.936 over 177 frames). Keep that rate for any length. Zoom in or out to suit the line (in on a build or a pointed line, out on a list or a wider thought); not on every hold.
  - The adjustment clip must start and end exactly on the A-roll clip under it [Tim]: one frame over a cut zooms the next shot for a frame and then snaps back, which reads as a glitch. Take the span from the live timeline item (GetStart/GetEnd), never from planned frame maths (the cut list's lengths were off by one frame on four of eleven Simone holds). After placing, read every adjustment clip back and compare it with the V1 item it covers.
  - The API can't create adjustment clips or set the zoom rectangles. Clone an existing Dynamic Zoom adjustment clip (Tim's on Simone C03a is the reference) in an exported DRT (EffectFiltersBA: 0x81 + zstd, zoom doubles at bytes 183 and 247 of the decoded data; swap them for a zoom out), import the DRT as a new timeline, and keep the old one in a Backup bin. The adjustment clips go on the track directly above V1 (add to the existing one, kept in time order), never above the captions or the card: an adjustment clip zooms every track below it, text included.
- Jump cuts: cover the visible ones with B-roll or a punch-in change. Leave a cut uncovered when the audio flows and the jump is small (head moves under ~1% of the frame), or when covering it would leave only a sliver of the speaker between two B-roll shots. Check with `learn-from-tim/scripts/jumpcut_check.py`.
- Keep on-camera windows inside one piece where possible (no slivers).

## 4. Verify before handover

- Enable A1 on the current timeline (`GetIsTrackEnabled` is reliable only on the current timeline; set with `SetTrackEnable`).
- Every V1 clip belongs to this concept: its source range is in this concept's cut list and it has its audio under it. A silent clip, or one from another concept's range, is a stray (Simone C03c, Nov 2026: C03a's opening line, video only, sat after a 33-frame gap at the end). Never close a gap or move a clip before checking what it is (source time, audio, which concept); a gap with a silent clip after it is a question for the editor, not a fix [Tim, 10 Nov 2026].
- Duplicate the timeline, run `CreateSubtitlesFromAudio` on the copy, poll `GetCreateSubtitlesFromAudioStatus`, read the subtitle items, and check the whole script reads clean with no clipped words and no um, uh or stutter left. Delete the temporary timeline.
- Re-run `scripts/filler_scan.py` on the source ranges actually used; nothing flagged as "likely filler" should remain inside a piece, unless it's reported to the editor as left in on purpose.
- Run `scripts/cut_review.py CUT.json OUT_DIR --card <job card>` (frame size from the delivery) and look at the sheets: last and first frame of every join, the difference image, the waveform across the cut, the jump size (shift %, diff) and the silence across the join. It suggests "invisible", "smooth cut" or "cover" per join. Fix clipped breaths, half-open mouths on edge frames and joins whose air is outside about 0.20–0.32 s before the editor sees the cut.
- Listen-check the joins flagged by `cut_air.py`.
- Then the QA loop (qa-loop skill, stage `aroll`): the qa-manager agent checks the cut with fresh eyes; fix what it confirms, ask the editor the creative calls.
- Report: running time against the job card Target length, beats, the tightest pauses, the QA result, anything borderline for the editor.

## Recut on a copy (the editor's timeline untouched)

To change A-roll pieces after B-roll is placed (filler removal, a re-pick, a tighter answer):
1. `scripts/resolve_snapshot.py` (run_script, read-only) → snapshot.json.
2. edits.json: which A-roll items are replaced by which new source ranges (from `cut_pieces.py`).
3. `scripts/recut_plan.py snapshot.json edits.json plan.json` (timeline fps from the snapshot; `--card` only as a fallback): lays out the new A-roll and moves every other item and marker with the words it sat on (B-roll that started at a join starts at the new join); prints the before/after table and any item it had to shorten.
4. `scripts/resolve_relay.py` (run_script): STEP "create" duplicates the timeline under a new name and empties it, STEP "place" re-appends each track with speeds, framing, names, colours and enabled states.
5. Run `broll/scripts/broll_gate.py` on the copy: B-roll edges must still sit exactly on the A-roll cuts (recut_plan.py snaps edges that sat on or within 3 frames of a join; any 1-2 frame flash of the speaker is a glitch [Tim, 11 Nov 2026]). Fix any re-placed item that drifted off a cut the same way.
6. Proxy render and `finish-pass/scripts/render_check.py`, then the editor listens.

## Resolve API recipes

- Append a piece: `MediaPool.AppendToTimeline([{"mediaPoolItem", "startFrame", "endFrame", "recordFrame", "trackIndex"}])` with integer source frames; `endFrame = sf + ceil(D * clip_fps / timeline_fps)` (timeline fps from the job card Delivery line, 24 by default; Resolve floors the duration; float ends leave gaps).
- Media pool names like `LIAM.A_FX3_0272.MP4`: key with `name.rsplit('.', 1)`.
- There is no move API. To shift a section: duplicate the timeline as a backup, then rebuild the items from `GetSourceStartTime`/`GetSourceEndTime` with rounded source frames.
- Punch-in: `item.SetProperty("ZoomX"/"ZoomY", 1.35)`, `"Pan"`, `"Tilt"`. Vertical 1080x1920 (Beon default delivery) from 16:9: to see the whole source temporarily set Zoom 0.3164.
- Markers: `timeline.AddMarker(frame, color, name, note, duration, customData)`, `DeleteMarkerAtFrame`.
- Multicam (Tim: "create the multicam clip first, audio from the A cam with the mic"):
  - Call `MediaPool.CreateMulticamClip([A, B], {"angleSyncMode": resolve.MULTICAM_ANGLE_SYNC_AUDIO, "multicamAudioMode": resolve.MULTICAM_AUDIO_REFERENCE})` with the mic camera first (`shoot.audio.mic_camera`; `shoot.multicam.audio_ref_camera`). That puts its audio on every angle. Record the clip name and angle offsets in `shoot.multicam`.
  - Verify the angle offsets and audio in a timeline FCPXML export (`mc-angle` / `mc-source`).
  - Resolve moves the sources into an "Original Clips" bin.
  - The API can't switch angles on a timeline item. Put B-angle pieces on a named track above V1 (synced source range), and tell the editor.

See `references/c7-example.md` for a worked comparison of Claude's C7 cut against Tim's final.
