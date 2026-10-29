# Tim's colour grading: what I learned (C6, C1, C7, read only)

> Tim's corrections (15 Oct 2026): there are no fixed Temp/Tint numbers, always measure with the scope (the values below are what C7 needed). Even with the meat centred, complicated light can still be off, so check by eye. Don't skip a shot because it's already close; dial every shot in.

Learned 15 Oct 2026 from Tim's finished grades on Namir Mikha C6, C1 and C7 (142 graded clips). Nothing in the project was changed.

**How:**
- Exported each timeline as DRT and decoded every clip's node graph.
- Exported a 33-point LUT of every clip's grade.
- Applied the LUTs to the source frames with ffmpeg, so I could measure each shot after Tim's grade, and before it using the untouched template (C7 only).
- Checked the method against still 1.1.1: the highlights match within 1 to 6 code values.

## Where the settings live in the grade file

- **Balance node:**
  - Temp is param 2248147221 and Tint is param 2248147222.
  - Both are stored in the same units the panel shows (e.g. −340 / +10). When a setting is missing from the file, it is 0.
- **HDR node:**
  - Global is param 2248147717, zone "Global", field 2.
  - The stored value is the number the panel shows (Simon −0.9984 ≈ −1.00; Namir base −0.0292 ≈ 0).
  - Tim confirmed every shot should start at Global 0. The 1.1.1 still still had −1.00 on it because it hadn't been reset.
  - Rough effect of 1.0: about −150 code values on midtones and about −70 on bright surfaces.
- **Contrast node:**
  - Custom Curves, params 2248148230–33 (Y, R, G, B).
  - Six points each, on a 0–1023 scale.
  - Template points: (71,66) (336,364) (542,659) (795,911) (855,971) (947,986).

## What Tim actually does

1. **Interview A-roll keeps the template.** All 28 Simon pieces are at Temp 0, Tint 0 and the base HDR. The one exception is the piece at 972, where HDR is down 0.56; Tim says he eyeballed that one, so it's not a rule. The white wall stays around 973 and the neutrals stay a little warm (Cb −16). Consistency across the interview matters more than hitting 896.
2. **Grade by scene, then nudge single shots.**
   - One white balance goes on each room or lighting set and is copied across. C7 interiors R8, R9, R10, R12, R14 and R16 all have exactly −340 / +10 / −0.49. In C6, seven pieces from the C0837–C0843 set share −80 / +0.5 / −1.39.
   - Single shots then get their own exposure tweak (R13, G1, R17).
3. **The grade follows the edit, not the clip.** 0325 is −170 / +12.5 in C1 but −340 / +10 in C7. Each one matches its neighbours.
4. **White balance by light type:**
   - Interiors with warm downlights or bounce (neutrals Cb −14 to −29) get strong cooling (Temp −340 to −400), plus Tint +5 to +10 to remove the green.
   - Daylight exteriors get Temp 0 to −170.
   - Hero intro/outro facades (0333, 0329) and the bedroom set (0290, 0294, 0320) keep their warmth: Temp untouched.
   - Tim's reason: bedrooms are often lit with yellow light, so keep them slightly yellow to match the room, but not too much.
5. **Neutrals land a touch warm and a touch magenta, not dead centre.** Across all B-roll after grading:
   - Cb median about −5 (middle half from −12 to +5).
   - Cr median about +5 (middle half from 0 to +10).
6. **Exposure:**
   - The main bright surface (white wall, facade or ceiling) lands around 880–910 when it dominates the frame: IN 899, R2b 903 (he raised this one), R3 877, R4 909, R5 901, R18 892, G2 891, OUT 894.
   - Windows, sky and sun patches are allowed to stay near clipping (R1, R8, R10, R17 at about 950–1000).
   - Scene-graded shots can sit lower (R12 782, R14 734, R16 864).
7. **On very bright sunlit shots he flattens the Contrast curve.**
   - Shots: R4, R5 and R6 (facades) and R7 (the sunlit hallway).
   - He pulls the top points down so whites roll off instead of bunching at the top: 911→868 and 971→932 on the facades, and 911→823 and 971→891 on R7.
   - This is the one node outside Balance and HDR that he changes.
   - Tim's rule: only on sunny white facades, where hard sun makes the whites bunch at the top. Everything else uses Balance and HDR only.

## Where my rule (neutrals to 0,0 and surface to 896 on every shot) would have gone wrong

- I would have cooled and darkened the Simon A-roll. Tim left it alone.
- I would have neutralised every shot on its own. Tim matches whole scenes and keeps hero exteriors and the bedrooms warm.
- My "biggest bright area" measure picks windows on R1, R8, R10 and R17, so I would have darkened those too much.
- I would never have touched Contrast.
- I would have centred the neutrals exactly, where Tim leaves a little warmth.

## How I'll measure next time

- **Highlights:** use the largest near-white surface that isn't clipping and isn't a light source. Leave out windows, sky, practicals, sun patches and spots smaller than 0.5% of the frame. Cross-check against the dense top of the waveform. Target 880–910, but leave it if it's already within about ±50 and looks right.
- **White balance:** use neutral pixels only (low chroma, Y above 200). Target Cb −5 ±8 and Cr +5 ±6.
  - Interiors under warm light: cool them. Bedrooms with yellow light are the exception: leave them slightly warm.
  - Daylight exteriors: only a light correction.
  - Hero facade shots: keep the warmth.
- **Scenes:** grade one hero shot per scene, copy that grade to every shot in the same room and light, then adjust exposure only on the outliers.
- **A-roll:** keep the template. Only change it when the light changes during the take; C1's C0834 A-roll varies Temp from −10 to −170 between segments.
