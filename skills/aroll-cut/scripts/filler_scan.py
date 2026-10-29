#!/usr/bin/env python3
"""List likely ums, uhs, stutters and false starts inside the A-roll pieces you plan to use.
usage: filler_scan.py TRANSCRIPT.json AUDIO.wav [A-B ...]
TRANSCRIPT.json: word-timed transcript, either Resolve's MediaPoolItem.GetTranscription(True)
  saved as {"fps": 25, "start_tc": "07:34:33:03", "segments": [{"words": [{"start": tc, "end": tc,
  "text": ..}]}]} (the shot-log transcripts/ format), or {"words": [{"start": s, "end": s, "text": ..}]}
  in seconds.
AUDIO.wav: mono 16 kHz from the interview's mic channel (ffmpeg -i clip -map 0:a:0 -af "pan=mono|c0=c0" -ar 16000 a.wav).
A-B: optional source-second ranges to scan (the answers you plan to use); default = whole clip.
Transcripts usually DROP fillers, so the scan also looks at the audio:
  FILLER    a transcribed um/uh/er/ah/mm
  UNTRANS   speech energy that no transcribed word covers, even allowing 0.3 s of word-time drift
  STRETCH   a word held far longer than normal ("aaand", "feeeel ..."), often a hidden hesitation
  REPEAT    the same word or two-word phrase said twice in a row (stutter / restart)
  PAUSE     a silent gap >= 0.3 s mid-sentence (hesitation; see the cutting rules)
UNTRANS lines carry a steadiness check: an "uh"/"um" is one held, voiced vowel or hum, so its
spectral centroid barely moves (variation < 0.3), while short real words with consonants vary 0.4-1.0
(calibrated on Arriva Oct C1, Azar). It only works on short isolated sounds, not on whole phrases.
Each line gives the source time to look at. Check before cutting and keep the speech flowing."""
import json, re, sys, wave
import numpy as np

FILLERS = {"um", "uh", "uhm", "umm", "uhh", "er", "erm", "ah", "eh", "hmm", "mm", "mhm"}

def tc_s(tc, fps):
    h, m, s, f = [int(x) for x in tc.split(":")]
    return (h * 3600 + m * 60 + s) + f / fps

def load_words(path):
    j = json.load(open(path))
    if "words" in j:
        return [(float(w["start"]), float(w["end"]), w["text"].strip()) for w in j["words"]]
    fps = float(j.get("fps") or 25); st = tc_s(j["start_tc"], fps)
    out = []
    for s in j["segments"]:
        for w in s.get("words", []):
            t = w["text"].strip()
            if t and t != "(...)":
                out.append((tc_s(w["start"], fps) - st, tc_s(w["end"], fps) - st, t))
    return out

def load_audio(path):
    w = wave.open(path)
    return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768, w.getframerate()

def energy(x, sr):
    hop = sr // 100; n = len(x) // hop
    return 20 * np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)

def steadiness(x, sr, a, b):
    """(centroid variation, voiced fraction) for a stretch of audio; fillers: cv < 0.3, voiced > 0.75."""
    seg = x[int(a * sr):int(b * sr)]; n = int(0.032 * sr); hop = int(0.01 * sr)
    if len(seg) < n + 3 * hop:
        return None, None
    fr = np.array([seg[i:i + n] * np.hanning(n) for i in range(0, len(seg) - n, hop)])
    S = np.abs(np.fft.rfft(fr, axis=1))[:, :n // 4] + 1e-6
    f = np.fft.rfftfreq(n, 1 / sr)[:n // 4]
    cen = (S * f).sum(1) / S.sum(1)
    lo, hi = int(sr / 400), int(sr / 70); voiced = 0
    for v in fr:
        ac = np.correlate(v, v, "full")[n - 1:]
        k = lo + int(np.argmax(ac[lo:hi]))
        voiced += ac[k] > 0.3 * ac[0]
    return float(np.std(cen) / np.mean(cen)), voiced / len(fr)

def tag(x, sr, a, b):
    cv, vo = steadiness(x, sr, a, b)
    if cv is None:
        return ""
    return f" [steady cv {cv:.2f}, voiced {vo:.0%}{', likely filler' if cv < 0.3 and vo > 0.75 else ''}]"

def norm(t):
    return re.sub(r"[^a-z0-9']", "", t.lower())

def main():
    words = load_words(sys.argv[1]); x, sr = load_audio(sys.argv[2]); fr = energy(x, sr)
    thr = np.percentile(fr, 10) + 12; sp = fr > thr
    rng = [tuple(float(v) for v in r.split("-")) for r in sys.argv[3:]] or [(0, len(fr) / 100)]
    hits = []
    for a, b in rng:
        ws = [w for w in words if w[1] >= a - 0.3 and w[0] <= b + 0.3]   # every word touching the range
        for i, (s, e, t) in enumerate(ws):
            n = norm(t)
            if n in FILLERS:
                hits.append((s, "FILLER", f"'{t}' {s:.2f}-{e:.2f}"))
            d = e - s
            if (d > 0.55 and len(n) <= 4) or d > 0.9:
                hits.append((s, "STRETCH", f"'{t}' held {d:.2f}s ({s:.2f}-{e:.2f}): check for a drawn-out vowel or a hidden 'uh'"))
            if i and n and n == norm(ws[i - 1][2]):
                hits.append((s, "REPEAT", f"'{ws[i-1][2]} {t}' at {ws[i-1][0]:.2f}"))
            if i >= 3 and n and [norm(w[2]) for w in ws[i - 1:i + 1]] == [norm(w[2]) for w in ws[i - 3:i - 1]]:
                hits.append((s, "REPEAT", f"'{ws[i-3][2]} {ws[i-2][2]}' twice from {ws[i-3][0]:.2f}"))
            if i:
                gap = s - ws[i - 1][1]
                if gap >= 0.3 and not ws[i - 1][2].endswith((".", "?", "!", ",")):
                    hits.append((ws[i - 1][1], "PAUSE", f"{gap:.2f}s between '{ws[i-1][2]}' and '{t}'"))
        cov = np.zeros(len(fr), bool)
        for s, e, _ in ws:
            cov[max(0, int((s - 0.3) * 100)):int((e + 0.3) * 100)] = True   # word times drift up to ~0.3 s
        k = int(a * 100); end = min(len(fr), int(b * 100))
        while k < end:
            if sp[k] and not cov[k]:
                k0 = k
                while k < end and sp[k] and not cov[k]:
                    k += 1
                if k - k0 >= 20:
                    hits.append((k0 / 100, "UNTRANS", f"speech {k0/100:.2f}-{k/100:.2f} ({(k-k0)/100:.2f}s, peak {fr[k0:k].max():.0f} dB) outside every transcribed word" + tag(x, sr, k0 / 100, k / 100)))
            k += 1
    for t, kind, msg in sorted(set(hits)):
        print(f"{t:8.2f}  {kind:8s} {msg}")
    if not hits:
        print("no candidates found")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main()
