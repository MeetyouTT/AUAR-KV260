"""One current authorized 180-second read-only performance window. No old gate."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,subprocess,hashlib,re,os,traceback
ROOT=Path(__file__).resolve().parent.parent
SHARED=Path('E:/Win共享文件/语音共享文件/deliverables/2026-11-02_5090_deployment/joint_acceptance_180s_20261102')
CONTRACT=SHARED/'PERFORMANCE_MEASUREMENT_HANDOFF.json'
def utc():return datetime.now(timezone.utc).isoformat()
def read(p):
 try:return json.loads(p.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return {}
def publish(**fields):
 s=read(SHARED/'RESOURCE_OBSERVER_STATUS.json');s.update(fields,updated_utc=utc(),output_directory=str(ROOT),resource_observer_thread='01a19c53-3a84-7c30-8e70-9368a35318d8',full_joint_function_acceptance=False)
 for p in [SHARED/'RESOURCE_OBSERVER_STATUS.json',ROOT/'RESOURCE_OBSERVER_STATUS.json']:
  t=p.with_suffix('.json.narrow.tmp');t.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8');t.replace(p)
def main():
 raw=CONTRACT.read_bytes();c=json.loads(raw)
 assert c['ready'] is True and c['permission_active'] is True
 assert c['resource_sampling_duration_seconds']==180 and c['resource_sampling_interval_seconds']==2
 end=datetime.fromisoformat(c['window_end_utc'].replace('Z','+00:00'))
 assert datetime.now(timezone.utc)+timedelta(seconds=190)<end,'Need at least 190 seconds in the current grant'
 boot=c['boot_id'];assert re.fullmatch('[0-9a-f-]{36}',boot)
 metadata={k:c.get(k) for k in ['schema','status','ready','permission_active','issued_host_utc','window_start_utc','window_end_utc','resource_sampling_duration_seconds','resource_sampling_interval_seconds','measurement_scope_label','boot_id','startup_sha256','human_request_message_id','human_request_verified_thread','owners']}
 metadata['original_handoff_sha256']=hashlib.sha256(raw).hexdigest()
 (ROOT/'data'/'used_PERFORMANCE_HANDOFF_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
 source=(ROOT/'scripts'/'board_monitor.py').read_bytes()
 command=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ServerAliveInterval=15','aura-kv260','python3 -u - --duration 180 --expected-boot '+boot+' --expected-camera-pid 362659']
 output=ROOT/'data'/'board_numeric.jsonl';errors=ROOT/'data'/'board_stderr.log'
 with output.open('x',encoding='utf-8') as stream,errors.open('wb') as err:
  p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
  p.stdin.write(source);p.stdin.close()
  publish(phase='RUNNING_NARROW_PERFORMANCE',prepared=True,collector_active=True,ssh_pid=p.pid,collector_host_pid=os.getpid(),sample_count=0,host_started_utc=utc(),collector_sha256=hashlib.sha256(source).hexdigest(),output_file=str(output),measurement_scope=c.get('measurement_scope_label'),pending_board_stage=None,acceptance_paused_by_main=False,interval_seconds=2,max_duration_seconds=180,gate_watcher_pid=None,auto_figure_worker_pid=None)
  start=None;last=None;samples=0
  for line in p.stdout:
   r=json.loads(line);r['host_received_utc']=utc();stream.write(json.dumps(r,separators=(',',':'))+'\n');stream.flush()
   if r.get('event')=='start':
    start=r;publish(board_observer_pid=r['pid'],board_start_monotonic_s=r['monotonic_s'],boot_id=r['boot_id'],first_host_receipt_utc=r['host_received_utc'],actual_measurement_T0_board_monotonic_s=r['monotonic_s'])
   if r.get('event')=='sample':
    samples+=1
    if samples%5==0:publish(sample_count=samples,last_sample_monotonic_s=r['board_monotonic_s'],last_host_receipt_utc=r['host_received_utc'])
   if r.get('event')=='end':last=r
  code=p.wait(timeout=15)
  assert code==0 and last and last.get('stopped_by_signal') is False,'Incomplete observer; inspect preserved numeric data'
  publish(phase='COLLECTED_NARROW_PERFORMANCE',collector_active=False,sample_count=samples,exit_code=code,host_completed_utc=utc(),actual_observer_elapsed_s=last.get('elapsed_s'),actual_measurement_T0_board_monotonic_s=start['monotonic_s'] if start else None,actual_measurement_END_board_monotonic_s=(start['monotonic_s']+last['elapsed_s']) if start else None,resource_measurement_this_window='MEASURED_READ_ONLY_NARROW_SCOPE',new_DPU_runner=False,new_model_inference_by_resource_observer=False)
if __name__=='__main__':
 try:main()
 except Exception as exc:
  publish(phase='NARROW_RESOURCE_ERROR',collector_active=False,error_type=type(exc).__name__,error=str(exc));traceback.print_exc();raise
