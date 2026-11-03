"""Analyze the sealed serial ABBA and JPEG-factor control without composite scoring."""
from pathlib import Path
import argparse,csv,json,statistics as S
from quality_checks import check_suite,descriptive_jpeg_contribution

def mean(values):return sum(values)/len(values) if values else None
def spread(values):return dict(n=len(values),mean=mean(values),min=min(values),max=max(values),sample_std=S.stdev(values) if len(values)>1 else None) if values else None
def avg(stats,divisor=1):return stats['mean']/divisor if stats and stats.get('mean') is not None else None
def camera(row):
    values=row['resources']['camera_samples'];result={}
    if len(values)>1:
        a,b=values[0],values[-1];dt=b['at']-a['at']
        for key in ('capture_frames','detected_frames','preview_frames','identity.processed'):
            if key in a['numeric'] and key in b['numeric']:result[key+'_per_second']=(b['numeric'][key]-a['numeric'][key])/dt
    result['error_samples']=sum(any(v for k,v in x['numeric'].items() if k.endswith('_error_present')) for x in values)
    result['people_counts']=sorted({x['numeric'].get('people_count') for x in values if x['numeric'].get('people_count') is not None})
    return result

def flatten(row,case_dir=None):
    r=row['resources'];s=row['summary'];display=s['end_display'];cold=row.get('first_ready_resources') or {}
    pid=str(row['pid']);cold_mem=cold.get('process_memory',{}).get(pid,{})
    return dict(index=row['index'],backend=row['backend'],duration=s['measurement_duration_seconds'],
      renderer_cpu_s_s=r['renderer_family_cpu_seconds_per_second'],board_cpu_s_s=r['whole_board_cpu_seconds_per_second'],
      board_without_sampler_cpu_s_s=r['board_excluding_collector_cpu_seconds_per_second'],sampler_cpu_s_s=r['collector_cpu_seconds_per_second'],
      xserver_cpu_s_s=sum(x['rate'] for x in r['display_server_cpu_seconds_per_second'].values()) if 'display_server_cpu_seconds_per_second' in r else None,
      camera_cpu_s_s=r.get('camera_cpu_seconds_per_second'),RSS_MiB=avg(r.get('rss_kib'),1024),PSS_MiB=avg(r.get('pss_kib'),1024),
      Mali_family_MiB=avg(r.get('mali_family_bytes'),1048576),Mali_global_MiB=avg(r.get('mali_global_bytes'),1048576),
      MemAvailable_MiB=avg(r.get('memory_available_kib'),1024),rx_MiB_s=r['network_bytes_per_second']['eth0']['rx_bytes']/1048576 if 'eth0' in r['network_bytes_per_second'] else None,
      achieved_fps=s['handoff_fps_over_measurement'],tail_p95_ms=display['p95_ms'],tail_p99_ms=display['p99_ms'],tail_max_ms=display['max_ms'],
      net_target_frame_deficit_estimate=max(0,int(s['measurement_duration_seconds']*16)-int(s['received_during_measurement'])),
      matching_backend_fraction=s['observed_target_mode_fraction'],command_failures=len(s.get('command_failures',[])),
      cold_first_observed_frame_seconds=s['stages'].get('first_observed_backend_handoff_seconds'),
      cold_cpu_seconds=cold['family_cpu_ticks']/cold['cpu_system']['hz'] if cold.get('family_cpu_ticks') is not None and cold.get('cpu_system',{}).get('hz') else None,
      cold_RSS_HWM_MiB=cold_mem['rss_high_water_kib']/1024 if cold_mem.get('rss_high_water_kib') is not None else None,
      **camera(row))

