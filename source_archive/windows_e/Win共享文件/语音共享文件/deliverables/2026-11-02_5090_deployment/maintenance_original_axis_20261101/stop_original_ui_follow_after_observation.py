import datetime,hashlib,http.client,json,time
from pathlib import Path
BOOT='903cfade-b93c-48fa-804e-379be1967313'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert hashlib.sha256(Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json').read_bytes()).hexdigest()=='092c2ccf0872cae2f6e13c81e2d8b8a2ffe3b0800ab701566128b5c7947159af'
assert Path('/proc/97312/stat').read_text().rsplit(')',1)[1].split()[19]=='2695022'
def req(command=None):
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
 try:
  if command:c.request('POST','/api/command',json.dumps({'type':command}).encode(),{'Origin':'http://127.0.0.1:8783','Host':'127.0.0.1:8783','Content-Type':'application/json'})
  else:c.request('GET','/api/state')
  r=c.getresponse();body=r.read(2097153);assert r.status==200 and len(body)<=2097152
  return json.loads(body)
 finally:c.close()
before=req();report_path=(before.get('manual_pan',{}).get('face_follow') or {}).get('report')
assert report_path=='/home/root/aura-pan-wide-20261028/control-10282601/runs/ui-27059117073481/trial.json'
req('pan_stop');deadline=time.monotonic()+12
while True:
 s=req();p=s['manual_pan'];rb=p.get('readback') or {}
 stopped=p.get('automatic_following') is False and p.get('state')=='READY' and rb.get('flags')==0 and rb.get('lease_left_ms')==0
 if stopped or time.monotonic()>=deadline:break
 time.sleep(.3)
v=json.loads(Path(report_path).read_text());r=v.get('result') or {}
backend=p.get('backend_pid');owner=None
if type(backend) is int and backend>0:
 proc=Path('/proc')/str(backend)
 owner={'pid':backend,'birth_ticks':(proc/'stat').read_text().rsplit(')',1)[1].split()[19],'command_sha256':hashlib.sha256((proc/'cmdline').read_bytes()).hexdigest()}
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot_id':BOOT,'explicit_pan_stop_sent_once':True,'ui_stopped_ready':stopped,'pan_state':p.get('state'),'automatic_following':p.get('automatic_following'),'current_readback':rb,'manual_backend_owner':owner,'original_report_path':report_path,'original_report_sha256':hashlib.sha256(Path(report_path).read_bytes()).hexdigest(),'report_status':v.get('status'),'report_error':v.get('error'),'result':{k:r.get(k) for k in ('state','reason','pulse_us','commands_accepted','segments','elapsed_s','stopped','visual_center_completions','hardware_ramp_commits')},'input_summary':v.get('input_summary'),'telemetry':v.get('telemetry'),'reader_queue':v.get('reader_queue'),'runtime_fault_count':(s.get('runtime_faults') or {}).get('count'),'ui_page':s.get('ui_page'),'saved_listening_enabled':(s.get('handsfree_dialogue') or {}).get('enabled')}))
