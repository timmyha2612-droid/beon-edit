"""Typeset Kinetic captions word by word (Fluid Reveal Words Kinetic).

    python3 kinetic_layout.py WORK_DIR [--width 3840 --height 2160 --size 0.075 --slam 1.25]

Needs uharfbuzz + fonttools (run from a venv). Reads WORK/plans.json, KEYS from WORK/captions.py
(KEYS = {caption index: {display token number: 1 italic | 2 big italic highlight}}) and BLOCKS from
WORK/blocks.py:

    BLOCKS = {timeline name: [(start, end, x, y, align, max_width), ...]}

one entry per stretch of the edit (frames on the subtitle timeline): where the caption block sits
in that shot's negative space. x/y are frame fractions (y from the bottom, Text+ style) of the
block's anchor: its left edge (align "left"), right edge ("right") or centre ("center"), and its
vertical middle. A caption takes the block that covers most of its time and is shown only while
that shot is up ("show": local [from, to) frames), so it never lands on the wrong angle.

Writes WORK/layout.json: per caption {"anchor": [x, y], "show": [from, to], "words": [{text, style, scale, dx, dy}]}
with each word's centre as an offset from the anchor at the base size, so the build can keep the
words relative to Txt1's Center / Size (move or scale the whole block from the Inspector).

Each word sits on its own Text+ layer, so Regular and Italic can mix on one line. Blocks of up
to 2 lines: one line for 1-2 words that fit, otherwise the most balanced 2-line split, shrunk only
if a line still overflows max_width. Two-tier captions (Tim's "Search is / *changing.*"
reference): when a caption has any key 2, its key-2 words are big italic (--slam, 1.6x) and the
rest small regular (--small, 0.72x), each run on its own line. Spacing is ink-aware: a regular space between advance boxes,
widened when an italic's overhang would bring the inks closer than MIN_INK_GAP em.
Calibration (Resolve 21.1, measured 3 Nov 2026): 1 em = Text+ Size x frame width x 0.6451,
Text+ centres the advance box, and its centre sits 0.35 em above the baseline (Regular and Italic
share hhea metrics). Word scale goes through Text+ WordSize, which grows a word from its baseline.
"""
import argparse
import json
import os
import sys

import uharfbuzz as hb
from fontTools.ttLib import TTFont

EM_PER_SIZE = 0.6451
FONTS = {"Regular": "LibreBaskerville-Regular.ttf", "Italic": "LibreBaskerville-Italic.ttf"}
LINE_TOP, LINE_BOTTOM = 0.3, 0.9   # baseline gap = 0.3 em of the upper line + 0.9 em of the lower (1.2 em when equal)
CAP, DESC = 0.72, 0.22              # ink above / below the baseline, in em, for centring a block
MIN_INK_GAP = 0.22    # em, smallest visible gap between two words' inks


def font_path(name):
    for d in (os.path.expanduser("~/Library/Fonts"), "/Library/Fonts"):
        if os.path.exists(os.path.join(d, name)):
            return os.path.join(d, name)
    raise FileNotFoundError(name)


def load(style):
    path = font_path(FONTS[style])
    face = hb.Face(open(path, "rb").read())
    hh = TTFont(path)["hhea"]
    return hb.Font(face), face.upem, (hh.ascent + hh.descent) / 2 / face.upem


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


def best_lines(words, space, maxw):
    whole = set_line([dict(w) for w in words], space)
    if len(words) == 1 or (len(words) == 2 and whole <= maxw):
        return [words]
    best = None
    for k in range(1, len(words)):
        a, b = words[:k], words[k:]
        wid = max(set_line([dict(w) for w in a], space), set_line([dict(w) for w in b], space))
        if best is None or wid < best[0]:
            best = (wid, [a, b])
    return best[1]


def block_for(blocks, start, end):
    cover = [(min(end, b[1]) - max(start, b[0]), b) for b in blocks]
    return max(cover)[1]


