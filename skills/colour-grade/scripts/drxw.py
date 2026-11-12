#!/usr/bin/env python3
"""Write a Resolve grade (DRX) with new Balance Temp/Tint and HDR Global values.
usage: drxw.py TEMPLATE.drx OUT.drx TEMP TINT HDR_GLOBAL
TEMPLATE = a still exported with GalleryStillAlbum.ExportStills(..., "drx") (Beon's 9-node template,
or the client profile's grade.template_still), into the job's scratch folder (beon_config.scratch_dir).
Only those three values change; every other byte of the grade is kept. Proven 15 Oct 2026 on
Resolve 21.1.1: the parse/encode round trip is byte-exact, and a written DRX applied with
Graph.ApplyGradeFromDRX(path, 0) read back exactly from the timeline DRT.
Apply each DRX ONCE per clip (a second apply on an already-graded clip crashed Resolve).
Needs drxlib.py beside it, plus zstandard (pip install zstandard) or Python 3.14 compression.zstd."""
import os, re, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import drxlib
try:
    from compression import zstd as _z
    def zcompress(b): return _z.compress(b)
except Exception:
    try:
        import zstandard
        def zcompress(b): return zstandard.ZstdCompressor(level=3).compress(b)
    except ImportError:
        def zcompress(b): raise SystemExit("needs zstd: pip install zstandard (or Python 3.14+)")

TEMP, TINT, HDR = 2248147221, 2248147222, 2248147717

def _varint(n):
    out = bytearray()
    while True:
        b = n & 0x7f; n >>= 7
        if n: out.append(b | 0x80)
        else:
            out.append(b); return bytes(out)

def encode(tree):
    out = bytearray()
    for f, ty, v in tree:
        if ty == 'v': out += _varint(f << 3) + _varint(v)
        elif ty == 'd': out += _varint((f << 3) | 1) + struct.pack('<d', v)
        elif ty == 'f': out += _varint((f << 3) | 5) + struct.pack('<f', v)
        else:
            b = v.encode() if ty == 's' else bytes.fromhex(v) if ty == 'b' else encode(v)
            out += _varint((f << 3) | 2) + _varint(len(b)) + b
    return bytes(out)

def _first(lst, f, key=None):
    for ff, ty, v in lst:
        if ff == f and ty == 'm' and (key is None or (v and v[0][0] == 1 and v[0][2] == key)):
            return v
    return None

def _node(tree, label):
    top = tree[0][2] if tree[0][0] == 1 and tree[0][1] == 'm' else tree
    for f, ty, v in top:
        if f == 7 and ty == 'm' and any(x[0] == 6 and x[1] == 's' and x[2] == label for x in v):
            return v
    raise KeyError("node %r not found" % label)

def _params(node):
    return _first(_first(_first(_first(node, 9), 1, 1), 6), 2, 1)

def _param(plist, pid):
    for i, (f, ty, v) in enumerate(plist):
        if f == 3 and ty == 'm' and v and v[0][0] == 1 and v[0][2] == pid:
            return i, v
    return None, None

def make_drx(template, out_path, temp, tint, hdr):
    x = open(template, errors="replace").read()
    h = re.search(r"<Body>([0-9a-fA-F]+)</Body>", x).group(1)
    tree = drxlib.parse(drxlib.hexbody(h))
    pl = _params(_node(tree, "Balance"))
    i, t = _param(pl, TEMP)
    if t is None:
        pl.append((3, 'm', [(1, 'v', TEMP), (2, 'm', [(1, 'f', float(temp))])])); i = len(pl) - 1
    else:
        t[1] = (2, 'm', [(1, 'f', float(temp))])
    _, n = _param(pl, TINT)
    if n is None:
        pl.insert(i + 1, (3, 'm', [(1, 'v', TINT), (2, 'm', [(1, 'f', float(tint))])]))
    else:
        n[1] = (2, 'm', [(1, 'f', float(tint))])
    _, hq = _param(_params(_node(tree, "HDR")), HDR)
    zones = hq[1][2][0][2]                        # 2 -> 16 -> zone messages
    done = False
    for f, ty, v in zones:
        if f == 1 and ty == 'm' and any(e[:3] == (1, 's', 'Global') for e in v):
            for k, e in enumerate(v):
                if e[0] == 2 and e[1] == 'f':
                    v[k] = (2, 'f', float(hdr)); done = True
    if not done:
        raise RuntimeError("HDR Global zone not found in template")
    body = (b"\x81" + zcompress(encode(tree))).hex()
    with open(out_path, "w") as fo:
        fo.write(x.replace(h, body))
    return out_path

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(__doc__); sys.exit(0)
    if len(sys.argv) != 6:
        sys.exit(__doc__)
    print(make_drx(sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])))
