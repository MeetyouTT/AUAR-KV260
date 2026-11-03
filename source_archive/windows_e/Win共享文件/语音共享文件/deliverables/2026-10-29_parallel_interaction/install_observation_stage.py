"""Reversible source transaction for live instrumentation, not final acceptance."""
import hashlib,json,os,runpy,sys,time,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura'
sys.path[:0]=[str(H.parent/'2026-10-29_audio_animation_polish'),str(H.parent/'2026-10-29_service_recovery')]
from board_guard import capture,same
from recovery_common import checkpoint
assert not (H/'observation_installation.json').exists()
manifest=json.loads((H/'merged_manifest.json').read_text(encoding='utf-8'))['files']
baseline=json.loads((H/'baseline.json').read_text(encoding='utf-8'))
same(baseline['board'],capture());time.sleep(.6);same(baseline['board'],capture())
for name,item in manifest.items():
    target=A/name;actual=hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
    assert actual==item['current_before_sha256'],('Concurrent source update',name)
    assert hashlib.sha256((H/'merged/aura'/name).read_bytes()).hexdigest()==item['sha256']
private=checkpoint('before')
(H/'private_before_observation.json').write_text(json.dumps(private,indent=2),encoding='utf-8')
backup=H/'observation_source_before';records={}
for name,item in manifest.items():
    target=A/name
    if target.exists():
        saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(target.read_bytes())
    records[name]={'before':item['current_before_sha256'],'after':item['sha256']}
report=dict(status='PREPARED',phase='OBSERVATION_CALIBRATION_NOT_FINAL',files=records,
 checked_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
 real_private_backup_reference='private_before_observation.json',microphone_enabled=False,motion_command_sent=False,
 new_anonymous_binding_not_yet_integrated=True)
def save():(H/'observation_installation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
save()
written=[]
try:
    for name,item in records.items():
        target=A/name
        actual=hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
        assert actual==item['before'],('Concurrent source update',name)
        raw=(H/'merged/aura'/name).read_bytes();target.parent.mkdir(parents=True,exist_ok=True)
        temporary=target.with_name(target.name+'.coordination-'+uuid.uuid4().hex);temporary.write_bytes(raw);os.replace(temporary,target);written.append(name)
    capabilities=runpy.run_path(str(A/'common/voice_service_capabilities.py'))
    report.update(status='INSTALLED_FOR_OBSERVATION',revision=capabilities['SERVICE_REVISION'],
      fingerprint=capabilities['source_fingerprint'](A),enforcing_gpu_policy=False,other_model_processes_stopped=False)
except Exception as exc:
    report.update(status='INSTALL_FAILED',error=type(exc).__name__+': '+str(exc))
    for name in reversed(written):
        target=(A/name).resolve();target.relative_to(A.resolve());item=records[name]
        assert hashlib.sha256(target.read_bytes()).hexdigest()==item['after'],'Concurrent rollback source change'
        if item['before'] is None:target.unlink()
        else:
            raw=(backup/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==item['before']
            temporary=target.with_name(target.name+'.restore-'+uuid.uuid4().hex);temporary.write_bytes(raw);os.replace(temporary,target)
    report['sources_restored']=True;save();raise
save();print(json.dumps({key:report[key] for key in ('status','phase','revision','fingerprint','enforcing_gpu_policy','new_anonymous_binding_not_yet_integrated')}))
