import datetime,hashlib,http.client,json,subprocess,time
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='903cfade-b93c-48fa-804e-379be1967313'
startup=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
assert hashlib.sha256(startup.read_bytes()).hexdigest()=='3f5e81abc20ce5169ac91ae302611cba8958175a6a2bdb615fd9b858353120d5'
for pid,birth in ((82126,'2524927'),(82130,'2525033'),(79866,'2265436')):
 assert (Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19]==birth
c=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
try:
 c.request('POST','/api/command',json.dumps({'type':'pan_stop'}).encode(),{'Origin':'http://127.0.0.1:8783','Host':'127.0.0.1:8783','Content-Type':'application/json'})
 r=c.getresponse();body=r.read(2097153);post_status=r.status
finally:c.close()
time.sleep(.5)
c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
try:
 c.request('GET','/api/state');r=c.getresponse();body=r.read(2097153);assert r.status==200 and len(body)<=2097152
 s=json.loads(body);p=s.get('manual_pan',{});h=s.get('handsfree_dialogue',{})
finally:c.close()
owners=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:maps=(proc/'maps').read_text()
 except (FileNotFoundError,ProcessLookupError):continue
 if 'libvsrv.so' in maps or '/dev/mem' in maps:owners.append(int(proc.name))
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pan_stop_sent_once':True,'post_status':post_status,'pan':{k:p.get(k) for k in ('state','automatic_following','pulse_us','target_us','backend_pid')},'pan_error_present':bool(p.get('error')),'native_register_map_owners':owners,'listening_enabled':h.get('enabled'),'microphone_open':h.get('microphone_open'),'playing':s.get('playing')}))
