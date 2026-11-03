"""Build the minimal, verified 汐蓝 migration package without local models/envs."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import zipfile

AURA=Path(__file__).resolve().parents[1];SHARED=AURA.parent;WORKSPACE=SHARED.parent
ROOT=SHARED/'deliverables/2026-10-06_xilan_live'

def build(destination):
    files=set()
    def tree(path,allowed):
        for file in path.rglob('*'):
            if file.is_file() and file.suffix.lower() in allowed and '__pycache__' not in file.parts:files.add(file)
    tree(AURA/'board',{'.py'})
    tree(AURA/'tools',{'.py','.bat'})
    tree(AURA/'assets/avatar',{'.png','.json'})
    tree(AURA/'docs/demo_stage',{'.md'})
    files.update([AURA/'README.md',AURA/'requirements-live.txt',AURA/'tests/test_realtime_stage.py',AURA/'tests/test_realtime_audio_protocol.py'])
    reuse=SHARED/'deliverables/2026-10-06_avatar_reuse'
    files.update([reuse/'preview_script.py',reuse/'emotion_profile.json'])
    tree(reuse/'candidates',{'.png'})
    blink=SHARED/'deliverables/2026-10-06_voice_blink'
    files.add(blink/'blink_profile.json');tree(blink/'eyes',{'.png'})
    voice=SHARED/'deliverables/2026-10-06_voice_selected_soft_young'
    files.update([voice/'selection.json',voice/'base_model_verification.json',voice/'reference/soft_young.wav'])
    tree(ROOT/'cache',{'.wav','.json'})
    for file in ROOT.iterdir():
        if file.is_file() and file.suffix in {'.html','.js','.json','.md','.bat','.png'} and file.name not in {'package_manifest.json','package_verification.json','migration_verification.json'}:files.add(file)
    # Keep the latest measured session with its window/frame evidence, rather
    # than bundling older diagnostic attempts as current acceptance evidence.
    reports=sorted((ROOT/'evidence').glob('live_*.json'))
    if reports:
        latest=reports[-1];files.add(latest);stamp=latest.stem.removeprefix('live_')
        for name in ('window','frame'):
            proof=ROOT/'evidence'/f'{name}_{stamp}.png'
            if proof.is_file():files.add(proof)
    files.add(SHARED/'.cline-handover.md')
    files=sorted(files,key=lambda file:file.relative_to(SHARED).as_posix())
    for file in files:
        if not file.is_file():raise FileNotFoundError(file)
    # Do not overwrite the user's live connection setting. The portable copy
    # starts with manual playback until its own dialogue host is configured.
    config_path=ROOT/'stage_config.json';config=json.loads(config_path.read_text(encoding='utf-8'))
    config['dialogue']['enabled']=False
    overrides={config_path:json.dumps(config,ensure_ascii=False,indent=2).encode('utf-8')}
    records=[]
    for file in files:
        data=overrides[file] if file in overrides else file.read_bytes()
        records.append({'file':file.relative_to(SHARED).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    manifest={'version':1,'character':'汐蓝','purpose':'PC live-stage migration foundation; cached playback needs no inference model',
              'model_environments_included':False,'portable_dialogue_enabled':False,'live_config_preserved':True,
              'file_count':len(records),'source_bytes':sum(row['bytes'] for row in records),'files':records}
    manifest_bytes=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8')
    (ROOT/'package_manifest.json').write_bytes(manifest_bytes)
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():destination=destination.with_stem(destination.stem+'_'+str(time.time_ns()))
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for file,row in zip(files,records):
            name='共享文件夹/'+row['file']
            if file in overrides:archive.writestr(name,overrides[file])
            else:archive.write(file,name)
        archive.writestr('共享文件夹/package_manifest.json',manifest_bytes)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        for row in records:
            data=archive.read('共享文件夹/'+row['file'])
            assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
    report={'status':'PASS','archive':str(destination),'archive_bytes':destination.stat().st_size,'archive_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),
            'verified_entries':len(records)+1,'manifest_entries':len(records),'source_bytes':manifest['source_bytes'],
            'voice_cache_clips':len(list((ROOT/'cache').glob('*.wav'))),'all_entry_hashes_verified':True}
    destination.with_suffix('.verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'package_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2));return destination

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=WORKSPACE/'存档/汐蓝_实时演示移机基础包_2026-10-06_r1.zip');args=parser.parse_args();build(args.out)
