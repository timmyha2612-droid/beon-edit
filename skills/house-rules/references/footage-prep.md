# Footage Prep first [Tim, 9 Nov 2026]

Tim's Footage Prep app scores, flags and picks selects from every shoot. It goes first on **every footage
task** (sorting, B-roll picks, A-roll angle and take choices, grade groups), not only B-roll.

## 1. Is it reachable?

At the start of the first footage task in a session, look for its MCP tools (ToolSearch `footage-prep`;
they are named like `library_shoots`, `inspect_folder`, `import`, `progress`, `selects`, `clips`).

- **Reachable:** `library_shoots` (query = client or shoot). Not there: `inspect_folder`, then `import`
  (client name, `watch: false`), and wait on `progress` until analysis is done. Never pass `switch_shoot`
  unless Tim asked (opening a shoot switches the app for him).
- **Not reachable** (tools missing, server down, app not installed on this machine): tell Tim in one line
  and carry on, don't wait for an answer:
  > Footage Prep isn't reachable here, so I'm using the fallback (ingest.py + contact sheets) for <shoot>. Scores will be Claude's own until the shoot is in the app.

  Fallback = `shotlog/scripts/ingest.py` (probe, gyro shake windows, keyframes, contact sheets) plus the
  B-roll window scoring in `broll_auto.py`. Record `footage_prep.available: false` in the shot log and the
  job card, so the next session retries the app.

## 2. What to take from it

| Footage Prep | Used for |
|---|---|
| `selects` (`in_frame`/`out_frame`, score) | The only ranges B-roll is picked from |
| flags (`shaky`, `whip`, `motion_blur`, `blocked`) | Excluded from picks |
| `metrics.stability`, jitter, shaky_frac (gyro / rtmd) | Ranking; >= ~0.75 preferred, < ~0.65 only when it's the only shot for the line (flag it) |
| `auto_tier` / Tim's tier (`hero`, `reject`) | Hero first; never use `reject` |
| `movement` (locked / steady / pan / tilt / pan_tilt / gimbal / handheld) | Gyroflow preset, static-shot Dynamic Zoom, move flow |

## 3. Priority and the second look

- Footage Prep's scorer wins when it disagrees with Claude's own measurements for **choosing** a shot.
- Its winners still get checked twice. Before placing, the editor checks the subject and people match
  the line, the framing works in 9:16, and the stretch actually used (often 2-3 s of a 3-12 s select) is
  smooth at the slot's speed (`broll_auto.py` measures that stretch). After placing, the qa-manager agent
  checks again with fresh eyes (broll checklist B-09, B-20, B-21), and its judgement calls get the
  qa-verifier's second look.
- Report which app selects were used (clip, frames, score, stability) and any you overrode, with why.

## 4. Into the shot log

Merge, don't replace: the shot log keeps one block per source, so it's always clear who said what
(shotlog skill, `footage_prep` and `claude` blocks per clip). Stabilisation renders inside the app are
Tim's to start; list the shots that need them.
