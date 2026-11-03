"""Extract to a fresh workspace path and run the offline stage preflight."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

AURA=Path(__file__).resolve().parents[1];ROOT=AURA.parent/'deliverables/2026-10-06_xilan_live'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path);args=parser.parse_args()
    destination=AURA.parent.parent/'tmp'/f'xilan-migration-check-{time.time_ns()}';destination.mkdir(parents=True)
    with zipfile.ZipFile(args.archive) as archive:
        manifest=json.loads(archive.read('共享文件夹/package_manifest.json'))
        for member in archive.infolist():
            target=(destination/member.filename).resolve()
            if not target.is_relative_to(destination.resolve()):raise ValueError('Invalid package entry')
        archive.extractall(destination)
    shared=destination/'共享文件夹'
    config=json.loads((shared/'deliverables/2026-10-06_xilan_live/stage_config.json').read_text(encoding='utf-8'))
    assert config['dialogue']['enabled'] is False
    for row in manifest['files']:
        data=(shared/row['file']).read_bytes()
        if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Changed file: '+row['file'])
    result=subprocess.run([sys.executable,'-B',str(shared/'aura/tools/realtime_stage.py'),'--check'],cwd=shared,capture_output=True,text=True,encoding='utf-8',timeout=60)
    if result.returncode:raise RuntimeError(result.stdout+'\n'+result.stderr)
    check=json.loads(result.stdout.strip().splitlines()[-1])
    assert check['status']=='PASS' and check['inference_model_loaded'] is False
    assert len(check['cached_clips'])==4 and all(row['cache_hit'] for row in check['cached_clips'])
    report={'status':'PASS','archive':str(args.archive),'fresh_extract':str(shared),'verified_files':manifest['file_count'],
            'portable_dialogue_enabled':False,'isolated_process_check':check,
            'note':'Fresh relative paths; cache-only preflight using playback Python without Qwen/Torch. Not another physical PC or board test.'}
    (ROOT/'migration_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    args.archive.with_suffix('.migration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
