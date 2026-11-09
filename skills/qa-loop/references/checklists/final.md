# QA checklist: final pass (the whole edit, on the proxy render)

Sources: finish-pass skill, the stage checklists, client profile, job card.
Get: a fresh proxy render of the whole timeline (`finish-pass/scripts/resolve_proxy_render.py`, only while
Tim isn't in Resolve) and `finish-pass/scripts/render_check.py PROXY OUT --cuts <edit points>`.

| ID | Check | How | Kind | Pass when |
|---|---|---|---|---|
| F-01 | No black or frozen frames, no 1-2 frame slivers | render_check | hard | none |
| F-02 | No pops or level jumps at cuts, no long silences | render_check | hard | none flagged |
| F-03 | Loudness and true peak | render_check | hard | the client's target (ask if the profile has none) |
| F-04 | Delivery format | render settings readback | hard | 1080x1920 24p vertical (or what the job card says) |
| F-05 | Hand-over state | track readback | hard | V1/A1 interview, V2 B-roll, A3 free for music (or Tim's music untouched), A1 enabled unless Tim moved dialogue to A2, Blue marker on the break |
| F-06 | End card | V1/V2 above everything, right asset and length (Namir: Reel Tail, 65 f) | hard | as the client profile |
| F-07 | Every stage passed QA | `qa_round.py status QA_DIR` | hard | aroll, broll, grade (if graded), subtitles (if subbed) PASS, or settled by Tim (ESCALATE answered, PARTIAL gaps told to him) |
| F-08 | Watch-down | watch the proxy start to finish | judgement | nothing jarring that the stage checks missed (note time codes) |
| F-09 | Tim's render settings restored | render preset list | hard | the temporary preset and jobs removed |
