"""Auto Subtitles - Fluid Reveal Words captions for the current timeline.

Run from Workspace > Scripts > Edit > Auto Subtitles on the Edit page.

1. Transcribes the audio on audio track 1 (Resolve's own transcription; reused if it exists).
2. Maps every word through the timeline's cuts, so timings follow the edit.
3. Splits the words into captions: each sentence starts a new caption, at most two
   lines of ~24 characters, breaking at pauses and commas, never ending on a/the/to/of.
4. Builds them as Fluid Reveal Words titles on "<timeline> Subtitles" (a duplicate of
   the timeline, emptied) with no gaps and each word timed to when it is spoken, then
   places that timeline on a new top video track of the current timeline.

To use your own look, style one Fluid Reveal Words title by hand (font, size, colour,
position, motion), leave it selected on the timeline and run the script: every caption
copies it. Delete the styled title afterwards.

Your timeline's existing clips are never moved. Decompose the placed clip
(right-click > Decompose in Place) if you want the titles loose on the timeline.
"""
import re
import time

# Runs inside Resolve, so it can't read the intake files. Where its values come from:
# fps from the timeline itself; the look from the selected styled title (match it to the job card
# Subtitles line, confirmed by the editor); transcription language from Resolve's project settings
# (set it to shoot.language / the client profile language). The timing constants below are Beon
# house rules: Claude edits them only if the job card says otherwise.
TITLE = "Fluid Reveal Words"
MAX_LINE = 24          # characters per line
MAX_LINES = 2
MAX_WORDS = 12         # word layers in the title
MAX_FRAMES = 110       # titles are inserted at their 5 s default length, so stay under it
SENTENCE_GAP = 0       # captions run back to back
IN_DUR, OUT_DUR, LAST_OUT_DUR = 18, 4, 0   # last caption holds to the end (approved on C2a)
LEAD = 2               # words start revealing this many frames before they are spoken
MIN_GAP = 4            # words always reveal one at a time, at least this many frames apart
MIN_SHOW = 6           # every word is on screen at least this long before the caption exits
WEAK = {"a", "an", "the", "to", "of", "and", "or", "but", "that", "i", "your", "my", "our", "in", "on",
        "at", "for", "with", "is", "are", "was", "be", "this", "you", "we", "it", "if", "so", "as"}


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


# ---------------------------------------------------------------- timecode helpers
def fps_of(timeline):
    return float(timeline.GetSetting("timelineFrameRate"))


def tc_to_frames(tc, fps):
    h, m, s, f = (int(x) for x in re.split("[:;]", tc))
    base = round(fps)
    return ((h * 60 + m) * 60 + s) * base + f


