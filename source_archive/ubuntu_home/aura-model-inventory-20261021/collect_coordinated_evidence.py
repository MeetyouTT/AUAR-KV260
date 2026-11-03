"""Export bounded numeric evidence; raw observations remain private on board."""
import base64,gzip,hashlib,json
from pathlib import Path
root=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live')
reports=sorted(root.glob('coordinated50-*/deployment-result.json'),key=lambda p:p.stat().st_mtime)
out=[]
for p in reports:
    raw=p.read_bytes();d=json.loads(raw)
    if not d.get('complete'):continue
    value={k:d.get(k) for k in ('scope','complete','passed','error','elapsed_s','observed_seconds',
        'observed_yolo_hz','observed_yunet_hz','observed_capture_hz','cpu_window','usb_warning_count',
        'native_completed_delta','published_delta','sampled_freshness','throughput_and_protection_passed',
        'freshness_final','gap_record_retention_passed','rollback_verified','rollback_error',
        'rollback_timer_left_armed','timer','protected_audio_source_verified','restored_audio_pid',
        'original_unit_sha256','candidate_unit_sha256','retry_hashes','process_setting','handoff_root')}
    value.update(private_full_report=str(p),private_full_report_sha256=hashlib.sha256(raw).hexdigest(),samples=[])
    for s in d.get('samples',[]):
        face=s.get('face_targets',{});schedule=s.get('dpu_schedule',{})
        diag=schedule.get('optional_diagnostics',{})
        fresh=face.get('freshness_metrics',{})
        value['samples'].append({**{k:s.get(k) for k in ('elapsed_s','pid','detected_frames','capture_frames','observation_age_ms')},
            'face_source_age_ms':face.get('source_age_ms'),'face_backend':face.get('backend'),
            'face_processed':face.get('processed'),'face_discarded':face.get('discarded'),
            'yunet':schedule.get('optional',{}).get('yunet'),'primary_period_overruns':schedule.get('primary_period_overruns'),
            'native_counters':diag.get('counters',{}).get('yunet'),'fault_events':diag.get('fault_events'),
            'retry':face.get('slot_retry'),'freshness_counters':fresh.get('counters')})
    value['restored']={k:d.get('restored',{}).get(k) for k in ('pid','camera_error','detector_error','identity_backend','face_targets','pipeline_metrics','shadow')}
    out.append(value)
payload=json.dumps({'scope':'numeric_projection_of_complete_coordinated_trials','reports':out},separators=(',',':')).encode()
print(json.dumps({'reports':len(out),'bytes':len(payload),'gzip_base64':base64.b64encode(gzip.compress(payload,mtime=0)).decode()}))
