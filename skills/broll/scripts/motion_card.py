#!/usr/bin/env python3
"""Motion card: read a B-roll shot's movement from one image.
usage: motion_card.py CLIP T_IN SRC_DUR OUT.png [--speed 100] [--pan 0 --tilt 0 --zoom 1] [--label R4]
                      [--root SHOOT] [--card JOB_CARD.md | --size 1080x1920 --fps 24]
T_IN/SRC_DUR in source seconds. Crop = the window the timeline shows (delivery size from --card/--size,
default 9:16 1080x1920, source scaled to cover it); jitter in px at the delivery width, output frames at the
timeline fps (default 24). With --root, CLIP can be a stem or a path relative to the shoot (A001/C0012.MP4).
Prints a one-line JSON verdict; the PNG has a filmstrip, first/last onion skin with flow arrows,
the camera path (pan/tilt/zoom speed) and per-frame jitter at output resolution.
Jitter tiers are provisional (calibrate against gyro): <1.0 px pass, 1.0-2.0 check, >2.0 fix."""
import os, json, argparse, subprocess
from _beon import add_delivery_args, delivery, find_clip
ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("clip"); ap.add_argument("t_in",type=float); ap.add_argument("dur",type=float); ap.add_argument("out")
ap.add_argument("--speed",type=float,default=100); ap.add_argument("--pan",type=float,default=0); ap.add_argument("--tilt",type=float,default=0)
ap.add_argument("--zoom",type=float,default=1); ap.add_argument("--label",default=""); ap.add_argument("--W",type=int,default=270)
ap.add_argument("--root",help="shoot or card folder CLIP is relative to"); add_delivery_args(ap)
a=ap.parse_args()
import numpy as np, cv2
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
DL=delivery(a); OW,OH,TLF=DL["width"],DL["height"],DL["fps"]
if a.root or not os.path.isfile(a.clip): a.clip=find_clip(a.root,a.clip)
def probe(clip):
    r=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height,r_frame_rate","-of","json",clip],capture_output=True,text=True)
    s=json.loads(r.stdout)["streams"][0]; n,d=s["r_frame_rate"].split("/"); return s["width"],s["height"],float(n)/float(d)
SW,SH,FPS=probe(a.clip)
s=max(OW/SW,OH/SH)*a.zoom; cw=min(SW,int(OW/s))//2*2; ch=min(SH,int(OH/s))//2*2
cx=int(max(0,min(SW-cw,SW/2-a.pan/s-cw/2))); cy=int(max(0,min(SH-ch,SH/2+a.tilt/s-ch/2)))
W=a.W; H=int(W*OH/OW)//2*2
def frames(fmt,ch_):
    vf=f"crop={cw}:{ch}:{cx}:{cy},scale={W}:{H}:flags=area,format={fmt}"
    r=subprocess.run(["ffmpeg","-v","error","-ss",f"{a.t_in:.3f}","-i",a.clip,"-t",f"{a.dur:.3f}","-vf",vf,"-f","rawvideo","-"],capture_output=True)
    f=np.frombuffer(r.stdout,np.uint8); n=len(f)//(W*H*ch_); return f[:n*W*H*ch_].reshape(n,H,W,ch_) if ch_>1 else f[:n*W*H].reshape(n,H,W)
G=frames("gray",1); C=frames("rgb24",3)
n=len(G)
orb=cv2.ORB_create(800)
dx=[];dy=[];ds=[];dr=[];ok=[]
kp0,de0=orb.detectAndCompute(G[0],None)
for i in range(1,n):
    kp1,de1=orb.detectAndCompute(G[i],None); M=None
    if de0 is not None and de1 is not None and len(kp0)>20 and len(kp1)>20:
        m=cv2.BFMatcher(cv2.NORM_HAMMING,crossCheck=True).match(de0,de1)
        if len(m)>15:
            p0=np.float32([kp0[x.queryIdx].pt for x in m]); p1=np.float32([kp1[x.trainIdx].pt for x in m])
            M,_=cv2.estimateAffinePartial2D(p0,p1,method=cv2.RANSAC,ransacReprojThreshold=2.0)
    if M is None:
        (sx,sy),_=cv2.phaseCorrelate(np.float32(G[i-1]),np.float32(G[i])); M=np.array([[1,0,sx],[0,1,sy]],float); ok.append(False)
    else: ok.append(True)
    sc=float(np.hypot(M[0,0],M[1,0])); rot=float(np.degrees(np.arctan2(M[1,0],M[0,0])))
    # translation of the frame centre
    c=np.array([W/2,H/2]); c2=M[:,:2]@c+M[:,2]; t=c2-c
    dx.append(-t[0]); dy.append(-t[1]); ds.append(sc); dr.append(rot)   # camera motion = opposite of image motion
    kp0,de0=kp1,de1
