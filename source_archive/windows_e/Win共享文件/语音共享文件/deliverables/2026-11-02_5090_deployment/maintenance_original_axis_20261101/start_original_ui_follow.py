import datetime,hashlib,http.client,json,time
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='903cfade-b93c-48fa-804e-379be1967313'
assert hashlib.sha256(Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json').read_bytes()).hexdigest()=='092c2ccf0872cae2f6e13c81e2d8b8a2ffe3b0800ab701566128b5c7947159af'
for pid,birth in ((97308,'2694906'),(97312,'2695022'),(79866,'2265436')):
 assert (Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19]==birth

def req(command=None):
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
 try:
  if command:c.request('POST','/api/command',json.dumps({'type':command}).encode(),{'Origin':'http://127.0.0.1:8783','Host':'127.0.0.1:8783','Content-Type':'application/json'})
  else:c.request('GET','/api/state')
  r=c.getresponse();body=r.read(2097153);assert r.status==200 and len(body)<=2097152
  return json.loads(body)
 finally:c.close()
before=req();pan=before['manual_pan'];rb=pan.get('readback',{})
assert pan.get('state')=='READY' and pan.get('automatic_following') is False and not pan.get('error')
assert rb.get('flags')==0 and rb.get('lease_left_ms')==0
reply=req('pan_face_follow')
time.sleep(.6);after=req();p=after['manual_pan'];f=p.get('face_follow',{})
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original_ui_command_sent_once':'pan_face_follow','before_page':before.get('ui_page'),'after_page':after.get('ui_page'),'automatic_following':p.get('automatic_following'),'state':p.get('state'),'pulse_us':p.get('pulse_us'),'face_follow':{k:f.get(k) for k in ('state','phase','reason','commands_accepted','segments','report')},'runtime_fault_count':(after.get('runtime_faults') or {}).get('count'),'microphone_open':(after.get('handsfree_dialogue') or {}).get('microphone_open')}))
