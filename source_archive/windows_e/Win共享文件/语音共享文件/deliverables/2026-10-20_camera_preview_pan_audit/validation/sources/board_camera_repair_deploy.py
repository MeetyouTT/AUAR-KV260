"""Install two guarded GUI fixes; keep camera, models, native driver and voice."""
import base64,hashlib,json,subprocess,sys,time,traceback,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
payload=json.loads((HERE/'payload.json').read_text());base=payload['baseline'];root=Path(base['aura_root'])
dropin=Path('/etc/systemd/system/aura-avatar-ui.service.d/80-aura-pan-manual-20261020.conf')
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
report={'status':'STARTING','movement_commands_sent':0};changed=False;old_files={}
def digest(raw):return hashlib.sha256(raw).hexdigest()
def cmd(args,timeout=30):
 r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 assert r.returncode==0,(args,r.stderr[-1200:],r.stdout[-1200:]);return r.stdout
def unit(name):return {k:cmd(['systemctl','show',name,'-p',k,'--value']).strip() for k in ['ActiveState','MainPID','WorkingDirectory','ExecStart']}
def api(data=None):
 url='http://127.0.0.1:8783'
 req=url+'/api/state' if data is None else urllib.request.Request(url+'/api/command',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':url})
 with opener.open(req,timeout=3) as r:return json.load(r)
def camera():
 with opener.open('http://127.0.0.1:8790/health',timeout=1) as r:v=json.load(r)
 assert not v['camera_error'] and not v['detector_error']
 return {k:v.get(k) for k in ['pid','capture_hz','detection_hz','identity_recognition','camera_error','detector_error']}
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==base['boot_id']
 before=unit('aura-avatar-ui.service');report['before']=before
 assert before['ActiveState']=='active' and before['WorkingDirectory']==str(root)
 assert str(Path(base['startup'])/'launcher.py') in before['ExecStart']
 oldconfig=Path(base['startup'])/'config.json'
 assert digest(oldconfig.read_bytes())==base['startup_config_sha256']
 config=json.loads(oldconfig.read_text());old_dropin=dropin.read_bytes()
 assert str(Path(base['startup'])/'launcher.py').encode() in old_dropin
 for rel,sha in config['component_sha256'].items():assert digest((root/rel).read_bytes())==sha,rel
 new_files={}
 for rel,item in payload['files'].items():
  raw=(root/rel).read_bytes();assert digest(raw)==item['old_sha256'],rel;old_files[rel]=raw
  if 'base64' in item:new=base64.b64decode(item['base64'])
  else:
   text=raw.decode()
   for old,replacement in item['replacements']:
    assert text.count(old)==1,(rel,'replacement is not unique');text=text.replace(old,replacement)
   new=text.encode()
  assert digest(new)==item['sha256'],rel;compile(new,rel,'exec');new_files[rel]=new
 gui=api();assert gui['phase']=='IDLE' and not gui['playing'] and not gui['avatar_command_pending']
 assert gui['manual_pan']['state']=='READY'
 assert gui['manual_pan']['readback']['flags']==0 and gui['manual_pan']['readback']['lease_left_ms']==0
 report['pulse_before']=gui['manual_pan']['pulse_us'];report['camera_before']=camera();report['camera_unit_before']=unit('aura-camera-ui.service')
 backup=HERE/'backup';backup.mkdir(exist_ok=False)
 for rel,raw in old_files.items():
  p=backup/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 (backup/'dropin.conf').write_bytes(old_dropin)
 cmd(['systemctl','stop','aura-avatar-ui.service']);changed=True
 for rel,raw in new_files.items():(root/rel).write_bytes(raw)
 startup=HERE/'startup';startup.mkdir(exist_ok=False)
 (startup/'launcher.py').write_bytes((Path(base['startup'])/'launcher.py').read_bytes())
 config['component_sha256'].update({rel:item['sha256'] for rel,item in payload['files'].items()})
 assert config['display_retrain_off_seconds']==2
 (startup/'config.json').write_text(json.dumps(config,indent=2)+'\n')
 report['preflight']=json.loads(cmd([sys.executable,'-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight']))
 assert dropin.read_bytes()==old_dropin
 dropin.write_text('[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+str(startup/'launcher.py')+' --config '+str(startup/'config.json')+'\n')
 cmd(['systemctl','daemon-reload']);cmd(['systemctl','start','--no-block','aura-avatar-ui.service'])
 deadline=time.monotonic()+150
 while time.monotonic()<deadline:
  try:
   gui=api();pan=gui.get('manual_pan',{})
   if pan.get('state')=='FAULT':raise RuntimeError(pan.get('error','Pan unavailable'))
   if pan.get('state')=='READY' and pan.get('backend_pid') and unit('aura-avatar-ui.service')['ActiveState']=='active':break
  except (OSError,ValueError):pass
  time.sleep(.4)
 else:raise RuntimeError('Camera repair UI readiness timeout')
 report['after']=unit('aura-avatar-ui.service');report['pan_after']=pan
 report['camera_after']=camera();report['camera_unit_after']=unit('aura-camera-ui.service')
 assert report['camera_unit_before']==report['camera_unit_after']
 assert report['camera_before']['pid']==report['camera_after']['pid']
 assert pan['pulse_us']==report['pulse_before'] and pan['history']==[]
 assert pan['readback']['flags']==0 and pan['readback']['lease_left_ms']==0
 report['ui_actions']=[api({'type':'ui_page','page':'vision'}),api({'type':'pan_dialog'})]
 assert all(x.get('ok') for x in report['ui_actions'])
 report['status']='CAMERA_FIX_INSTALLED_PANEL_OPEN_SCREEN_VERIFICATION_PENDING'
except BaseException as exc:
 report.update(status='FAILED',error=type(exc).__name__+': '+str(exc));(HERE/'failure-traceback.txt').write_text(traceback.format_exc())
 if changed:
  try:
   cmd(['systemctl','stop','aura-avatar-ui.service'])
   for rel,raw in old_files.items():(root/rel).write_bytes(raw)
   dropin.write_bytes(old_dropin);cmd(['systemctl','daemon-reload']);cmd(['systemctl','start','--no-block','aura-avatar-ui.service'])
   report['rollback']='Previous two sources and startup restored; UI restart requested'
  except BaseException as e:report['rollback_error']=str(e)
finally:
 (HERE/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report),flush=True)
