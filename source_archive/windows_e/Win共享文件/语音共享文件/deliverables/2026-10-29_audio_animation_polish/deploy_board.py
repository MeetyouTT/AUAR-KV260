"""Guarded single UI switch, preserving all existing systemd overrides and motion pins."""
import json,time
from board_guard import H,SCRIPT,capture,same,ssh
b=json.loads((H/'preflight.json').read_text(encoding='utf-8'));same(b,capture());time.sleep(.8);same(b,capture())
c=json.loads((H/'candidate.json').read_text(encoding='utf-8'))
assert json.loads((H/'native_visual.json').read_text())['status']=='PASS'
assert json.loads((H/'renderer_after.json').read_text())['status']=='PASS'
script=r'''
import contextlib,hashlib,io,json,os,re,subprocess,time,urllib.request
from pathlib import Path
b=BASE;c=CANDIDATE
def capture():
 out=io.StringIO()
 with contextlib.redirect_stdout(out):exec(GUARD,{'__name__':'guard'})
 return json.loads(out.getvalue())
def stable(v):
 assert v['safe'] and not v['mismatches'],'Not safely idle'
 for key in ('boot','actual_config','actual_runtime','config_sha256','pending_config_sha256','pending_launcher_sha256','mechanical_sha256','settings','firmware','fdt_sha256','vart'):
  assert v[key]==b[key],'Concurrent board update: '+key
 for name in ('ui','camera'):
  for key in ('MainPID','ExecStart','DropInPaths','NRestarts','ActiveState'):assert v[name][key]==b[name][key],name+key
stable(capture());time.sleep(.6);stable(capture())
stage=Path(c['stage']);startup=Path(c['startup']);root=Path(c['runtime'])
assert hashlib.sha256((startup/'launcher.py').read_bytes()).hexdigest()==b['pending_launcher_sha256']
cfg=json.loads((startup/'config.json').read_text())
assert {k:v for k,v in cfg.items() if k not in ('runtime','component_sha256')}=={k:v for k,v in b['pending'].items() if k not in ('runtime','component_sha256')}
assert cfg['component_sha256']==c['pins']
for name,sha in c['pins'].items():assert hashlib.sha256((root/'aura'/name).read_bytes()).hexdigest()==sha,name
paths=[Path(name) for name in b['ui']['DropInPaths'].split()]
prior={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
depth=max(len(re.match('z*',p.name).group()) for p in paths)+1
override=Path('/etc/systemd/system/aura-avatar-ui.service.d')/('z'*depth+'-aura-audio-animation-20261029.conf')
content=('[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+str(startup/'launcher.py')+' --config '+str(startup/'config.json')+'\n').encode()
assert not override.exists()
report=dict(status='SWITCHING',override=str(override),override_sha256=hashlib.sha256(content).hexdigest(),
 prior_overrides=prior,previous_pending_config=b['pending_config'],runtime=str(root),microphone_enabled=False,motion_command_sent=False)
def save():
 temporary=stage/'deployment.json.tmp';temporary.write_text(json.dumps(report,indent=2));os.replace(temporary,stage/'deployment.json')
save()
try:
 override.write_bytes(content);subprocess.run(['systemctl','daemon-reload'],check=True,timeout=15)
 subprocess.run(['systemctl','restart','aura-avatar-ui.service'],check=True,timeout=120)
 deadline=time.monotonic()+35;after=None;last=''
 while time.monotonic()<deadline:
  try:
   after=capture()
   assert after['actual_config']==str(startup/'config.json') and after['actual_runtime']==str(root)
   assert after['safe'] and not after['mismatches'] and after['pins']==c['pins']
   assert after['camera']['MainPID']==b['camera']['MainPID'] and after['camera']['ExecStart']==b['camera']['ExecStart']
   assert after['state']['camera_epoch']==b['state']['camera_epoch']
   for key in ('boot','mechanical_sha256','settings','firmware','fdt_sha256','vart'):assert after[key]==b[key],key
   assert after['pan']['automatic_following'] is False and after['pan']['pulse_us']==b['pan']['pulse_us']
   assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==sha for p,sha in prior.items())
   assert after['state']['portrait_offload']['mode']=='remote'
   break
  except Exception as exc:last=type(exc).__name__+': '+str(exc);time.sleep(.5)
 else:raise RuntimeError('Post-deploy readiness: '+last)
 report.update(status='COMMITTED',after=after,pins=len(c['pins']),prior_overrides_preserved=True,
  optimized_launcher_preserved=True,mechanical_configuration_unchanged=True,camera_process_unchanged=True,
  microphone_enabled=False,physical_playback=False,motion_command_sent=False)
except Exception as exc:
 report.update(status='FAILED',error=type(exc).__name__+': '+str(exc))
 try:
  effective=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
  assert str(startup/'config.json') in effective,'Concurrent unit update; rollback deferred'
  assert override.read_bytes()==content,'Own override modified; rollback deferred'
  override.unlink();subprocess.run(['systemctl','daemon-reload'],check=True,timeout=15)
  subprocess.run(['systemctl','restart','aura-avatar-ui.service'],check=True,timeout=120)
  report.update(status='ROLLED_BACK',rollback_config=b['pending_config'])
 except Exception as rollback:report['rollback_error']=type(rollback).__name__+': '+str(rollback)
finally:save()
print(json.dumps(report))
'''.replace('BASE',repr(b)).replace('CANDIDATE',repr(c)).replace('GUARD',repr(SCRIPT))
try:v=json.loads(ssh('python3 -B -',script,timeout=200))
except Exception as exc:
    (H/'deployment_transport_failure.json').write_text(json.dumps({'status':'CHECK_REMOTE_TRANSACTION','error':str(exc),'stage':c['stage']},indent=2),encoding='utf-8');raise
(H/'deployment.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({key:v.get(key) for key in ('status','runtime','pins','optimized_launcher_preserved','mechanical_configuration_unchanged','camera_process_unchanged','error','rollback_error')}))
raise SystemExit(0 if v['status']=='COMMITTED' else 1)
