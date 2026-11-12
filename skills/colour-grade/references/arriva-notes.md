# Arriva grading notes (read 15 Oct 2026)

## Template

- Gallery album "Stills 1" holds 8 stills. The 9-node tree is labelled "Tim's Color Grading Node Tree #1_1". `ExportStills(..., "drx")` writes it as `still_I.Still.drx`.
- Values in that still: Temp 70, Tint absent (0), HDR Global −0.9984. Reset to 0/0/0 before using it as the start point.
- Its nodes: CST In, CST Out, Balance, Contrast, HDR, LUT, Sat, Noise Red, Sharpen.
- The other stills are older 7-node trees (no Noise Red or Sharpen) or a "False Color Check" tree. Don't use them.

## Tim's Arriva grades (Temp / Tint / HDR Global)

| Timeline | A-roll | B-roll |
|---|---|---|
| C2 Amrita Testimonial v01 | 60 / +0.5 / −1.315 (one grade for all pieces, one piece −1.678) | 60 / +0.5 / −1.315; outliers at −0.838 and −0.895 |
| Sep C3 | −80 / −6.5 / −0.998 | sets of −80 / −6.5 / 0, 50 / −2 / 0, −10 / −2 / 0, 330 / −5 / 0 |
| C4 | −230 / 0 / −1.0 (multicam) | −310 / +14 / −1.5 for most; outliers −460 / +14 / −0.173 and HDR −1.231, −0.694 |

On Arriva, Tim does move the A-roll grade per concept (one grade for the whole interview). HDR Global often sits around −1 to −1.5, so measure every time; don't assume 0.

## Calibration (Oct shoot, Rahul cam + Liam FX3, template at 0/0/0)

Measured on 20 hero frames, 9:16 crop, 33-point LUTs exported from Resolve:

| Change | Neutral shift (Cb, Cr) | Luma |
|---|---|---|
| Temp +200 | about (−22, +16), range (−11…−27, +10…+21) | |
| Tint +20 | about (+19, +32), range (+8…+22, +17…+40) | |
| HDR Global −1 | | p50 −150…−187; waveform top −23…−151 (windows barely move) |

Effects are close to linear. Solve the 2×2 system for Temp/Tint per hero, then check it by eye. Starting points measured for Oct C1/C3 (not applied) are in the shoot's `_shotlog/plans/grade_starting_points.json`.

## The 15 Oct crash, step by step

1. One `run_script_unsafe` call looped six DRX applies onto the same multicam A-roll item, with `ExportLUT` after each.
2. Apply 1 (t200) and its LUT worked. The item read back Temp 200 / Tint 0 / HDR 0 in the DRT, which proved the writer.
3. Apply 2 (tm200) on the same, now-graded item never returned. Every scripting call timed out after that, and Resolve closed; Tim reopened it. Nothing was lost (the timelines were saved).
4. Afterwards: three applies on three fresh clips of a scratch timeline took 0.12–0.29 s each, and each `ExportLUT` about 0.15 s.
5. Rule: one apply per clip, nothing heavy in loops inside Resolve, measure outside Resolve (numpy).