def comparison(rows,base,candidate='new',pairs=None):
    a=[x for x in rows if x['backend']==base];b=[x for x in rows if x['backend']==candidate]
    metrics=('renderer_cpu_s_s','board_cpu_s_s','board_without_sampler_cpu_s_s','RSS_MiB','PSS_MiB','Mali_family_MiB','Mali_global_MiB','MemAvailable_MiB','rx_MiB_s','achieved_fps','tail_p95_ms','tail_p99_ms','xserver_cpu_s_s','camera_cpu_s_s','capture_frames_per_second','detected_frames_per_second','preview_frames_per_second','identity.processed_per_second')
    result={'baseline':base,'candidate':candidate,'metrics':{},'pairs':pairs or []}
    by={x['index']:x for x in rows}
    for key in metrics:
        av=[x[key] for x in a if x.get(key) is not None];bv=[x[key] for x in b if x.get(key) is not None]
        deltas=[by[n][key]-by[o][key] for o,n in (pairs or []) if by[n].get(key) is not None and by[o].get(key) is not None]
        ds=spread(deltas)
        result['metrics'][key]={'baseline':spread(av),'candidate':spread(bv),'paired_new_minus_old':ds,
          'all_pair_deltas_negative':bool(deltas) and all(x<0 for x in deltas),
          'new_minus_old_percent_of_baseline_mean':(mean(bv)-mean(av))/mean(av)*100 if av and bv and mean(av) else None}
        if key in ('renderer_cpu_s_s','board_cpu_s_s','board_without_sampler_cpu_s_s'):
            result['metrics'][key]['descriptive_consistent_cpu_reduction_signal']=bool(ds and ds['n']>1 and all(x<0 for x in deltas) and abs(ds['mean'])>2*ds['sample_std'])
    return result

def observed_context_comparability(rows,pairs):
    by={row['index']:row for row in rows};checks=[]
    for old,new in pairs:
        def context(row):
            identity=row.get('identity.processed_per_second')
            return dict(people_counts=row.get('people_counts'),identity_processed_per_second=identity,
                identity_work_observed=(identity>0) if identity is not None else None,
                camera_cpu_seconds_per_second=row.get('camera_cpu_s_s'),capture_hz=row.get('capture_frames_per_second'),detected_hz=row.get('detected_frames_per_second'))
        a,b=context(by[old]),context(by[new])
        known=bool(a['people_counts']) and bool(b['people_counts']) and a['identity_work_observed'] is not None and b['identity_work_observed'] is not None
        matches=(a['people_counts']==b['people_counts'] and a['identity_work_observed']==b['identity_work_observed']) if known else None
        checks.append(dict(old_index=old,new_index=new,baseline=a,candidate=b,observed_context_matches=matches))
    all_match=bool(checks) and all(x['observed_context_matches'] is True for x in checks)
    return dict(status='OBSERVED_CONTEXT_MATCHES' if all_match else 'OBSERVED_CONTEXT_CHANGED' if any(x['observed_context_matches'] is False for x in checks) else 'UNKNOWN',
        all_pairs_observed_context_match=all_match,pairs=checks,
        limitation='Same PID/config and sampled people/identity activity are necessary workload context, not proof of identical camera pixels. Mismatched pairs stay in all numeric summaries but cannot identify a same-workload whole-board effect.')

