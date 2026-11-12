"""Resync Subtitles - re-time Fluid Reveal Words subtitles to the speech after you edit.

Run from Workspace > Scripts > Edit > Resync Subtitles on the Edit page, any time after
you trim, blade, move or retype subtitles, or re-cut the audio. For every Fluid Reveal
Words title on the timeline (or only the selected ones), it matches the title's words to
the transcript of audio track 1 under the title's current position and sets each word
to reveal when it is spoken.

It only changes values inside the titles: it never adds, moves or deletes clips, never
switches page or timeline, and never touches anything else.
"""
import difflib
import re

# Runs inside Resolve, so it can't read the intake files: fps comes from the timeline and each clip,
# words from Resolve's transcript of A1 (language: Resolve's project setting, set from shoot.language /
# the client profile). The timing constants below are Beon house rules.
GROUP = "FluidRevealWords"
LEAD = 2          # words start revealing this many frames before they are spoken
MIN_GAP = 4       # words always reveal one at a time, at least this many frames apart
MIN_SHOW = 6      # every word is on screen at least this long before the caption exits
MAX_WORDS = 12
SEARCH_PAD = 12   # frames either side of a title to look for its words


def get_resolve():
    r = globals().get("resolve")
    if r:
        return r
    try:
        return app.GetResolve()  # noqa: F821 - injected by Resolve's script menu
    except Exception:
        pass
    try:
        return bmd.scriptapp("Resolve")  # noqa: F821
    except Exception:
        pass
    import DaVinciResolveScript as dvr
    return dvr.scriptapp("Resolve")


def tc_to_frames(tc, fps):
    h, m, s, f = (int(x) for x in re.split("[:;]", tc))
    return ((h * 60 + m) * 60 + s) * round(fps) + f


def norm(text):
    return re.sub(r"[^a-z0-9']", "", text.lower().replace("’", "'"))


def tokens_of(text):
    """Display tokens (one per word layer) and the spoken words each stands for."""
    out = []
    for tok in text.split():
        parts = [norm(p) for p in re.split(r"[-–—]", tok) if norm(p)]
        out.append(parts or [norm(tok)])
    return out


def timeline_words(timeline):
    """Transcript words mapped onto the timeline through the cuts on audio track 1."""
    words, cache = [], {}
    tl_fps = float(timeline.GetSetting("timelineFrameRate") or 24)
    for it in timeline.GetItemListInTrack("audio", 1) or []:
        m = it.GetMediaPoolItem()
        if not m:
            continue
        key = m.GetUniqueId()
        if key not in cache:
            fps = float(m.GetClipProperty("FPS") or 24)
            # Words carry the clip's own timecode: count from the clip's first frame instead.
            origin = tc_to_frames(m.GetClipProperty("Start TC") or "00:00:00:00", fps)
            tr = m.GetTranscription() or {}
            cache[key] = (fps, [(tc_to_frames(w["start"], fps) - origin, tc_to_frames(w["end"], fps) - origin, w["text"].strip())
                                for seg in tr.get("segments", []) for w in seg.get("words", [])])
        fps, src_words = cache[key]
        k = tl_fps / fps                     # e.g. 25p camera clip on a 24p timeline
        s, e = it.GetSourceStartFrame(), it.GetSourceEndFrame()
        for ws, we, text in src_words:
            if text and text != "(...)" and s <= (ws + we) / 2 < e:
                words.append((it.GetStart() + round(max(0, ws - s) * k), norm(text)))
    return sorted(words)


def subtitle_items(timeline):
    selected = [i for i in (timeline.GetSelectedClips() or []) if is_subtitle(i)]
    if selected:
        return selected
    items = []
    for t in range(1, timeline.GetTrackCount("video") + 1):
        items += [i for i in (timeline.GetItemListInTrack("video", t) or []) if is_subtitle(i)]
    return items


def is_subtitle(item):
    try:
        return item.GetFusionCompCount() > 0 and item.GetFusionCompByIndex(1).FindTool(GROUP) is not None
    except Exception:
        return False


