#!/usr/bin/env python3
"""Retime (and merge) the Text+ captions of an exported DRT from a plan.
usage: retime_captions_drt.py IN.drt OUT.drt PLAN.json [--start FRAME]   (FRAME = timeline start frame, default 86400)
plan.json: [{"old": [start, text], "new": [start, end, text] or null}, ...] (record frames from the
timeline start); captions not in the plan (e.g. a Text+ question card) are left alone. Each kept title's text and Fusion comp range are
rewritten to match."""
import re, sys, json, zlib, struct, zipfile

src, dst, plan = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3]))
T0 = int(sys.argv[sys.argv.index("--start") + 1]) if "--start" in sys.argv else 86400
zin = zipfile.ZipFile(src)
name = max((n for n in zin.namelist() if n.startswith("SeqContainer/")), key=lambda n: len(zin.read(n)))
B = zin.read(name).decode()

pat = re.compile(r"[ \t]*<Element>\s*<Sm2TiVideoClip DbId=\"[^\"]+\">(?:(?!</Sm2TiVideoClip>).)*?<PrettyType>Fusion Title</PrettyType>.*?</Sm2TiVideoClip>\s*</Element>\n", re.S)
clips = [m for m in pat.finditer(B) if "TextPlus" in zlib.decompress(bytes.fromhex(re.search(r"<CompositionBA>([0-9a-f]+)</CompositionBA>", m.group(0)).group(1))[4:]).decode("latin1")
         or True]


def comp_parts(x):
    h = re.search(r"<CompositionBA>([0-9a-f]+)</CompositionBA>", x).group(1)
    blob = zlib.decompress(bytes.fromhex(h)[4:])
    ct = blob.find(b"Composition {"); nul = blob.find(b"\x00", ct)
    return h, blob[:ct], blob[ct:nul].decode(), zlib.decompressobj().decompress(blob[nul + 5:]).decode()


def comp_text(m):
    inner = comp_parts(m.group(0))[3]
    v = re.search(r'StyledText = Input \{ Value = "(.*?)(?<!\\)", \}', inner).group(1)
    return v.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")


def lua(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


texty = []
for m in clips:
    h, hdr, ctext, inner = comp_parts(m.group(0))
    if "StyledText" in inner:
        s = int(re.search(r"<Start>(\d+)</Start>", m.group(0)).group(1)) - T0
        texty.append((s, m))
want = {(e["old"][0], e["old"][1]): e["new"] for e in plan}
texty = [(s, m, want[(s, comp_text(m))]) for s, m in texty if (s, comp_text(m)) in want]
assert len(texty) == len(plan), (len(texty), len(plan))

out, pos = [], 0
for s, m, p in sorted(texty, key=lambda x: x[1].start()):
    x = m.group(0)
    out.append(B[pos:m.start()]); pos = m.end()
    if p is None:
        continue                                   # merged away
    ns, ne, text = p
    d = ne - ns
    assert d > 0
    x = re.sub(r"<Start>\d+</Start>", "<Start>%d</Start>" % (T0 + ns), x, 1)
    x = re.sub(r"<Duration>\d+</Duration>", "<Duration>%d</Duration>" % d, x, 1)
    h, hdr, ctext, inner = comp_parts(x)
    last = d - 1
    ctext = re.sub(r"RenderRange = \{ 0, \d+ \}", "RenderRange = { 0, %d }" % last, ctext)
    ctext = re.sub(r"GlobalRange = \{ 0, \d+ \}", "GlobalRange = { 0, %d }" % last, ctext)
    ctext = re.sub(r"GlobalEnd = \d+", "GlobalEnd = %d" % last, ctext)
    inner = re.sub(r"GlobalOut = Input \{ Value = \d+, \}", "GlobalOut = Input { Value = %d, }" % last, inner)
    inner = re.sub(r'StyledText = Input \{ Value = ".*?(?<!\\)", \}', lambda _: "StyledText = Input { Value = %s, }" % lua(text), inner, 1)
    ib = inner.encode()
    data = ctext.encode() + b"\x00" + struct.pack("<I", len(ib)) + zlib.compress(ib, 9)
    body = hdr[:-4] + struct.pack(">I", len(data)) + data
    out.append(x.replace(h, (struct.pack(">I", len(body)) + zlib.compress(body, 9)).hex()))
out.append(B[pos:])
B = "".join(out)
z = zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED)
for n in zin.namelist():
    z.writestr(n, B if n == name else zin.read(n))
z.close()
print("retimed", sum(1 for e in plan if e["new"]), "removed", sum(1 for e in plan if e["new"] is None))
