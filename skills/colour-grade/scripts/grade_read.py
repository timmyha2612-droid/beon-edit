#!/usr/bin/env python3
"""Read Tim's grades without touching the project.
1) In Resolve (read-only): timeline.Export('/tmp/x.drt', resolve.EXPORT_DRT)
2) python3 grade_read.py /tmp/x.drt [template_body.bin]
Prints one row per graded video clip: name, start, Temp, Tint, HDR Global, and which other
nodes differ from the template (by hash). Needs drxlib.py beside it (zstd: Python 3.14
compression.zstd or the zstandard package)."""
import sys, re, json, zipfile, hashlib, collections
import drxlib
T="/9#1/1[1]/6#1/2[1]/3[2248147221]/2#1/1#1"      # Balance > Temp (panel units)
N="/9#1/1[1]/6#1/2[1]/3[2248147222]/2#1/1#1"      # Balance > Tint (panel units)
H="/9#1/1[1]/6#1/2[1]/3[2248147717]/2#1/16#1/1[Global]/2#1"  # HDR > Global exposure (panel value)
def flatten(t, pre, out):
    occ=collections.Counter()
    for f,ty,v in t:
        if ty=='m' and v and v[0][0]==1 and v[0][1] in ('v','s'): key=f"{pre}/{f}[{v[0][2]}]"
        else: occ[f]+=1; key=f"{pre}/{f}#{occ[f]}"
        if ty=='m': flatten(v,key,out)
        else: out[key]=round(v,5) if isinstance(v,float) else v
    return out
def nodes(d):
    t=drxlib.parse(d); res={}
    top=t[0][2] if t[0][0]==1 and t[0][1]=='m' else t
    for f,ty,v in top:
        if f==7 and ty=='m':
            lab=next((x[2] for x in v if x[0]==6 and x[1]=='s'),"?")
            res[lab]=flatten([x for x in v if x[0] in (9,10)],"",{})
    return res
def sig(fl):
    fl={k:v for k,v in fl.items() if "/10#1/1#" not in k and "ContextFilter_" not in str(v)}
    return hashlib.md5(json.dumps(sorted(fl.items())).encode()).hexdigest()[:5]
z=zipfile.ZipFile(sys.argv[1])
nm=max([n for n in z.namelist() if n.startswith("SeqContainer")],key=lambda n:z.getinfo(n).file_size)
x=z.read(nm).decode("utf-8","replace")
tmpl=nodes(open(sys.argv[2],"rb").read()) if len(sys.argv)>2 else None
for m in re.finditer(r"<Sm2TiVideoClip .*?</Sm2TiVideoClip>",x,re.S):
    b=m.group(0); g=lambda t:(re.search(f"<{t}>(.*?)</{t}>",b,re.S) or [None,None])[1]
    body=re.search(r"<Body>([0-9a-fA-F]+)</Body>",b)
    if not body: continue
    n=nodes(drxlib.hexbody(body.group(1)))
    other=[l for l in n if l not in ("Balance","HDR") and tmpl and sig(n[l])!=sig(tmpl.get(l,{}))]
    print(json.dumps({"name":g("Name"),"start":int(g("Start"))-86400,"dur":int(g("Duration")),
        "file":(g("MediaFilePath") or "").split("/")[-1],"temp":n.get("Balance",{}).get(T,0),"tint":n.get("Balance",{}).get(N,0),
        "hdr_global":n.get("HDR",{}).get(H,0),"nodes":list(n.keys()),"changed_vs_template":other}))
