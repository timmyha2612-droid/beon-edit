# QA checklist: A-roll (interview cut)

Sources: aroll-cut skill (sections 2, 2a, 2b, 3, 4), client profile, job card.
Get: the current timeline's V1/A1 items (source ranges, Zoom/Pan/Tilt), the cut list, transcripts in the
shot log, and a proxy render (finish-pass `resolve_proxy_render.py`, only while the editor isn't in Resolve).

| ID | Check | How | Kind | Pass when |
|---|---|---|---|---|
| A-01 | Story follows the job card beats, right answers used | job card vs the cut's transcript | creative | the card's beats in order; anything else goes to the editor |
| A-02 | Running time vs the target length | timeline length vs job card | hard | within the target the card states |
| A-03 | No clipped words at piece edges | `cut_review.py` sheets, 10 ms energy at every edge | hard | no word energy cut at an in/out |
| A-04 | No um/uh/stutter/false start left inside a used piece | `filler_scan.py` on the used ranges; tiny-window transcript of each flag | hard | nothing flagged "likely filler" unless the report lists it as left in on purpose |
| A-05 | No breath or mouth click before the first word | energy contour of the first ~0.8 s of each piece | hard | piece starts ~0.05 s before the word |
| A-06 | Air at joins | `cut_air.py` *(calibrating)* | hard | 0.20-0.32 s across a join (client profile may be tighter: Green 0.00-0.27) |
| A-07 | Speech flows, doesn't sound rushed or stitched | listen to the proxy around every removal and join | judgement | natural phrasing, no pitch jump or missing breath |
| A-08 | Tone at joins | F0 of each piece's tail vs the next piece | judgement | no still-talking tone into a new thought |
| A-09 | Speaker centred in every shot, one Zoom/Tilt per framing level | read back every V1 item; one still from the middle of each clip, centre of mass of the person vs the wall | hard | same Zoom and Tilt at each framing level; the person within 1% of frame centre in every clip (2% inside a run); back-to-back clips at the same zoom share one Pan |
| A-10 | Speaker centred in the delivery frame *(9:16)* | rendered stills with a centre line | hard | body centre within ~2-3% of frame width |
| A-11 | Jump cuts | `learn-from-tim/scripts/jumpcut_check.py`, cut_review suggestions | judgement | each visible jump is covered, a Smooth Cut, or small (<~1% head move) and the audio flows |
| A-12 | Smooth Cuts don't morph | stills of each Smooth Cut, face and mouth | judgement | no warping |
| A-13 | Adjustment clips (Dynamic Zoom) match the clip under them | GetStart/GetEnd of each adjustment clip vs the V1 item | hard | exact frame match |
| A-14 | A1 enabled, no clipped audio used | GetIsTrackEnabled on the current timeline; cut_pieces clipped-sample report | hard | A1 on; clipped channel avoided or reported |
| A-15 | Whole script reads clean | read-only: audio of the proxy render (`ffmpeg -i PROXY -vn -ac 1 -ar 16000 cut.wav`), `whisper-cli -m <editor.json tools.whisper.model> -oj -of OUT cut.wav`, read it start to finish (no Whisper: transcribe a copy of the audio another way, else not_checked) | hard | no clipped words, no fillers left |
