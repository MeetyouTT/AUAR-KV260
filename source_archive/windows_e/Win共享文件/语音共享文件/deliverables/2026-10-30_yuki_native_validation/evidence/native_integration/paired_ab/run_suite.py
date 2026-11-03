"""Serial paired renderer runs with1Hz OS and0.2Hz camera numeric telemetry."""
from pathlib import Path
import argparse,hashlib,json,os,signal,subprocess,sys,time,traceback
ROOT=Path('/home/root/aura-yuki-validation-20261030/native_integration');AB=ROOT/'paired_ab'
sys.path.insert(0,str(AB))
from telemetry import snapshot,live_ui_metrics,HZ

def read(path):return json.loads(Path(path).read_text())
def save(path,value):Path(path).write_text(json.dumps(value,indent=2))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def stop_owned(process):
    if process.poll() is not None:return
    command=Path('/proc',str(process.pid),'cmdline').read_bytes()
    if str(AB/'paired_renderer_harness.py').encode() not in command:raise RuntimeError('Refuse to stop unverified case process')
    assert os.getpgid(process.pid)==process.pid
    os.killpg(process.pid,signal.SIGTERM)
    try:process.wait(timeout=8)
    except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)

def aggregate(rows,start,end,pid):
    steady=[row for row in rows if start<=row['at']<=end and pid in row['family_pids']]
    if len(steady)<5:return {'valid':False,'reason':'Too few aligned steady samples'}
    first,last=steady[0],steady[-1];duration=last['at']-first['at']
    whole=(last['cpu_system']['busy_ticks']-first['cpu_system']['busy_ticks'])/HZ/duration
    own=(last['family_cpu_ticks']-first['family_cpu_ticks'])/HZ/duration
    sampler=(last['collector_cpu_ticks']-first['collector_cpu_ticks'])/HZ/duration
    def stats(values):
        values=sorted(values)
        return {'mean':sum(values)/len(values),'min':values[0],'max':values[-1]} if values else None
    camera=[row for row in steady if row.get('camera',{} ) and row['camera'].get('available')]
    return dict(valid=True,measured_wall_seconds=duration,aligned_begin=first['at'],aligned_end=last['at'],samples=len(steady),
      whole_board_cpu_seconds_per_second=whole,renderer_family_cpu_seconds_per_second=own,collector_cpu_seconds_per_second=sampler,
      board_excluding_collector_cpu_seconds_per_second=whole-sampler,
      family_pids_seen=sorted({p for row in steady for p in row['family_pids']}),
      rss_kib=stats([row['family_rss_kib'] for row in steady if row['family_rss_kib']>0]),pss_kib=stats([row['family_pss_kib'] for row in steady if row['family_pss_kib'] is not None]),
      mali_family_bytes=stats([row['gpu']['family_mali_bytes'] for row in steady if row['gpu']['family_mali_bytes'] is not None]),
      mali_global_bytes=stats([row['gpu']['global_mali_bytes'] for row in steady if row['gpu']['global_mali_bytes'] is not None]),
      gpu_utilization_raw={key:stats([row['gpu'][key] for row in steady if row['gpu'].get(key) is not None]) for key in ('utilization_gp_raw','utilization_pp_raw','utilization_gp_pp_raw')},
      gpu_utilization_unit='UNVERIFIED_RAW_DEBUGFS_VALUE; no percentage conversion',
      memory_available_kib=stats([row['memory_system']['MemAvailable_kib'] for row in steady]),
      network_bytes_per_second={interface:{key:(last['network'][interface][key]-first['network'][interface][key])/duration for key in ('rx_bytes','tx_bytes')} for interface in first['network'] if interface in last['network']},
      camera_samples=[dict(at=row['at'],**row['camera']) for row in camera],
      sampler_wall_ms=stats([row['sampling_ms'] for row in steady]))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--execute',action='store_true')
    args=parser.parse_args();plan=read(args.plan)
    assert plan['schema']=='aura.paired_ab.suite.v1'
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==plan['boot_id']
    for name,digest in plan['input_sha256'].items():assert sha(AB/name)==digest,name
    if not args.execute:print(json.dumps(dict(status='PLAN_VERIFIED_NO_EXECUTION',cases=plan['cases'])));return
    out=args.output.resolve();assert out.is_relative_to(AB.resolve()) and not out.exists();out.mkdir(parents=True)
    basis=read(ROOT/'board_source/manifest.json');child=basis['child_pid']
    for value in Path('/proc',child,'environ').read_bytes().split(b'\0'):
        key,sep,data=value.partition(b'=')
        if sep and key in (b'DISPLAY',b'XAUTHORITY'):os.environ[key.decode()]=os.fsdecode(data)
    report=dict(status='RUNNING',cases=[],boot_id=plan['boot_id'],plan_sha256=sha(args.plan),production_modified=False,
      scope='isolated foreground renderer pipeline in opaque mapped window; unchanged real UI/camera common background; no production cutover',board_wall_clock_utc_trusted=False)
    save(out/'suite-result.json',report)
    print(json.dumps(dict(event='SUITE_STARTED',pid=os.getpid(),output=str(out),cases=plan['cases'])),flush=True)
    try:
        for index,backend in enumerate(plan['cases']):
            assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==plan['boot_id']
            assert subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()==basis['pid']
            assert str(read(Path(basis['runtime'])/'launch.json')['pid'])==child
            live_before=live_ui_metrics()
            assert live_before['available'] and live_before['portrait'].get('mode')=='remote' and live_before['portrait'].get('target_fps')==16 and not live_before['playing']
            case=out/(str(index+1).zfill(2)+'-'+backend)
            command=['python3','-B',str(AB/'paired_renderer_harness.py'),'--backend',backend,
              '--runtime',basis['runtime'],'--board-manifest',str(ROOT/'board_source/manifest.json'),
              '--fresh-baseline',str(AB/'fresh-baseline.json'),'--server-proof',str(AB/'isolated-server-proof.json'),
              '--scenario',str(AB/plan['scenario']),'--pcm',str(AB/'public_pcm.wav'),'--envelope',str(AB/'public_envelope.json'),
              '--window',str(AB/'window-v1.json'),'--output',str(case),'--execute']
            if backend=='new':command+=['--yuki-root',str(AB/'yuki-root.json'),'--candidate-manifest',str(ROOT/'ui_candidate/manifest.json')]
            rows=[];now=time.monotonic();next_sample=now;last_camera=-100;process=None;first_ready_sample=None;started=now
            current=dict(index=index+1,backend=backend,command=command,status='STARTING',case=str(case),started_monotonic=now,live_ui_before=live_before)
            save(out/'current-case.json',current)
            try:
                with (out/(case.name+'.log')).open('w') as log:
                    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True,cwd=str(AB))
                    current.update(pid=process.pid,status='RUNNING');save(out/'current-case.json',current)
                    print(json.dumps(dict(event='CASE_STARTED',index=index+1,backend=backend,pid=process.pid,at=time.monotonic())),flush=True)
                    deadline=now+float(plan.get('case_timeout_seconds',210))
                    announced=False
                    while process.poll() is None:
                        now=time.monotonic()
                        if now>=deadline:raise RuntimeError('Isolated case timeout')
                        if now>=next_sample:
                            sample=snapshot(process.pid,include_camera=now-last_camera>=5)
                            if sample['camera'] is not None:last_camera=now
                            rows.append(sample);next_sample+=1
                            if next_sample<time.monotonic():next_sample=time.monotonic()+1
                            if sample['memory_system']['MemAvailable_kib']<256*1024:raise RuntimeError('Abort owned case: low board memory')
                        if first_ready_sample is None and (case/'ready.json').exists():first_ready_sample=snapshot(process.pid,include_camera=False)
                        if not announced and (case/'measurement-ready.json').exists():
                            announced=True;marker=read(case/'measurement-ready.json')
                            print(json.dumps(dict(event='CASE_MEASURING',index=index+1,backend=backend,pid=process.pid,at=marker['at'])),flush=True)
                        time.sleep(.1)
                current['returncode']=process.returncode
                case.mkdir(parents=True,exist_ok=True)
                summary=read(case/'summary.json') if (case/'summary.json').exists() else {'status':'MISSING_SUMMARY'}
                save(case/'os-samples.json',rows)
                if first_ready_sample:save(case/'first-ready-resources.json',first_ready_sample)
                start=summary.get('stages',{}).get('measurement_start_monotonic')
                end=summary.get('stages',{}).get('measurement_end_monotonic')
                if end is None and (case/'samples.json').exists():
                    values=read(case/'samples.json');end=values[-1]['at'] if values else None
                current.update(status='COMPLETE' if process.returncode==0 and summary['status']=='COMPLETE' else 'FAIL',
                  elapsed_seconds=time.monotonic()-started,summary=summary,
                  resources=aggregate(rows,start,end,process.pid) if start is not None and end is not None else {'valid':False},first_ready_resources=first_ready_sample)
                current['live_ui_after']=live_ui_metrics()
                save(case/'paired-result.json',current)
                report['cases'].append(current);save(out/'suite-result.json',report)
                brief={key:current['resources'].get(key) for key in ('valid','measured_wall_seconds','whole_board_cpu_seconds_per_second','renderer_family_cpu_seconds_per_second','rss_kib','pss_kib','mali_family_bytes')}
                print(json.dumps(dict(event='CASE_FINISHED',index=index+1,backend=backend,status=current['status'],resources=brief,
                  fps=summary.get('handoff_fps_over_measurement'),tail_display=summary.get('end_display'),elapsed_seconds=current['elapsed_seconds'])),flush=True)
                if current['status']!='COMPLETE' or not current['resources']['valid']:raise RuntimeError('Case invalid: '+case.name)
            finally:
                if process:stop_owned(process)
            time.sleep(float(plan.get('cooldown_seconds',4)))
        report['status']='COMPLETE'
    except Exception as error:report.update(status='FAIL',error=str(error),traceback=traceback.format_exc())
    finally:
        report['ended_monotonic']=time.monotonic();save(out/'suite-result.json',report);print(json.dumps(dict(status=report['status'],cases=len(report['cases']),error=report.get('error'))))
    if report['status']!='COMPLETE':raise SystemExit(2)

if __name__=='__main__':main()