def word_frames(item, words):
    """Timeline frame each display token is spoken at (aligned by text, gaps interpolated)."""
    comp = item.GetFusionCompByIndex(1)
    text = comp.FindTool(GROUP).GetInput("TextContent") or ""
    toks = tokens_of(text)
    start, end = item.GetStart(), item.GetEnd()
    near = [(f, w) for f, w in words if start - SEARCH_PAD <= f < end + SEARCH_PAD]
    flat = [(i, p) for i, parts in enumerate(toks) for p in parts]
    sm = difflib.SequenceMatcher(None, [p for _, p in flat], [w for _, w in near], autojunk=False)
    frames = [None] * len(toks)
    exact = [False] * len(toks)
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        for k in range(a2 - a1):
            ti = flat[a1 + k][0]
            if frames[ti] is not None:
                continue
            if op == "equal":
                frames[ti], exact[ti] = near[b1 + k][0], True
            elif op == "replace" and b2 > b1:
                # Retyped or misheard word ("rate" vs transcript "right"): take the replaced word's time.
                frames[ti] = near[b1 + min(k * (b2 - b1) // (a2 - a1), b2 - b1 - 1)][0]
    matched = sum(exact)
    # Unmatched tokens (retyped words, words the transcript missed): place them between neighbours.
    for i in range(len(frames)):
        if frames[i] is None:
            prev = next((frames[j] for j in range(i - 1, -1, -1) if frames[j] is not None), start)
            nxt = next((frames[j] for j in range(i + 1, len(frames)) if frames[j] is not None), None)
            frames[i] = prev if nxt is None else (prev + nxt) // 2
    # Never earlier than the title or out of order.
    for i in range(len(frames)):
        frames[i] = max(frames[i], start, frames[i - 1] if i else start)
    return comp, frames, matched, len(toks)


def spread(times, latest, gap=MIN_GAP):
    """Spoken times, nudged so words always reveal one at a time (>= gap frames apart)
    and no later than `latest`. Falls back to an even spread when the caption is too short."""
    t = [max(0, x) for x in times]
    for i in range(1, len(t)):
        t[i] = max(t[i], t[i - 1] + gap)
    if t and t[-1] > latest:
        t[-1] = latest
        for i in range(len(t) - 2, -1, -1):
            t[i] = min(t[i], t[i + 1] - gap)
    if t and t[0] < 0:
        step = latest / max(len(t) - 1, 1)
        t = [round(i * step) for i in range(len(t))]
    return t


def min_gap(t):
    return min((b - a for a, b in zip(t, t[1:])), default=MIN_GAP)


def apply(item, comp, frames):
    a = comp.GetAttrs()
    render_start, render_end = a["COMPN_RenderStart"], a["COMPN_RenderEnd"]
    g, main = comp.FindTool(GROUP), comp.FindTool("Main")
    out_dur = int(g.GetInput("OutDur") or 0)
    dur = int(render_end - render_start + 1)
    # Never several words at once (see word_times in Auto Subtitles).
    spoken = [int(f - item.GetStart()) for f in frames]
    rel = spread(spoken, max(0, dur - out_dur - MIN_SHOW))
    if min_gap(rel) < MIN_GAP:
        roomier = spread(spoken, max(0, dur - out_dur - 2))
        if min_gap(roomier) > min_gap(rel):
            rel = roomier
    times = [int(t + render_start) for t in rel]  # comp frames (trims shift these)
    last = times[-1] - render_start if times else 0
    g.SetInput("InDur", max(8, min(18, render_end - render_start + 1 - out_dur - last + LEAD)))
    if main.GetInput("WordTime1") is not None:
        for k in range(1, MAX_WORDS + 1):
            main.SetInput(f"WordTime{k}", times[k - 1] if k <= len(times) else -1)
    else:  # titles made before word timing existed: set each word's reveal directly
        for k in range(1, MAX_WORDS + 1):
            curve = comp.FindTool(f"InCurve{k}")
            if curve and k <= len(times):
                curve.Input.SetExpression("min(max((time-(%d))/max(Main.InDur,1),0),1)" % (times[k - 1] - LEAD))
    return times


def run(dry_run=False, log=print):
    resolve = get_resolve()
    timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()
    words = timeline_words(timeline)
    if not words:
        log("Resync Subtitles: no transcript found for audio track 1 (run Auto Subtitles first).")
        return []
    report = []
    for item in subtitle_items(timeline):
        comp, frames, matched, total = word_frames(item, words)
        times = None if dry_run else apply(item, comp, frames)
        report.append({"name": item.GetName(), "start": item.GetStart(), "frames": frames,
                       "matched": matched, "total": total, "times": times})
        if matched < total:
            log(f"  {item.GetName()}: {total - matched} of {total} words differ from the transcript (timed by position) - worth a look")
    log(f"Resync Subtitles: {'checked' if dry_run else 're-timed'} {len(report)} subtitles.")
    return report


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print("Resync Subtitles:", e)
