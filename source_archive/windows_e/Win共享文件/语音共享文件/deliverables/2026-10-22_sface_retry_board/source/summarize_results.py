"""Read filtered board reports and retain coverage/measurement limitations."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'reports-all.json').read_text())
summaries=[]
for item in data['reports']:
    r=item['report']
    for variant,s in r.get('variants',{}).items():
        first=s.get('first');last=s.get('last') or s.get('latest_camera_seen')
        if not first or not last:continue
        diagnostics=last.get('pipeline_metrics',{}).get('optional_diagnostics',{})
        before=first['shadow']['execution'];after=last['shadow']['execution']
        complete=s.get('complete') is True
        value={'scope':r['scope'],'variant':variant,'report_path':item['path'],
            'observed_seconds':s.get('observed_seconds'),'functional_passed':s.get('functional_passed',False),
            'stage_targets_met':s.get('stage_targets_met',False),'complete':complete,
            'yolo_hz':s.get('observed_yolo_hz'),'yunet_hz':s.get('observed_yunet_hz'),
            'capture_hz':s.get('observed_capture_hz'),'sface_hz':s.get('sface_hz'),
            'sface_completed_window':s.get('sface_completed_window'),
            'sface_accepted_window':s.get('sface_accepted_window'),
            'sface_requests_window':after['requests']-before['requests'],
            'sface_slot_denials_window':after['slot_denials']-before['slot_denials'],
            'source_coverage_ok':s.get('source_coverage_ok',False),
            'one_face_samples':s.get('one_face_samples'), 'samples':len(s['samples']),
            'prepared_crops_window':s.get('prepared_crops_window'),
            'cpu_percent_of_board':s.get('cpu_window',{}).get('cpu_percent_of_board'),
            'sface_crop_to_feature_ms':last['shadow']['accepted_latency_ms'],
            'sface_optional_occupancy_max_ms':last['dpu_schedule']['optional']['sface']['maximum_ms'],
            'yunet_optional_occupancy_max_ms':last['dpu_schedule']['optional']['yunet']['maximum_ms'],
            'primary_period_overruns_before':first['dpu_schedule']['primary_period_overruns'],
            'primary_period_overruns_after':last['dpu_schedule']['primary_period_overruns'],
            'new_primary_period_overruns':last['dpu_schedule']['primary_period_overruns']-first['dpu_schedule']['primary_period_overruns'],
            'optional_fault_event_count':len(diagnostics.get('fault_events',[])),
            'diagnostic_errors':diagnostics.get('diagnostic_errors'),
            'native_counters':diagnostics.get('counters'),
            'slot_retry':last['shadow'].get('slot_retry',{'enabled':False}),
            'usb_warnings':s.get('usb_warnings'),
            'actual_identity_decisions':last['shadow']['identity_decisions_from_shadow'],
            'templates_written':last['shadow']['templates_written'],
            'rollback_verified':r['rollback_verified'],'restored_pid':r['restored']['pid'],
            'error':r.get('error'),'paired_speedup_valid':False,
            'dpu_hardware_busy_measured':False,'formal_sface_backend_migrated':False}
        if not complete:
            fault=r.get('fault_camera_snapshot') or last
            value['last_healthy_sample_elapsed_s']=s.get('elapsed_s')
            value['partial_completed_window_to_fault_snapshot']=fault['shadow']['execution']['completed']-before['completed']
            value['native_total_completed_at_fault_snapshot']=fault['shadow']['execution']['completed']
            value['partial_window_not_600s_result']=True
            value['usb_warnings_verified_by_separate_kernel_window']=True
        summaries.append(value)
(ROOT/'results-summary.json').write_text(json.dumps({'paired_speedup_valid':False,
    'reason':'A face coverage insufficient; B measured separately; long window has independent coverage',
    'rows':summaries},indent=2)+'\n')
for value in summaries:
    print(json.dumps({key:value[key] for key in ('scope','variant','observed_seconds','sface_completed_window',
        'sface_hz','yolo_hz','yunet_hz','source_coverage_ok','stage_targets_met','error')},ensure_ascii=False))
