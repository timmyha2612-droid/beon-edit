# QA checklist: colour grade

Sources: colour-grade skill, client profile (e.g. Arriva moves the A-roll grade per concept).
Get: DRT export + `colour-grade/scripts/grade_read.py --card <job card>`, one LUT per grade group, hero frames
measured with `colour-grade/scripts/measnp.py --card <job card>` outside Resolve (on the Mac, or in the device
VM if run_env is device-vm; never measure inside Resolve).

| ID | Check | How | Kind | Pass when |
|---|---|---|---|---|
| G-01 | Template node tree untouched | `grade_read.py file.drt template_body.bin`: decode the template body from the template still DRX (colour-grade "Order of work" step 2); it lists the nodes that differ from the template. No template body: not_checked | hard | only Balance (Temp/Tint) and HDR Global changed (Contrast only on sunny white facades) |
| G-02 | No auto white balance | grade_read's "other nodes differ" list for the Balance node beyond Temp/Tint; if that can't tell, not_checked | hard | Balance holds only Temp/Tint |
| G-03 | Neutrals land on Beon's target | measnp on each group's hero frame *(calibrating)* | hard | neutral Cb ~ -5, Cr ~ +5 (Beon's warm-magenta touch); client profile first (Arriva moves per concept) |
| G-04 | Exposure on the main white surface | measnp *(calibrating)* | hard | ~880-910 on the waveform, ignoring windows, sky, practicals, small hot spots |
| G-05 | Scene consistency | grade groups by room/light/camera | hard | shots in the same room and light share a grade (outliers only nudge exposure) |
| G-06 | A-roll consistent across the interview | grade_read on V1 | hard | one grade per interview (unless the light changes) |
| G-07 | Scarce neutrals flagged | measnp neutral pixel share | hard | < ~5% neutral pixels -> flagged for the editor, not trusted |
| G-08 | Looks right to the eye | thumbnail sheet: whites, skin, bedrooms slightly warm, facades keep warmth | judgement | nothing looks off |
