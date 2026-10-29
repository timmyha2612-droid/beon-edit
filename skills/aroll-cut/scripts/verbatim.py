#!/usr/bin/env python3
"""Verbatim, word-timed transcript (keeps um, uh, stutters, cut-offs) of the interview ranges you plan to use.
usage: ~/cw/bin/python verbatim.py MODEL_DIR AUDIO.wav OUT.json A-B [A-B ...] [--pad 0.6] [--budget 150] [--dtype float32]
  MODEL_DIR  a local CrisperWhisper 2.0 folder (config.json, model.safetensors, tokenizer files, ...)
             downloaded by Tim (Hugging Face is blocked in the VM and the cloud workspace)
  AUDIO.wav  mono 16 kHz mic channel, time 0 = source clip start (same file cut_pieces.py uses)
  A-B        source-second ranges (the answers in the plan); each is padded by --pad on both sides
Writes OUT.json as {"engine": ..., "words": [{"start", "end", "text"}], "done": ["A-B", ...]} in source
seconds, the format cut_pieces.py and filler_scan.py read. Fillers come out as "[um]", "[uh]".
Resumable: ranges already in OUT.json are skipped and the script stops itself at --budget seconds
(device_bash calls are short), so run it again until it prints DONE.
Setup (device VM, aarch64, once): python3 -m venv ~/cw && ~/cw/bin/pip install --no-cache-dir
"torch==2.5.1" "crisperwhisper[transformers]==2.0.3"  (newer aarch64 torch wheels pull GBs of CUDA;
the ct2 backend has x86_64 wheels only).
LICENCE: the inference code is MIT, the CrisperWhisper 2.0 weights are Nyra's non-commercial research
licence. Client work needs Tim's commercial licence from Nyra in place before this runs on it."""
import argparse, json, os, time
import numpy as np
import soundfile as sf

ap = argparse.ArgumentParser()
ap.add_argument("model"); ap.add_argument("wav"); ap.add_argument("out"); ap.add_argument("ranges", nargs="+")
ap.add_argument("--pad", type=float, default=0.6); ap.add_argument("--budget", type=float, default=150)
ap.add_argument("--dtype", default="float32")
a = ap.parse_args()
T0 = time.time()
res = json.load(open(a.out)) if os.path.exists(a.out) else {"engine": os.path.basename(a.model.rstrip("/")), "words": [], "done": []}
todo = [r for r in a.ranges if r not in res["done"]]
if todo:
    import torch
    torch.set_num_threads(os.cpu_count() or 4)
    from crisperwhisper import CrisperWhisperModel
    model = CrisperWhisperModel(a.model, backend="transformers", device="cpu", compute_type=a.dtype)
    x, sr = sf.read(a.wav, dtype="float32")
    if x.ndim > 1:
        x = x[:, 0]
    for r in todo:
        if time.time() - T0 > a.budget:
            break
        lo, hi = (float(v) for v in r.split("-"))
        s0 = max(0.0, lo - a.pad); s1 = min(len(x) / sr, hi + a.pad)
        seg = x[int(s0 * sr):int(s1 * sr)]
        out = model.transcribe(seg, sr=sr, language="en", mode="verbatim", word_timestamps=True)
        for w in out.words or []:
            if w.start is None or w.end is None:
                continue
            res["words"].append({"start": round(s0 + w.start, 3), "end": round(s0 + w.end, 3), "text": w.word.strip() if hasattr(w, "word") else str(w.text).strip()})
        res["done"].append(r)
        print(f"{r}: {out.text[:160]}")
        json.dump(res, open(a.out, "w"), indent=0)
res["words"] = sorted({(w["start"], w["end"], w["text"]): w for w in res["words"]}.values(), key=lambda w: w["start"])
json.dump(res, open(a.out, "w"), indent=0)
left = [r for r in a.ranges if r not in res["done"]]
print("DONE" if not left else f"PARTIAL ({len(left)} ranges left) - run again", f"{time.time() - T0:.0f}s")
