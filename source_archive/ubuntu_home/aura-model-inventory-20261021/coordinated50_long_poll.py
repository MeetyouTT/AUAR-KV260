import json,subprocess
from pathlib import Path
root=Path('/home/root/aura-dpu-vision-20261021')
launch=root/'postpower-coordinated50-launches/fda2e51c83dd27b4/launch-result.json'
out={'short_launch':json.loads(launch.read_text()) if launch.exists() else None}
rows=sorted((root/'postpower-retry-live').glob('coordinated50-*/deployment-result.json'),key=lambda p:p.stat().st_mtime)
if rows:
    p=rows[-1];d=json.loads(p.read_text());samples=d.get('samples',[])
    out['report_path']=str(p)
    out['handoff_root']=d.get('handoff_root')
    out['summary']={k:d.get(k) for k in ('scope','phase','passed','complete','error','elapsed_s',
        'observed_seconds','observed_yolo_hz','observed_yunet_hz','cpu_window','usb_warning_count',
        'sampled_freshness','gap_record_retention_passed','throughput_and_protection_passed',
        'rollback_verified','rollback_error','sample_count','protected_audio_source_verified','restored_audio_pid')}
    last=samples[-1] if samples else {}
    face=last.get('face_targets',{});metrics=d.get('freshness_final') or face.get('freshness_metrics',{})
    out['latest_yunet']=last.get('dpu_schedule',{}).get('optional',{}).get('yunet')
    out['latest_source_age_ms']=face.get('source_age_ms')
    out['recovery_stats']=face.get('slot_retry')
    out['gap_counters']={k:metrics.get('counters',{}).get(k) for k in ('offers','attempts',
        'slot_unavailable','definite_clipped_gap_intervals','observed_gap_intervals','cancelled_busy')}
    out['gap_records']=metrics.get('gap_records');out['gap_records_dropped']=metrics.get('gap_records_dropped')
long=root/'postpower-long-launches/28b4a68b26979f4d/launch-result.json'
out['long_launch']=json.loads(long.read_text()) if long.exists() else None
out['long_service']=subprocess.run(['systemctl','show','aura-postpower-long-28b4a68b26979f4d','-p','MainPID','-p','ActiveState','-p','Result'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5).stdout.strip()
print(json.dumps(out,separators=(',',':')))
