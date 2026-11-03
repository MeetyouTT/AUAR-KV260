import hashlib,http.client,json,time
from pathlib import Path
stage={'__name__':'_cpu_transaction_reviewed'};exec(compile(GTK_SOURCE,'<reviewed-gtk-template>','exec'),stage)
pin=stage['pinned'];read=stage['read_file'];proc=stage['proc']
assert EXPECTED['handoff_status']=='IDLE_GUI_CAMERA_LISTENING_TRANSFERRED_TO_CPU_WINDOW'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==EXPECTED['boot_id']
startup_path=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
raw,_=pin(startup_path,EXPECTED['startup_sha256']);startup=json.loads(raw);aura=Path(startup['runtime'])/'aura';pins=startup['component_sha256']
assert len(pins)==380
for name,digest in pins.items():pin(aura/name,digest)
for key in ('gui_owner','gtk_owner','camera_owner'):assert proc(EXPECTED[key]['pid'])==EXPECTED[key]
for name,digest in EXPECTED['identity_own_source_pins'].items():assert pins[name]==digest
pan_components,pan_external=stage['pan_closure'](aura,pins)
for path,digest in pan_external.items():pin(Path(path),digest)
selected=stage['selected_readback'](aura,startup,{str((aura/n).resolve()):(aura/n).resolve() for n in stage['TARGETS']})
assert selected['sha256']==EXPECTED['selected_face_binding']['sha256'] and selected['source_count']==EXPECTED['selected_face_binding']['source_pin_count']
camera=EXPECTED['camera_owner'];binding=selected['binding']
assert binding['board_boot_id']==EXPECTED['boot_id'] and binding['camera_pid']==camera['pid'] and str(binding['camera_start_ticks'])==camera['birth_ticks'] and binding['camera_cmdline_sha256']==camera['command_sha256']
def request(data=None):
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
 try:
  if data is None:c.request('GET','/api/state')
  else:c.request('POST','/api/command',json.dumps(data).encode(),{'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
  r=c.getresponse();b=r.read(2097153);assert r.status==200 and len(b)<=2097152;return json.loads(b)
 finally:c.close()
def idle(s):
 assert s.get('phase')=='IDLE' and s.get('playing') is False and not s.get('pending_job')
 h=s['handsfree_dialogue'];assert h.get('enabled') is False and h.get('microphone_open') is False and h.get('state')=='PAUSED'
 assert s['manual_pan'].get('automatic_following') is False
s=request();idle(s);original=s.get('ui_page');changed=original!='vision'
if changed:
 assert request({'type':'ui_page','page':'vision'}).get('ok') is True
 deadline=time.monotonic()+5
 while True:
  s=request();idle(s)
  if s.get('ui_page')=='vision':break
  assert time.monotonic()<deadline;time.sleep(.2)
assert s.get('ui_page')=='vision' and startup_path.read_bytes()==raw
for key in ('gui_owner','gtk_owner','camera_owner'):assert proc(EXPECTED[key]['pid'])==EXPECTED[key]
print(json.dumps({'status':'FRESH_BENCHMARK_VISION_PREPARED','boot_id':EXPECTED['boot_id'],'startup_path':str(startup_path),'startup_sha256':EXPECTED['startup_sha256'],'component_sha256':pins,'components_verified':380,'owners':{'camera':camera,'gui_supervisor':EXPECTED['gui_owner'],'gui_gtk':EXPECTED['gtk_owner']},'selected_readback':{'path':selected['path'],'sha256':selected['sha256'],'source_count':selected['source_count']},'pan_component_sha256':pan_components,'pan_external_sha256':pan_external,'original_page':original,'page':'vision','page_command_sent_once':changed,'platform':'benchmark as authorized handoff; no platform action','axis_commands':False,'service_actions':False}))
