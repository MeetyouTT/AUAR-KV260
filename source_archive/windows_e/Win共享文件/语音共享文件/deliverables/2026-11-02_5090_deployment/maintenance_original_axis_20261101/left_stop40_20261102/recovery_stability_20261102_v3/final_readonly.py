import datetime
import hashlib
import http.client
import json
from pathlib import Path
import time

B=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13');A=B/'runtime/aura'
ROOT=Path('/home/root/aura-pan-wide-20261028/control-10282601-left40-right45-stable150-35d5e154')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(port,path):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=4)
    try:
        c.request('GET',path);r=c.getresponse();raw=r.read(2097153);assert r.status==200 and len(raw)<=2097152
        return json.loads(raw)
    finally:c.close()
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot=='903cfade-b93c-48fa-804e-379be1967313'
owners=[]
for pid,birth,cmd in ((97308,'2694906','48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'),
                      (97312,'2695022','bb612bf74a9fefd8528337b6d907298563a3c7abe1703b53e54db32971fef121'),
                      (79866,'2265436','acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd')):
    p=Path('/proc')/str(pid)
    assert p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==birth and sha(p/'cmdline')==cmd
    owners.append(dict(pid=pid,birth=birth,cmd_sha256=cmd))
startup_sha=sha(B/'startup/config.json')
assert startup_sha=='1177df3831407bc819c1f1e3b89090f8c6b97661c8e74c2866b281be93b0a9c8'
pins=json.loads((B/'startup/config.json').read_bytes())['component_sha256']
assert len(pins)==380 and all(sha(A/k)==v for k,v in pins.items())
face=json.loads((A/'config/pan_face.local.json').read_bytes())
assert face['release_root']==str(ROOT)
manifest=json.loads((ROOT/'deployment-manifest.json').read_bytes())
assert len(manifest['files'])==25 and sha(ROOT/'deployment-manifest.json')==face['manifest_sha256']
assert all(sha(f['destination'])==f['sha256'] for f in manifest['files'])
state=get(8783,'/api/state');pan=state['manual_pan'];follow=pan.get('face_follow') or {}
report_path=Path(follow['report']);assert report_path.is_relative_to(ROOT/'runs') and report_path.is_file()
report=json.loads(report_path.read_bytes());result=report.get('result') or {};control=result.get('control') or {}
params=report['control_parameters']
assert params['left_target_center_ratio']==.4 and params['target_center_ratio']==.45 and params['center_tolerance_ratio']==.03
assert params['rearm_stability_ms']==150 and params['rearm_stability_minimum_distinct_sources']==3 and params['rearm_stability_requires_new_detection'] is True
assert report['consumer_manifest_sha256']==face['manifest_sha256']
side=control.get('recenter_trigger_side');target=control.get('target_center_ratio')
assert side in (-1,0,1) and target==(.4 if side==-1 else .45)
zone=Path(face['arguments']['zone-settings']);assert sha(zone)=='815fb333ad60137c93d2147ab14574903556b551d15cad5621320ba94cdfd4e3'
children=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        cmd=(p/'cmdline').read_bytes()
        if (str(ROOT/'run_face_motion.py').encode()+b'\0') not in cmd:continue
        children.append(dict(pid=int(p.name),birth=(p/'stat').read_text().rsplit(')',1)[1].split()[19],
            cmd_sha256=hashlib.sha256(cmd).hexdigest(),has_left40=b'--left-target-center-ratio\x000.40\0' in cmd,
            has_right45=b'--target-center-ratio\x000.45\0' in cmd))
    except (FileNotFoundError,ProcessLookupError):pass
camera=get(8790,'/health')
faults=state.get('runtime_faults')
out=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),boot_id=boot,
    startup_sha256=startup_sha,face_config_sha256=sha(A/'config/pan_face.local.json'),controller_root=str(ROOT),
    controller_manifest_sha256=face['manifest_sha256'],components_verified=380,selected_files_verified=25,
    owners=owners,follow_processes=children,camera_pid=camera.get('pid'),camera_error=camera.get('camera_error'),
    detector_error=camera.get('detector_error'),runtime_fault_count=faults.get('count') if isinstance(faults,dict) else len(faults) if isinstance(faults,list) else None,
    ui_page=state.get('ui_page'),following=pan.get('automatic_following'),pan_state=pan.get('state'),pan_error=pan.get('error'),
    current_readback=pan.get('readback'),report=str(report_path),report_status=report.get('status'),report_error=report.get('error'),
    report_result={k:result.get(k) for k in ('state','reason','active','fatal','elapsed_s','pulse_us','commands_accepted',
        'segments','visual_center_completions','target_center_ratio','recenter_state','recenter_intent_pending','rearm_stability_ms','rearm_stability_gate','rearm_stability_waits','rearm_stability_passes','events')},
    controller={k:control.get(k) for k in ('recenter_trigger_side','target_center_ratio','configured_target_center_ratio',
        'configured_left_target_center_ratio','recenter_phase','recenter_active','raw_center_ratio','raw_left_ratio')},
    report_heartbeat_age_ms=round(time.monotonic()*1000-result['heartbeat_mono_ms'],3) if result.get('heartbeat_mono_ms') else None,
    configured_targets=dict(left=.4,right=.45,tolerance=.03,rearm_stability_ms=150),zone=report['zone'],zone_settings_sha256=sha(zone),
    observed_numeric_trace=[{k:v.get(k) for k in ('received_mono_ms','state','position','face_center_ratio','face_left_ratio',
        'decision','source_age_ms','detection_age_ms')} for v in report.get('observation_trace',[])][-16:],
    device_commands_sent=False,physical_stop_position_acceptance='PENDING_USER_FEEDBACK')
print(json.dumps(out))
