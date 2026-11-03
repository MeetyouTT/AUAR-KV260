"""Analyze the sealed serial ABBA and JPEG-factor control without composite scoring."""
from pathlib import Path
import argparse,csv,json,statistics as S

def mean(values):return sum(values)/len(values) if values else None
def spread(values):return dict(n=len(values),mean=mean(values),min=min(values),max=max(values),sample_std=S.stdev(values) if len(values)>1 else None) if values else None
def camera(row):
    values=row['resources']['camera_samples'];result={}
    if len(values)>1:
        a,b=values[0],values[-1];dt=b['at']-a['at']
        for key in ('capture_frames','detected_frames','preview_frames','identity.processed'):
            if key in a['numeric'] and key in b['numeric']:result[key+'_per_second']=(b['numeric'][key]-a['numeric'][key])/dt
    result['error_samples']=sum(any(v for k,v in x['numeric'].items() if k.endswith('_error_present')) for x in values)
    result['people_counts']=sorted({x['numeric'].get('people_count') for x in values if x['numeric'].get('people_count') is not None})
    return result

def flatten(row):
    r=row['resources'];s=row['summary'];display=s['end_display'];cold=row.get('first_ready_resources') or {}
    pid=str(row['pid']);cold_mem=cold.get('process_memory',{}).get(pid,{})
    return dict(index=row['index'],backend=row['backend'],duration=s['measurement_duration_seconds'],
      renderer_cpu_s_s=r['renderer_family_cpu_seconds_per_second'],board_cpu_s_s=r['whole_board_cpu_seconds_per_second'],
      board_without_sampler_cpu_s_s=r['board_excluding_collector_cpu_seconds_per_second'],sampler_cpu_s_s=r['collector_cpu_seconds_per_second'],
      xserver_cpu_s_s=sum(x['rate'] for x in r.get('display_server_cpu_seconds_per_second',{}).values()),
      camera_cpu_s_s=r.get('camera_cpu_seconds_per_second'),RSS_MiB=r['rss_kib']['mean']/1024,PSS_MiB=r['pss_kib']['mean']/1024,
      Mali_family_MiB=r['mali_family_bytes']['mean']/1048576,Mali_global_MiB=r['mali_global_bytes']['mean']/1048576,
      MemAvailable_MiB=r['memory_available_kib']['mean']/1024,rx_MiB_s=r['network_bytes_per_second'].get('eth0',{}).get('rx_bytes',0)/1048576,
      achieved_fps=s['handoff_fps_over_measurement'],tail_p95_ms=display['p95_ms'],tail_p99_ms=display['p99_ms'],tail_max_ms=display['max_ms'],
      missed_target_frames=max(0,int(s['measurement_duration_seconds']*16)-int(s['received_during_measurement'])),
      matching_backend_fraction=s['observed_target_mode_fraction'],command_failures=len(s.get('command_failures',[])),
      cold_first_observed_frame_seconds=s['stages'].get('first_observed_backend_handoff_seconds'),
      cold_cpu_seconds=cold.get('family_cpu_ticks',0)/100,cold_RSS_HWM_MiB=(cold_mem.get('rss_high_water_kib') or 0)/1024,
      **camera(row))

def comparison(rows,base,candidate='new',pairs=None):
    a=[x for x in rows if x['backend']==base];b=[x for x in rows if x['backend']==candidate]
    metrics=('renderer_cpu_s_s','board_cpu_s_s','board_without_sampler_cpu_s_s','RSS_MiB','PSS_MiB','Mali_family_MiB','Mali_global_MiB','MemAvailable_MiB','rx_MiB_s','achieved_fps','tail_p95_ms','tail_p99_ms')
    result={'baseline':base,'candidate':candidate,'metrics':{},'pairs':pairs or []}
    by={x['index']:x for x in rows}
    for key in metrics:
        av=[x[key] for x in a if x[key] is not None];bv=[x[key] for x in b if x[key] is not None]
        deltas=[by[n][key]-by[o][key] for o,n in (pairs or []) if by[n][key] is not None and by[o][key] is not None]
        result['metrics'][key]={'baseline':spread(av),'candidate':spread(bv),'paired_new_minus_old':spread(deltas),
          'all_pair_deltas_negative':bool(deltas) and all(x<0 for x in deltas)}
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('result',type=Path);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    suite=json.loads(args.result.read_text(encoding='utf8'));assert suite['status']=='COMPLETE'
    rows=[flatten(x) for x in suite['cases']];assert len(rows)==12
    main_rows=rows[:8];control_rows=rows[8:]
    report={'schema':'aura.paired_ab.analysis.v1','runs':rows,
      'main':comparison(main_rows,'old',pairs=[(1,2),(4,3),(5,6),(8,7)]),
      'same_noJPEG_feature_control':comparison(control_rows,'old_nojpeg',pairs=[(9,10),(12,11)]),
      'GPU_utilization':'UNKNOWN: readable utilization nodes stayed zero during known GLES work; do not interpret as0percent',
      'measurement_scope':'process families and unchanged common live UI/camera background in isolated mapped opaque test windows; not a production cutover',
      'attribution_limit':'A/B pipeline differs in JPEG, old fallback prewarm, queues and snapshot cadence; same-noJPEG control isolates only JPEG factor. No claim of pure character algorithm efficiency.',
      'physical_scanout_audio_acceptance':False,'automatic_replacement_authorized':False}
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'analysis.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    columns=[k for k in rows[0] if k not in ('people_counts',)]
    with (args.output/'runs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore');w.writeheader();w.writerows(rows)
    print(json.dumps({k:v for k,v in report.items() if k not in ('runs',)},ensure_ascii=True))

if __name__=='__main__':main()
