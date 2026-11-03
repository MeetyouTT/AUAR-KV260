"""Reversible reviewed source install; LLM/voice sources and data stay untouched."""
import hashlib,json,os,shutil,sys,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura'
sys.path.insert(0,str(A));from common.voice_service_capabilities import source_fingerprint,SOURCE_FILES
assert (H/'native_visual.json').is_file() and json.loads((H/'native_visual.json').read_text())['status']=='PASS'
assert not (H/'source_installation.json').exists(),'Already installed; inspect recorded status'
fingerprint=source_fingerprint(A)
assert fingerprint=='5a4fa28e8679ffd24b61e940455e7dd2341c02c8ae70e8997aa5682c157471f3'
changes={}
for directory in ('board','shared','windows'):
    for path in (H/'candidate'/directory).rglob('*.py'):
        name=path.relative_to(H/'candidate'/directory).as_posix();assert name not in SOURCE_FILES
        changes['aura/'+name]=path.read_bytes()
snapshot=H/'renderer_snapshot';assert not snapshot.exists();shutil.copytree(H/'candidate/renderer_snapshot',snapshot)
old_config=json.loads((H.parent/'2026-10-27_windows_portrait/host_config.json').read_text(encoding='utf-8'))
old_config['snapshot']=str(snapshot)
changes['aura/config/portrait_host.local.json']=json.dumps(old_config,indent=2).encode()
changes['start_portrait.ps1']=("$ErrorActionPreference='Stop'\n& (Join-Path $PSScriptRoot 'deliverables/2026-10-29_audio_animation_polish/start_host.ps1')\nWrite-Host 'Wired CPU portrait service READY on 8796.'\n").encode()
backup=H/'source_backup';records={}
for name,raw in changes.items():
    path=P/name;prior=path.read_bytes() if path.exists() else None
    if prior is not None:
        dst=backup/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(prior)
    records[name]={'before':hashlib.sha256(prior).hexdigest() if prior is not None else None,'after':hashlib.sha256(raw).hexdigest()}
report=dict(status='PREPARED',files=records,voice_fingerprint_before=fingerprint,source_backup=str(backup))
(H/'source_installation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for name,raw in changes.items():
    path=P/name
    assert (hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None)==records[name]['before'],name
    temporary=path.with_name(path.name+'.audio-animation-'+uuid.uuid4().hex);temporary.write_bytes(raw);os.replace(temporary,path)
assert source_fingerprint(A)==fingerprint
report.update(status='INSTALLED',voice_fingerprint_after=source_fingerprint(A),llm_weights_moved=False,voice_model_restarted=False)
(H/'source_installation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'files':len(records),'voice_source_fingerprint_unchanged':True,'historical_snapshot_unchanged':True}))
