"""Fresh original-UI stop handoff for the authorized CPU optimization window."""
import datetime
import hashlib
import http.client
import json
from pathlib import Path
import time

B=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
A=B/'runtime/aura';S=B/'startup/config.json';F=A/'config/pan_face.local.json'
EXPECTED_BOOT='903cfade-b93c-48fa-804e-379be1967313'
EXPECTED_STARTUP='1177df3831407bc819c1f1e3b89090f8c6b97661c8e74c2866b281be93b0a9c8'
EXPECTED_FACE='5af0f923b5df3d14047b720cb46513e33f9be3be0452dffec9b74235db067acf'
EXPECTED_MANIFEST='9cd35b967bf9c859ed3f1f4de4dc5dad199e81ddfed845435fc8745a41be0ba9'
ROOT=Path('/home/root/aura-pan-wide-20261028/control-10282601-left40-right45-stable150-35d5e154')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def request(port=8783,path='/api/state',command=None):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=4)
    try:
        if command:
            c.request('POST','/api/command',json.dumps({'type':command}).encode(),
                {'Origin':'http://127.0.0.1:8783','Host':'127.0.0.1:8783','Content-Type':'application/json'})
        else:c.request('GET',path)
        r=c.getresponse();data=r.read(2097153);assert r.status==200 and len(data)<=2097152
        return json.loads(data)
    finally:c.close()
def identity(pid):
    p=Path('/proc')/str(pid)
    return dict(pid=pid,birth=p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19],
        cmd_sha256=sha(p/'cmdline'))
def owners():
    expected=((97308,'2694906','48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'),
              (97312,'2695022','bb612bf74a9fefd8528337b6d907298563a3c7abe1703b53e54db32971fef121'),
              (79866,'2265436','acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'))
    values=[]
    for pid,birth,cmd in expected:
        v=identity(pid);assert v['birth']==birth and v['cmd_sha256']==cmd;values.append(v)
    return values
def snapshot():
    state=request();p=state['manual_pan'];follow=p.get('face_follow') or {}
    faults=state.get('runtime_faults') or {}
    return dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),ui_page=state.get('ui_page'),
        state=p.get('state'),following=p.get('automatic_following'),error=p.get('error'),
        pulse_us=p.get('pulse_us'),backend_pid=p.get('backend_pid'),readback=p.get('readback'),
        face_follow={k:follow.get(k) for k in ('state','reason','commands_accepted','elapsed_s','final_flags','report','error','process_cleanup')},
        runtime_fault_count=faults.get('count') if isinstance(faults,dict) else None)
def stopped(v):
    rb=v.get('readback') or {}
    return (v['following'] is False and v['state']=='READY' and not v['error']
        and rb.get('flags')==0 and rb.get('lease_left_ms')==0 and rb.get('reason')==0)
def follower_owners():
    result=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            cmd=(p/'cmdline').read_bytes()
            if (str(ROOT/'run_face_motion.py').encode()+b'\0') in cmd:result.append(identity(int(p.name)))
        except (FileNotFoundError,ProcessLookupError):pass
    return result

boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot==EXPECTED_BOOT
assert sha('/sys/firmware/fdt')=='d68bc147f22f5ab23bc60f0c2762af4bcd7b64340953e9c948e28ffa6b80f7ca'
owner_before=owners();assert sha(S)==EXPECTED_STARTUP and sha(F)==EXPECTED_FACE
startup=json.loads(S.read_bytes());pins=startup['component_sha256']
assert len(pins)==380 and all(sha(A/k)==v for k,v in pins.items())
face=json.loads(F.read_bytes());assert face['release_root']==str(ROOT)
assert face['manifest_sha256']==sha(ROOT/'deployment-manifest.json')==EXPECTED_MANIFEST
manifest=json.loads((ROOT/'deployment-manifest.json').read_bytes())
assert len(manifest['files'])==25 and all(sha(f['destination'])==f['sha256'] for f in manifest['files'])
pan_pins={k:dict(path=str(A/k),pin_sha256=v,actual_sha256=sha(A/k)) for k,v in pins.items() if k.startswith('config/pan_')}
zone=Path(face['arguments']['zone-settings']);zone_sha=sha(zone)
before=snapshot();before_follow_owners=follower_owners();stop_sent=False
if not stopped(before):
    # Only the existing UI owns STOP. Never toggle the follow command here.
    request(command='pan_stop');stop_sent=True
    until=time.monotonic()+15
    while True:
        after=snapshot()
        if stopped(after) and not follower_owners():break
        assert time.monotonic()<until,'Original UI STOP not confirmed'
        time.sleep(.25)
