"""Typeset Kinetic captions word by word (Fluid Reveal Words Kinetic).

    python3 kinetic_layout.py WORK_DIR [--font libre|garet --width 3840 --height 2160 --size 0.075 --slam 1.25]

Needs uharfbuzz + fonttools (run from a venv). Reads WORK/plans.json, KEYS from WORK/captions.py
(KEYS = {caption index: {display token number: 1 key | 2 key + larger}}) and BLOCKS from
WORK/blocks.py:

    BLOCKS = {timeline name: [(start, end, x, y, align, max_width), ...]}

one entry per stretch of the edit (frames on the subtitle timeline): where the caption block sits
in that shot's negative space. x/y are frame fractions (y from the bottom, Text+ style) of the
block's anchor: its left edge (align "left"), right edge ("right") or centre ("center"), and its
vertical middle. A caption takes the block that covers most of its time and is shown only while
that shot is up ("show": local [from, to) frames), so it never lands on the wrong angle.

Writes WORK/layout.json: per caption {"anchor", "show": [from, to], "font", "base", "words": [{text, style, scale, dx, dy}]}
with each word's centre as an offset from the anchor at the base size, so the build can keep the
words relative to Txt1's Center / Size (move or scale the whole block from the Inspector).

Each word sits on its own Text+ layer, so Regular and Italic can mix on one line. Blocks of up
to 2 lines: one line for 1-2 words that fit, otherwise the most balanced 2-line split, shrunk only
if a line still overflows max_width. Spacing is ink-aware: a regular space between advance boxes,
widened when an italic's overhang would bring the inks closer than MIN_INK_GAP em.
Font sets: libre = Libre Baskerville Regular + Italic key words; garet = Garet Book for every
word (no italic exists, and Tim rejected Heavy key words), so only a slam (2) word stands out.
Calibration (Resolve 21.1, measured 3 Nov 2026): Text+ sizes a font by its full hhea height, so
1 em = Text+ Size x frame width x 0.7987 / ((ascent - descent) / upem): 0.644 for Libre
Baskerville, 0.551 for Garet. Text+ centres the advance box; the centre sits MID em above the
baseline (measured per font). Word scale goes through Text+ WordSize, which grows a word from its
baseline, so baselines stay level without any lift.
"""
import argparse
import json
import os
import sys

import uharfbuzz as hb
from fontTools.ttLib import TTFont

SIZE_TO_LINE = 0.7987   # Text+ Size x frame width = this many hhea line heights
FONTSETS = {
    "libre": {"family": "Libre Baskerville", "mid": 0.35,
              "Regular": ("LibreBaskerville-Regular.ttf", "Regular"), "Key": ("LibreBaskerville-Italic.ttf", "Italic")},
    "garet": {"family": "Garet", "mid": 0.297,
              "Regular": ("Garet-Book.ttf", "Book"), "Key": ("Garet-Book.ttf", "Book")},   # Tim: no Heavy key words
}
LINE_PITCH = 1.2      # em, baseline to baseline
MIN_INK_GAP = 0.22    # em, smallest visible gap between two words' inks


def font_path(name):
    for d in (os.path.expanduser("~/Library/Fonts"), "/Library/Fonts"):
        if os.path.exists(os.path.join(d, name)):
            return os.path.join(d, name)
    raise FileNotFoundError(name)


def load(file_name, mid):
    path = font_path(file_name)
    face = hb.Face(open(path, "rb").read())
    hh = TTFont(path)["hhea"]
    return hb.Font(face), face.upem, mid, (hh.ascent - hh.descent) / face.upem


def measure(font, upem, text):
    """Advance and ink extents (left, right) of text, in em, from the pen origin."""
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {})
    pen, lo, hi = 0, None, None
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        ext = font.get_glyph_extents(info.codepoint)
        if ext and ext.width:
            a = pen + pos.x_offset + ext.x_bearing
            lo, hi = (a if lo is None else min(lo, a)), (a + ext.width if hi is None else max(hi, a + ext.width))
        pen += pos.x_advance
    return pen / upem, (lo or 0) / upem, (hi or pen) / upem


def set_line(words, space):
    """Place words left to right (px from the line's left advance edge); returns the width."""
    x = 0
    for i, w in enumerate(words):
        if i:
            p = words[i - 1]
            # a regular space between advance boxes, unless an italic overhang closes the inks up
            ink_gap = MIN_INK_GAP * max(p["em"], w["em"])
            x = max(p["x"] + p["w"] + space, p["x"] + p["ink"][1] * p["em"] + ink_gap - w["ink"][0] * w["em"])
        w["x"] = x
    return words[-1]["x"] + words[-1]["w"] if words else 0


ONE_LINE_SLACK = 1.1   # keep one line, shrunk to fit, when it is at most this much too wide

