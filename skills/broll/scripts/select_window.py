"""Pick the smoothest window of a given source length inside Footage Prep selects.
usage: select_window.py '[[slot, clip, need_src_frames, [[in,out],...]], ...]' out.json CLIP_FOLDER [--card JOB_CARD.md] [--size WxH]
Scores each window by optical-flow jitter p90 (px at the delivery width, default 1080), speed evenness and
direction reversals. clip = stem (C0012), file name (any video extension) or path relative to CLIP_FOLDER
(A001/C0012.MP4). Frames are source frames at the clip's own fps (probed; 50 if ffprobe can't tell)."""
import argparse,json,subprocess
from _beon import add_delivery_args, delivery, find_clip
ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("job"); ap.add_argument("out"); ap.add_argument("clipdir"); add_delivery_args(ap,fps=False)
A=ap.parse_args()
import cv2,numpy as np
OUT_W=delivery(A)["width"]
def src_fps(f):
    r=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=r_frame_rate','-of','csv=p=0',f],capture_output=True,text=True).stdout.strip()
    try: n,d=r.split('/')[:2]; return float(n)/float(d)
    except (ValueError,ZeroDivisionError): return 50.0
def path(clip,a,b):
    f=find_clip(A.clipdir,clip)
    cmd=['ffmpeg','-v','error','-ss',f'{a/src_fps(f):.3f}','-i',f,'-frames:v',str(b-a),'-vf','scale=320:180,format=gray','-f','rawvideo','-']
    raw=subprocess.run(cmd,capture_output=True).stdout
    fr=np.frombuffer(raw,np.uint8).reshape(-1,180,320).astype(np.float32)
    d=[cv2.phaseCorrelate(fr[i-1],fr[i])[0] for i in range(1,len(fr))]
    return np.array(d)  # per-frame dx,dy in 320px units
def score(d):
    # smooth intended move = moving average over 25 frames; jitter = residual
    k=25; ker=np.ones(k)/k
    sm=np.stack([np.convolve(d[:,j],ker,'same') for j in range(2)],1)
    res=d-sm; jit=np.hypot(res[:,0],res[:,1])*(OUT_W/320)  # approx px at the delivery width (1080 by default; 9:16 crop ~ 1/3 width scaled)
    sp=np.hypot(sm[:,0],sm[:,1]); cv=np.std(sp)/(np.mean(sp)+0.05)
    ang=np.arctan2(sm[:,1],sm[:,0]); rev=float(np.mean(np.cos(ang-np.median(ang))<0)) if np.mean(sp)>0.15 else 0
    return float(np.percentile(jit,90)),float(np.mean(sp)),float(cv),rev
job=json.loads(A.job); out={}
for slot,clip,need,sels in job:
    best=None
    for a,b in sels:
        if b-a<need: continue
        d=path(clip,a,b)
        for s in range(0,len(d)-need+1,5):
            p90,sp,cv,rev=score(d[s:s+need])
            cost=p90+2*rev+0.5*min(cv,2)
            if best is None or cost<best[0]: best=(cost,a+s,p90,sp,cv,rev)
    out[slot]=dict(clip=clip,sf=best[1],p90=round(best[2],2),speed=round(best[3],2),speed_cv=round(best[4],2),reversal=round(best[5],2)) if best else None
    print(slot,out[slot],flush=True)
json.dump(out,open(A.out,'w'),indent=1)
