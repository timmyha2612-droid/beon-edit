# QA checklist: final pass (the whole edit, on the proxy render)

Sources: finish-pass skill, the stage checklists, client profile, job card.
Get: a fresh proxy render of the whole timeline (`finish-pass/scripts/resolve_proxy_render.py`, only while
the editor isn't in Resolve) and `finish-pass/scripts/render_check.py PROXY OUT --cuts <edit points> --card <job card>`.
Delivery = client profile `delivery` + job card Delivery line (`beon_config.delivery(card)`); Beon default 9:16 1080x1920 24p.

| ID | Check | How | Kind | Pass when |
|---|---|---|---|---|
| F-01 | No black or frozen frames, no 1-2 frame slivers | render_check | hard | none |
| F-02 | No pops or level jumps at cuts, no long silences | render_check | hard | none flagged |
| F-03 | Loudness and true peak | render_check | hard | the delivery loudness and true peak (render_check flags LOUD ... OFF delivery); none set: ask the editor and write it back to the client profile |
| F-04 | Delivery format | render settings readback; render_check FORMAT flags | hard | the delivery aspect, resolution and fps |
| F-05 | Hand-over state | track readback | hard | V1/A1 interview, V2 B-roll, A3 free for music (or the editor's music untouched), A1 enabled unless the editor moved dialogue to A2, Blue marker on the break |
| F-06 | End card | V1/V2 above everything, right asset and length | hard | as the client profile `end_card` (asset, length_f, music_tail_s) |
| F-07 | Every stage passed QA | `qa_round.py status QA_DIR` | hard | aroll, broll, grade (if graded), subtitles (if subbed) PASS, or settled by the editor (ESCALATE answered, PARTIAL gaps told to them) |
| F-08 | Watch-down | watch the proxy start to finish | judgement | nothing jarring that the stage checks missed (note time codes) |
| F-09 | The editor's render settings restored | render preset list | hard | the temporary preset and jobs removed |
