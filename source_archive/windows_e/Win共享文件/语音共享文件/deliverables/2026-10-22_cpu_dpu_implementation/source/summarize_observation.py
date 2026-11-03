"""Export actual sampled deltas. No reconstruction of unsampled failures."""
import argparse,csv,json
from pathlib import Path


def summarize(report):
    samples=report['samples'];rows=[]
    for first,last in zip(samples,samples[1:]):
        elapsed=last['elapsed_s']-first['elapsed_s']
        if elapsed<=0 or first['pid']!=last['pid']:raise ValueError('Mixed camera epoch or nonmonotonic samples')
        a=first['shadow'];b=last['shadow'];cpu=last.get('cpu_window') or {}
        row={'elapsed_s':last['elapsed_s'],'interval_s':elapsed,'camera_pid':last['pid'],
            'sampled_face_count':last['face_count'],
            'single_face_at_both_endpoints':first['face_count']==last['face_count']==1,
            'yolo_hz':(last['detected_frames']-first['detected_frames'])/elapsed,
            'yunet_hz':(last['dpu_schedule']['optional']['yunet']['calls']-first['dpu_schedule']['optional']['yunet']['calls'])/elapsed,
            'sface_completed':b['execution']['completed']-a['execution']['completed'],
            'sface_accepted':b['accepted']-a['accepted'],
            'sface_deferred':b['deferred']-a['deferred'],
            'sface_rejected_stale':b['stale']-a['stale'],
            'sface_failures':b['failures']-a['failures'],
            'cpu_pct_board':cpu.get('cpu_percent_of_board'),
            'camera_core_seconds':cpu.get('camera_core_seconds'),
            'camera_rss_bytes':cpu.get('camera_rss_bytes'),
            'primary_observation_age_ms_snapshot':last['observation_age_ms']}
        rows.append(row)
    summary={'scope':'Observed health sample intervals only; failure state may not have been recorded',
        'complete':report['complete'],'passed':report['passed'],'observation_status':report.get('observation_status'),
        'error':report.get('error'),'sample_count':len(samples),'interval_count':len(rows),
        'target_observation_seconds':1800,
        'last_recorded_elapsed_s':samples[-1]['elapsed_s'] if samples else None,
        'rollback_verified':report.get('rollback_verified'),
        'ui_pid_preserved_during_trial':report.get('ui_pid_preserved'),
        'xserver_pid_preserved':report.get('xserver_pid_preserved'),
        'identity_database_configuration_changed':report['identity_database_configuration_changed'],
        'no_field_identity_acceptance':True}
    if rows:
        seconds=sum(r['interval_s'] for r in rows)
        completed=sum(r['sface_completed'] for r in rows);accepted=sum(r['sface_accepted'] for r in rows)
        cpu_windows=[(r['interval_s'],r['cpu_pct_board']) for r in rows if r['cpu_pct_board'] is not None]
        summary.update(recorded_interval_seconds=seconds,
            observed_yolo_hz=sum(r['interval_s']*r['yolo_hz'] for r in rows)/seconds,
            observed_yunet_hz=sum(r['interval_s']*r['yunet_hz'] for r in rows)/seconds,
            sface_completed_in_recorded_intervals=completed,sface_accepted_in_recorded_intervals=accepted,
            sface_valid_hz_in_recorded_intervals=accepted/seconds,
            sampled_cpu_pct_board_duration_weighted=sum(t*v for t,v in cpu_windows)/sum(t for t,_ in cpu_windows),
            camera_core_seconds_in_recorded_intervals=sum(r['camera_core_seconds'] or 0 for r in rows),
            sface_latency_cumulative_at_last_sample=samples[-1]['shadow']['accepted_latency_ms'],
            identity_decisions_from_shadow=samples[-1]['shadow']['identity_decisions_from_shadow'],
            templates_written=samples[-1]['shadow']['templates_written'])
    return summary,rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('report',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();summary,rows=summarize(json.loads(args.report.read_text()))
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if rows:
        with (args.output/'intervals.csv').open('w',newline='') as out:
            writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(json.dumps(summary))


if __name__=='__main__':main()
