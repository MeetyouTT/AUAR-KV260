"""Readonly canonical-source checks and a reviewable candidate deployment plan."""
import ast,hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
def declarations(path):
    result={}
    for node in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in ('SERVICE_REVISION','SOURCE_FILES'):
                    result[target.id]=ast.literal_eval(node.value)
    return result
def fingerprint(files,*,candidate=False):
    digest=hashlib.sha256()
    for name in files:
        path=H/'candidate_source'/name
        if not candidate or not path.exists():path=A/name
        digest.update(name.encode()+b'\0');digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()
before=declarations(A/'common/voice_service_capabilities.py')
candidate=declarations(H/'candidate_source/common/voice_service_capabilities.py')
old=json.loads((H.parent/'2026-10-28_timeline_memory/PROGRESS.json').read_text(encoding='utf-8'))
assert before['SERVICE_REVISION']=='voice-timeline-20261028-r1'
before_fp=fingerprint(before['SOURCE_FILES']);assert before_fp==old['source_fingerprint']
files={}
for path in sorted((H/'candidate_source').rglob('*.py')):
    name=path.relative_to(H/'candidate_source').as_posix();actual=A/name;prior=H/'before'/name
    ast.parse(path.read_text(encoding='utf-8'))
    if actual.exists():assert prior.exists() and prior.read_bytes()==actual.read_bytes(),'Concurrent source change: '+name
    else:assert not prior.exists()
    files[name]={'before':hashlib.sha256(actual.read_bytes()).hexdigest() if actual.exists() else None,
                 'candidate':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
starter=H.parent/'2026-10-28_device_skills/start_devices.py'
assert starter.read_bytes()==(H/'start_devices_before.py').read_bytes()
plan={'status':'READY_OFFLINE_USER_HOLD','applied':False,'user_hold_board':True,
    'reason':'User confirmed another board test is in progress; retain its state and do not switch production services.',
    'expected_production_revision':before['SERVICE_REVISION'],'expected_production_fingerprint':before_fp,
    'candidate_revision':candidate['SERVICE_REVISION'],'candidate_fingerprint':fingerprint(candidate['SOURCE_FILES'],candidate=True),
    'hub_before':'device-timeline-v1','hub_candidate':'device-timeline-v2','files':files,
    'device_startup':{'path':str(starter),'before':hashlib.sha256(starter.read_bytes()).hexdigest(),
                      'candidate':hashlib.sha256((H/'start_devices_candidate.py').read_bytes()).hexdigest()},
    'board_files_to_replace':[],
    'future_checks':['Wait for the user to say the parallel board test has finished.',
        'Re-read actual board boot, systemd entry, source/config pins and no-motion/listening/IDLE_READY state; do not start its UI just to pass this check.',
        'Confirm the exact loaded Windows r1 fingerprint and unchanged candidate baselines.',
        'Take consistent production-view SQLite snapshots using an independent WMI helper, not the packaged tool AppData view.',
        'Run pending ARM core tests in isolation after the board testing window is released.',
        'Only then restart this project voice and CPU device services with the candidate; preserve other model owners and D-drive storage.',
        'Validate background worker health, digest source visibility, deletion/ACK barriers, actual speech and UI state.',
        'Rollback code only on failed acceptance; retain the latest authoritative databases and built-in SQLite invalidation triggers.']}
(H/'deployment_preview.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':plan['status'],'candidate_revision':plan['candidate_revision'],
    'candidate_fingerprint':plan['candidate_fingerprint'],'canonical_unchanged':True,'files':len(files)}))
