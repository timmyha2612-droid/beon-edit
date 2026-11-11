# Tim's B-roll rulebook

The one list of how Tim handles B-roll. The B-roll work follows it, and the checks (`broll_gate.py`,
the motion cards, and the qa-manager agent with its checklist `qa-loop/references/checklists/broll.md`) judge against it. If a rule here and a script disagree,
the rule wins and the script gets fixed. Client profiles can override a rule for that client.

Tags: [Tim] said or confirmed by Tim (source, date) · [inferred] measured, not confirmed · default = starting
value the learning loop adjusts from Tim's corrections.

## 1. Every shot records why [Tim, 9 Nov 2026]

Each placed shot carries a reason record (`why` in the plan row from `broll_auto.py`, kept in the shot log
`plans/`):

| Field | Example |
|---|---|
| `line` | "the finishes are all custom" |
| `move` | "slow push-in (Footage Prep: gimbal)" |
| `speed` | "60%: matches the push speed of B3 and B5" / "100%: no reason to slow" |
| `gyro` | "preset 0.5 + horizon lock: gimbal push" / "no gyro track: listed for Tim" |
| `pan` | "Pan centres the stone benchtop (x 0.62)" |
| `dynamic_zoom` | "static shot: zoom in 4% onto the tapware" (static shots only) |

Checks compare each reason with this rulebook. When Tim changes a shot, the reason shows exactly what
he overrode, and the learning loop learns from that.

## 2. Speed [Tim, 9 Nov 2026]

- **Default 100%.** Slow down (anywhere from 48% to 100%) only with a valid reason:
  1. `shake`: calm shake or jerkiness Gyroflow didn't fully fix. Never on a shot Footage Prep calls
     `locked`/`steady` with gyro `metrics.stability` >= 0.95: the camera didn't move, so whatever moves in
     frame is the subject (people talking or turning, cars), not shake. Those play at 100% [10 Nov 2026,
     Hired Home C0168 was slowed to 48% for Nicole turning on a locked-off shot].
  2. `match`: match the camera speed of the shots before and after (be versatile: a fast push between two
     slow ones gets slowed so the run feels even).
  3. `stretch`: the speaker would otherwise stay on screen longer than 4 s and there's no more B-roll.
  4. `hero`: a hero or mood shot that should breathe (closing exterior, breathing gap).
- 25p footage on a 24p timeline plays at 96% with Nearest retime (`cadence`), so every frame plays once.
- **Limits** (defaults):
  - People talking: no slower than ~80%. Slowed mouths look weird.
  - People moving, not talking: no slower than ~60%.
  - Everything else: down to 48%.
  - Below 48% only for 100 fps footage (down to 25%).
- Retime: Optical Flow on every slowed shot; Speed Warp Better below 48%.
- The Namir and Arriva profiles used to say "48% first"; they now follow this rule, with a note to ask
  Tim whether those clients keep the old habit. Until he answers, use this rule.

## 3. Gyroflow [Tim, Mill + Green, Oct-Nov 2026]

- Stabilise every handheld B-roll shot that has gyro data (Sony rtmd track). Drone shots are already smooth:
  skip. No gyro track: list the shot for Tim.
