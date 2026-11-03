"""Read existing numeric follower evidence. No images, identity data or device IO."""
import datetime
import hashlib
import http.client
import json
from pathlib import Path

ROOT=Path('/home/root/aura-pan-wide-20261028/control-10282601-left40-right45-py39-14e598cf')
B=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
def get(port,path):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=4)
    try:
        c.request('GET',path);r=c.getresponse();data=r.read(2097153);assert r.status==200 and len(data)<=2097152
        return json.loads(data)
    finally:c.close()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
state=get(8783,'/api/state');pan=state['manual_pan'];camera=get(8790,'/health')
reports=[]
for p in sorted((ROOT/'runs').glob('ui-*/trial.json')):
    assert not p.is_symlink() and p.stat().st_size<3000000
    r=json.loads(p.read_bytes());v=r.get('result') or {}
    reports.append(dict(path=str(p),sha256=sha(p),status=r.get('status'),error=r.get('error'),
        boot_id=r.get('boot_id'),consumer_manifest_sha256=r.get('consumer_manifest_sha256'),control_polarity=r.get('control_polarity'),
        control_parameters=r.get('control_parameters'),zone=r.get('zone'),zone_settings_sha256=r.get('zone_settings_sha256'),
        result=v,observation_trace=r.get('observation_trace'),input_summary=r.get('input_summary'),
        input_timing=r.get('input_timing'),reader_queue=r.get('reader_queue'),submission_timing=r.get('submission_timing'),
        telemetry=r.get('telemetry'),stop_proof=r.get('stop_proof'),keys=sorted(r)))
health={k:camera.get(k) for k in ('pid','board_boot_id','camera_error','detector_error','capture_age_ms','capture_frames',
    'capture_hz','detected_frames','detection_hz','last_inference_ms','observation_age_ms','observation_frame_id',
    'pipeline_metrics','dpu_schedule','preview_error','preview_hz')}
out=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    startup_sha256=sha(B/'startup/config.json'),current_manual_pan=pan,
    runtime_faults=state.get('runtime_faults'),camera_numeric_health=health,reports=reports,
    device_commands_sent=False,field_direction_label='User-view right vs left; mapping to PWM sign not inferred')
print(json.dumps(out))
