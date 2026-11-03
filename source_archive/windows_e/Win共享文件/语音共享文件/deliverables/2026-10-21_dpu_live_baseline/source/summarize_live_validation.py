"""Summarize filtered board evidence without images, audio, or identity records."""
import argparse,csv,hashlib,json,math
from pathlib import Path

def quantile(values,q):
    values=sorted(values)
    if not values:return None
    index=(len(values)-1)*q
    lo,hi=math.floor(index),math.ceil(index)
    return values[lo]+(values[hi]-values[lo])*(index-lo)

def summarize(report):
    rows=report.get('samples',[])
    snapshots=[r['health'] for r in rows if 'health' in r]
    ages=[s['observation_age_ms'] for s in snapshots if s.get('observation_age_ms') is not None]
    face_ms=[s['face_targets']['last_inference_ms'] for s in snapshots if s.get('face_targets',{}).get('last_inference_ms') is not None]
    cpus=[r['cpu_pct_board'] for r in rows if r.get('cpu_pct_board') is not None]
    result={k:report.get(k) for k in ('scope','root','boot_id','phase','passed','complete','error','elapsed_s',
        'elapsed_observation_s','observed_yolo_hz','observed_yunet_hz','cpu_pct_board_observation',
        'kernel_warning_count','maximum_observation_age_ms','ui_pid_preserved','protected_configuration_unchanged',
        'sface_embedding_backend_changed','identity_database_changed','rollback_exit_code','timer') if k in report}
    result['sample_count']=len(rows) if rows else report.get('sample_count',0)
    result['full_samples_available']=bool(rows)
    result['statistics_scope']='Health snapshots sampled every 5 seconds, not the distribution of all inference calls'
    result['cpu_pct_board_5s_windows']={k:quantile(cpus,q) for k,q in [('median',.5),('p95',.95),('p99',.99)]}
    result['primary_observation_age_ms_snapshots']={k:quantile(ages,q) for k,q in [('median',.5),('p95',.95),('p99',.99)]}
    result['last_face_inference_ms_snapshots']={k:quantile(face_ms,q) for k,q in [('median',.5),('p95',.95),('p99',.99)]}
    if snapshots:
        final=snapshots[-1]
        result['last_sample_health']=final
        schedule=final.get('dpu_schedule',{}) or {}
        optional=schedule.get('optional',{}).get('yunet',{})
        result['face_slot_acceptance_fraction']=optional.get('calls',0)/max(1,optional.get('calls',0)+optional.get('skipped',0))
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--candidate',type=Path)
    args=parser.parse_args()
    report=json.loads(args.report.read_text());result=summarize(report)
    result['input_evidence_sha256']=hashlib.sha256(args.report.read_bytes()).hexdigest()
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'live-validation-summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    if args.baseline and args.candidate:
        first=json.loads(args.baseline.read_text());last=json.loads(args.candidate.read_text())
        comparisons=[]
        def add(metric,a,b,unit,scope):comparisons.append({'metric':metric,'baseline':a,'yunet_dpu':b,'difference':b-a,'unit':unit,'scope':scope})
        add('total_cpu',first['cpu_percent_of_board'],last['cpu_percent_of_board'],'percent of four-core board','Sequential ~15 s live windows; scene is not fixed')
        for name in ('board_camera_motion.py','board_avatar_pan.py','gstreamer_audio_worker.py'):
            a=next(p['percent_of_board'] for p in first['processes'] if p['name']==name)
            b=next(p['percent_of_board'] for p in last['processes'] if p['name']==name)
            add(name,a,b,'percent of four-core board','Same settings; process IDs may differ after restart')
        add('dpu_task_busy',first['dpu_task_busy_percent'],last['dpu_task_busy_percent'],'percent of time','XRT task busy; not MAC efficiency or FPGA static resources')
        add('dpu_completed_commands',first['dpu_commands_completed'],last['dpu_commands_completed'],'commands in measured window','YOLO only vs YOLO plus YuNet; not identity successes')
        with (args.output/'comparison.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(comparisons[0]));writer.writeheader();writer.writerows(comparisons)
        print(json.dumps(comparisons,ensure_ascii=False))
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
