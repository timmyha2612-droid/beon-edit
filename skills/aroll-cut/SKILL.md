---
name: aroll-cut
description: "This skill should be used when building or tightening the interview (A-roll) cut of a Beon Media concept video in DaVinci Resolve: \"put together the A-roll\", \"cut the interview\", \"build the meat first\", \"tighten the pauses\", \"take out the ums\", \"remove the stutters\", \"follow this story\", or fixing cuts that sound rough or clipped. Covers story beats, dialogue cutting, removing fillers and stutters while keeping the speech flowing, air at joins, multicam, punch-ins, jump cuts and verification.\n"
metadata:
  version: "0.3.0"
---

# A-roll cut (Tim's method)

Build the spoken spine first. Tim reviews it before any B-roll goes on.

## 1. Brief to beats

- Run the house-rules grilling first (length, jokes, camera, music).
- Turn the brief into story beats (e.g. C7: "the first step was…" → approach and outcome → materials, finishes, design decisions → conclusion).
- Use the strongest answers. When the speaker repeats himself, use the final version (usually the cleanest).
- Cut from Tim's multicam when it exists; A cam only unless told. Single-cam interviews use punch-ins (below).
- Read the shot log `interviews` entry for transcripts, best lines and `avoid` lists. Transcribe if missing.
- Show Tim the beat list and lines (pop-up questions with suggested choices) before cutting when the brief leaves choices open.

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

Write the picks as rough source ranges (transcript times are fine) in a plan JSON and run `cut_pieces.py plan.json`. In one pass it snaps every in and out to a real silence (never inside a word), sets the air, trims hesitations by punctuation (0.22 s mid-sentence, 0.35 s after a comma, 0.45 s after a full stop), finds untranscribed ums and uhs with the steadiness test, removes isolated ones and "and and" stutters on function words (`"fillers": "cut"`), and prints the AppendToTimeline items laid end to end (multicam: `src_fps` 24 plus the angle offset). Glued fillers ("is-uhh", "uh-making") and fillers inside continuous speech are only flagged with a suggested cut: decide those by the rules in 2b and tell Tim about the ones left in. Treat its output as the first cut, not the final word: read every flag.

## 2b. Remove ums, uhs and stutters (Tim, 15 Oct 2026)

Tim's rule for every talking-head A-roll: take out the fillers and stutters, but the speech must still flow and sound smooth after they're gone. Flow beats purity. If a removal makes a line sound clipped, rushed or stitched together, put a little air back, try another take of the line, or leave that one in and tell Tim.

What to remove:
- Fillers: um, uh, er, ah, erm, mm, including when they're glued to a word ("is-uhh", "and-uhh").
- Stutters and repeats: "the the", "I I", "we take, we take pride".
- False starts and restarts: keep the final complete version of the phrase.
- Self-corrections, "sorry", and crew voices inside the answer.

