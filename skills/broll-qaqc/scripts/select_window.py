"""Pick the smoothest window of a given source length inside Footage Prep selects.
usage: select_window.py '[[slot, clip_stem, need_src_frames, [[in,out],...]], ...]' out.json CLIP_FOLDER
Scores each window by optical-flow jitter p90 (px at 1080 wide), speed evenness and direction reversals."""
import cv2,numpy as np,json,sys,subprocess
D = sys.argv[3].rstrip("/") + "/"  # folder holding the clips
def path(clip,a,b):
    cmd=['ffmpeg','-v','error','-ss',f'{a/50:.3f}','-i',D+clip+'.MP4','-frames:v',str(b-a),'-vf','scale=320:180,format=gray','-f','rawvideo','-']
    raw=subprocess.run(cmd,capture_output=True).stdout
    fr=np.frombuffer(raw,np.uint8).reshape(-1,180,320).astype(np.float32)
    d=[cv2.phaseCorrelate(fr[i-1],fr[i])[0] for i in range(1,len(fr))]
    return np.array(d)  # per-frame dx,dy in 320px units
def score(d):
    # smooth intended move = moving average over 25 frames; jitter = residual
    k=25; ker=np.ones(k)/k
    sm=np.stack([np.convolve(d[:,j],ker,'same') for j in range(2)],1)
    res=d-sm; jit=np.hypot(res[:,0],res[:,1])*(1080/320)  # approx px at output width (9:16 crop ~ 1/3 width scaled) 
    sp=np.hypot(sm[:,0],sm[:,1]); cv=np.std(sp)/(np.mean(sp)+0.05)
    ang=np.arctan2(sm[:,1],sm[:,0]); rev=float(np.mean(np.cos(ang-np.median(ang))<0)) if np.mean(sp)>0.15 else 0
    return float(np.percentile(jit,90)),float(np.mean(sp)),float(cv),rev
job=json.loads(sys.argv[1]); out={}
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
json.dump(out,open(sys.argv[2],'w'),indent=1)
