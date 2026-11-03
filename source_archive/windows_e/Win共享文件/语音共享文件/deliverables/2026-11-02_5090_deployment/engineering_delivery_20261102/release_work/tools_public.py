from common import *
def put(n,s):
    p=ROOT/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((s.strip()+'\n').encode())
put('sim/motion/run_pure_suite.py',r'''
"""Run the frozen controller against a synthetic scene and software clock."""
import sys
import unittest
import test_left_episode
import test_hardware_slew
import test_rearm_stability

suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m)
    for m in (test_left_episode, test_hardware_slew, test_rearm_stability))
result=unittest.TextTestRunner(verbosity=1).run(suite)
if any(m in sys.modules for m in ('vsrv_driver','vsrv_transport','live_writer')):
    raise SystemExit('Unexpected hardware writer imported')
sys.exit(0 if result.wasSuccessful() else 1)
''')
put('build/scripts/pack_firmware.py',r'''
"""Make the board payload from a checked XSA. Runs offline and only writes --out."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'build/original'))
from bitstream_pairing import check_pairing
APP='aura-visual-servo-b4096-wide-v1'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xsa',required=True,type=Path)
    parser.add_argument('--bit',required=True,type=Path,help='companion bitstream from the same routed design')
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    dest=args.out.resolve()
    if dest==ROOT or ROOT in dest.parents:
        parser.error('use a new output outside the package')
    with zipfile.ZipFile(args.xsa) as z:
        bits=[n for n in z.namelist() if n.endswith('.bit')]
        if len(bits)!=1 or not any(n.endswith('.hwh') for n in z.namelist()):
            raise SystemExit('XSA must contain one bitstream and a hardware handoff')
        raw=z.read(bits[0])
    paired=check_pairing(args.bit.read_bytes(),raw)
    dest.mkdir(parents=True,exist_ok=False)
    stage=dest/APP
    stage.mkdir()
    (dest/'paired.bit').write_bytes(raw)
    (dest/'full_pl.bif').write_text('all:\n{\n [destination_device=pl] paired.bit\n}\n')
    bootgen=os.environ.get('BOOTGEN','bootgen')
    subprocess.run([bootgen,'-arch','zynqmp','-image','full_pl.bif','-o',str(stage/(APP+'.bit.bin'))],cwd=str(dest),check=True)
    # The DPU ABI and fixed overlay are frozen to the released wide platform.
    # Require matching register/IP layouts before pairing existing XCLBIN/DTBO.
    with zipfile.ZipFile(ROOT/'board/handoff/wide.xsa') as az, zipfile.ZipFile(args.xsa) as bz:
        def hwh(z):
            names=[n for n in z.namelist() if n.rsplit('/',1)[-1]=='kv260_ispMipiRx_vcu_DP.hwh']
            if len(names)!=1:
                raise ValueError('expected a single KV260 handoff')
            return z.read(names[0])
        if hwh(az)!=hwh(bz):
            raise SystemExit('HWH differs from audited platform; review ABI and regenerate companion artifacts')
    source=ROOT/'board/firmware'/APP
    manifest=json.loads((ROOT/'board/firmware_pairing.json').read_text())
    for n in [APP+'.dtbo',APP+'.xclbin','shell.json']:
        payload=(source/n).read_bytes()
        key='/lib/firmware/xilinx/'+APP+'/'+n
        if hashlib.sha256(payload).hexdigest()!=manifest['runtime_files'][key]:
            raise SystemExit('Reference payload hash mismatch: '+n)
        (stage/n).write_bytes(payload)
    (dest/'pairing.json').write_text(json.dumps(paired,indent=2)+'\n')
    print('Verified firmware set:',stage)

if __name__=='__main__':
    main()
''')
put('build/scripts/verify.py',r'''
"""Offline, single-threaded release integrity and reference checks. Python 3.8+."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
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
    print('PASS | {} release files | board 380 + startup | motion 25 | 3 DPU models | paired firmware | 5 LLM and 5 TTS samples'.format(len(listed)))
if __name__=='__main__':
    main()
''')
put('board/scripts/stage.py',r'''
"""Prepare a new rootfs staging tree on a PC. No device I/O or service actions."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'build/scripts'))
from verify import main as verify_release
def read(n):return json.loads((ROOT/n).read_text(encoding='utf8'))
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',required=True,type=Path,help='new empty staging directory')
    ap.add_argument('--audio',type=Path,help='auar_board_audio_dependencies.zip')
    a=ap.parse_args(); out=a.out.resolve()
    if out==ROOT or ROOT in out.parents or out.exists():
        ap.error('--out must be a new directory outside the release')
    verify_release()
    audio_manifest=read('models/board_audio_dependencies.json')
    cfg=read('src/software/config/board_avatar_gtk.json')['board_business']
    if a.audio:
        with zipfile.ZipFile(a.audio) as z:
            for r in audio_manifest:
                data=z.read('board_audio/'+r['path'])
                if len(data)!=r['bytes'] or hashlib.sha256(data).hexdigest()!=r['sha256']:
                    raise RuntimeError('Board audio dependency mismatch: '+r['path'])
    out.mkdir(parents=True)
    def dest(path):
        if not path.startswith('/') or '..' in Path(path).parts:raise ValueError(path)
        return out/path.lstrip('/')
    def cp(src,path):
        p=dest(path);p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists() and p.read_bytes()!=src.read_bytes():raise RuntimeError('conflict: '+path)
        shutil.copyfile(str(src),str(p))
    def tree(src,path):
        for p in src.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:cp(p,path+'/'+p.relative_to(src).as_posix())
    startup=read('board/config/startup.snapshot.json')
    bus=startup['runtime']
    tree(ROOT/'src/software',bus+'/aura')
    cp(ROOT/'board/config/startup.snapshot.json',bus.rsplit('/',1)[0]+'/startup/config.json')
    cp(ROOT/'board/startup/launcher.py',bus.rsplit('/',1)[0]+'/startup/launcher.py')
    tree(ROOT/'board/firmware','/lib/firmware/xilinx')
    tree(ROOT/'src/motion/follow',read('src/software/config/pan_face.local.json')['release_root'])
    tree(ROOT/'src/camera/runtime',read('src/camera/release_r4.json')['deployment_path']+'/aura')
    for n,r in read('src/camera/entry_chain/source_paths.json').items():cp(ROOT/r['path'],n)
    for e in read('board/config/deployment_files.json'):cp(ROOT/e['source'],e['destination'])
    if a.audio:
        roots={'asr':cfg['asr_directory'],'speaker':cfg['speaker']['model_directory'],
               'frontend':cfg['frontend_directory'],'wheels_arm64':'/opt/auar/wheels'}
        with zipfile.ZipFile(a.audio) as z:
            for r in audio_manifest:
                kind,n=r['path'].split('/',1)
                p=dest(roots[kind]+'/'+n);p.parent.mkdir(parents=True,exist_ok=True)
                with z.open('board_audio/'+r['path']) as f,p.open('wb') as w:shutil.copyfileobj(f,w)
    print('PASS: offline rootfs staging:',out)
    print('Follow board/readme.md for image, clock, per-boot camera binding, private-area bootstrap and commissioning.')
if __name__=='__main__':main()
''')