def frames_to_tc(frames, fps):
    base = round(fps)
    f = int(frames)
    return "%02d:%02d:%02d:%02d" % (f // (base * 3600), f // (base * 60) % 60, f // base % 60, f % base)


# ---------------------------------------------------------------- 1. transcript
def ensure_transcripts(project, items, log):
    pool_items = {}
    for it in items:
        m = it.GetMediaPoolItem()
        pool_items[m.GetUniqueId()] = m
    for m in pool_items.values():
        if (m.GetTranscription() or {}).get("segments"):
            continue
        log(f"Transcribing {m.GetName()} (one time only)...")
        if not m.TranscribeAudio():
            raise RuntimeError(f"Could not start transcription for {m.GetName()}")
        while True:
            time.sleep(3)
            st = project.GetTranscribeAudioStatus() or {}
            if st.get("Error"):
                raise RuntimeError(f"Transcription failed: {st['Error']}")
            if st.get("JobStatus") in ("Complete", "Inactive"):
                break
            if st.get("JobStatus") == "Cancelled":
                raise RuntimeError("Transcription was cancelled")
            log(f"  {st.get('CompletionPercentage', 0)}%")
    return pool_items


# ---------------------------------------------------------------- 2. words on the timeline
def timeline_words(timeline):
    items = [i for i in (timeline.GetItemListInTrack("audio", 1) or []) if i.GetMediaPoolItem()]
    if not items:
        raise RuntimeError("No audio clips on audio track 1")
    return items


def source_words(m):
    """Transcript words as (start, end, text) in source frames counted from the clip's first frame.
    Resolve stamps words with the clip's own timecode, so the clip's Start TC is subtracted."""
    src_fps = float(m.GetClipProperty("FPS") or 24)
    origin = tc_to_frames(m.GetClipProperty("Start TC") or "00:00:00:00", src_fps)
    tr = m.GetTranscription() or {}
    return src_fps, [(tc_to_frames(w["start"], src_fps) - origin, tc_to_frames(w["end"], src_fps) - origin, w["text"].strip())
                     for seg in tr.get("segments", []) for w in seg.get("words", [])]


def map_words(items, tl_fps=None):
    words = []
    cache = {}
    for it in items:
        m = it.GetMediaPoolItem()
        key = m.GetUniqueId()
        if key not in cache:
            cache[key] = source_words(m)
        src_fps, src_words = cache[key]
        k = (tl_fps or src_fps) / src_fps          # e.g. 25p camera clip on a 24p timeline
        s, e = it.GetSourceStartFrame(), it.GetSourceEndFrame()
        for ws, we, text in src_words:
            if not text or text == "(...)":
                continue
            if s <= (ws + we) / 2 < e:
                words.append({"t0": it.GetStart() + round((max(ws, s) - s) * k),
                              "t1": it.GetStart() + round((min(we, e) - s) * k), "text": text})
    words.sort(key=lambda w: w["t0"])
    return words


# ---------------------------------------------------------------- 3. captions
def is_sentence_end(text):
    return text.endswith((".", "?", "!"))


def fits(tokens):
    return len(tokens) <= MAX_WORDS and best_lines(tokens) is not None


def best_lines(tokens):
    """Split tokens into <= MAX_LINES lines of <= MAX_LINE chars, balanced, not ending a line on a weak word."""
    one = " ".join(tokens)
    if len(one) <= MAX_LINE:
        return [one]
    if MAX_LINES < 2:
        return None
    best = None
    for i in range(1, len(tokens)):
        a, b = " ".join(tokens[:i]), " ".join(tokens[i:])
        if len(a) > MAX_LINE or len(b) > MAX_LINE:
            continue
        score = abs(len(a) - len(b))
        last = tokens[i - 1].lower().strip(",.?!")
        if tokens[i - 1].endswith(","):
            score -= 6
        if last in WEAK:
            score += 12
        if best is None or score < best[0]:
            best = (score, [a, b])
    return best[1] if best else None


BACKCHANNEL = {"yeah", "yep", "yes", "right", "mhm", "mm", "hmm", "uh", "um", "okay", "ok"}
QUESTION_STARTS = {"what", "what's", "how", "why", "where", "when", "who", "which", "is", "are", "do", "does",
                   "did", "can", "could", "would", "should", "will", "have", "has"}
COMMA_BEFORE = {"because", "but", "so", "which"}
COMPOUNDS = {("click", "through"), ("follow", "up"), ("e", "commerce"), ("long", "term"), ("short", "term"),
             ("real", "time"), ("check", "in"), ("set", "up"), ("sign", "up"), ("opt", "in")}


def bare(text):
    return text.lower().strip(",.?!")


def sentences(words):
    out, cur = [], []
    for w in words:
        cur.append(dict(w))
        if is_sentence_end(w["text"]):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def tidy(sentence):
    """Clean one spoken sentence: drop stutters, fix capitals, commas and question marks."""
    ws = sentence
    # Repeated 1-3 word runs ("actually actually", "what's the what's the"): keep the last copy.
    changed = True
    while changed:
        changed = False
        for n in (3, 2, 1):
            for i in range(len(ws) - 2 * n + 1):
                if [bare(w["text"]) for w in ws[i:i + n]] == [bare(w["text"]) for w in ws[i + n:i + 2 * n]]:
                    ws = ws[:i] + ws[i + n:]
                    changed = True
                    break
            if changed:
                break
    if not ws:
        return ws
    end = ws[-1]["text"][-1] if is_sentence_end(ws[-1]["text"]) else ""
    body = ws[-1]["text"].rstrip(".?!")
    if bare(ws[0]["text"]) in QUESTION_STARTS and len(ws) > 2:
        end = "?"
    ws[-1]["text"] = body + (end or "")
    first = ws[0]["text"]
    ws[0]["text"] = first[:1].upper() + first[1:]
    for i in range(1, len(ws)):
        b = bare(ws[i]["text"])
        if b in COMMA_BEFORE and not ws[i - 1]["text"].endswith((",", ".", "?", "!")):
            ws[i - 1]["text"] += ","
        if i == 1 and bare(ws[0]["text"]) == "well" and not ws[0]["text"].endswith(","):
            ws[0]["text"] += ","
    if bare(ws[0]["text"]) == "well" and len(ws) > 1 and not ws[0]["text"].endswith(","):
        ws[0]["text"] += ","
    # A "well" set off by a pause mid-sentence is an aside: "what we report on is, well, how many..."
    for i in range(1, len(ws) - 1):
        if bare(ws[i]["text"]) == "well" and ws[i]["t0"] - ws[i - 1]["t1"] >= 5:
            if not ws[i - 1]["text"].endswith((",", ".", "?", "!")):
                ws[i - 1]["text"] += ","
            if not ws[i]["text"].endswith(","):
                ws[i]["text"] += ","
    # Spoken compounds the transcript splits: join into one hyphenated word.
    i = 0
    while i < len(ws) - 1:
        pair = (bare(ws[i]["text"]), bare(ws[i + 1]["text"]))
        if pair in COMPOUNDS:
            tail = ws[i + 1]["text"][len(pair[1]):] if ws[i + 1]["text"].lower().startswith(pair[1]) else ""
            ws[i]["text"] = ws[i]["text"].rstrip(",") + "-" + pair[1] + tail
            ws[i]["t1"] = ws[i + 1]["t1"]
            del ws[i + 1]
        i += 1
    return ws


def split_sentence(ws):
    """Fewest captions that fit, then the most natural breaks (pauses, commas, no weak endings)."""
    n = len(ws)
    INF = float("inf")
    best = [(INF, None)] * (n + 1)
    best[0] = (0, None)
    for j in range(1, n + 1):
        for i in range(max(0, j - MAX_WORDS), j):
            if best[i][0] == INF:
                continue
            tokens = [w["text"] for w in ws[i:j]]
            if not fits(tokens) or ws[j - 1]["t1"] - ws[i]["t0"] > MAX_FRAMES:
                continue
            chars = len(" ".join(tokens))
            cost = 100                                   # every caption costs: prefer fewer
            cost += abs(chars - 2 * MAX_LINE * 0.7) / 3  # prefer comfortably full captions
            if j < n:
                gap = ws[j]["t0"] - ws[j - 1]["t1"]
                last = ws[j - 1]["text"]
                if bare(last) in WEAK:
                    cost += 25
                if last.endswith(","):
                    cost -= 15
                cost -= min(gap, 12) * 2                 # break where he pauses
            if j - i == 1 and n > 1:
                cost += 40                               # avoid one-word orphans
            if best[i][0] + cost < best[j][0]:
                best[j] = (best[i][0] + cost, i)
    if best[n][0] == INF:  # a single word too long to fit: give each word its own caption
        return [[w] for w in ws]
    cuts, j = [], n
    while j > 0:
        i = best[j][1]
        cuts.append(ws[i:j])
        j = i
    return cuts[::-1]


def chunk(words):
    caps = []
    for s in sentences(words):
        if len(s) == 1 and bare(s[0]["text"]) in BACKCHANNEL:
            continue  # "Yeah." / "Right." from the other speaker: the previous caption holds over it
        s = tidy(s)
        if s:
            caps += split_sentence(s)
    return caps


def spread(times, latest, gap=MIN_GAP):
    """Spoken times, nudged so words always reveal one at a time (>= gap frames apart)
    and no later than `latest`. Falls back to an even spread when the caption is too short."""
    t = [max(0, x) for x in times]
    for i in range(1, len(t)):                       # push clumped words later
        t[i] = max(t[i], t[i - 1] + gap)
    if t and t[-1] > latest:                         # too late: pull back from the end
        t[-1] = latest
        for i in range(len(t) - 2, -1, -1):
            t[i] = min(t[i], t[i + 1] - gap)
    if t and t[0] < 0:                               # not enough room: even spread
        step = latest / max(len(t) - 1, 1)
        t = [round(i * step) for i in range(len(t))]
    return t


def min_gap(t):
    return min((b - a for a, b in zip(t, t[1:])), default=MIN_GAP)


def word_times(spoken, dur, out_dur):
    """Never several words at once: spread to MIN_GAP, and on very fast speech let the
    last word land up to 2 frames before the exit rather than clump."""
    t = spread(spoken, max(0, dur - out_dur - MIN_SHOW))
    if min_gap(t) < MIN_GAP:
        roomier = spread(spoken, max(0, dur - out_dur - 2))
        if min_gap(roomier) > min_gap(t):
            t = roomier
    return t


def plan_captions(words, tl_start, tl_end):
    groups = chunk(words)
    caps = []
    for g in groups:
        tokens = [w["text"] for w in g]
        caps.append({"text": "\n".join(best_lines(tokens)), "start": max(tl_start, g[0]["t0"]),
                     "word_starts": [max(tl_start, w["t0"]) for w in g]})
    for n, c in enumerate(caps):
        c["end"] = caps[n + 1]["start"] if n + 1 < len(caps) else tl_end
        c["out_dur"] = LAST_OUT_DUR if n + 1 == len(caps) else OUT_DUR
        dur = c["end"] - c["start"]
        c["times"] = word_times([t - c["start"] for t in sorted(c["word_starts"])], dur, c["out_dur"])
        c["in_dur"] = max(8, min(IN_DUR, dur - c["out_dur"] - c["times"][-1] + LEAD))
    return caps


# ---------------------------------------------------------------- 4. build
def find_pool_timeline(media_pool, name):
    found = []

    def walk(folder):
        for c in folder.GetClipList() or []:
            if c.GetName() == name and c.GetClipProperty("Type") == "Timeline":
                found.append(c)
        for f in folder.GetSubFolderList() or []:
            walk(f)

    walk(media_pool.GetRootFolder())
    return found[0] if found else None


def unique_name(project, base):
    names = {project.GetTimelineByIndex(i).GetName() for i in range(1, project.GetTimelineCount() + 1)}
    name, n = base, 2
    while name in names:
        name, n = f"{base} {n}", n + 1
    return name


def move_playhead(timeline, frame, fps):
    """Set the playhead and wait until Resolve reports it there: titles are inserted at the
    playhead, and it lags behind SetCurrentTimecode, especially just after a timeline switch."""
    want = frames_to_tc(frame, fps)
    for _ in range(60):
        timeline.SetCurrentTimecode(want)
        if timeline.GetCurrentTimecode() == want:
            return
        time.sleep(0.05)
    raise RuntimeError(f"Playhead would not move to {want}")


# Look of a hand-styled title, copied onto every caption. Per-caption values (text, word
# timing, in/out lengths) are set separately. The custom curve shapes (InLookup/OutLookup)
# can't be copied by script: change those in build_presets.py and reinstall the title.
STYLE_KEYS = ("Font", "Style", "Red", "Green", "Blue", "Alpha", "Size", "Tracking", "LineSpacing", "Position",
              "JustifyL", "WordStagger", "SyncOffset", "InCurve", "InEaseIn", "InEaseOut", "Rise", "InBlur",
              "OutCurve", "OutEaseIn", "OutEaseOut", "OutLift", "OutBlur")


def read_style(item):
    g = item.GetFusionCompByIndex(1).FindTool("FluidRevealWords")
    style = {}
    for k in STYLE_KEYS:
        v = g.GetInput(k)
        if isinstance(v, dict):                     # Position comes back as {1.0: x, 2.0: y, 3.0: z}
            v = [v[key] for key in sorted(v)][:2]
        if v is not None:
            style[k] = v
    return style


def apply_style(g, style, last=False):
    for k, v in style.items():
        if last and k in ("OutLift", "OutBlur"):
            continue                                # the last caption holds, no outro
        g.SetInput(k, v)


def selected_style(timeline):
    """Style of the Fluid Reveal Words title selected on the timeline, if one is."""
    for it in timeline.GetSelectedClips() or []:
        try:
            if it.GetFusionCompCount() and it.GetFusionCompByIndex(1).FindTool("FluidRevealWords"):
                return read_style(it), it.GetName()
        except Exception:
            pass
    return None, None


def build(resolve, project, timeline, caps, log, style=None):
    fps = fps_of(timeline)
    media_pool = project.GetMediaPool()
    tl_start, tl_end = timeline.GetStartFrame(), timeline.GetEndFrame()

    # Duplicate (never create) the timeline: creating timelines or changing their settings
    # while Fusion titles render can deadlock Resolve.
    timeline.SetCurrentTimecode(frames_to_tc(tl_end, fps))
    name = unique_name(project, timeline.GetName() + " Subtitles")
    subs = timeline.DuplicateTimeline(name)
    if not subs:
        raise RuntimeError("Could not duplicate the timeline")
    project.SetCurrentTimeline(subs)
    for _ in range(40):
        if project.GetCurrentTimeline().GetName() == name:
            break
        time.sleep(0.1)
    time.sleep(0.5)
    leftovers = []
    for kind in ("video", "audio"):
        for t in range(1, subs.GetTrackCount(kind) + 1):
            leftovers += subs.GetItemListInTrack(kind, t) or []
    if leftovers:
        subs.DeleteClips(leftovers, False)
    # One video track only: with more, Resolve's track targeting can drop the titles onto V2+.
    for t in range(subs.GetTrackCount("video"), 1, -1):
        subs.DeleteTrack("video", t)
    log(f"Building {len(caps)} captions on '{name}'...")

    # Inserting a title splits the previous one and pushes its tail along; removing the tail
    # leaves every caption ending exactly where the next begins.
    for c in caps:
        move_playhead(subs, c["start"], fps)
        item = subs.InsertFusionTitleIntoTimeline(TITLE)
        if not item:
            raise RuntimeError(f"Could not insert '{TITLE}' - is the title installed?")
        if item.GetStart() != c["start"]:
            raise RuntimeError(f"A title landed at {frames_to_tc(item.GetStart(), fps)}, "
                               f"wanted {frames_to_tc(c['start'], fps)} - stopped so nothing is misplaced")
        tails = [i for i in subs.GetItemListInTrack("video", 1) if i.GetStart() >= item.GetEnd()]
        if tails:
            subs.DeleteClips(tails, False)
    move_playhead(subs, tl_end, fps)
    if subs.InsertFusionTitleIntoTimeline(TITLE):
        extra = [i for i in subs.GetItemListInTrack("video", 1) if i.GetStart() >= tl_end]
        if extra:
            subs.DeleteClips(extra, False)

    titles = subs.GetItemListInTrack("video", 1)
    for n, (c, item) in enumerate(zip(caps, titles), start=1):
        comp = item.GetFusionCompByIndex(1)
        g, main = comp.FindTool("FluidRevealWords"), comp.FindTool("Main")
        if main is None or main.GetInput("WordTime1") is None:
            raise RuntimeError(f"The installed '{TITLE}' is an old version without word timing")
        if style:
            apply_style(g, style, last=not c["out_dur"])
        g.SetInput("TextContent", c["text"])
        g.SetInput("InDur", c["in_dur"])
        g.SetInput("OutDur", c["out_dur"])
        if not style or not c["out_dur"]:
            g.SetInput("OutBlur", 6 if c["out_dur"] else 0)
            g.SetInput("OutLift", 0.015 if c["out_dur"] else 0)
        for k in range(1, MAX_WORDS + 1):
            main.SetInput(f"WordTime{k}", c["times"][k - 1] if k <= len(c["times"]) else -1)
        item.SetName(f"Sub {n:02d}")

    # Place the subtitle timeline on a new top track of the original timeline.
    project.SetCurrentTimeline(timeline)
    timeline.AddTrack("video")
    track = timeline.GetTrackCount("video")
    timeline.SetTrackName("video", track, "Subtitles")
    pool_tl = find_pool_timeline(media_pool, name)
    placed = media_pool.AppendToTimeline([{"mediaPoolItem": pool_tl, "startFrame": 0, "endFrame": tl_end - tl_start,
                                           "trackIndex": track, "recordFrame": tl_start, "mediaType": 1}])
    if not placed:
        raise RuntimeError(f"Built '{name}' but could not place it on track V{track}")
    return name, track


def run(dry_run=False, log=print):
    resolve = get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    timeline = project.GetCurrentTimeline()
    if timeline.GetName().endswith("Subtitles"):
        raise RuntimeError("Open the timeline you want subtitled, not a Subtitles timeline")
    items = timeline_words(timeline)
    ensure_transcripts(project, items, log)
    words = map_words(items, fps_of(timeline))
    caps = plan_captions(words, timeline.GetStartFrame(), timeline.GetEndFrame())
    if dry_run:
        return caps
    style, styled_from = selected_style(timeline)
    if style:
        log(f"Using the look of the selected title '{styled_from}' (font, size, colour, position, motion).")
    name, track = build(resolve, project, timeline, caps, log, style)
    log(f"Done: {len(caps)} captions from '{name}' placed on V{track}.")
    return caps


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print("Auto Subtitles:", e)
