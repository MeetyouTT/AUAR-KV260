"""Summarize numeric same-PID evidence without claiming a controlled speedup."""
import json
import math
from pathlib import Path


def assess(value):
    report=value['report'];samples=report['samples']
    assert report['complete'] and report['rollback_verified']
    result={key:report.get(key) for key in ('scope','passed','error','observed_seconds',
        'observed_yolo_hz','observed_yunet_hz','observed_capture_hz','cpu_window','freshness',
        'throughput_and_optional_protection_passed','affinity_shutdown_error')}
    result.update(sample_count=len(samples),restored_pid=report['restored']['pid'],
        thread_cleanup=report.get('affinity_shutdown',{}).get('clean_selected_thread_restoration_and_close'),
        controlled_speedup_proven=False,dpu_busy_fraction_measured=False,
        scope_limits='sparse health snapshots; successful face results may contain no detected face')
    end=report.get('camera_after') or report.get('fault_camera_snapshot') or report.get('latest_camera_seen')
    if end:
        result['last_optional']=end['dpu_schedule']['optional']
    if len(samples)>1:
        first,last=samples[0],samples[-1];assert first['pid']==last['pid']
        ages=[sample['face_targets']['source_age_ms'] for sample in samples]
        assert all(type(age) is int and age>=0 for age in ages)
        delta_seconds=(last['pipeline_metrics']['optional_diagnostics']['snapshot_mono_ns']
            -first['pipeline_metrics']['optional_diagnostics']['snapshot_mono_ns'])/1e9
        published=last['face_targets']['processed']-first['face_targets']['processed']
        native=last['dpu_schedule']['optional']['yunet']['calls']-first['dpu_schedule']['optional']['yunet']['calls']
        result.update(snapshot_span_seconds=delta_seconds,published_result_delta=published,
            native_completed_delta=native,maximum_sampled_face_age_ms=max(ages),
            sampled_face_age_p95_ms=sorted(ages)[math.ceil(len(ages)*.95)-1],
            sampled_face_age_at_or_over_ttl=sum(age>=1000 for age in ages),
            primary_period_overruns_first=first['dpu_schedule']['primary_period_overruns'],
            primary_period_overruns_last=last['dpu_schedule']['primary_period_overruns'])
        if report.get('observed_seconds'):
            result['published_results_per_harness_second']=published/report['observed_seconds']
    return result


if __name__=='__main__':
    root=Path(__file__).resolve().parent
    results={}
    for name in ('first','short','long'):
        p=root/('result-'+name+'.json')
        if not p.exists():p=root/'evidence'/('trial-'+name+'.json')
        if p.exists():results[name]=assess(json.loads(p.read_text()))
    print(json.dumps(results,ensure_ascii=False,indent=2))
