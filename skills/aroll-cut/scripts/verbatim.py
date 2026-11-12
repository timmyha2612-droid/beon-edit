#!/usr/bin/env python3
"""Verbatim, word-timed transcript (keeps um, uh, stutters, cut-offs) of the interview ranges you plan to use.
usage: <crisperwhisper python> verbatim.py MODEL_DIR AUDIO.wav OUT.json A-B [A-B ...] [--pad 0.6] [--budget 150]
       [--dtype float32] [--lang en]
  MODEL_DIR  a local CrisperWhisper 2.0 folder (config.json, model.safetensors, tokenizer files, ...),
             or "auto" for editor.json tools.crisperwhisper.model_dir; run the script with
             tools.crisperwhisper.python (e.g. ~/cw/bin/python). If run_env is device-vm, the editor
             downloads the folder on the Mac (Hugging Face is blocked in the VM and the cloud workspace)
  AUDIO.wav  mono 16 kHz mic channel, time 0 = source clip start (same file cut_pieces.py uses)
  A-B        source-second ranges (the answers in the plan); each is padded by --pad on both sides
Writes OUT.json as {"engine": ..., "words": [{"start", "end", "text"}], "done": ["A-B", ...]} in source
seconds, the format cut_pieces.py and filler_scan.py read. Fillers come out as "[um]", "[uh]".
Resumable: ranges already in OUT.json are skipped and the script stops itself at --budget seconds
(if run_env is device-vm, device_bash calls are short), so run it again until it prints DONE.
--lang: the shoot's language (shoot.language, default en); a regional code like en-AU is cut to en.
Setup (once; if run_env is device-vm, aarch64): python3 -m venv ~/cw && ~/cw/bin/pip install --no-cache-dir
"torch==2.5.1" "crisperwhisper[transformers]==2.0.3"  (newer aarch64 torch wheels pull GBs of CUDA;
the ct2 backend has x86_64 wheels only).
LICENCE: the inference code is MIT, the CrisperWhisper 2.0 weights are Nyra's non-commercial research
licence. Client work needs a commercial licence from Nyra in place before this runs on it
(editor.json tools.crisperwhisper.licence: true); the script warns when it isn't recorded."""
import argparse, json, os, pathlib, sys, time

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("model", help='CrisperWhisper 2.0 folder, or "auto" for editor.json tools.crisperwhisper.model_dir')
ap.add_argument("wav"); ap.add_argument("out"); ap.add_argument("ranges", nargs="+")
ap.add_argument("--pad", type=float, default=0.6); ap.add_argument("--budget", type=float, default=150)
ap.add_argument("--dtype", default="float32"); ap.add_argument("--lang", default="en")
a = ap.parse_args()
LANG = (a.lang or "en").lower().split("-")[0].split("_")[0]   # en-AU -> en; Whisper takes base codes only
T0 = time.time()
try:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "house-rules" / "scripts"))
    import beon_config as bc
    cw = (bc.load_editor().get("tools") or {}).get("crisperwhisper") or {}
except ImportError:          # copied somewhere without the plugin (e.g. a VM): pass MODEL_DIR explicitly
    cw = {}
if a.model == "auto":
    if not cw.get("model_dir"):
        sys.exit('MODEL_DIR "auto" needs tools.crisperwhisper.model_dir in ~/.beon-edit/editor.json')
    a.model = os.path.expanduser(cw["model_dir"])
if cw.get("licence") is not True:
    print("NOTE: no commercial CrisperWhisper licence recorded (editor.json tools.crisperwhisper.licence); "
          "don't use this on client work until there is one", file=sys.stderr)
import numpy as np
import soundfile as sf
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
        out = model.transcribe(seg, sr=sr, language=LANG, mode="verbatim", word_timestamps=True)
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
