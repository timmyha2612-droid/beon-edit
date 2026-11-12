"""Measure how far a 9:16 still is off-level: median angle of near-vertical lines (walls, door frames,
window mullions). Returns degrees to ROTATE the picture (positive = counter-clockwise) to make verticals vertical,
plus the minimum zoom that keeps the frame covered after that rotation.
usage: level_check.py [--center] [--card JOB_CARD.md | --size 1080x1920] [--src-aspect 16:9] STILL...
The zoom maths assume the delivery size (default 1080x1920) filled by a --src-aspect source (default 16:9)."""
import sys,math,json
def vert_tilt(path,center=None):
    import cv2,numpy as np
    im=cv2.imread(path,cv2.IMREAD_GRAYSCALE); h,w=im.shape
    im=cv2.createCLAHE(clipLimit=3.0,tileGridSize=(8,8)).apply(cv2.normalize(im,None,0,255,cv2.NORM_MINMAX))
    e=cv2.Canny(cv2.GaussianBlur(im,(5,5),0),20,60)
    L=cv2.HoughLinesP(e,1,np.pi/720,60,minLineLength=h//12,maxLineGap=6)
    angs=[];wts=[]
    for x1,y1,x2,y2 in (L.reshape(-1,4) if L is not None else []):
        dx,dy=x2-x1,y2-y1
        if abs(dy)<1: continue
        if center and not (center[0]*w <= (x1+x2)/2 <= center[1]*w): continue
        a=math.degrees(math.atan2(dx,dy))  # 0 = vertical; + = top leans right
        if a>90: a-=180
        if a<-90: a+=180
        if abs(a)<8: angs.append(a); wts.append(math.hypot(dx,dy))
    if len(angs)<3: return None,len(angs)
    o=np.argsort(angs); a=np.array(angs)[o]; wv=np.cumsum(np.array(wts)[o])
    return float(a[np.searchsorted(wv,wv[-1]/2)]),len(angs)
def min_zoom(theta_deg,win_w=1080,win_h=1920,img_w=3413.3,img_h=1920,cx=0.0):
    t=math.radians(abs(theta_deg)); z=1.0
    for x in (-win_w/2+cx,win_w/2+cx):
        for y in (-win_h/2,win_h/2):
            u=abs(x*math.cos(t)+y*math.sin(t)); v=abs(-x*math.sin(t)+y*math.cos(t))
            z=max(z,u/(img_w/2),v/(img_h/2))
    return z
if __name__=='__main__':
    import argparse
    from _beon import add_delivery_args, delivery
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stills",nargs="+"); ap.add_argument("--center",action="store_true",help="verticals in the middle 40%% only (keystone exteriors)")
    ap.add_argument("--src-aspect",default="16:9"); add_delivery_args(ap,fps=False)
    A=ap.parse_args(); d=delivery(A)
    sw,sh=(float(v) for v in A.src_aspect.split(":"))
    fill=max(d["width"]/sw,d["height"]/sh)       # source scaled to cover the frame
    geo=dict(win_w=d["width"],win_h=d["height"],img_w=sw*fill,img_h=sh*fill)
    if (d["width"],d["height"])==(1080,1920) and A.src_aspect=="16:9": geo["img_w"]=3413.3
    out={}; ctr=(0.3,0.7) if A.center else None
    for p in A.stills:
        a,n=vert_tilt(p,ctr)
        out[p]=dict(lean_deg=a,lines=n,rotate=None if a is None else -a,zoom=None if a is None else round(min_zoom(a,**geo)*1.005,4))
    print(json.dumps(out,indent=1))
