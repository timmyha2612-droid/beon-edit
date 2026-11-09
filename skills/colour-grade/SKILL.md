---
name: colour-grade
description: "This skill should be used when colour grading a Beon Media edit in DaVinci Resolve with Tim's template, or when reading or learning his grades: \"grade C7\", \"apply the template\", \"white balance these shots\", \"fix the exposure\", \"learn my colour grading\". Covers the 9-node template, scope-led white balance and HDR exposure, grading by scene, the light (crash-safe) grading method, and reading/writing grades through DRX/DRT.\n"
metadata:
  version: "0.2.1"
---

# Colour grade (Tim's workflow)

> **Job card first.** Before any work in this skill, make sure this job has a job card (house-rules, "Grill first"). No card: stop and run the grilling with Tim. The `job_guard` hook blocks Resolve edits without one.

## The template

- Start every shot from Tim's template still at Temp 0, Tint 0 and HDR Global 0. Follow the node tree exactly; never add, remove or reorder nodes.
  - Namir projects: gallery still "1.1.1".
  - Arriva project: gallery still labelled "Tim's Color Grading Node Tree #1_1" (exports as `still_I.Still.drx`). It holds Temp 70 and HDR −1.00, so reset those to 0/0/0 before use.
- Nodes (9): CST In (S-Gamut3.Cine/S-Log3 → DaVinci Wide Gamut/Intermediate) · Noise Red · Balance · HDR · Contrast (custom curves) · Sat · Sharpen · CST Out (→ Rec.709 Gamma 2.4) · LUT (Tim's Hollywood Look 14).
- Only touch two things: Balance (Temp and Tint) and HDR (Global wheel exposure).
- Contrast curve: only on sunny white facades, flattening the top so whites roll off instead of bunching.
- Never use auto white balance.

## White balance (Balance node, Temp and Tint)

- Read the vectorscope and centre the "colour meat" (the neutral pixels: walls, ceilings, white surfaces).
- Measure on the final output (after CST Out and LUT). Neutral pixels: low chroma (|Cb,Cr| < 40 on the 10-bit scale) and Y > 200. Rec.709: Y = .2126R + .7152G + .0722B, Cb = (B−Y)/1.8556, Cr = (R−Y)/1.5748. Temp moves the blue↔amber axis, Tint the green↔magenta axis.
- Tim's finished neutrals land a touch warm and magenta (about Cb −5, Cr +5), not dead centre.
- In mixed or complicated light the meat can sit in the centre and the shot still looks off. Sanity-check whites and skin by eye on a thumbnail sheet; when unsure, flag the shot for Tim.
- There are no fixed numbers. Measure every time. As a sense of scale only: C7 warm-lit interiors needed strong cooling plus a little positive Tint to remove green; daylight exteriors needed little or none.
- Bedrooms lit with yellow light stay slightly yellow to match the room, not too much. Hero exterior facades keep some warmth.
- When fewer than ~5% of pixels are neutral (dark gym, kitchen under downlights, lift lobby), the measured balance is unreliable: judge by eye and flag it.

## Exposure (HDR node, Global)

- Set Global so the main white surface sits around 896 on the waveform (Tim's grades land about 880–910), depending on the shot.
- Judge the meat of the footage, never the peak: ignore small hot spots (< 0.5% of the frame), windows, skylights, sky, practicals and sun patches. Pick the surface on the thumbnail; don't trust the top of the waveform alone (on the Arriva lobby and yard shots it is the windows).
- Dial in every shot to the target. Don't skip a shot because it's already close.

## Grade by scene

- Grade one hero shot per room or lighting set (and per camera), copy that grade to every shot in the same room and light, then nudge exposure on the shots that stand out (C7: six interiors share one white balance).
- The same clip can need a different grade in a different concept: match its neighbours in this edit.
- Interview A-roll gets one grade for the whole interview; consistency matters more than hitting a number. Namir: Tim keeps the template on A-roll. Arriva: Tim sets the A-roll grade per concept (see `references/arriva-notes.md`). Re-check only where the light changes during the take.

## Keep Resolve light (what broke on Arriva Oct C1/C3)

- **Never apply a DRX twice to the same clip.** On 15 Oct, a script applied six test grades in a row to one clip. The first apply worked; the second, onto the now-graded clip, froze Resolve and it closed. Single applies on fresh clips take 0.1–0.3 s.
- To redo a graded clip: `GetNodeGraph().ResetAllGrades()` in its own call, then apply once. Or `CopyGrades` from a correctly graded clip.
- **Never measure inside Resolve's Python.** The old method decoded 4K frames and looped over pixels in plain Python (ResolvePython has no numpy), in back-to-back 50 s batches with a LUT export per clip. That tied up Resolve and the Mac and made Resolve lag. `meas.py` and `batch.py` are kept for reference only; don't run them.
- Do all measuring in the device VM with numpy (`scripts/measnp.py`, `scripts/calib.py`): 20 hero frames × 4 LUTs take about 20 s.
- One Resolve action per call (apply, copy, export LUT, export DRT), short calls, nothing heavy in a loop. If Tim is working in Resolve, say before you start.
- Export LUTs only for calibration (4) and one per scene for verification, never one per clip.

## Order of work

1. Confirm Tim wants Claude to grade, which timelines, and whether he is in Resolve.
2. **Template DRX:** `GalleryStillAlbum.ExportStills(stills, folder, "still", "drx")` into a non-Dropbox scratch folder; find the 9-node still with `scripts/grade_read.py`-style decoding.
3. **Calibration DRX:** `scripts/drxw.py TEMPLATE.drx OUT.drx TEMP TINT HDR` writes base (0 0 0), t200 (200 0 0), n20 (0 20 0) and hm1 (0 0 -1).
4. **Calibrate once on a scratch timeline:**
   - Create a scratch timeline (e.g. "zz Claude grade test") with four fresh 1 s clips.
   - In one call per clip, apply one calibration DRX once and `ExportLUT(resolve.EXPORT_LUT_33PTCUBE, path)`.
   - Delete the scratch timeline afterwards (it's Claude's, not Tim's).
5. **Measure in the VM:**
   - Group shots by room, light and camera, and pick a hero frame per group (source path, time, the item's Pan).
   - Run `scripts/calib.py jobs.json LUTDIR OUTDIR`. It measures with a fixed neutral mask, solves Temp/Tint for Cb −5 / Cr +5 and Global for ~896 on the main near-white surface, and writes a thumbnail sheet.
   - Look at the sheet, then apply Tim's rules: A-roll consistency, warm bedrooms and facades, windows ignored, flags where neutrals are scarce.
6. **Write grades:** `drxw.py` writes one DRX per group, plus one per exposure outlier.
7. **Apply each clip's grade once:**
   - For each group, `ApplyGradeFromDRX(path, 0)` on one clip, then `CopyGrades([...rest of the group])` in the next call.
   - Outliers get their own DRX applied once instead of the copy.
8. **Verify:**
   - Export the DRT and run `grade_read.py` to confirm the values.
   - Export one LUT per group and re-measure with `measnp.py`.
9. **QA:** run the QA loop (qa-loop skill, stage `grade`) before Tim sees it.
10. **Report a table:** shot | group | Temp | Tint | Global | neutral Cb/Cr | surface level | flags, plus the QA result. Tim checks.

## Reading and writing grades (no colour API for Temp/Tint/HDR)

- Read without touching: `timeline.Export(path, resolve.EXPORT_DRT)`, then `scripts/grade_read.py file.drt [template_body.bin]` (needs `scripts/drxlib.py`). Per clip it prints Temp, Tint, HDR Global and which other nodes differ from the template.
- Grade storage: DRX/DRT `<Body>` hex → byte 0 = 0x81, bytes 1+ = zstd → protobuf-like tree. Node records are field 7 (label in field 6, params in field 9 → 1[1] → 6 → 2[1] → field-3 param entries).
  - Temp = param 2248147221, Tint = param 2248147222. Each entry is `(1: id, 2: {1: float})` in panel units; absent = 0.
  - HDR Global exposure = param 2248147717 → field 2 → 16 → zone message with `1: "Global"`, `2: float` (the panel value).
  - Contrast curves = params 2248148230–33 (Y, R, G, B), six points on 0–1023.
- Writing works (proven 15 Oct on Arriva). Decode, set the floats, and insert a Tint entry after Temp when it's absent. Re-encode: the round trip is byte-exact. Then zstd-compress, prefix 0x81, replace `<Body>` and apply. Read back via DRT: Temp 200 / Tint 0 / HDR 0 came back exactly. `scripts/drxw.py` does all of this.
- Other API: `Graph.ApplyGradeFromDRX(path, gradeMode)`, `Graph.ResetAllGrades()`, `TimelineItem.CopyGrades(items)`, `TimelineItem.ExportLUT(type, path)`, `Graph.SetLUT`, `SetCDL`, `GetNodeLabel`, `GetToolsInNode`.

`references/learned-from-c6-c1-c7.md` has the full analysis of Tim's Namir grades. `references/arriva-notes.md` has the Arriva grades, calibration numbers and the 15 Oct crash details.
