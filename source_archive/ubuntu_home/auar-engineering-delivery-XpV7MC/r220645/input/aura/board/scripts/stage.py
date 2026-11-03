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
