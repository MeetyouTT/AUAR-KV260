"""Use the original UI once, then read only the new follower's live report."""
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import time

B=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
A=B/'runtime/aura';S=B/'startup/config.json'
ROOT=Path('/home/root/aura-pan-wide-20261028/control-10282601-left40-right45-aaaa15bf')
TX=Path('/home/root/aura-5090-recovery-20261102-903cfade/original-follow-left40-right45-v1')
MANIFEST='9856e25396a55ab4bf17cdcf80b3264aa756919121e19fcb17d89d985ac5097f'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def create(p,value):
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:
        f.write((json.dumps(value,indent=2)+'\n').encode());f.flush();os.fsync(f.fileno())
def request(kind=None):
    c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
    try:
        if kind:c.request('POST','/api/command',json.dumps({'type':kind}).encode(),
            {'Origin':'http://127.0.0.1:8783','Host':'127.0.0.1:8783','Content-Type':'application/json'})
        else:c.request('GET','/api/state')
        r=c.getresponse();raw=r.read(2097153);assert r.status==200 and len(raw)<=2097152
        return json.loads(raw)
    finally:c.close()
def verify():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='903cfade-b93c-48fa-804e-379be1967313'
    assert sha('/sys/firmware/fdt')=='d68bc147f22f5ab23bc60f0c2762af4bcd7b64340953e9c948e28ffa6b80f7ca'
    assert sha(S)=='73e532adad9f4769149f6c8b57844fcdc23a3d6df274902015d51323f5390453'
    owners=[]
    for pid,birth,cmd in ((97308,'2694906','48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'),
                          (97312,'2695022','bb612bf74a9fefd8528337b6d907298563a3c7abe1703b53e54db32971fef121'),
                          (79866,'2265436','acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd')):
        p=Path('/proc')/str(pid)
        assert p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==birth and sha(p/'cmdline')==cmd
        owners.append(dict(pid=pid,birth=birth,cmd_sha256=cmd))
    pins=json.loads(S.read_bytes())['component_sha256']
    assert len(pins)==380 and all(sha(A/k)==v for k,v in pins.items())
    face=json.loads((A/'config/pan_face.local.json').read_bytes())
    assert face['release_root']==str(ROOT) and face['manifest_sha256']==sha(ROOT/'deployment-manifest.json')==MANIFEST
    assert face['arguments']['left-target-center-ratio']=='0.40' and face['arguments']['target-center-ratio']=='0.45'
    files=json.loads((ROOT/'deployment-manifest.json').read_bytes())['files']
    assert len(files)==25 and all(sha(f['destination'])==f['sha256'] for f in files)
    return owners
def snapshot():
    state=request();p=state['manual_pan'];follow=p.get('face_follow') or {};rb=p.get('readback') or {}
    value=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),page=state.get('page'),
        following=p.get('automatic_following'),pan_state=p.get('state'),pan_error=p.get('error'),readback=rb,
        backend_pid=p.get('backend_pid'),face_follow=follow)
    path=follow.get('report')
    if path and Path(path).is_relative_to(ROOT/'runs') and Path(path).is_file():
        r=json.loads(Path(path).read_bytes());control=r.get('result') or {};c=control.get('control') or {}
        value.update(report=path,report_status=r.get('status'),report_error=r.get('error'),
            consumer_manifest_sha256=r.get('consumer_manifest_sha256'),control_parameters=r.get('control_parameters'),
            zone=r.get('zone'),zone_settings_sha256=r.get('zone_settings_sha256'),
            report_result={k:control.get(k) for k in ('state','reason','active','fatal','pulse_us','target_us',
                'commands_accepted','segments','visual_center_completions','target_center_ratio','recenter_state',
                'recenter_intent_pending','motion_mode','readback','hardware_width_trace')},
            controller={k:c.get(k) for k in ('recenter_trigger_side','target_center_ratio','configured_target_center_ratio',
                'configured_left_target_center_ratio','recenter_active','recenter_direction','recenter_phase','raw_center_ratio',
                'raw_left_ratio','authority_deadline_mono_ms')},
            observation_trace=[{k:v.get(k) for k in ('received_mono_ms','state','position','face_center_ratio','face_left_ratio',
                'decision','source_age_ms','detection_age_ms')} for v in r.get('observation_trace',[])])
    return value

owners=verify();before=snapshot();rb=before['readback']
assert before['following'] is False and before['pan_state']=='READY' and not before['pan_error']
assert rb.get('flags')==0 and rb.get('lease_left_ms')==0 and rb.get('reason')==0
create(TX/'ui-start-intent.json',dict(command='pan_face_follow',once=True,before=before))
request('pan_face_follow')
snapshots=[];end=time.monotonic()+10;matched=False
while True:
    value=snapshot();snapshots.append(value)
    if value.get('consumer_manifest_sha256')==MANIFEST:
        params=value['control_parameters']
        assert params['left_target_center_ratio']==.4 and params['target_center_ratio']==.45
        assert params['center_tolerance_ratio']==.03 and params['hardware_slew_recenter'] is True
        c=value['controller'];side=c['recenter_trigger_side'];target=c['target_center_ratio']
        assert side in (-1,0,1) and target==(.4 if side==-1 else .45)
        matched=True
    if time.monotonic()>=end:break
    time.sleep(.5)
owners=verify()
result=dict(status='ORIGINAL_UI_STARTED_NEW_TARGETS_CONFIRMED' if matched else 'START_REQUIRES_READONLY_RECONCILIATION',
    original_ui_command_sent_once='pan_face_follow',repeat_toggle_sent=False,owners=owners,
    actual_new_report_verified=matched,snapshots=snapshots,
    hardware_target_acceptance='PENDING_USER_OBSERVATION',gui_restarted=False,camera_restarted=False)
create(TX/'ui-start-receipt.json',result)
print(json.dumps(result))
