#!/usr/bin/env python3
"""Choose a 9:16 Pan by eye in one look: the full 16:9 frame with a Pan ruler and the vertical windows drawn on.
usage: framing_sheet.py CLIP T OUT.jpg [--pans -400,0,400] [--zoom 1.0] [--tilt 0] [--x 0.62,...] [--times 2.0,4.5]
                        [--root SHOOT] [--card JOB_CARD.md | --size 1080x1920]
  CLIP T     source file and time (s); --times adds more rows (e.g. start and end of a moving shot).
             With --root, CLIP can be a stem or a path relative to the shoot (A001/C0012.MP4), any extension.
  --card/--size  delivery size (default 1080x1920). The sheet is meant for 9:16 deliveries; other sizes
             draw their own window the same way (fill = source scaled to cover the delivery frame).
  --pans     windows to draw (Inspector Pan values at a 1080x1920 timeline)
  --x        subject centre(s) as a fraction of the frame width: prints the Pan that centres them
Pan maths (1080x1920 timeline, UHD or HD 16:9 source, scale-to-fill): the source is drawn
1920/H*zoom times, so Pan = (0.5 - x) * W * 1920/H * zoom; at Zoom 1 on UHD that is (0.5 - x) * 3413,
and the window can slide +-1166 before it runs off the frame. Check both ends of a moving shot:
a pan that frames the start can lose the subject by the end.
--space fit: print and draw fit-space Pan, for timelines that report scaleToFit but render fill
(Pan = (0.5 - x) * 1080 at Zoom 1 on UHD; Green Oct 2026). Verify with one rendered still."""
import argparse, subprocess
from _beon import add_delivery_args, delivery, find_clip

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("clip"); ap.add_argument("t", type=float); ap.add_argument("out")
ap.add_argument("--pans", default="0"); ap.add_argument("--zoom", type=float, default=1.0)
ap.add_argument("--tilt", type=float, default=0.0); ap.add_argument("--x", default="")
ap.add_argument("--times", default="")
ap.add_argument("--space", choices=["fill", "fit"], default="fill")
ap.add_argument("--root", help="shoot or card folder CLIP is relative to")
add_delivery_args(ap, fps=False)
a = ap.parse_args()
import numpy as np
import cv2
DL = delivery(a); OW, OH = DL["width"], DL["height"]
if a.root or not __import__("os").path.isfile(a.clip):
    a.clip = find_clip(a.root, a.clip)
r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                    "-of", "csv=p=0", a.clip], capture_output=True, text=True)
W, H = [int(v) for v in r.stdout.strip().split(",")[:2]]
s = max(OW / W, OH / H) * a.zoom                           # fill: 1920 / H on a 16:9 source at 1080x1920
u = min(OW / W, OH / H) / max(OW / W, OH / H) if a.space == "fit" else 1.0   # Pan unit -> fill-space pixels
DW = 1280; k = DW / W; DH = int(H * k)
for x in [float(v) for v in a.x.split(",") if v]:
    p = (0.5 - x) * W * s * u
    print(f"subject at x={x:.2f} -> Pan {p:+.0f}" + ("  (beyond the frame edge: zoom in or accept off-centre)" if abs(p) > (W * s / 2 - OW / 2) * u else ""))
rows = []
for t in [a.t] + [float(v) for v in a.times.split(",") if v]:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", a.clip, "-frames:v", "1", "-vf", f"scale={DW}:{DH}",
                          "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    im = np.frombuffer(raw[:DW * DH * 3], np.uint8).reshape(DH, DW, 3).copy()
    lim = (W * s / 2 - OW / 2) * u
    step = 200 if u == 1.0 else 50
    for pv in range(-int(lim // step) * step, int(lim) + 1, step):
        cx = int((W / 2 - pv / u / s) * k)
        cv2.line(im, (cx, DH - 14), (cx, DH), (255, 255, 255), 1)
        cv2.putText(im, f"{pv}", (cx - 14, DH - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (255, 255, 255), 1, cv2.LINE_AA)
    for i, pv in enumerate(float(v) for v in a.pans.split(",") if v):
        cw, ch = OW / s * k, OH / s * k
        cx = (W / 2 - pv / u / s) * k; cy = (H / 2 + a.tilt / s) * k
        col = [(0, 255, 255), (0, 255, 0), (255, 128, 0), (255, 0, 255)][i % 4]
        cv2.rectangle(im, (int(cx - cw / 2), int(cy - ch / 2)), (int(cx + cw / 2), int(cy + ch / 2)), col, 2)
        cv2.putText(im, f"Pan {pv:g}", (int(cx - cw / 2) + 4, int(cy - ch / 2) + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, col, 2, cv2.LINE_AA)
    cv2.putText(im, f"t={t:.2f}s zoom {a.zoom:g}", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    rows.append(im)
cv2.imwrite(a.out, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 80])
print("wrote", a.out)
