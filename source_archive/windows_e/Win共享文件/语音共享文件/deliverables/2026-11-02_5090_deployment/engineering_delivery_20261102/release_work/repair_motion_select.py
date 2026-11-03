from common import *
p=W/'software.py'
s=p.read_text(encoding='utf8')
a=s.index('if sha(mp)!=actual')
b=s.index("copy(d/'APPLIED.json'",a)
s=s[:a]+"""lookup=d.parent
for script in [lookup/'apply_left40_right45.prepared.py',lookup/'py39_fix/apply_py39_fix.prepared.py',d/'apply_stable150.prepared.py']:
    line=next(l for l in script.read_text(encoding='utf-8').splitlines() if l.startswith("candidate_manifest['scope']="))
    suffix=ast.literal_eval(line.split("manifest['scope']+",1)[1])
    m['scope']+=suffix
for r in m['files']:
    n=r['source_rel'];p=rc/n
    r.update(destination=actual['release_root']+'/'+n,sha256=sha(p),bytes=p.stat().st_size)
    copy(p,ROOT/'src/motion/follow'/n)
mp=ROOT/'src/motion/follow/deployment-manifest.json'
mp.write_bytes((json.dumps(m,sort_keys=True,indent=2)+'\\\\n').encode())
assert sha(mp)==actual['manifest_sha256'],sha(mp)
"""+s[b:];p.write_text(s,encoding='utf8')