# Words a reader expects to stay with what follows: never end a line on one of these.
CLINGY = {"a", "an", "the", "to", "of", "in", "on", "for", "and", "or", "and/or", "but", "if", "is",
          "it", "it's", "i", "we", "you", "be", "so", "not", "our", "their", "your", "my", "at", "by"}


def best_lines(words, space, maxw):
    """One line whenever the caption fits (or would after a shrink of up to 1/ONE_LINE_SLACK). Otherwise the 2-line split that reads most naturally:
    prefer breaking after punctuation, never leave a lone short word on a line or end the first
    line on a word that clings to the next ("a", "to", "not"...), then balance the widths."""
    if set_line([dict(w) for w in words], space) <= maxw * ONE_LINE_SLACK:
        return [words]                      # slightly over: the caller shrinks it rather than break it
    best = None
    for k in range(1, len(words)):
        a, b = words[:k], words[k:]
        wa, wb = set_line([dict(w) for w in a], space), set_line([dict(w) for w in b], space)
        last = a[-1]["text"].lower()
        cost = max(wa, wb) / maxw + abs(wa - wb) / maxw * 0.25
        cost += 0 if last[-1:] in ",.;:?!…" else 0.3                   # natural pause
        cost += 1.0 if last.strip(",.;:?!…") in CLINGY else 0
        cost += 1.0 if any(len(l) == 1 and len(l[0]["text"]) <= 3 for l in (a, b)) else 0
        cost += 2.0 if max(wa, wb) > maxw else 0
        if best is None or cost < best[0]:
            best = (cost, [a, b])
    return best[1]


def block_for(blocks, start, end):
    cover = [(min(end, b[1]) - max(start, b[0]), b) for b in blocks]
    return max(cover)[1]


def window(block, start, end):
    """Local frames [show, hide) the caption stays on its block's shot (hide None = to the end)."""
    return [max(0, block[0] - start), block[1] - start if block[1] < end else None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("--width", type=float, default=3840)
    ap.add_argument("--height", type=float, default=2160)
    ap.add_argument("--size", type=float, default=0.075)
    ap.add_argument("--slam", type=float, default=1.25)
    ap.add_argument("--font", choices=sorted(FONTSETS), default="libre")
    a = ap.parse_args()
    sys.path.insert(0, a.work)
    from captions import KEYS
    from blocks import BLOCKS
    fs = FONTSETS[a.font]
    fonts = {kind: load(fs[kind][0], fs["mid"]) for kind in ("Regular", "Key")}
    style_of = {kind: fs[kind][1] for kind in ("Regular", "Key")}
    plans = json.load(open(os.path.join(a.work, "plans.json")))
    em1 = a.size * a.width * SIZE_TO_LINE / fonts["Regular"][3]   # em in px at the base size
    out = {}
    for name, plan in plans.items():
        caps = []
        for n, c in enumerate(plan["caps"]):
            blk = block_for(BLOCKS[name], c["start"], c["end"])
            bx, by, align, maxw = blk[2:]
            maxw *= a.width
            keys = KEYS.get(n, {})
            fit = 1.0
            while True:
                words = []
                for i, t in enumerate(c["text"].split(), 1):
                    k = keys.get(i, 0)
                    kind = "Key" if k else "Regular"
                    style = style_of[kind]
                    scale = (a.slam if k == 2 else 1) * fit
                    font, upem, mid, _ = fonts[kind]
                    adv, lo, hi = measure(font, upem, t)
                    em = em1 * scale
                    words.append({"text": t, "style": style, "scale": scale, "w": adv * em, "ink": (lo, hi), "em": em, "mid": mid})
                space = measure(fonts["Regular"][0], fonts["Regular"][1], " ")[0] * em1 * fit
                lines = best_lines(words, space, maxw)
                widths = [set_line(l, space) for l in lines]
                if max(widths) <= maxw or fit < 0.6:
                    break
                fit *= 0.95
            pitch = LINE_PITCH * em1 * fit
            for li, (line, lw) in enumerate(zip(lines, widths)):
                left = {"left": 0, "right": -lw, "center": -lw / 2}[align]
                base_dy = (len(lines) - 1) / 2 * pitch - li * pitch   # line centres around the anchor
                for w in line:
                    w["dx"] = (left + w["x"] + w["w"] / 2) / a.width
                    # WordSize grows a word from its baseline, so equal centres keep baselines level
                    w["dy"] = base_dy / a.height
            caps.append({"anchor": [bx, by], "show": window(blk, c["start"], c["end"]),
                         "font": fs["family"], "base": style_of["Regular"],
                         "words": [{k: round(w[k], 5) if isinstance(w[k], float) else w[k]
                                    for k in ("text", "style", "scale", "dx", "dy")} for l in lines for w in l]})
        out[name] = caps
    json.dump(out, open(os.path.join(a.work, "layout.json"), "w"), indent=1)
    print("layout:", {k: len(v) for k, v in out.items()},
          "max words/caption", max(len(c["words"]) for caps in out.values() for c in caps))


main()