dx=np.array(dx);dy=np.array(dy);dz=np.log(np.array(ds))*100;dr=np.array(dr)
k=max(3,int(round(FPS*0.4))|1)
def smooth(v): pad=np.pad(v,(k//2,k//2),mode="edge"); return np.convolve(pad,np.ones(k)/k,"valid")
sx_,sy_,sz_,sr_=smooth(dx),smooth(dy),smooth(dz),smooth(dr)
jit=np.hypot(dx-sx_,dy-sy_)*(OW/W)            # px per source frame at output res
spf=(FPS*a.speed/100)/TLF                        # source frames per output frame
jit_out=jit*min(1.0,spf)
sp=np.hypot(sx_,sy_)
# move label
tot=np.array([dx.sum(),dy.sum()]); zt=dz.sum()
lab=[]
if abs(tot[0])>W*0.04: lab.append("pans right" if tot[0]>0 else "pans left")
if abs(tot[1])>H*0.04: lab.append("tilts down" if tot[1]>0 else "tilts up")
if abs(zt)>3: lab.append("pushes in" if zt>0 else "pulls out")
label=" + ".join(lab) or "static"
mv=np.hypot(sp, np.abs(sz_)*W/200)
cv_=float(np.std(mv[k:-k])/max(1e-6,np.mean(mv[k:-k]))) if n>3*k and np.mean(mv)>0.2 else 0.0
third=max(1,len(mv)//4); e0=float(mv[:third].mean()); em=float(mv[third:-third].mean()) if len(mv)>2*third else float(mv.mean()); e1=float(mv[-third:].mean())
flags=[]
if label!="static" and em>0.3:
    if e0<0.5*em: flags.append("starts mid-ease (speeding up)")
    if e1<0.5*em: flags.append("ends mid-ease (slowing down)")
    if cv_>0.3: flags.append(f"uneven speed (cv {cv_:.2f})")
# per-axis ease: an axis carrying real motion that slows or speeds up by >50% across the shot
for nm,v in (("pan",sx_),("tilt",sy_),("zoom",sz_*W/200)):
    q=max(1,len(v)//5); a0=abs(float(v[:q].mean())); a1=abs(float(v[-q:].mean())); pk=max(a0,a1)
    if pk>0.3 and min(a0,a1)<0.5*pk: flags.append(f"{nm} {'slows' if a1<a0 else 'speeds up'} {int(round((1-min(a0,a1)/pk)*100))}% across the shot")
# reversal: dominant axis velocity changes sign for > 0.2 s
dom=sx_ if abs(tot[0])>=abs(tot[1]) else sy_
sg=np.sign(dom); main=np.sign(dom.sum())
if main!=0 and np.sum(sg==-main)>0.2*FPS: flags.append("direction reversal (reset?)")
p90=float(np.percentile(jit_out,90)); tier="pass" if p90<1.0 else ("check" if p90<2.0 else "fix")
verdict={"label":a.label,"move":label,"jitter_p90_px":round(p90,2),"jitter_max_px":round(float(jit_out.max()),2),"tier":tier,"flags":flags,"frames":n,"fps":FPS,"speed":a.speed,"tracked":f"{sum(ok)}/{len(ok)}"}
# ---- card
fig=plt.figure(figsize=(10.8,9.6),dpi=100)
gs=fig.add_gridspec(3,6,height_ratios=[1.25,1.0,0.8],hspace=0.35,wspace=0.08)
idx=np.linspace(0,n-1,6).astype(int)
for j,i in enumerate(idx):
    ax=fig.add_subplot(gs[0,j]); ax.imshow(C[i]); ax.set_axis_off(); ax.set_title(f"{a.t_in+i/FPS:.2f}s",fontsize=9)
ax=fig.add_subplot(gs[1,0:2])
on=np.zeros((H,W,3),np.uint8); on[...,0]=G[0]; on[...,1]=G[-1]; on[...,2]=G[-1]
ax.imshow(on); ax.set_axis_off(); ax.set_title("onion: red = first, cyan = last",fontsize=9)
mid=n//2; f=cv2.calcOpticalFlowFarneback(G[max(0,mid-2)],G[min(n-1,mid+2)],None,0.5,3,21,3,5,1.1,0)
ax=fig.add_subplot(gs[1,2:4]); ax.imshow(C[mid]); ax.set_axis_off(); ax.set_title("image motion mid-shot (arrows)",fontsize=9)
st=24; yy,xx=np.mgrid[st//2:H:st,st//2:W:st]; u=f[yy,xx,0]; v=f[yy,xx,1]
ax.quiver(xx,yy,u,v,color="yellow",angles="xy",scale_units="xy",scale=0.25,width=0.004)
ax=fig.add_subplot(gs[1,4:6]); t=np.arange(len(dx))/FPS
ax.plot(t,sx_,label="pan (+right)"); ax.plot(t,sy_,label="tilt (+down)"); ax.plot(t,sz_*W/200,label="zoom (+in)")
ax.axhline(0,color="grey",lw=.6); ax.set_title("camera speed, px/frame (smoothed)",fontsize=9); ax.legend(fontsize=7); ax.tick_params(labelsize=7)
ax=fig.add_subplot(gs[2,0:6]); ax.plot(t,jit_out,color="black",lw=1)
for y,c in ((1.0,"#2E8F52"),(2.0,"#C8423A")): ax.axhline(y,color=c,lw=.8,ls="--")
ax.set_title(f"jitter per output frame (px at {OW} wide); green = pass line, red = fix line",fontsize=9); ax.set_xlabel("seconds into window",fontsize=8); ax.tick_params(labelsize=7)
fig.suptitle(f"{a.label}  {label}  |  jitter p90 {p90:.2f}px ({tier})  |  {'; '.join(flags) or 'clean move'}",fontsize=11,fontweight="bold")
fig.savefig(a.out,bbox_inches="tight"); print(json.dumps(verdict))
