"""Inventory installed original axis paths and parameters; no project/device imports or actions."""
import datetime
import hashlib
import json
from pathlib import Path
import time

BOOT='903cfade-b93c-48fa-804e-379be1967313'
STARTUP=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
startup_raw=STARTUP.read_bytes()
assert hashlib.sha256(startup_raw).hexdigest()=='3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'
startup=json.loads(startup_raw);aura=Path(startup['runtime'])/'aura'
sources={}

def public(path, text=True):
    path=Path(path);result={'path':str(path),'exists':path.exists(),'symlink':path.is_symlink()}
    assert path.suffix not in ('.db','.sqlite','.sqlite3')
    if not path.is_file() or path.is_symlink():return result
    assert path.resolve(strict=True)==path and path.stat().st_size<=16000000
    data=path.read_bytes();result.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
    if text and len(data)<=160000 and path.suffix in ('.json','.py','.txt','.md'):
        result['text']=data.decode('utf-8')
    sources[str(path)]=result
    return result

def document(path):
    value=public(path)
    assert 'text' in value
    return json.loads(value['text'])

manual_path=aura/'config/pan_manual.local.json';manual=document(manual_path)
face_path=Path(manual['face_follow_config']);face=document(face_path)
manual_release=document(manual['release_manifest'])
arguments=face['arguments'];argument_documents={}
for key in ('context','direction-evidence','human-evidence','zone-settings'):
    if key in arguments:argument_documents[key]=document(arguments[key])
base=Path('/home/root/aura-pan-wide-20261028/control-10282601')
selected=Path(face['release_root'])
controllers={}
for root in sorted({base,selected},key=str):
    manifest=public(root/'deployment-manifest.json')
    entries=json.loads(manifest['text'])['files']
    checks=[]
    for item in entries:
        actual=public(item['destination'],text=False)
        checks.append({'path':item['destination'],'expected_sha256':item['sha256'],
            'actual_sha256':actual.get('sha256'),'matches':actual.get('sha256')==item['sha256']})
    for name in ('run_face_motion.py','continuous_face_control.py','hardware_slew_session.py',
                 'face_zone.py','face_stream.py','session_shutdown.py','trajectory.py',
                 'input_timing.py','input_freshness.py','session_target.py','pwm_budget.py',
                 'batch_transport.py','deadline_driver.py'):
        public(root/name)
    controllers[str(root)]={'manifest_path':str(root/'deployment-manifest.json'),
        'manifest_sha256':manifest['sha256'],'files':checks,'all_match':all(v['matches'] for v in checks)}

for name in ('tools/board_avatar_pan.py','tools/face_pan_controls.py','tools/follow_process_cleanup.py',
             'board/motion/manual_live_config.py','board/motion/manual_vsrv.py',
             'board/motion/manual_process.py','board/motion/current_reference_release.py',
             'board/motion/rated_range_release.py','board/motion/manual_release.py'):
    data=public(aura/name)
    assert data.get('sha256')==startup['component_sha256'][name]

release=Path('/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c')
for name in ('candidate-manifest.json','bench_identity_stop.py','rated_range_trial.py',
             'driver/vsrv_driver.py','driver/vsrv_transport.py','driver/libvsrv.so'):
    public(release/name)
ops=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
for name in ('boot_ops.py','native_entry.py','native_entry_pan_face_v5.py','policy.py'):
    public(ops/name)

maintenance={}
for root in (Path('/home/root/aura-pan-wide-resume-20261029'),
             Path('/home/root/aura-system-pan-20261028'),
             Path('/home/root/aura-axis-priority-20261101-3c94e7a0')):
    items=[]
    if root.is_dir():
        for child in sorted(root.iterdir(),key=lambda p:p.name):
            if child.is_symlink():continue
            if child.is_file():
                items.append({'path':str(child),'bytes':child.stat().st_size})
                if child.suffix=='.py':public(child)
            elif child.is_dir() and child.name in ('tools','ops','scripts','maintenance'):
                for path in sorted(child.iterdir(),key=lambda p:p.name):
                    if path.is_file() and not path.is_symlink():
                        items.append({'path':str(path),'bytes':path.stat().st_size})
                        if path.suffix=='.py':public(path)
    maintenance[str(root)]={'exists':root.is_dir(),'shallow_files':items}

assert hashlib.sha256(STARTUP.read_bytes()).hexdigest()==hashlib.sha256(startup_raw).hexdigest()
print(json.dumps({'schema':'aura-original-axis-inventory-readonly-1','boot_id':BOOT,
    'board_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'board_mono':time.monotonic(),
    'startup_sha256':hashlib.sha256(startup_raw).hexdigest(),'runtime_root':str(aura),
    'manual_config_path':str(manual_path),'manual_config':manual,'face_config_path':str(face_path),
    'face_config':face,'manual_release':manual_release,'argument_documents':argument_documents,
    'controllers':controllers,'maintenance_roots':maintenance,'sources':sources,
    'board_mutations':False,'project_imported':False,'device_opened':False,
    'service_or_loader_or_motion_action_sent':False,'database_opened':False}))
