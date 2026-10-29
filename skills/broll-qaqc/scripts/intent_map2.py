"""Intent map v2: image motion (keyframe optical flow) decides the move, gyro decides shake.
Tiers: REJECT (resets/reversals, stop-start stalls, first/last 1 s, too short)
       OK (clean but secondary: steady holds/moves that aren't the clip's main move)
       CANDIDATE (the clip's real move(s) and anything uncertain -> dense scan later)"""
import sys, os, re, json, subprocess, numpy as np, telemetry_parser, cv2
D = os.path.expanduser("~/mnt/Namir Mikha/[01. Content]/Videography/1. SHOOTS/2026/Shoot 16. Bishop St")
def path(c):
    return f"{D}/Day 1/{c}.MP4" if c.startswith("C08") else f"{D}/Day 2/FX3 A CAM Gimbal/LIAM.A_FX3_{c}.MP4"
EDGE, W, H = 1.0, 192, 108
MOVE_T = float(os.environ.get('MOVE_T', 1.2))   # px/s at 192 px width
def gyro_shake(c):
    try:
        imu = telemetry_parser.Parser(path(c)).normalized_imu()
    except Exception:
        return None
    t = np.array([s["timestamp_ms"] for s in imu])/1000.0; g = np.array([s["gyro"] for s in imu], float)
    b = np.floor(t*100).astype(int); n = b.max()+1; cnt = np.bincount(b, minlength=n).astype(float); cnt[cnt==0] = 1
    gs = np.vstack([np.bincount(b, weights=g[:,k], minlength=n)/cnt for k in range(3)]).T
    k = np.ones(50)/50; lf = np.vstack([np.convolve(gs[:,i], k, "same") for i in range(3)]).T
    hf = gs - lf; k2 = np.ones(20)/20
    return np.sqrt(np.convolve((hf**2).sum(axis=1), k2, "same"))      # 100 Hz
def keyframes(c):
    p = subprocess.run(["ffmpeg","-v","info","-skip_frame","nokey","-i",path(c),"-vsync","0",
                        "-vf",f"scale={W}:{H},format=gray,showinfo","-f","rawvideo","-"], capture_output=True)
    ts = [float(x) for x in re.findall(rb"pts_time:([0-9.]+)", p.stderr)]
    fr = np.frombuffer(p.stdout, np.uint8).reshape(-1, H, W)
    return np.array(ts[:len(fr)]), fr
yy, xx = np.mgrid[0:H, 0:W]; RX, RY = xx - W/2, yy - H/2; R2 = RX**2 + RY**2 + 1
def flows(fr, ts):
    rows = []
    # Sony long-GOP keyframes alternate by a small constant spatial offset, so i->i+1 flow flips sign every
    # interval. Same-parity pairs (i->i+2) cancel it; the result is assigned to interval [ts[i], ts[i+1]].
    for i in range(len(fr)-1):
        j = min(i+2, len(fr)-1)
        f = cv2.calcOpticalFlowFarneback(fr[i], fr[j], None, 0.5, 3, 15, 3, 5, 1.2, 0)
        dt = max(ts[j]-ts[i], 1e-3)
        fx, fy = f[...,0]/dt, f[...,1]/dt                     # px per second at 192x108
        dx, dy = float(np.median(fx)), float(np.median(fy))
        div = float(np.median((fx*RX + fy*RY)/R2))*100        # zoom-like expansion (push in > 0)
        resid = float(np.percentile(np.hypot(fx-dx, fy-dy), 90))
        rows.append((ts[i], ts[i+1], dx, dy, div, resid))  # interval kept contiguous
    return rows
def label(dx, dy, div):
    lab = []
    if abs(div) > 0.25: lab.append("push in" if div > 0 else "pull out")
    if abs(dx) > MOVE_T: lab.append("moves left" if dx > 0 else "moves right")
    if abs(dy) > MOVE_T: lab.append("moves up" if dy > 0 else "moves down")
    return " + ".join(lab) or "static"
