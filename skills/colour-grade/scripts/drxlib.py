
import re, binascii, struct
try:
    from compression import zstd
    def unz(b): return zstd.decompress(b)
except Exception:
    try:
        import zstandard
        def unz(b): return zstandard.ZstdDecompressor().decompress(b, max_output_size=20_000_000)
    except ImportError:
        def unz(b): raise SystemExit("needs zstd: pip install zstandard (or Python 3.14+)")
def varint(b,i):
    r=s=0
    while True:
        c=b[i]; i+=1; r|=(c&0x7f)<<s; s+=7
        if c<0x80: return r,i
def parse(b):
    i=0; out=[]
    try:
        while i<len(b):
            k,i=varint(b,i); f,wt=k>>3,k&7
            if f==0 or f>100000: return None
            if wt==0: v,i=varint(b,i); out.append((f,'v',v))
            elif wt==1: out.append((f,'d',struct.unpack('<d',b[i:i+8])[0])); i+=8
            elif wt==5: out.append((f,'f',struct.unpack('<f',b[i:i+4])[0])); i+=4
            elif wt==2:
                n,i=varint(b,i); sub=b[i:i+n]; i+=n
                if i>len(b): return None
                p=parse(sub) if n>1 else None
                if sub and all(32<=c<127 for c in sub): out.append((f,'s',sub.decode()))
                elif p is not None: out.append((f,'m',p))
                else: out.append((f,'b',sub.hex()))
            else: return None
        return out
    except Exception: return None
def dump(t, ind=0, lines=None):
    lines = [] if lines is None else lines
    for f,ty,v in t:
        if ty=='m': lines.append('  '*ind+f'{f}:'); dump(v,ind+1,lines)
        else: lines.append('  '*ind+f'{f} {ty} {round(v,6) if isinstance(v,float) else v}')
    return lines
def hexbody(h):
    b = binascii.unhexlify(h)
    return unz(b[1:]) if b[1:5]==bytes.fromhex("28b52ffd") else b
