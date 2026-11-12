# LEGACY, kept for reference only. Do not run: it measured inside Resolve's Python, which made
# Resolve lag (colour-grade "Keep Resolve light"). Use measnp.py outside Resolve instead.
# Its /tmp/claude_drx paths and 3840x2160 / 1080x1920 sizes are the old hardcoded ones.
import subprocess, struct, math, os, array
FF="/opt/homebrew/bin/ffmpeg"
W0,H0=180,320
def frame(src, t, crop, lut, W=W0, H=H0, rng="pc"):  # pc matches Resolve on Sony XAVC (validated vs still 1.1.1)
    cw,ch,cx,cy = crop
    vf=f"crop={cw}:{ch}:{cx}:{cy},scale={W}:{H}:in_range={rng}:in_color_matrix=bt709:out_range=pc:flags=area,format=rgb48le"
    if lut: vf+=f",lut3d=file='{lut}':interp=tetrahedral"
    cmd=[FF,"-v","error","-ss",f"{t:.3f}","-i",src,"-frames:v","1","-vf",vf,"-f","rawvideo","-pix_fmt","rgb48le","-"]
    raw=subprocess.run(cmd,capture_output=True,timeout=40).stdout
    a=array.array("H"); a.frombytes(raw[:W*H*6])
    return a
def crop_for(pan,tilt,zoom,W=3840,H=2160,tw=1080,th=1920):
    s=th/H*zoom
    cw=min(W,tw/s); ch=min(H,th/s)
    cx=W/2-pan/s-cw/2; cy=H/2+tilt/s-ch/2
    cx=max(0,min(W-cw,cx)); cy=max(0,min(H-ch,cy))
    return int(cw)//2*2,int(ch)//2*2,int(cx),int(cy)
def pct(v,q):
    v=sorted(v); return v[min(len(v)-1,int(q/100*len(v)))]
def stats(a,W=W0,H=H0):
    n=W*H; Y=[0.0]*n; Cb=[0.0]*n; Cr=[0.0]*n
    for i in range(n):
        r=a[3*i]/64.0; g=a[3*i+1]/64.0; b=a[3*i+2]/64.0
        y=.2126*r+.7152*g+.0722*b; Y[i]=y; Cb[i]=(b-y)/1.8556; Cr[i]=(r-y)/1.5748
    out={"p50":pct(Y,50),"p90":pct(Y,90),"p99":pct(Y,99),"max":max(Y)}
    # neutral
    nb=nr=c=0
    for i in range(n):
        if Y[i]>200 and math.hypot(Cb[i],Cr[i])<40: nb+=Cb[i]; nr+=Cr[i]; c+=1
    out["neu"]=(round(nb/c,1),round(nr/c,1),round(c/n*100)) if c else None
    out["all"]=(round(sum(Cb)/n,1),round(sum(Cr)/n,1))
    # bright surfaces: Y>=p85, connected comps >=0.5%
    thr=pct(Y,85); m=[Y[i]>=thr for i in range(n)]; seen=[False]*n; comps=[]
    for s in range(n):
        if m[s] and not seen[s]:
            st=[s]; seen[s]=True; px=[]
            while st:
                k=st.pop(); px.append(k); x=k%W
                for nb_ in (k-1 if x>0 else -1, k+1 if x<W-1 else -1, k-W, k+W):
                    if 0<=nb_<n and m[nb_] and not seen[nb_]: seen[nb_]=True; st.append(nb_)
            comps.append(px)
    big=[p for p in comps if len(p)>=0.005*n]; big.sort(key=len,reverse=True)
    out["surf"]=[(round(len(p)/n*100,1), round(pct([Y[k] for k in p],50)), round(sum(k%W for k in p)/len(p)/W,2), round(sum(k//W for k in p)/len(p)/H,2)) for p in big[:4]]
    small=sum(len(p) for p in comps if len(p)<0.005*n)
    out["spots%"]=round(small/n*100,2)
    tops=[]
    for c0 in range(0,W,10):
        col=sorted(Y[r*W+c] for r in range(H) for c in range(c0,min(W,c0+10))); tops.append(col[int(len(col)*.98)])
    out["wtop"]=round(pct(tops,50))
    for k in ("p50","p90","p99","max"): out[k]=round(out[k])
    out["thr85"]=round(thr)
    return out
def ppm(a,path,W=W0,H=H0):
    with open(path,"wb") as f:
        f.write(f"P6 {W} {H} 255\n".encode()); f.write(bytes(min(255,v>>8) for v in a))