def analyse(c):
    ts, fr = keyframes(c); dur = float(ts[-1]) if len(ts) else 0
    sh = gyro_shake(c)
    rows = flows(fr, ts)
    vec = np.array([[r[2], r[3], r[4]*8] for r in rows])           # weight divergence so pushes count
    mag = np.linalg.norm(vec, axis=1)
    # hysteresis: start moving above MOVE_T, stop below MOVE_T/2 (kills flicker on slow slides)
    moving = np.zeros(len(mag), bool); st = bool(mag[0] > MOVE_T) if len(mag) else False
    for k, m_ in enumerate(mag):
        if st and m_ < MOVE_T*0.5: st = False
        elif not st and m_ > MOVE_T: st = True
        moving[k] = st
    # 1) runs of moving / static intervals
    runs = []; i = 0
    while i < len(rows):
        j = i
        while j+1 < len(rows) and moving[j+1] == moving[i]: j += 1
        runs.append([i, j, bool(moving[i])]); i = j+1
    # 2) split moving runs where direction flips
    segs = []
    for a, b, mv in runs:
        if not mv: segs.append((a, b, False)); continue
        s0 = a
        for k in range(a+1, b+1):
            cosv = np.dot(vec[k], vec[k-1])/(mag[k]*mag[k-1]+1e-9)
            if cosv < -0.2: segs.append((s0, k-1, True)); s0 = k
        segs.append((s0, b, True))
    out = []
    for a, b, mv in segs:
        t0, t1 = rows[a][0], rows[b][1]
        v = vec[a:b+1].mean(axis=0); m = mag[a:b+1]
        shk = float(np.median(sh[int(t0*100):int(t1*100)])) if sh is not None and int(t1*100) > int(t0*100) else None
        out.append({"t0": round(t0,2), "t1": round(t1,2), "moving": mv, "dir": v.tolist(),
                    "speed": round(float(m.mean()),1), "cv": round(float(m.std()/(m.mean()+1e-9)),2) if mv else None,
                    "label": label(*vec[a:b+1].mean(axis=0)[:2], vec[a:b+1].mean(axis=0)[2]/8),
                    "shake": round(shk,2) if shk is not None else None,
                    "resid": round(float(np.mean([rows[k][5] for k in range(a,b+1)])),1), "flags": []})
    # 3) stalls: a moving segment whose speed dips < 35% of its median for >= 1 interval inside, then recovers
    for s in out:
        if not s["moving"]: continue
    # main move = longest smooth moving segment that's not a whip
    def mscore(s): return (s["t1"]-s["t0"]) * (1 - min(s["cv"] or 0, 0.9)) * (1 if s["speed"] < 40 else 0.2) * (1 if (s["shake"] or 0) < 1.5 else 0.5)
    movers = [s for s in out if s["moving"] and s["t0"] >= EDGE - 0.5]
    main = max(movers, key=mscore) if movers else None
    if main: main["flags"].append("MAIN MOVE")
    md = np.array(main["dir"]) if main else None
    for idx, s in enumerate(out):
        d = s["t1"] - s["t0"]
        if s["moving"] and main is not None and s is not main:
            cosm = np.dot(s["dir"], md)/(np.linalg.norm(s["dir"])*np.linalg.norm(md)+1e-9)
            if cosm < -0.3: s["flags"].append("reset/reversal")
        # stall = brief static gap between two moving segments in the SAME direction
        if not s["moving"] and 0 < idx < len(out)-1 and out[idx-1]["moving"] and out[idx+1]["moving"] and d <= 1.2:
            a, b = np.array(out[idx-1]["dir"]), np.array(out[idx+1]["dir"])
            real = np.linalg.norm(a) > 2*MOVE_T and np.linalg.norm(b) > 2*MOVE_T and np.linalg.norm(s["dir"]) < 0.5*MOVE_T
            if real and np.dot(a, b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-9) > 0.5: s["flags"].append("stop-start stall")
        if s["t1"] <= EDGE or s["t0"] >= dur - EDGE: s["tier"], s["why"] = "REJECT", "first/last 1 s"
        elif "reset/reversal" in s["flags"]: s["tier"], s["why"] = "REJECT", "reset/reversal"
        elif "stop-start stall" in s["flags"]: s["tier"], s["why"] = "REJECT", "stop-start stall"
        elif d < 0.9: s["tier"], s["why"] = "REJECT", "too short"
        else:
            unsure = (s["shake"] is not None and 0.35 <= s["shake"] <= 0.6) or (s["cv"] or 0) > 0.4 or (not s["moving"] and s["resid"] > 6)
            if s["shake"] is not None and s["shake"] > 0.6: s["flags"].append("shaky -> Gyroflow?")
            if not s["moving"] and s["resid"] > 6: s["flags"].append("something moving in frame (people?)")
            if s is main: s["tier"], s["why"] = "CANDIDATE", "main move"
            elif unsure: s["tier"], s["why"] = "CANDIDATE", "uncertain"
            else: s["tier"], s["why"] = "OK", "steady hold" if not s["moving"] else "steady secondary move"
    for s in out: s["dir"] = [round(float(v),1) for v in s["dir"]]
    return {"dur": round(dur,2), "keyframes": len(ts), "segments": out}
res = {c: analyse(c) for c in sys.argv[1:]}
print(json.dumps(res))
