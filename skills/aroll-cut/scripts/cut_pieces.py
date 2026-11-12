#!/usr/bin/env python3
"""Rough A-roll picks -> clean, flowing sub-pieces and a ready AppendToTimeline list, in one pass.
usage: cut_pieces.py plan.json [out.json] [--card JOB.md] [--shoot FOLDER] [--lang en] [--tl-fps 24]
plan.json:
 {"transcript": ".../_shotlog/transcripts/CLIP.json",  # same formats as filler_scan.py
  "wav": "a.wav",               # mono 16 kHz mic channel, time 0 = source clip start
  "video": "/path/A_cam.MP4",   # optional, for cut_review.py
  "src_fps": 25, "src_offset": 0.0,   # Resolve source frame = round((t + src_offset) * src_fps)
                                      # (multicam clip: src_fps = timeline fps and the angle's offset,
                                      #  shoot.multicam.angle_offsets_s)
  "tl_fps": 24, "record_start": 0, "track": 1,
  "card": ".../_shotlog/jobs/C1.md",  # optional (or --card): tl_fps from its Delivery line / client profile
  "shoot": ".../<shoot folder>",      # optional (or --shoot; default the card's Shoot line): shoot.audio,
                                      #  shoot.multicam, shoot.cameras[].fps and shoot.language
  "lang": "en",                       # optional (or --lang): filler and function-word lists
  "fillers": "flag",            # "flag" lists likely ums/uhs; "cut" also removes the isolated ones
  "pans": {"Q1": 85},           # optional, per label, for cut_review.py
  "pieces": [[a, b, "Q1"], ...]}  # source seconds; transcript times are fine (drift is handled)
Missing values: src_fps = the plan, else the timeline fps when shoot.multicam.exists, else the mic
camera's fps (shoot.audio.mic_camera in shoot.cameras), else 25; tl_fps = --tl-fps, else the plan, else
the job card's delivery fps, else 24.
What it does per piece (house rules, aroll-cut SKILL.md section 2 and 2b):
  - snaps the in and out to a real silence between words (never inside a word), head air 0.10 s,
    tail air 0.15 s, both limited by the silence that is actually there (flags when it's short);
  - trims mid-sentence hesitations: silences >= 0.25 s are cut down to 0.22 s mid-sentence,
    0.35 s after a comma, 0.45 s after a full stop;
  - finds untranscribed speech blobs (ums/uhs the transcript dropped), tags them with the
    steadiness test, and with "fillers": "cut" removes the isolated likely ones, leaving about
    0.24 s of silence across the join; glued ones are only flagged (check by ear / energy);
  - lays the sub-pieces end to end from record_start and prints the AppendToTimeline items.
Then: add "mediaPoolItem" to each append item, append, run cut_review.py, and listen to every flag."""
import argparse, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from filler_scan import (np, bc, load_words, load_audio, energy, steadiness, norm, FILLERS, fillers_for,
                         job_language, need_numpy)

# Short words whose stutter ("and and", "the the") is cut automatically, per language. English only so far.
FUNCTION_BY_LANG = {
    "en": {"and", "the", "a", "an", "i", "we", "to", "so", "it", "is", "that", "but", "of", "in", "our",
           "my", "you", "they", "it's", "i'm", "we're", "this", "for", "with", "on", "be"},
}
FUNCTION = FUNCTION_BY_LANG["en"]
HEAD, TAIL = 0.10, 0.15
KEEP = {"period": 0.45, "comma": 0.35, "mid": 0.22}
FILL_SIDE = 0.12


def runs(mask, i0, i1, minlen=1):
    out, k = [], max(0, i0)
    i1 = min(len(mask), i1)
    while k < i1:
        if mask[k]:
            k0 = k
            while k < i1 and mask[k]:
                k += 1
            if k - k0 >= minlen:
                out.append((k0, k))
        else:
            k += 1
    return out


