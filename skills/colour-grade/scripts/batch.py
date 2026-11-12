# LEGACY, kept for reference only. Do not run: it measured inside Resolve's Python, which made
# Resolve lag (colour-grade "Keep Resolve light"). Use calib.py / measnp.py outside Resolve instead.
# Its /tmp/claude_drx paths and 3840x2160 / 1080x1920 sizes are the old hardcoded ones.
import sys, json, os, time
sys.path.insert(0,"/tmp/claude_drx")
import meas
def run(budget=50, order=None):
    jobs=json.load(open("/tmp/claude_drx/jobs.json"))
    rp="/tmp/claude_drx/res.json"
    res=json.load(open(rp)) if os.path.exists(rp) else {}
    os.makedirs("/tmp/claude_drx/thumbs",exist_ok=True)
    t0=time.time(); done=0
    if order: jobs=sorted(jobs,key=lambda j: order.index(j["tl"]))
    for j in jobs:
        if j["key"] in res: continue
        if time.time()-t0>budget: break
        cr=meas.crop_for(j["pan"],j["tilt"],j["zoom"])
        r={}
        try:
            a=meas.frame(j["src"],j["t"],cr,j["lut"],rng="pc"); r["after"]=meas.stats(a); meas.ppm(a,f"/tmp/claude_drx/thumbs/{j['key']}_A.ppm")
            if j["before"]:
                b=meas.frame(j["src"],j["t"],cr,"/tmp/claude_drx/luts/C7_t1_0.cube",rng="pc"); r["before"]=meas.stats(b); meas.ppm(b,f"/tmp/claude_drx/thumbs/{j['key']}_B.ppm")
        except Exception as e: r["err"]=str(e)
        res[j["key"]]=r; done+=1
        json.dump(res,open(rp,"w"))
    return {"done":done,"total":len(res),"left":len(jobs)-len(res),"sec":round(time.time()-t0)}
