#!/usr/bin/env python3
"""Pick the steadiest source window for a B-roll slot from the gyro cache (no decoding, instant).
usage: bestwin.py GYRO_DIR CLIP REC_SECONDS [--speed 100] [--lo 1.0] [--hi -1.0] [--k 3] [--avoid 6.0-8.5,...]
  GYRO_DIR  cache from shotlog/scripts/ingest.py (gyro/<CLIP>.json: win = [[t, shake, speed], ...])
  CLIP      file stem, e.g. C1087
  REC_SECONDS  how long the shot plays on the timeline; at --speed 60 it uses 0.6 x that of source
  --lo/--hi    usable source range (default: skip the first and last 1 s; --hi negative = from the end)
  --avoid      source ranges already used in this series (shot log usage) - never overlapped
Ranks windows by mean shake (deg/s, RMS of gyro minus its 0.4 s average), then max, and prints the
top --k non-overlapping candidates with tier (pass < 0.35, check 0.35-0.6, fix > 0.6) and how even
the camera speed is (cv of speed: > 0.3 = the move speeds up or slows down inside the shot).
Then render a motion card on the winner before placing it (gyro can't see focus pulls or resets)."""
import argparse, json, os
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("gyro"); ap.add_argument("clip"); ap.add_argument("rec", type=float)
ap.add_argument("--speed", type=float, default=100); ap.add_argument("--lo", type=float, default=1.0)
ap.add_argument("--hi", type=float, default=-1.0); ap.add_argument("--k", type=int, default=3)
ap.add_argument("--avoid", default="")
a = ap.parse_args()
j = json.load(open(os.path.join(a.gyro, "gyro", a.clip + ".json")) if os.path.isdir(os.path.join(a.gyro, "gyro"))
              else open(os.path.join(a.gyro, a.clip + ".json")))
if "win" not in j:
    raise SystemExit(f"{a.clip}: {j.get('err', 'no gyro windows')}")
Wn = np.array(j["win"], float)
t, sh, sp = Wn[:, 0], Wn[:, 1], Wn[:, 2]
need = a.rec * a.speed / 100
hi = j["dur"] + a.hi if a.hi < 0 else a.hi
avoid = [tuple(float(v) for v in r.split("-")) for r in a.avoid.split(",") if r]
tier = lambda v: "pass" if v < 0.35 else "check" if v < 0.6 else "fix"
c = []
for s in np.arange(a.lo, hi - need + 1e-6, 0.1):
    if any(s < y and s + need > x for x, y in avoid):
        continue
    m = (t + 0.5 >= s) & (t + 0.5 <= s + need)          # window centres inside the shot
    if not m.any():
        m = np.abs(t + 0.5 - (s + need / 2)) <= 0.5
    if not m.any():
        continue
    mean_sp = float(sp[m].mean())
    even = float(sp[m].std() / mean_sp) if mean_sp > 1 else 0.0
    c.append((round(float(sh[m].mean()), 3), round(float(sh[m].max()), 3), round(float(s), 2), round(mean_sp, 1), round(even, 2)))
c.sort()
best = []
for x in c:
    if all(abs(x[2] - b[2]) >= max(0.5, need * 0.8) for b in best):
        best.append(x)
    if len(best) >= a.k:
        break
print(f"{a.clip}: need {need:.2f}s of source for {a.rec:.2f}s at {a.speed:g}%  (clip {j['dur']}s, median shake {j.get('shake_med')})")
for mean, mx, s, v, ev in best:
    print(f"  in {s:6.2f}  out {s + need:6.2f}  shake mean {mean:.3f} max {mx:.3f} [{tier(mean)}]  "
          f"cam speed {v:5.1f} deg/s{'  uneven ' + str(ev) if ev > 0.3 else ''}")
if not best:
    print("  no window fits: shorten the shot, slow it down, or use another clip")
