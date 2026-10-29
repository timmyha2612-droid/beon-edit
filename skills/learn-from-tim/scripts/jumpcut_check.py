#!/usr/bin/env python3
"""How visible is each same-framing A-roll cut?
usage: jumpcut_check.py CLIP PIECES.json    PIECES = [[rec_start, rec_end, src_in_s, src_out_s, zoom, pan, tilt], ...]
Prints per cut: source gap, mean abs pixel difference, face-centre shift (% of frame width).
Tim leaves a cut uncovered when the head moves < ~1% and the audio flows; covered jumps were 2-3x larger."""
import sys, json, subprocess, numpy as np, cv2
src=sys.argv[1]; P=json.load(open(sys.argv[2]))
face=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
def grab(t,z,pan,tilt):
    s=1920/2160*z; cw=int(1080/s)//2*2; ch=int(1920/s)//2*2; cx=int(1920-pan/s-cw/2); cy=max(0,min(2160-ch,int(1080+tilt/s-ch/2)))
    r=subprocess.run(["ffmpeg","-v","error","-ss",f"{t:.3f}","-i",src,"-frames:v","1","-vf",f"crop={cw}:{ch}:{cx}:{cy},scale=270:480,format=gray","-f","rawvideo","-"],capture_output=True)
    return np.frombuffer(r.stdout,np.uint8).reshape(480,270)
def fc(g):
    f=face.detectMultiScale(g,1.1,5,minSize=(40,40)); 
    if not len(f): return None
    x,y,w,h=max(f,key=lambda b:b[2]*b[3]); return np.array([x+w/2,y+h/2])
for a,b in zip(P,P[1:]):
    if a[1]!=b[0]: continue
    g1=grab(a[3]-0.04,*a[4:7]); g2=grab(b[2],*b[4:7])
    f1,f2=fc(g1),fc(g2); sh=None if f1 is None or f2 is None else round(float(np.hypot(*(f1-f2)))/270*100,1)
    kind="zoom change" if a[4]!=b[4] else "same framing"
    print(f"cut @{a[1]}  {kind}  src gap {b[2]-a[3]:.2f}s  diff {np.abs(g1.astype(float)-g2).mean():.1f}  face shift {sh}%")
