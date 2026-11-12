#!/usr/bin/env python3
"""Measure air and pauses on an A-roll cut list.
usage: cut_air.py AUDIO.wav CUTS.json      (CUTS = [[src_in_s, src_out_s], ...] in the wav's time)
wav: mono 16 kHz from the interview clip's mic channel (shoot.audio.mic_camera / mic_channel;
ffmpeg -i clip -ac 1 -ar 16000 a.wav).
Prints per piece: head air (s before first speech), tail air (s after last speech), inner pauses >= 0.15 s,
plus medians. House targets: head ~0.10 s, tail ~0.15 s, join ~0.28 s, mid-sentence gaps >= ~0.3 s removed
(some clients run tighter: see the client profile)."""
import argparse, sys, json, wave
ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("wav"); ap.add_argument("cuts"); A=ap.parse_args()
try: import numpy as np
except ImportError: sys.exit("needs numpy (pip install numpy, or run it with the python that has it)")
w=wave.open(A.wav); x=np.frombuffer(w.readframes(w.getnframes()),np.int16).astype(np.float32)/32768; SR=w.getframerate()
hop=SR//100; fr=np.array([20*np.log10(np.sqrt((x[i:i+hop]**2).mean())+1e-9) for i in range(0,len(x)-hop,hop)])
thr=np.percentile(fr,10)+12
cuts=json.load(open(A.cuts)); H=[];T=[]
for a,b in cuts:
    seg=fr[int(a*100):int(b*100)]>thr; v=np.where(seg)[0]
    if not len(v): print(f"{a:.2f}-{b:.2f} no speech"); continue
    h=v[0]/100; t=(len(seg)-1-v[-1])/100; H.append(h); T.append(t)
    gaps=[];run=0
    for k in range(v[0],v[-1]+1):
        if not seg[k]: run+=1
        else:
            if run>=15: gaps.append((round((int(a*100)+k-run)/100,2),round(run/100,2)))
            run=0
    flag=" <- gaps to consider removing" if any(g[1]>=0.3 for g in gaps) else ""
    print(f"{a:7.2f}-{b:7.2f}  head {h:.2f}  tail {t:.2f}  pauses {gaps}{flag}")
if H: print(f"median head {np.median(H):.2f}  tail {np.median(T):.2f}  join {np.median([T[i]+H[i+1] for i in range(len(H)-1)] or [0]):.2f}")
