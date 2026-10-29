"""Export each timeline's transcript words (mapped through its audio cuts) for hand captions.

Run inside Resolve (run_script_unsafe) with `resolve`, `project`, `WORK` (work folder) and
`NAMES` (timeline names, or name prefixes) injected. Uses Resolve's own word-timed
transcription of the clips on audio track 1 (TranscribeAudio, reused once done).
Writes WORK/words.json:
  {timeline name: {start, end, cuts: [(start, end)], words: [(t0, t1, text)]}}
with every frame relative to the timeline start.
"""
import json
import os



def load_auto(path):
    src = open(path).read()
    ns = {"resolve": resolve, "__name__": "lib"}  # noqa: F821
    exec(compile(src, path, "exec"), ns)
    return ns


def export(auto_path):
    ns = load_auto(auto_path)
    out = {}
    for i in range(1, project.GetTimelineCount() + 1):  # noqa: F821
        t = project.GetTimelineByIndex(i)  # noqa: F821
        if not any(t.GetName().startswith(n) for n in NAMES) or t.GetName().endswith("Subtitles"):  # noqa: F821
            continue
        items = ns["timeline_words"](t)
        ns["ensure_transcripts"](project, items, print)  # noqa: F821
        words = ns["map_words"](items, ns["fps_of"](t))
        b = t.GetStartFrame()
        out[t.GetName()] = {"start": b, "end": t.GetEndFrame(),
                            "cuts": [(c.GetStart() - b, c.GetEnd() - b) for c in items],
                            "words": [(w["t0"] - b, w["t1"] - b, w["text"]) for w in words]}
    os.makedirs(WORK, exist_ok=True)  # noqa: F821
    json.dump(out, open(os.path.join(WORK, "words.json"), "w"))  # noqa: F821
    return {k: len(v["words"]) for k, v in out.items()}
