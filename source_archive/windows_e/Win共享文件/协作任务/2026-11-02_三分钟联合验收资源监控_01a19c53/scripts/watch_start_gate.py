"""Watch local acceptance markers; perform zero board calls before a valid gate."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,time,hashlib,os,re,traceback

ROOT=Path(__file__).resolve().parent.parent
SHARED=Path('E:/Win共享文件/语音共享文件/deliverables/2026-11-02_5090_deployment/joint_acceptance_180s_20261102')
STATUS=SHARED/'RESOURCE_OBSERVER_STATUS.json'

def utc():return datetime.now(timezone.utc).isoformat()
def read(path):
 try:return json.loads(path.read_text(encoding='utf-8-sig'))
 except (OSError,ValueError):return None
def publish(**fields):
 old=read(STATUS) or {};old.update(fields,updated_utc=utc(),gate_watcher_pid=os.getpid())
 raw=json.dumps(old,ensure_ascii=False,indent=2)
 for p in [STATUS,ROOT/'RESOURCE_OBSERVER_STATUS.json']:
  temp=p.with_name(p.name+'.resource.tmp');temp.write_text(raw,encoding='utf-8');temp.replace(p)
def stamp(value):return datetime.fromisoformat(value.replace('Z','+00:00'))

def main():
 publish(phase='ARMED_LOCAL_WAIT_FRESH_HANDOFF_AND_START_GATE',prepared=True,collector_active=False,max_duration_seconds=180,interval_seconds=2,sample_count=0,error=None,error_type=None,error_utc=None,local_wait_limit_seconds=21600,local_wait_started_utc=utc())
 deadline=time.monotonic()+21600
 while time.monotonic()<deadline:
  gate=read(SHARED/'START_GATE.json');contract=read(SHARED/'LIVE_READY_HANDOFF.json');run=read(SHARED/'RUN_CURRENT.json')
  if not gate or not contract or not run or contract.get('ready') is not True or contract.get('permission_active') is not True:
   time.sleep(.25);continue
  hold=read(ROOT/'POST_REPAIR_GATE_HOLD.json') or {}
  if hold:
   current_sha=hashlib.sha256((SHARED/'LIVE_READY_HANDOFF.json').read_bytes()).hexdigest()
   if current_sha==hold.get('rejected_handoff_sha256'):
    time.sleep(.25);continue
   issued=contract.get('issued_host_utc')
   if not issued or stamp(issued)<=stamp(hold['require_issued_after_utc']):
    time.sleep(.25);continue
  if gate.get('run_id')!=run.get('run_id') or not gate.get('start_not_before_utc'):
   time.sleep(.25);continue
  if contract.get('duration_seconds')!=180:raise RuntimeError('Unexpected handoff duration')
  begin=stamp(gate['start_not_before_utc']);now=datetime.now(timezone.utc)
  if (now-begin).total_seconds()>10:raise RuntimeError('Refuse late start: gate is more than 10 seconds old')
  if contract.get('window_end_utc') and now>=stamp(contract['window_end_utc']):raise RuntimeError('Expired handoff')
  boot=contract.get('boot_id');assert isinstance(boot,str) and re.fullmatch(r'[0-9a-f-]{36}',boot)
  publish(phase='ARMED_WAIT_GATE_TIME',run_id=run['run_id'],start_not_before_utc=gate['start_not_before_utc'],handoff_ready_verified=True)
  while datetime.now(timezone.utc)<begin:
   current=read(SHARED/'LIVE_READY_HANDOFF.json') or {}
   if current.get('permission_active') is not True:raise RuntimeError('Handoff revoked before start')
   time.sleep(.05)
  current=read(SHARED/'LIVE_READY_HANDOFF.json') or {}
  assert current.get('ready') is True and current.get('permission_active') is True
  break
 else:raise RuntimeError('No start gate received within local wait limit')

 formal=ROOT/'data'/'acceptance_board_numeric.jsonl';errfile=ROOT/'data'/'acceptance_board_stderr.log'
 assert not formal.exists(),'Preserve prior formal data'
 camera_owner=contract.get('camera_owner') or {}
 camera_pid=camera_owner.get('pid') or camera_owner.get('main_pid')
 remote='python3 -u - --duration 180 --expected-boot '+boot
 if isinstance(camera_pid,int):remote+=' --expected-camera-pid '+str(camera_pid)
 command=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ServerAliveInterval=15','aura-kv260',remote]
 source=(ROOT/'scripts'/'board_monitor.py').read_bytes()
 (ROOT/'data'/'used_START_GATE.json').write_text(json.dumps(gate,ensure_ascii=False,indent=2),encoding='utf-8')
 metadata={k:contract.get(k) for k in ['schema','status','ready','permission_active','duration_seconds','window_start_utc','window_end_utc','boot_id','startup_sha256','component_sha256','component_count','camera_owner','gui_owner','gtk_owner']}
 # Owner objects contain process metadata only in the handoff, never copy scene/name payloads.
 for key in ['camera_owner','gui_owner','gtk_owner']:
  if isinstance(metadata.get(key),dict):metadata[key]={k:v for k,v in metadata[key].items() if k in ['pid','main_pid','birth_ticks','start_ticks','command_sha256','comm','role']}
 (ROOT/'data'/'used_handoff_metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
 with formal.open('x',encoding='utf-8') as output,errfile.open('wb') as err:
  p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
  p.stdin.write(source);p.stdin.close()
  publish(phase='RUNNING',collector_active=True,ssh_pid=p.pid,run_id=run['run_id'],host_started_utc=utc(),output_file=str(formal),collector_sha256=hashlib.sha256(source).hexdigest(),sample_count=0)
  samples=0;start_event=None;end_event=None
  for line in p.stdout:
   received=utc()
   try:item=json.loads(line)
   except ValueError:raise RuntimeError('Unexpected observer stdout; inspect retained stderr')
   item['host_received_utc']=received
   output.write(json.dumps(item,separators=(',',':'))+'\n');output.flush()
   if item.get('event')=='start':
    start_event=item
    publish(board_observer_pid=item['pid'],board_start_monotonic_s=item['monotonic_s'],boot_id=item['boot_id'],board_wall_utc_untrusted=item.get('board_wall_utc_untrusted'))
   if item.get('event')=='sample':
    samples+=1
    if samples%5==0:publish(sample_count=samples,last_sample_monotonic_s=item['board_monotonic_s'],last_host_receipt_utc=received)
   if item.get('event')=='end':end_event=item
  code=p.wait(timeout=15)
  if code!=0 or not end_event:raise RuntimeError('Observer ended without normal completion; exit '+str(code))
  publish(phase='COLLECTED_WAIT_MAIN_WINDOW_SAMPLES',collector_active=False,sample_count=samples,exit_code=code,host_completed_utc=utc(),actual_observer_elapsed_s=end_event.get('elapsed_s'),start_event=start_event,end_event=end_event,board_files_or_services_modified=False,extra_model_inference=False)

if __name__=='__main__':
 try:main()
 except Exception as exc:
  publish(phase='RESOURCE_OBSERVER_ERROR',collector_active=False,error_type=type(exc).__name__,error=str(exc),error_utc=utc())
  traceback.print_exc();raise
