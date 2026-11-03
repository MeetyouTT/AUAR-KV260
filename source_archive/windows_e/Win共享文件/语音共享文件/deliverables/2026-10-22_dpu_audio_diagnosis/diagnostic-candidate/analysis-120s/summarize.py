"""Reproduce numeric, source-scoped analysis of existing sanitized evidence."""
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EVIDENCE=Path('/home/ghmd/aura-cpu-dpu-implementation-20261022')
current_path=EVIDENCE/'yunet-diagnostic-120s-full.json'
shadow_path=EVIDENCE/'longrun-failed-full.json'
current=json.loads(current_path.read_text())
shadow=json.loads(shadow_path.read_text())
first,last=current['samples'][0],current['samples'][-1]
stages=current['camera_after']['pipeline_metrics']['stages']
with (ROOT/'stages.csv').open('w',newline='') as out:
    writer=csv.writer(out)
    writer.writerow(['stage','scope','count','mean_ms','min_ms','max_ms','recent_count','recent_p50_ms','recent_p95_ms'])
    for stage,row in stages.items():
        writer.writerow([stage,'candidate process lifetime; recent quantiles last <=256 calls',row['count'],
                         row['mean_ms'],row['min_ms'],row['max_ms'],row['recent_count'],
                         row['recent_p50_ms'],row['recent_p95_ms']])
counter=current['camera_after']['dpu_schedule']['optional_diagnostics']['counters']['yunet']
s=shadow['samples'][-1]
elapsed=s['elapsed_s']-shadow['samples'][0]['elapsed_s']
h=s['shadow'];execution=h['execution']
total=current['pilot_cpu_total']
result={
    'scope':'READ_ONLY_EXISTING_EVIDENCE_NOT_NEW_BOARD_MEASUREMENT',
    'input_files':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (current_path,shadow_path)],
    'yunet_120s':{'passed_short_diagnostic':current['passed'],'long_run_accepted':False,
        'candidate_pid':current['camera_pid'],'observation_elapsed_s':current['observation_elapsed_s'],
        'actual_successful_waits':current['diagnostic_completed_waits'],
        'observed_yolo_hz':current['observed_yolo_hz'],'observed_yunet_hz':current['observed_yunet_hz'],
        'board_cpu_percent_4cores_total100':total['cpu_percent_of_board'],
        'camera_cpu_percent_of_board':total['camera_percent_of_board'],
        'camera_core_seconds_per_second':total['camera_core_seconds']/total['duration_s'],
        'usb_warnings':current['usb_audio_warning_count'],'rollback_verified':current['rollback_verified'],
        'admission_counters_process_lifetime':counter,
        'admitted_fraction':counter['admitted']/counter['requests'],
        'rejected_deadline_fraction_of_all':counter['rejected_deadline']/counter['requests'],
        'rejected_active_fraction_of_all':counter['rejected_active']/counter['requests'],
        'stage_durations_are_wall_not_cpu':True,'stages_overlap_and_must_not_be_summed':True,
        'new_xrt_task_busy_measurement_available':False},
    'old_shadow_last_saved_window':{'elapsed_s_between_saved_endpoints':elapsed,
        'last_saved_elapsed_s':s['elapsed_s'],'offered':h['offered'],'enqueued':h['enqueued'],
        'replaced':h['replaced'],'producer_dropped':h['producer_dropped'],'stale':h['stale'],
        'execution_requests':execution['requests'],'completed':execution['completed'],
        'slot_denials':execution['slot_denials'],
        'offered_hz':h['offered']/elapsed,'completed_hz':execution['completed']/elapsed,
        'completed_fraction_of_requests':execution['completed']/execution['requests'],
        'source':'last retained healthy snapshot, not missing failure snapshot',
        'socket_timeout_ms':650,'identity_post_process_interval_ms':500,'shadow_post_attempt_interval_ms':1000,
        'http_elapsed_or_timeout_count_measured':False,
        'timeout_plus_interval_arrival_explanation':'plausible from code; not proven per-request latency'}}
(ROOT/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'yunet_admitted_fraction':result['yunet_120s']['admitted_fraction'],
                 'shadow_offered_hz':result['old_shadow_last_saved_window']['offered_hz'],
                 'shadow_completed_hz':result['old_shadow_last_saved_window']['completed_hz']},indent=2))
