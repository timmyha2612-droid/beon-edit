#!/usr/bin/env python3
"""How visible is each same-framing A-roll cut?
usage: jumpcut_check.py CLIP PIECES.json [--card JOB_CARD | --size WxH]
       PIECES = [[rec_start, rec_end, src_in_s, src_out_s, zoom, pan, tilt], ...]
Timeline size: --size, else the job card Delivery / client profile delivery (--card, via beon_config),
else 1080x1920. Source size is probed (3840x2160 if ffprobe fails).
Prints per cut: source gap, mean abs pixel difference, face-centre shift (% of frame width).
Tim leaves a cut uncovered when the head moves < ~1% and the audio flows; covered jumps were 2-3x larger."""
import sys, json, pathlib, subprocess, argparse
ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("clip"); ap.add_argument("pieces"); ap.add_argument("--card"); ap.add_argument("--size",help="timeline WxH, e.g. 1080x1920")
A=ap.parse_args()
W,H=1080,1920
if A.size: W,H=map(int,A.size.lower().split("x"))
elif A.card:
    sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/"house-rules"/"scripts")); import beon_config as bc
    d=bc.delivery(A.card); W,H=int(d["width"]),int(d["height"])
import numpy as np, cv2
src=A.clip; P=json.load(open(A.pieces))
try:
    SW,SH=map(int,subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","csv=p=0:s=x",src],capture_output=True,text=True).stdout.strip().split("x")[:2])
except ValueError:
    SW,SH=3840,2160
OW=270; OH=int(round(OW*H/W))//2*2
face=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
def grab(t,z,pan,tilt):
    s=H/SH*z; cw=int(W/s)//2*2; ch=int(H/s)//2*2; cx=int(SW/2-pan/s-cw/2); cy=max(0,min(SH-ch,int(SH/2+tilt/s-ch/2)))
    r=subprocess.run(["ffmpeg","-v","error","-ss",f"{t:.3f}","-i",src,"-frames:v","1","-vf",f"crop={cw}:{ch}:{cx}:{cy},scale={OW}:{OH},format=gray","-f","rawvideo","-"],capture_output=True)
    return np.frombuffer(r.stdout,np.uint8).reshape(OH,OW)
def fc(g):
    f=face.detectMultiScale(g,1.1,5,minSize=(40,40)); 
    if not len(f): return None
    x,y,w,h=max(f,key=lambda b:b[2]*b[3]); return np.array([x+w/2,y+h/2])
for a,b in zip(P,P[1:]):
    if a[1]!=b[0]: continue
    g1=grab(a[3]-0.04,*a[4:7]); g2=grab(b[2],*b[4:7])
    f1,f2=fc(g1),fc(g2); sh=None if f1 is None or f2 is None else round(float(np.hypot(*(f1-f2)))/OW*100,1)
    kind="zoom change" if a[4]!=b[4] else "same framing"
    print(f"cut @{a[1]}  {kind}  src gap {b[2]-a[3]:.2f}s  diff {np.abs(g1.astype(float)-g2).mean():.1f}  face shift {sh}%")
