#!/usr/bin/env python3
"""Check every caption start against the pauses in the speech, measured from the audio level (not
whisper, whose word times run up to ~12 frames off: Simone C03b "Like, it's marketing 101." went up
9 frames early, over the end of "essential", because whisper put "Like" inside the word before).

usage: check_caption_starts.py WORK/<name>_state.json OUT_DIR/tl.wav [--fix PLAN.json]
(state from export_state.py, tl.wav from timeline_audio.py)

A caption is EARLY when she is still finishing the previous line (or silent) at its start and starts
its first word after a pause that ends within 14 frames after it; LATE when a pause ended more than 4
frames before it and it starts mid-word. The right start is 1 frame before speech resumes, or a
picture cut from 8 frames before that onset to 6 after (cuts win inside that window).
Every flag is confirmed by ear before it counts: the stretch between the caption's start and the
proposed one is transcribed. EARLY is real only when that stretch doesn't already hold the caption's
first word; LATE is real only when the stretch opens on that word (she says it before the caption appears; C03f
"difference in" means the break has no pause, not that the caption is late).
--fix writes a retime_captions_drt.py plan that moves only the confirmed starts (the caption before
each one ends there), leaving text and every other caption as they are.
"""
import json, sys, wave, array, math

state, wav = sys.argv[1], sys.argv[2]
fix = sys.argv[sys.argv.index("--fix") + 1] if "--fix" in sys.argv else None
s = json.load(open(state)); fps = s.get("fps", 24)
sub = min(c[3] for c in s["caps"]); caps = sorted(c for c in s["caps"] if c[3] == sub)
cuts = sorted({a for a, _ in s["v1"]} - {0})
w = wave.open(wav); sr = w.getframerate(); a = array.array("h"); a.frombytes(w.readframes(w.getnframes()))
hop = int(sr / fps)
env = [10 * math.log10(sum(x * x for x in a[i:i + hop:2]) / (hop / 2) / 32768 ** 2 + 1e-12) for i in range(0, len(a) - hop, hop)]
quiet = sorted(env)[len(env) // 10] + 10
loud = lambda k: 0 <= k < len(env) and env[k] >= quiet
# speech onsets: first loud frame after >= 3 quiet frames
onsets = [k for k in range(3, len(env)) if loud(k) and not any(loud(j) for j in range(k - 3, k))]


def right_start(o):
    near = [c for c in cuts if o - 8 <= c <= o + 6]
    return min(near, key=lambda c: abs(c - o)) if near else o - 1


moves = {}
for i, c in enumerate(caps[1:], 1):
    st = c[0]
    after = [o for o in onsets if st < o <= st + 14]
    before = [o for o in onsets if st - 14 <= o <= st]
    if after and not any(loud(k) for k in range(max(0, after[0] - 3), after[0])) and not (before and st - before[-1] <= 4):
        want = right_start(after[0])
        if want - st >= 3:
            moves[i] = ("EARLY", st, want)
    elif before and loud(st) and st - before[-1] > 4:
        want = right_start(before[-1])
        if st - want >= 5:
            moves[i] = ("LATE", st, want)


def heard(a, b):
    """Transcribe frames a..b of the timeline audio (padded so whisper runs)."""
    import subprocess, tempfile, os
    d = tempfile.mkdtemp()
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{a / fps:.3f}", "-t", f"{(b - a) / fps:.3f}", "-i", wav,
                    "-af", "apad=pad_dur=1", f"{d}/w.wav"], check=True)
    r = subprocess.run(["whisper-cli", "-m", os.path.expanduser("~/whisper-models/ggml-large-v3.bin"), "-l", "en", "-nt", "-np", f"{d}/w.wav"],
                       capture_output=True, text=True)
    return r.stdout.strip()


norm = lambda t: "".join(ch for ch in t.lower() if ch.isalnum())
# Confirm each EARLY flag by ear (Simone C03, 10 Nov: 9 of 14 flags were real; soft first words like
# "so", "of", "that" and a muted swear also read as pauses): transcribe the stretch between the
# caption's start and the proposed one. If it holds the caption's own first word, the start is right.
for i in list(moves):
    kind, st, want = moves[i]
    first = norm(caps[i][2].split()[0])
    if "*" in caps[i][2]:                                  # a bleeped word is silence in A1: never trust the gap
        print(f"{s['name']} [{i}] has a bleeped word, so its pause can't be trusted: left alone, listen to it")
        del moves[i]; continue
    if kind == "EARLY":
        got = heard(max(0, st - 6), want + 1)
        has = first and first in [norm(w) for w in got.split()]
        if has:
            print(f"{s['name']} [{i}] looks early but '{got}' already holds its first word: left alone")
            del moves[i]; continue
    else:
        got = heard(max(0, want - 2), st + 1)
        has = first and got.split() and norm(got.split()[0]) == first    # the stretch must OPEN on her first word
        if not has:
            print(f"{s['name']} [{i}] looks late but '{got}' doesn't hold its first word yet: left alone")
            del moves[i]; continue
    moves[i] = (kind, st, want, got)
for i, m in moves.items():
    kind, st, want = m[:3]
    extra = f"  (heard in between: {m[3]!r})" if len(m) > 3 else ""
    print(f"{s['name']} [{i}] {kind} by {abs(want - st)} frames: {st} -> {want}  {caps[i][2]!r}{extra}")
print(f"{s['name']}: {len(moves)} of {len(caps)} caption starts off the speech")
if fix:
    starts = [c[0] for c in caps]
    for i, m in moves.items():
        starts[i] = m[2]
    ok = all(b - a >= 12 for a, b in zip(starts, starts[1:] + [caps[-1][1]]))
    plan = [{"old": [c[0], c[2]], "new": [starts[i], starts[i + 1] if i + 1 < len(caps) else c[1], c[2]]} for i, c in enumerate(caps)]
    json.dump(plan, open(fix, "w"), indent=1)
    print("plan written" + ("" if ok else " (WARNING: a caption is now under 12 frames, check it)"))