def boundary(x, sr, a, b, fr, prefer="max"):
    """Where one sound turns into another inside continuous speech, or None.
    Looks for a spectral-centroid change of 1.4x or more across +-20 ms (fricative -> vowel, vowel ->
    nasal): prefer="last" takes the change nearest the end of the window (a word ending just before a
    filler), "first" the one nearest the start (a word starting just after it), "max" the sharpest.
    Falls back to a clear energy dip. Arriva C1: 'is' /z/ -> 'uhh' at 229.82; 'umm' -> 'making' at 254.71."""
    n, hop = int(0.03 * sr), int(0.01 * sr)
    t0 = max(0.0, a)
    seg = x[int(t0 * sr):int(b * sr) + n]
    if len(seg) < n + 6 * hop:
        return None
    fra = np.array([seg[i:i + n] * np.hanning(n) for i in range(0, len(seg) - n, hop)])
    S = np.abs(np.fft.rfft(fra, axis=1)) + 1e-9
    f = np.fft.rfftfreq(n, 1 / sr)
    cen = np.log((S * f).sum(1) / S.sum(1))
    k = 2
    jump = np.abs(cen[2 * k:] - cen[:-2 * k])            # change across +-20 ms
    big = np.nonzero(jump > np.log(1.4))[0]
    if len(big):
        i = int(np.argmax(jump)) if prefer == "max" else int(big[0] if prefer == "first" else big[-1])
        lo, hi = max(0, i - 3), min(len(jump), i + 4)       # sharpest point of that change
        i = lo + int(np.argmax(jump[lo:hi]))
        return round(t0 + (i + k) * 0.01 + 0.015, 3)
    e = fr[int(t0 * 100):int(b * 100)]
    if len(e) > 6:
        i = int(np.argmin(e[2:-2])) + 2
        if min(e[:i].max(), e[i:].max()) - e[i] > 6:
            return round(t0 + i * 0.01, 3)
    return None


def clean(sp, n=3):
    """Fill silent holes and drop speech blips shorter than n frames (10 ms each)."""
    sp = sp.copy()
    for val in (False, True):                     # close holes, then open blips
        for r0, r1 in runs(sp == val, 0, len(sp)):
            if r1 - r0 < n and r0 > 0 and r1 < len(sp):
                sp[r0:r1] = not val
    return sp


def silence_around(sil, k):
    """Extent of the silence run containing frame k (frame idx), or None."""
    if k < 0 or k >= len(sil) or not sil[k]:
        return None
    a = k
    while a > 0 and sil[a - 1]:
        a -= 1
    b = k
    while b < len(sil) and sil[b]:
        b += 1
    return a, b


def function_for(lang):
    code = (lang or "en").lower().split("-")[0].split("_")[0]
    return FUNCTION_BY_LANG.get(code, FUNCTION_BY_LANG["en"])


def safety_advice(shoot):
    """What to say when an answer clips: from shoot.audio when the shoot log has it."""
    au = (shoot or {}).get("audio") or {}
    if au.get("safety_channel"):
        off = au.get("safety_offset_db")
        return (f"shoot.audio: dialogue on camera {au.get('mic_camera', '?')} ch{au.get('mic_channel', '?')}, "
                f"safety ch{au['safety_channel']}" + (f" ({off} dB)" if off is not None else "")
                + "; cut and deliver from the channel that doesn't clip")
    return ("if the camera recorded a safety channel (e.g. Sony XLR: ch2 about 6 dB lower), cut and deliver "
            "from that channel instead, and note it in shoot.audio")


