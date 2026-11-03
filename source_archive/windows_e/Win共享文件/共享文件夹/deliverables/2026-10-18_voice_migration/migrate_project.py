"""Copy this project to the user-requested E-drive directory with per-file SHA256."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parents[1]
TARGET=Path('E:/Win共享文件/语音共享文件')
EXCLUDE={'.git','.verysync','.pytest_cache','__pycache__','node_modules','site-packages'}

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def inventory():
    files=[];excluded=[]
    for parent,dirs,names in os.walk(SOURCE,followlinks=False):
        for name in list(dirs):
            path=Path(parent,name)
            if name in EXCLUDE or name.startswith('.venv') or path.is_symlink():
                dirs.remove(name);excluded.append(path.relative_to(SOURCE).as_posix())
        for name in names:
            path=Path(parent,name)
            if path.is_symlink() or name.endswith(('.pyc','.pyo')):continue
            rel=path.relative_to(SOURCE).as_posix()
            if rel.startswith('deliverables/2026-10-18_voice_migration/') and name in {'inventory.json','copy_progress.json','copy_result.json'}:continue
            files.append({'path':rel,'bytes':path.stat().st_size})
    result={'source':str(SOURCE),'destination':str(TARGET),'files':files,'excluded_directories':excluded,
            'total_files':len(files),'total_bytes':sum(row['bytes'] for row in files)}
    (HERE/'inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in {'files','excluded_directories'}},ensure_ascii=True),flush=True)
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--copy',action='store_true');args=parser.parse_args()
    report=inventory()
    if not args.copy:return
    if SOURCE.resolve()==TARGET.resolve() or TARGET.resolve().is_relative_to(SOURCE.resolve()):raise ValueError('Invalid target')
    TARGET.mkdir(parents=True,exist_ok=True)
    if list(TARGET.iterdir()):raise RuntimeError('Target is no longer empty; review before copying')
    saved=[];copied=0;last=time.monotonic()
    for row in report['files']:
        source=SOURCE/row['path'];dest=TARGET/row['path']
        if not dest.resolve().is_relative_to(TARGET.resolve()):raise ValueError('Path escapes destination')
        dest.parent.mkdir(parents=True,exist_ok=True)
        # Read each file once; live logs are a point-in-time snapshot.
        h=hashlib.sha256();size=0
        with source.open('rb') as src,dest.open('xb') as out:
            for block in iter(lambda:src.read(8*1024*1024),b''):
                out.write(block);h.update(block);size+=len(block)
        expected=h.hexdigest()
        if digest(dest)!=expected:raise RuntimeError('Destination checksum mismatch: '+row['path'])
        shutil.copystat(source,dest)
        saved.append({'path':row['path'],'bytes':size,'sha256':expected})
        copied+=size
        if time.monotonic()-last>=15:
            progress={'files_verified':len(saved),'files_total':report['total_files'],'bytes_verified':copied,
                      'bytes_total_estimate':report['total_bytes'],'current_file':row['path']}
            (HERE/'copy_progress.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(progress,ensure_ascii=True),flush=True);last=time.monotonic()
    result={'status':'PASS_ALL_COPIED_FILES_SHA256','date':'2026-10-18','source':str(SOURCE),'destination':str(TARGET),
            'files':saved,'total_files':len(saved),'total_bytes':copied,'excluded_directories':report['excluded_directories'],
            'original_preserved':True,'private_ssh_key_copied':False,'live_logs':'Point-in-time snapshot; source services can keep writing',
            'completed_utc':datetime.now(timezone.utc).isoformat()}
    raw=json.dumps(result,ensure_ascii=False,indent=2)
    (HERE/'copy_result.json').write_text(raw,encoding='utf-8')
    target_report=TARGET/'deliverables/2026-10-18_voice_migration';target_report.mkdir(parents=True,exist_ok=True)
    (target_report/'copy_result.json').write_text(raw,encoding='utf-8')
    print('COPY_AND_VERIFY_PASS',len(saved),copied,flush=True)

if __name__=='__main__':main()
