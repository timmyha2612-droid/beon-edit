#!/usr/bin/env python3
"""Rebuild a timeline's A1 audio exactly as it plays and transcribe it, so every word time is a
timeline frame. Holes in A1 become silence.
usage: timeline_audio.py WORK/<name>_state.json OUT_DIR [--model PATH] [--card JOB_CARD.md] [--lang en]
(model: editor.json tools.whisper.model, else ~/whisper-models/ggml-large-v3.bin; language: shoot / client
profile via --card, else en)
Writes OUT_DIR/tl.wav (16 kHz mono, channel 1 of each clip) and OUT_DIR/tl.json (whisper-cli -ojf)."""
import argparse, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subs_intake  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("state"); ap.add_argument("out")
ap.add_argument("--model", default=subs_intake.whisper_model())
ap.add_argument("--card", help="job card: language from its shoot / client profile")
ap.add_argument("--lang", help="whisper language (default: from --card, else en)")
a = ap.parse_args()
lang = a.lang or subs_intake.language(a.card)
s = json.load(open(a.state)); fps = s["fps"]; os.makedirs(a.out, exist_ok=True)
srcs = sorted({x["src"] for x in s["a1"]}); idx = {p: i for i, p in enumerate(srcs)}
f, parts, t = [], [], 0
for i, x in enumerate(sorted(s["a1"], key=lambda x: x["rec0"])):
    if x["rec0"] > t:
        f.append(f"anullsrc=r=48000:cl=mono,atrim=duration={(x['rec0'] - t) / fps:.4f}[g{i}]"); parts.append(f"[g{i}]")
    f.append(f"[{idx[x['src']]}:a]atrim=start={x['t0']:.4f}:duration={(x['rec1'] - x['rec0']) / fps:.4f},"
             f"asetpts=PTS-STARTPTS,pan=mono|c0=c0,aresample=48000[a{i}]"); parts.append(f"[a{i}]")
    t = x["rec1"]
fc = ";".join(f) + ";" + "".join(parts) + f"concat=n={len(parts)}:v=0:a=1,aresample=16000[o]"
cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y"]
for p in srcs:
    cmd += ["-i", p]
subprocess.run(cmd + ["-filter_complex", fc, "-map", "[o]", f"{a.out}/tl.wav"], check=True)
subprocess.run(["whisper-cli", "-m", a.model, "-l", lang, "-mc", "0", "-ojf", "-of", f"{a.out}/tl", f"{a.out}/tl.wav"],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(f"{s['name']}: {t / fps:.2f} s of audio -> {a.out}/tl.wav, tl.json")