def piece(p, words, x, sr, fr, sp, fill_mode, fillers=FILLERS, function=FUNCTION, advice=None):
    a, b, label = p
    sil = ~sp
    flags = []
    # in-point: the silence run nearest a (by its end) in [a-0.5, a+0.3]
    cand = runs(sil, int((a - 0.5) * 100), int((a + 0.3) * 100), 4)
    if cand:
        s0, s1 = min(cand, key=lambda r: (abs(r[1] / 100 - a), -(r[1] - r[0])))
        onset = s1 / 100
        full = silence_around(sil, s0)
        h0 = max(full[0] / 100 if full else s0 / 100, onset - HEAD)
    else:
        onset = h0 = a
        flags.append(f"IN: no silence near {a:.2f}, the first word may be clipped; pick another in-point")
    # out-point: the silence run nearest b (by its start) in [b-0.3, b+0.5]
    cand = runs(sil, int((b - 0.3) * 100), int((b + 0.5) * 100), 4)
    if cand:
        s0, s1 = min(cand, key=lambda r: (abs(r[0] / 100 - b), -(r[1] - r[0])))
        offset = s0 / 100
        full = silence_around(sil, s0)
        t1 = min(full[1] / 100 if full else s1 / 100, offset + TAIL)
    else:
        offset = t1 = b
        flags.append(f"OUT: no silence near {b:.2f}, the last word may be clipped; pick another out-point")
    if onset - h0 < HEAD - 0.02:
        flags.append(f"IN: only {onset - h0:.2f}s of air before the first word (previous word close)")
    if t1 - offset < TAIL - 0.02:
        flags.append(f"OUT: only {t1 - offset:.2f}s of air after the last word")
    ws = [w for w in words if w[1] > onset - 0.3 and w[0] < offset + 0.3]
    cov = np.zeros(len(fr), bool)
    for s, e, _ in ws:
        cov[max(0, int((s - 0.3) * 100)):int((e + 0.3) * 100)] = True
    cuts = []

    def side(t_before):
        """Air to leave on the left of a filler cut: more after a full stop or comma."""
        prev = [w for w in ws if w[1] <= t_before + 0.15 and norm(w[2]) not in fillers]
        pt = prev[-1][2] if prev else ""
        return 0.30 if pt.endswith((".", "?", "!")) else 0.20 if pt.endswith((",", ";", ":")) else FILL_SIDE

    def target(t_before):
        """Total silence wanted across a filler join when one side has none (glued filler)."""
        return KEEP["period"] if side(t_before) == 0.30 else KEEP["comma"] if side(t_before) == 0.20 else 0.24

    def sil_near(t, before):
        """Silence run touching t (within 60 ms, word times from a verbatim model are ~30-40 ms)."""
        for d in range(0, 7):
            k = int(t * 100) + (-1 - d if before else d)
            r = silence_around(sil, k)
            if r and r[1] - r[0] >= 4:
                return r
        return None

    # transcribed fillers ("[um]", "uh") - from a verbatim transcript (verbatim.py) or the rare ones Resolve keeps
    for s, e, t in ws:
        if norm(t) not in fillers or e <= onset or s >= offset:
            continue
        before, after = sil_near(s, True), sil_near(e, False)
        c0 = before[0] / 100 + min(side(s), (before[1] - before[0]) / 200) if before else boundary(x, sr, s - 0.12, s + 0.12, fr)
        c1 = after[1] / 100 - min(FILL_SIDE, (after[1] - after[0]) / 200) if after else boundary(x, sr, e - 0.12, e + 0.12, fr)
        kind = "isolated" if before and after else "run into the next word" if before else "glued to the previous word" if after else "inside continuous speech"
        if c0 is None or c1 is None or c1 <= c0:
            flags.append(f"FILLER '{t}' {s:.2f}-{e:.2f} ({kind}): no clean cut point, another take or leave it")
        elif fill_mode == "cut":
            cuts.append((c0, c1, f"filler '{t}'"))
            flags.append(f"CUT filler '{t}' {s:.2f}-{e:.2f} ({kind}){'; listen closely' if kind != 'isolated' else ''}")
        else:
            flags.append(f"FILLER '{t}' {s:.2f}-{e:.2f} ({kind}): cut {c0:.2f}-{c1:.2f}")
    # untranscribed speech (hidden ums/uhs): the same test as filler_scan.py UNTRANS
    i0, i1 = int(onset * 100), int(offset * 100)
    for u0, u1 in runs(sp & ~cov, i0, i1, 20):
        cv, vo = steadiness(x, sr, u0 / 100, u1 / 100)
        likely = cv is not None and cv < 0.3 and vo > 0.75
        r0, r1 = u0, u1                                  # the whole speech run it sits in
        while r0 > 0 and sp[r0 - 1]:
            r0 -= 1
        while r1 < len(sp) and sp[r1]:
            r1 += 1
        glued_prev, glued_next = r0 < u0 - 15, r1 > u1 + 15   # a real word (>= 0.15 s) runs into it
        before, after = silence_around(sil, r0 - 1), silence_around(sil, r1)
        desc = (f"speech {u0/100:.2f}-{u1/100:.2f} not in the transcript"
                + (f" (steady cv {cv:.2f}, voiced {vo:.0%})" if cv is not None else ""))
        if not likely:
            flags.append(f"CHECK: {desc}; probably a word the transcript missed")
            continue
        if not glued_prev and not glued_next and before and after:
            c0 = before[0] / 100 + min(side(r0 / 100), (before[1] - before[0]) / 200)
            c1 = after[1] / 100 - min(FILL_SIDE, (after[1] - after[0]) / 200)
            if fill_mode == "cut":
                cuts.append((c0, c1, f"filler {u0/100:.2f}-{u1/100:.2f}"))
                flags.append(f"CUT likely filler: {desc}; listen to the join")
            else:
                flags.append(f"LIKELY FILLER: {desc}; isolated, cut {c0:.2f}-{c1:.2f}")
        elif glued_prev and not glued_next and after:
            # "is-uhh": find where the word ends (spectral change, e.g. the /z/ of "is" into the vowel)
            c0 = boundary(x, sr, u0 / 100 - 0.45, u0 / 100 + 0.05, fr, "last")
            c0 = None if c0 is None else round(c0 - 0.02, 3)        # end on the word, not on the filler
            c1 = after[1] / 100 - min(target(u0 / 100), 0.8 * (after[1] - after[0]) / 100)   # all the air comes from this side
            if c0 is not None and fill_mode == "cut":
                cuts.append((c0, c1, f"filler glued to previous word {u0/100:.2f}-{u1/100:.2f}"))
                flags.append(f"CUT filler glued to the previous word ('is-uhh'): {desc}; word ends {c0:.2f}; listen closely")
            else:
                flags.append(f"LIKELY FILLER glued to the previous word ('is-uhh'): {desc}; "
                             + (f"word ends at {c0:.2f}, cut {c0:.2f}-{c1:.2f}" if c0 is not None else "no clear word end: leave it or use another take"))
        elif glued_next and not glued_prev and before:
            # "uh-making": find where the next word starts (spectral change or energy dip, e.g. into the /m/)
            c0 = before[0] / 100 + min(target(r0 / 100), 0.8 * (before[1] - before[0]) / 100)  # all the air comes from this side
            c1 = boundary(x, sr, u1 / 100 - 0.1, u1 / 100 + 0.45, fr, "first")
            if c1 is not None and fill_mode == "cut":
                cuts.append((c0, c1, f"filler run into next word {u0/100:.2f}-{u1/100:.2f}"))
                flags.append(f"CUT filler run into the next word ('uh-making'): {desc}; word starts {c1:.2f}; listen closely")
            else:
                flags.append(f"LIKELY FILLER run into the next word ('uh-making'): {desc}; "
                             + (f"word starts at {c1:.2f}, cut {c0:.2f}-{c1:.2f}" if c1 is not None else "no clear word start: leave it or use another take"))
        else:
            flags.append(f"LIKELY FILLER inside continuous speech: {desc}; another take or leave it, tell the editor")
    # stutters: the same word twice in a row ("and and", "the the") -> keep the second
    inner = [w for w in ws if w[0] >= onset - 0.3 and w[1] <= offset + 0.3]
    for w1, w2 in zip(inner, inner[1:]):
        if not norm(w1[2]) or norm(w1[2]) != norm(w2[2]):
            continue
        s1 = runs(sil, int((w1[0] - 0.4) * 100), int((w1[0] + 0.3) * 100), 4)
        s2 = runs(sil, int((w2[0] - 0.4) * 100), int((w2[0] + 0.3) * 100), 4)
        if not s1 or not s2:
            flags.append(f"STUTTER '{w1[2]} {w2[2]}' at {w1[0]:.2f}: no clean gap, check by ear")
            continue
        b1 = silence_around(sil, min(s1, key=lambda r: abs(r[1] / 100 - w1[0]))[0])
        b2 = silence_around(sil, min(s2, key=lambda r: abs(r[1] / 100 - w2[0]))[0])
        if b1 == b2:
            continue
        c0 = b1[0] / 100 + min(FILL_SIDE, (b1[1] - b1[0]) / 200)
        c1 = b2[1] / 100 - min(FILL_SIDE, (b2[1] - b2[0]) / 200)
        if fill_mode == "cut" and norm(w1[2]) in function:
            cuts.append((c0, c1, f"stutter '{w1[2]} {w2[2]}'"))
            flags.append(f"CUT stutter '{w1[2]} {w2[2]}' at {w1[0]:.2f}; listen to the join")
        else:
            flags.append(f"STUTTER '{w1[2]} {w2[2]}' at {w1[0]:.2f}: cut {c0:.2f}-{c1:.2f} to keep the second")
    # hesitations
    for g0, g1 in runs(sil, int(onset * 100), int(offset * 100), 25):
        g0, g1 = g0 / 100, g1 / 100
        if any(c0 < g1 and c1 > g0 for c0, c1, _ in cuts):
            continue
        prev = [w for w in ws if w[1] <= g0 + 0.25]
        pt = prev[-1][2] if prev else ""
        keep = KEEP["period"] if pt.endswith((".", "?", "!")) else KEEP["comma"] if pt.endswith((",", ";", ":")) else KEEP["mid"]
        if g1 - g0 > keep + 0.12:                    # don't make a join for less than 0.12 s
            cuts.append((g0 + keep / 2, g1 - keep / 2, f"pause {g1 - g0:.2f}s after '{pt}'"))
    merged = []
    for c in sorted(cuts):
        if merged and c[0] <= merged[-1][1]:
            m = merged[-1]
            merged[-1] = (m[0], max(m[1], c[1]), m[2] + " + " + c[2])
        else:
            merged.append(c)
    subs, cur = [], h0
    for c0, c1, why in merged:
        subs.append([round(cur, 3), round(c0, 3), why])
        cur = c1
    subs.append([round(cur, 3), round(t1, 3), ""])
    subs = [s for s in subs if s[1] - s[0] > 0.04]
    clip = int((np.abs(x[int(h0 * sr):int(t1 * sr)]) >= 0.999).sum())
    if clip:
        flags.append(f"AUDIO: {clip} clipped samples in this answer; " + (advice or safety_advice(None)))
    return {"label": label, "onset": round(onset, 3), "offset": round(offset, 3),
            "text": " ".join(w[2] for w in ws if w[0] >= onset - 0.3 and w[1] <= offset + 0.3),
            "subs": subs, "flags": flags}