def main():
    p=argparse.ArgumentParser();p.add_argument('result',type=Path);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    suite=json.loads(args.result.read_text(encoding='utf8'));assert suite['status']=='COMPLETE'
    assert [x['backend'] for x in suite['cases']]==['old','new','new','old','old','new','new','old','old_nojpeg','new','new','old_nojpeg']
    assert [x['index'] for x in suite['cases']]==list(range(1,13))
    rows=[flatten(x) for x in suite['cases']];assert len(rows)==12
    main_rows=rows[:8];control_rows=rows[8:]
    report={'schema':'aura.paired_ab.analysis.v3','runs':rows,
      'main':comparison(main_rows,'old',pairs=[(1,2),(4,3),(5,6),(8,7)]),
      'same_noJPEG_feature_control':comparison(control_rows,'old_nojpeg',pairs=[(9,10),(12,11)]),
      'quality':check_suite(args.result,Path(__file__).parent/'scenario-v1.json'),
      'unpaired_A_C_descriptive_only':descriptive_jpeg_contribution(suite['cases']),
      'GPU_utilization':'UNKNOWN: debugfs raw-unit calibration is not established; all-zero values during known GLES rendering do not mean0percent',
      'gpu_raw_per_case':{str(x['index']):x['resources']['gpu_utilization_raw'] for x in suite['cases']},
      'measurement_scope':'process families and unchanged common live UI/camera background in isolated mapped opaque test windows; not a production cutover',
      'attribution_limit':'A/B pipeline differs in JPEG, old fallback prewarm, queues and snapshot cadence. C/B matches absence of JPEG only; transport/presenter/Gst versus EGL and cadence still differ. A/C is unpaired and time-separated. No pure character algorithm or exact additive JPEG saving claim.',
      'frame_statistics_scope':'P95/P99/max cover the final239 handoff/swap intervals, roughly15s at16fps; achieved FPS covers the full60s. Net target frame deficit is a boundary-sensitive estimate (+/-1), not a count of per-slot dropped frames. A identity callback entry and B EGL swap are different software boundaries; neither is physical scanout.',
      'cpu_signal_policy':'All pair deltas negative and absolute mean greater than2x sample standard deviation; descriptive n4/n2 rule, not statistical significance or a universal prediction. Whole-board and renderer-family signals separate.',
      'physical_scanout_audio_acceptance':False,'automatic_replacement_authorized':False}
    report['workload_context_comparability']={
        'main':observed_context_comparability(main_rows,[(1,2),(4,3),(5,6),(8,7)]),
        'noJPEG_control':observed_context_comparability(control_rows,[(9,10),(12,11)])}
    for group,key in [('main','main'),('same_noJPEG_feature_control','noJPEG_control')]:
        report[group]['eligible_for_matched_workload_interpretation']=report['workload_context_comparability'][key]['all_pairs_observed_context_match']
    report['background_load_note']='All runs retained. Case11 had people_count1 and active identity processing; case12 had people_count0 and no identity increments, changing the second control pair workload. Higher whole-boardCPU persisted in case12, so neither total difference is a pure renderer effect. Main8 cases all had people_count0 and no identity increments.'
    layers=[]
    for raw in suite['cases']:
        path=args.result.parent/(str(raw['index']).zfill(2)+'-'+raw['backend'])/'samples.json'
        samples=json.loads(path.read_text(encoding='utf8'))
        start=raw['summary']['stages']['measurement_start_monotonic'];end=raw['summary']['stages']['measurement_end_monotonic']
        measured=[x for x in samples if start<=x['at']<=end]
        layer={'index':raw['index'],'backend':raw['backend'],'counter_note':'Separate pipeline counters; never sum them as disjoint drops.'}
        for section,keys in [('presentation',('presented','dropped','expired')),('portrait',('sent','accepted','discarded','failures')),('native_stats',('frames','rejected_controls','stale_frames','elapsed_dropped_seconds'))]:
            values=[x[section] for x in measured if isinstance(x.get(section),dict)]
            layer[section]={key:{'first':values[0].get(key),'last':values[-1].get(key),'delta':values[-1][key]-values[0][key] if values[0].get(key) is not None and values[-1].get(key) is not None and values[-1][key]>=values[0][key] else None} for key in keys} if values else None
        for key in ('pushed','received'):
            a=raw['summary']['start_display'].get(key);b=raw['summary']['end_display'].get(key)
            layer['display_'+key+'_delta']=b-a if a is not None and b is not None else None
        layers.append(layer)
    report['pipeline_counters']=layers
    report['resource_reduction_proven_as_composite']=False
    report['quality_all_cases_pass']=report['quality']['status']=='PASS'
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'analysis.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    columns=[k for k in rows[0] if k not in ('people_counts',)]
    with (args.output/'runs.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore');w.writeheader();w.writerows(rows)
    print(json.dumps({k:v for k,v in report.items() if k not in ('runs',)},ensure_ascii=True))

if __name__=='__main__':main()