else:
    after=snapshot();assert stopped(after)
after_follow_owners=follower_owners();assert not after_follow_owners
owner_after=owners();assert owner_after==owner_before
assert sha(S)==EXPECTED_STARTUP and sha(F)==EXPECTED_FACE and sha(zone)==zone_sha
assert all(sha(A/k)==v for k,v in pins.items())
last_report={}
report_name=after['face_follow'].get('report')
if report_name:
    p=Path(report_name)
    allowed=[ROOT]+[Path(x['root']) for x in face.get('stopped_readback_predecessors',[])]
    assert any(p.is_relative_to(root/'runs') for root in allowed) and p.is_file() and not p.is_symlink()
    r=json.loads(p.read_bytes());result=r.get('result') or {}
    last_report=dict(path=str(p),sha256=sha(p),status=r.get('status'),error=r.get('error'),
        consumer_manifest_sha256=r.get('consumer_manifest_sha256'),
        result={k:result.get(k) for k in ('state','reason','fatal','elapsed_s','commands_accepted','segments','visual_center_completions','stopped')})
receipt_path=zone.parent/'face-stopped-readback.json'
receipt=None
if receipt_path.is_file():
    v=json.loads(receipt_path.read_bytes());p=Path(v['report'])
    assert any(p.is_relative_to(root/'runs') for root in [ROOT]+[Path(x['root']) for x in face.get('stopped_readback_predecessors',[])])
    receipt=dict(path=str(receipt_path),sha256=sha(receipt_path),receipt=v,
        referenced_report_sha_matches=p.is_file() and sha(p)==v['sha256'])
camera=request(8790,'/health');assert camera.get('pid')==79866 and camera.get('board_boot_id')==boot
out=dict(schema='aura-axis-cpu-coordination-handoff-1',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status='AXIS_STOP_CONFIRMED_FROZEN_FOR_CPU_OPTIMIZATION',authorization=dict(
        human_authorization_verified_in_thread='01a19b1a-6a07-7781-8af9-aacacb1c8ca4',
        scope='本次优化与复测的双向协调',sole_axis_writer='01a19b64-8194-70e3-806b-03fa9a283918'),
    boot_id=boot,fdt_sha256=sha('/sys/firmware/fdt'),owners=owner_after,
    business_root=str(B),startup_path=str(S),startup_sha256=sha(S),components_verified=380,
    pan_component_pins=pan_pins,controller_root=str(ROOT),controller_manifest_sha256=EXPECTED_MANIFEST,
    controller_files_verified=25,face_config_path=str(F),face_config_sha256=sha(F),face_config=face,
    zone_settings_path=str(zone),zone_settings_sha256=zone_sha,
    before=before,after=after,follow_processes_before=before_follow_owners,follow_processes_after=after_follow_owners,
    original_pan_stop_sent_once=stop_sent,axis_command_count=1 if stop_sent else 0,
    motion_start_or_publish_performed=False,already_stopped_readonly=not stop_sent,
    last_report=last_report,original_stopped_receipt=receipt,
    camera_numeric_state=dict(pid=camera.get('pid'),camera_error=camera.get('camera_error'),detector_error=camera.get('detector_error')),
    freeze=dict(axis_publication=True,follow_start=True,until='Explicit bilateral coordination after CPU candidate publication and fresh owner/pin verification'),
    allowed_cpu_owner_actions='CPU owner may normally stop/restart GUI and necessary camera services while retaining latest pan_* bytes/pins, control root, zone settings, and native protection chain.',
    retest_plan='After coordinated publication, dedicated axis chat alone owns bounded original-UI follow start and STOP; CPU owner read-only samples two real dialogue rounds plus 60–120 seconds of follow.',
    private_content_exported=False,models_or_camera_or_gui_sources_modified=False,native_recovery_modified=False)
print(json.dumps(out))