How to find them (transcripts usually drop fillers, so don't trust the text alone):
- Best: a verbatim transcript of the ranges you plan to use. `scripts/verbatim.py` runs CrisperWhisper 2.0 in the device VM and writes "[um]"/"[uh]" with ~30-40 ms word times, which `cut_pieces.py` then cuts precisely (isolated, glued or run-in). Needs the model folder from Tim (Hugging Face is blocked here) and, for client work, Nyra's commercial licence: the weights are non-commercial. Setup notes are in the script header (aarch64 VM: torch 2.5.1, transformers backend).
- Without it, use the audio checks below.
- Run `scripts/filler_scan.py TRANSCRIPT.json AUDIO.wav A-B ...` over the source ranges you plan to use. It flags:
  - transcribed fillers;
  - speech that falls outside every transcribed word (checked for "steadiness": an "uh" is one held voiced vowel, centroid variation < 0.3);
  - words held far too long (a drawn-out "aaand" often hides an "uh");
  - repeated words and phrases;
  - mid-sentence pauses ≥ 0.3 s.
- Treat every flag as a candidate. On Arriva Oct C1 the scan found the "family-based [uh] company" filler (405.76–406.42) and four more that the first cut had kept: "is [uh] seeing", "[uh] making life", "[uh] all the employees" and "it feels [uh] really good".
- When in doubt, look at the energy contour around the spot. A separate low, steady blob between two words is a filler. A blob that runs straight into the next word is probably the word itself, because word times drift.

How to cut one out so the speech still flows:
- Cut from about 0.10–0.12 s after the last clean word to about 0.10 s before the next one, snapped to real energy gaps. That gives roughly 0.22–0.28 s of silence across the join, the same as any other join.
- Audio safety channel: `cut_pieces.py` reports clipped samples per answer. Sony XLR setups record ch2 about 6 dB lower: on Arriva Oct (Azar, LIAM 0925) ch1 clipped in every answer (300+ samples in Q5) while ch2 never did. Tell Tim and work from the clean channel.
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
- List each removal in the A-roll report (source time and what was removed) so Tim can spot-check it, and re-run `cut_air.py` on the final pieces.

## 3. Picture on the A-roll

- Single-camera interviews alternate Zoom 1.0 and 1.35 (with pan and tilt to keep the face placed) on the visible pieces, so cuts read as angle changes. Land the conclusion in the close-up. C7 framing: medium Zoom 1.0 Pan −40; close-up Zoom 1.35 Pan −54 Tilt −150.
- Centre the speaker in the 9:16 frame on every piece [Tim, Simone Nov C03, 2 Nov 2026]: slide each A-roll piece left or right with Pan so the person (head and upper body) sits in the middle, in the wides and the close-ups. Same rule as B-roll reframing in broll-qaqc. Measure per piece, not once per take: people lean and shift between answers.
  - Measure the subject x on the source at 30/50/70% of each piece: face centre (Haar) and the upper-body mass (dark hair and clothes against the wall), averaged. The face detector misfires on turned heads (Simone C03h: one face read 0.46 against a body of 0.48), so fall back to the body when the two disagree by more than ~1%.
  - Pan units are not pixels and differ per timeline: set a test Pan on one wide and one close piece, export a still each, and measure how far the subject moved. Simone (UHD 25p on 1080x1920): 1 Pan unit = 2.28 px at Zoom 1.0 and 3.1 px at Zoom 1.44. Then Pan = (540 − predicted x px) / units-per-px, with predicted x px = 540 + (x − 0.5) × 3413 × zoom.
  - Check with rendered stills (a vertical centre line on a sheet): body centred within ~2-3% of the width.
- Jump cuts: cover the visible ones with B-roll or a punch-in change. Leave a cut uncovered when the audio flows and the jump is small (head moves under ~1% of the frame), or when covering it would leave only a sliver of the speaker between two B-roll shots. Check with `learn-from-tim/scripts/jumpcut_check.py`.
- Keep on-camera windows inside one piece where possible (no slivers).

## 4. Verify before handover

- Enable A1 on the current timeline (`GetIsTrackEnabled` is reliable only on the current timeline; set with `SetTrackEnable`).
- Duplicate the timeline, run `CreateSubtitlesFromAudio` on the copy, poll `GetCreateSubtitlesFromAudioStatus`, read the subtitle items, and check the whole script reads clean with no clipped words and no um, uh or stutter left. Delete the temporary timeline.
- Re-run `scripts/filler_scan.py` on the source ranges actually used; nothing flagged as "likely filler" should remain inside a piece, unless it's reported to Tim as left in on purpose.
- Run `scripts/cut_review.py CUT.json OUT_DIR` and look at the sheets: last and first frame of every join, the difference image, the waveform across the cut, the jump size (shift %, diff) and the silence across the join. It suggests "invisible", "smooth cut" or "cover" per join. Fix clipped breaths, half-open mouths on edge frames and joins whose air is outside about 0.20–0.32 s before Tim sees the cut.
- Listen-check the joins flagged by `cut_air.py`.
- Report: running time, beats, the tightest pauses, anything borderline for Tim.

## Recut on a copy (Tim's timeline untouched)

To change A-roll pieces after B-roll is placed (filler removal, a re-pick, a tighter answer):
1. `scripts/resolve_snapshot.py` (run_script, read-only) → snapshot.json.
2. edits.json: which A-roll items are replaced by which new source ranges (from `cut_pieces.py`).
3. `scripts/recut_plan.py snapshot.json edits.json plan.json`: lays out the new A-roll and moves every other item and marker with the words it sat on (B-roll that started at a join starts at the new join); prints the before/after table and any item it had to shorten.
4. `scripts/resolve_relay.py` (run_script): STEP "create" duplicates the timeline under a new name and empties it, STEP "place" re-appends each track with speeds, framing, names, colours and enabled states.
5. Proxy render and `finish-pass/scripts/render_check.py`, then Tim listens.

## Resolve API recipes

- Append a piece: `MediaPool.AppendToTimeline([{"mediaPoolItem", "startFrame", "endFrame", "recordFrame", "trackIndex"}])` with integer source frames; `endFrame = sf + ceil(D * clip_fps / 24)` (Resolve floors the duration; float ends leave gaps).
- Media pool names like `LIAM.A_FX3_0272.MP4`: key with `name.rsplit('.', 1)`.
- There is no move API. To shift a section: duplicate the timeline as a backup, then rebuild the items from `GetSourceStartTime`/`GetSourceEndTime` with rounded source frames.
- Punch-in: `item.SetProperty("ZoomX"/"ZoomY", 1.35)`, `"Pan"`, `"Tilt"`. Vertical 1080x1920 from 16:9: to see the whole source temporarily set Zoom 0.3164.
- Markers: `timeline.AddMarker(frame, color, name, note, duration, customData)`, `DeleteMarkerAtFrame`.
- Multicam (Tim: "create the multicam clip first, audio from the A cam with the mic"):
  - Call `MediaPool.CreateMulticamClip([A, B], {"angleSyncMode": resolve.MULTICAM_ANGLE_SYNC_AUDIO, "multicamAudioMode": resolve.MULTICAM_AUDIO_REFERENCE})` with the mic camera first. That puts its audio on every angle.
  - Verify the angle offsets and audio in a timeline FCPXML export (`mc-angle` / `mc-source`).
  - Resolve moves the sources into an "Original Clips" bin.
  - The API can't switch angles on a timeline item. Put B-angle pieces on a named track above V1 (synced source range), and tell Tim.

See `references/c7-example.md` for a worked comparison of Claude's C7 cut against Tim's final.
