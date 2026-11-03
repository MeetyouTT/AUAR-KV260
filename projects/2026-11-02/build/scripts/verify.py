"""Offline, single-threaded release integrity and reference checks. Python 3.8+."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
from public_board_files import verify_public_files
import sys
ROOT=Path(__file__).resolve().parents[2]
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def require(value,reason):
    if not value:raise RuntimeError(reason)
def load(path):return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
def exact(path,expected):require(digest(ROOT/path)==expected,'Wrong bytes: '+str(path))
def main():
    entries=(ROOT/'checksums.sha256').read_text(encoding='utf8').splitlines()
    listed=set()
    for line in entries:
        h,n=line.split('  ',1)
        require(n not in listed and not Path(n).is_absolute() and '..' not in Path(n).parts,'Invalid manifest entry')
        exact(n,h);listed.add(n)
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p!=ROOT/'checksums.sha256' and '__pycache__' not in p.parts}
    require(actual==listed,'Unexpected/missing release files: '+str(sorted(actual.symmetric_difference(listed))[:8]))
    r=load('data/reference/runtime_hashes.json')
    require(len(r['component_sha256'])==380,'380 runtime entries required')
    for n,h in r['component_sha256'].items():exact('src/software/'+n,h)
    exact('board/config/startup.snapshot.json',r['startup_sha256'])
    face=load('src/software/config/pan_face.local.json')
    exact('src/motion/follow/deployment-manifest.json',face['manifest_sha256'])
    motion=load('src/motion/follow/deployment-manifest.json')['files']
    require(len(motion)==25,'motion release length')
    for e in motion:exact('src/motion/follow/'+e['source_rel'],e['sha256'])
    for r in load('data/results/xir_three_models.json')['models']:
        exact('models/dpu/'+r['filename'],r['sha256'])
        dpu=[s for s in r['partitions'] if s['device']=='DPU']
        require(len(dpu)==1 and dpu[0]['fingerprint']=='0x101000056010407','DPU fingerprint')
    firmware=load('board/firmware_pairing.json')
    for n,h in firmware['runtime_files'].items():
        prefix='/lib/firmware/xilinx/'
        require(n.startswith(prefix),'firmware path')
        exact('board/firmware/'+n[len(prefix):],h)
    for f,k,goal in [('llm_cases.csv','rpc_ms',1837.416),('tts_cases.csv','rpc_ms',718.002)]:
        with (ROOT/'data/results/performance'/f).open(encoding='utf-8-sig',newline='') as stream:
            rows=list(csv.DictReader(stream))
        require(len(rows)==5 and math.isclose(statistics.median(float(r[k]) for r in rows),goal,abs_tol=.002),'public RPC result')
    verify_public_files(ROOT)
    print('PASS | {} release files | board 380 + startup | motion 25 | 3 DPU models | paired firmware | 5 LLM and 5 TTS samples'.format(len(listed)))
if __name__=='__main__':
    main()