def settings(plan, a):
    """(src_fps, tl_fps, shoot, lang) from the flags, the plan, the job card and the shoot log."""
    card_path = a.card or plan.get("card")
    card = bc.load_card(card_path) if bc and card_path else {}
    shoot = bc.load_shoot(a.shoot or plan.get("shoot") or card.get("Shoot")) if bc else {}
    tfps = a.tl_fps or plan.get("tl_fps") or (bc.delivery(card)["fps"] if bc and card else 24)
    sfps = plan.get("src_fps")
    if sfps is None:
        cams = {c.get("role"): c for c in shoot.get("cameras") or []}
        mic = cams.get((shoot.get("audio") or {}).get("mic_camera")) or {}
        sfps = tfps if (shoot.get("multicam") or {}).get("exists") else mic.get("fps") or 25
        print(f"src_fps not in the plan: using {sfps} (check it matches the clip you append)")
    lang = a.lang or plan.get("lang") or job_language(None, a.shoot or plan.get("shoot"), card_path)
    return float(sfps), float(tfps), shoot, lang


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan"); ap.add_argument("out", nargs="?")
    ap.add_argument("--card", help="job card: tl_fps from its Delivery line / client profile")
    ap.add_argument("--shoot", help="shoot folder: shoot.audio, shoot.multicam, shoot.cameras, shoot.language")
    ap.add_argument("--lang", help="language code for the filler lists (default: shoot / client / en)")
    ap.add_argument("--tl-fps", type=float, help="timeline fps (overrides the plan and the card)")
    a = ap.parse_args()
    need_numpy()
    plan = json.load(open(a.plan))
    sfps, tfps, shoot, lang = settings(plan, a)
    fillers, function, advice = fillers_for(lang), function_for(lang), safety_advice(shoot)
    words = load_words(plan["transcript"])
    x, sr = load_audio(plan["wav"])
    fr = energy(x, sr)
    sp = clean(fr > np.percentile(fr, 10) + 12)
    off = float(plan.get("src_offset", 0))
    rec, track = int(plan.get("record_start", 0)), int(plan.get("track", 1))
    out = {k: plan.get(k) for k in ("video", "wav", "transcript", "src_offset", "pans")}
    out["src_fps"], out["tl_fps"] = sfps, tfps
    out["pieces"], out["append"] = [], []
    for p in plan["pieces"]:
        r = piece(p, words, x, sr, fr, sp, plan.get("fillers", "flag"), fillers, function, advice)
        for s in r["subs"]:
            D = int(round((s[1] - s[0]) * tfps))
            sf = int(round((s[0] + off) * sfps))
            out["append"].append({"startFrame": sf, "endFrame": sf + math.ceil(D * sfps / tfps),
                                  "recordFrame": rec, "trackIndex": track, "label": r["label"],
                                  "src": [s[0], s[1]]})
            s.append(rec)
            rec += D
        out["pieces"].append(r)
        dur = sum(s[1] - s[0] for s in r["subs"])
        print(f"{r['label']}: {r['text'][:100]}")
        print(f"   words {r['onset']:.2f}-{r['offset']:.2f}  {len(r['subs'])} sub-pieces  {dur:.2f}s")
        for s in r["subs"]:
            print(f"     {s[0]:8.2f}-{s[1]:8.2f}  rec {s[3]:5d}  {s[2]}")
        for f in r["flags"]:
            print("   !", f)
    out["record_end"] = rec
    print(f"total {(rec - int(plan.get('record_start', 0))) / tfps:.2f}s, ends at record frame {rec}")
    dst = a.out or os.path.splitext(a.plan)[0] + "_cut.json"
    json.dump(out, open(dst, "w"), indent=1)
    print("wrote", dst)


if __name__ == "__main__":
    main()