- Presets by move (Footage Prep's `movement` label wins when given):

  | Move | Smoothness | Lock |
  |---|---|---|
  | Static / locked | 0.3 | Horizon lock 100 |
  | Slow push, slide, orbit, gimbal | 0.5 | Horizon lock 100 |
  | Tilt reveal | 0.5 | Roll only |
  | Handheld follow, walk-and-talk | 0.8 | No lock |

- Reframe first, Gyroflow second, then re-centre on the stabilised clip (the stabilisation crop shifts the frame).
- Keep the stabilised version even when it crops ~1.4x; Tim prefers it to a wider shaky shot (Green C3 C9995).
  The zoom limit (section 5) still applies: past the limit, re-pick a calmer window instead.
- If Gyroflow makes a shot shakier than the camera's own stabilisation, use the original (Green C1345).
- Horizon lock levels the gyro horizon, not the room: check the verticals after (section 5).

## 4. Movement [Tim]

- No jerky movement anywhere in the shot: no shake, no speed changes inside a move, no starting or ending
  mid-ease, no reversals (a videographer reset). Motion card flags: `uneven` (cv > 0.3), `mid-ease`, `reversal`.
- Keep moves whole: skip the first and last ~1 s of a clip; no focus pulls or exposure jumps.
- Flow through a run: never two opposite moves back to back; similar camera speeds (use `match` speed for this);
  cut on motion between moving shots; the last shot settles before cutting back to the speaker.
- Direction across a run: decided case by case from what the shoot has.
- The same room twice in a row is fine only from a different angle [Tim, 9 Nov 2026].

## 5. Framing and zoom [Tim]

- 9:16: slide the window with Pan so the subject the line is about sits in the middle. Moving shot: centre it
  mid-shot, then check the first and last frames still hold it. Empty room: frame the strongest feature or the
  leading lines. Confirm with one rendered still per timeline (Pan units differ per timeline).
- Straight verticals, level floor: `level_check.py` on a still, then `RotationAngle` and the **smallest** zoom that
  hides the corners. Strong keystone exteriors stay as shot.
- **Never zoom far enough to pixelate** [Tim, 9 Nov 2026]. Count the total: Resolve zoom × Gyroflow crop ×
  Dynamic Zoom peak.

  | Source | Fine | Check sharpness on a rendered still | Fail |
  |---|---|---|---|
  | UHD (2160 high) | up to 1.25x | 1.25-1.4x | over 1.4x |
  | 1080 high | up to 1.0x | 1.0-1.15x | over 1.15x |

  A UHD frame framed for 9:16 at zoom 1.0 already uses its full height (2160 px into 1920), so past ~1.12x the
  picture is being enlarged. Over the limit: re-pick, or less stabilisation.
- **Static shots always get a slight Dynamic Zoom** [Tim, 9 Nov 2026]: about 3-5% over the shot, in on a detail or
  feature the line names, out on a reveal, a wide or a list. Inside the zoom limit. The Resolve API can't create it;
  use the DRT clone method from aroll-cut ("Slow Dynamic Zoom on long holds") and test it on one timeline first.

## 6. Placement [Tim]

- **The speaker stays on screen at most 4 s at a time** [Tim, 9 Nov 2026], unless the B-roll is used up and
  everything is already stretched and slowed. Exceptions: jokes Tim chose to keep on camera (job card), the
  speaker's first introduction (name and role super). Anything else over 4 s goes to Tim.
- Open each speaker turn on camera ~1.5-2 s (fits inside the 4 s).
- Shots ~2-3 s, changing on sentence breaks. Open with 1-1.5 s of B-roll before the first line.
- Nothing on screen for under ~1 s (24 frames) between two other shots: no flash of the speaker between
  B-roll shots, no B-angle sliver. A B-roll shot covering an A-roll cut runs to that cut frame or past it.
- **B-roll edges land exactly on A-roll cuts, never 1-3 frames off** [Tim, Hired Home Nov S2 C4, 11 Nov 2026: "it will
  glitching"]. A B-roll shot that ends one frame before the cut flashes the outgoing speaker shot for a frame, even when the
  next A-roll piece is the same camera clip. Holds after every recut, re-place or trim: recut_plan.py keeps edges on the
  joins, and broll_gate.py checks slivers per timeline item (never merged) and names the B-roll edge to move.
- B-roll is video only, hard cuts, on V2, named `<slot> <clip>` (e.g. `R4 0331`).
- Breathing gap (hero shots, music only) when the edit needs it; size it to the music.
- Outro: Tim usually runs B-roll past the last word into the end card.

## 7. Matching the words [Tim, Mill, 9 Nov 2026]

- Literally relevant: "the finishes" = joinery, stone benchtop, tiles, tapware; never a toilet first.
- Exact match when there is one (what's named, the person talked about); otherwise whatever fits without
  implying something false. A line about a specific room or light shows that room if it's shown at all.
- Use the establishing shots: over the line that names the place, on level or location changes, and as the
  closing wide into the end card.
- People: confirm identity (shot log people registry); first and last ~0.3 s not on an open mouth or grimace;
  goofy moments only if the job card allows them.
- Light spots: a small blown highlight is fine; reject or shorten when it's a big part of the frame.

## 8. Where the shots come from

Footage Prep selects first (`house-rules/references/footage-prep.md`); the smoothest stretch of the select at
the slot's speed (`broll_auto.py`); unused windows before reused ones (shot log `usage`).