def window(block, start, end):
    """Local frames [show, hide) the caption stays on its block's shot (hide None = to the end)."""
    return [max(0, block[0] - start), block[1] - start if block[1] < end else None]


def tiers(words):
    """Two-tier caption: each run of small (lead-in) or big (highlight) words is its own line."""
    lines = []
    for w in words:
        if lines and lines[-1][-1]["big"] == w["big"]:
            lines[-1].append(w)
        else:
            lines.append([w])
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("--width", type=float, default=3840)
    ap.add_argument("--height", type=float, default=2160)
    ap.add_argument("--size", type=float, default=0.075)
    ap.add_argument("--slam", type=float, default=1.6, help="big (highlight) word scale in a two-tier caption")
    ap.add_argument("--small", type=float, default=0.72, help="lead-in word scale in a two-tier caption")
    a = ap.parse_args()
    sys.path.insert(0, a.work)
    from captions import KEYS
    from blocks import BLOCKS
    fonts = {s: load(s) for s in FONTS}
    plans = json.load(open(os.path.join(a.work, "plans.json")))
    em1 = a.size * a.width * EM_PER_SIZE                     # em in px at the base size
    out = {}
    for name, plan in plans.items():
        caps = []
        for n, c in enumerate(plan["caps"]):
            blk = block_for(BLOCKS[name], c["start"], c["end"])
            bx, by, align, maxw = blk[2:]
            maxw *= a.width
            keys = KEYS.get(n, {})
            tiered = 2 in keys.values()
            fit = 1.0
            while True:
                words = []
                for i, t in enumerate(c["text"].split(), 1):
                    k = keys.get(i, 0)
                    style = "Italic" if k else "Regular"
                    scale = (a.slam if k == 2 else a.small if tiered else 1) * fit
                    font, upem, mid = fonts[style]
                    adv, lo, hi = measure(font, upem, t)
                    em = em1 * scale
                    words.append({"text": t, "style": style, "scale": scale, "w": adv * em, "ink": (lo, hi), "em": em,
                                  "mid": mid, "big": k == 2})
                lines = tiers(words) if tiered else best_lines(words, measure(fonts["Regular"][0], fonts["Regular"][1], " ")[0] * em1 * fit, maxw)
                # each line spaced at its own size (a small lead-in line has small spaces)
                widths = [set_line(l, measure(fonts["Regular"][0], fonts["Regular"][1], " ")[0] * max(w["em"] for w in l)) for l in lines]
                if max(widths) <= maxw or fit < 0.6:
                    break
                fit *= 0.95
            # baselines top to bottom: LINE_TOP of the upper line's em + LINE_BOTTOM of the lower's
            ems = [max(w["em"] for w in l) for l in lines]
            base = [0.0]
            for i in range(1, len(lines)):
                base.append(base[-1] - (LINE_TOP * ems[i - 1] + LINE_BOTTOM * ems[i]))
            shift = -((base[0] + CAP * ems[0]) + (base[-1] - DESC * ems[-1])) / 2     # centre the ink block on the anchor
            for line, lw, b in zip(lines, widths, base):
                left = {"left": 0, "right": -lw, "center": -lw / 2}[align]
                for w in line:
                    w["dx"] = (left + w["x"] + w["w"] / 2) / a.width
                    # Text+ centre sits mid em (at Txt1's base size) above the baseline; a word's
                    # scale is a Text+ word transform that grows it from its baseline, so the
                    # offset stays at the base em whatever the word's scale.
                    w["dy"] = (b + shift + w["mid"] * em1) / a.height
            caps.append({"anchor": [bx, by], "show": window(blk, c["start"], c["end"]),
                         "words": [{k: round(w[k], 5) if isinstance(w[k], float) else w[k]
                                    for k in ("text", "style", "scale", "dx", "dy")} for l in lines for w in l]})
        out[name] = caps
    json.dump(out, open(os.path.join(a.work, "layout.json"), "w"), indent=1)
    print("layout:", {k: len(v) for k, v in out.items()},
          "max words/caption", max(len(c["words"]) for caps in out.values() for c in caps))

main()
