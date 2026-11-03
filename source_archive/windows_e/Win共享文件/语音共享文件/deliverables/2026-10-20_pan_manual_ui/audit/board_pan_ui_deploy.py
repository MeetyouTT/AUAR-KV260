"""Install an additive UI entrypoint against one exact live baseline, or restore it."""
import base64,hashlib,json,os,subprocess,sys,time,traceback,urllib.request
from pathlib import Path

HERE=Path(__file__).resolve().parent
payload=json.loads((HERE/'payload.json').read_text())
base=payload['baseline'];root=Path(base['aura_root']);startup=HERE/'startup'
dropin=Path('/etc/systemd/system/aura-avatar-ui.service.d/80-aura-pan-manual-20261020.conf')
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
report={'status':'STARTING','physical_test_commands_sent':0,'automatic_following':False,'baseline':base}
changed=False

def command(args,timeout=20):
 r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 assert r.returncode==0,(args,r.stderr[-1200:],r.stdout[-1200:])
 return r.stdout

def unit(name):
 return {k:command(['systemctl','show',name,'-p',k,'--value']).strip() for k in ['ActiveState','MainPID','WorkingDirectory','ExecStart']}

def get(port,path):
 with opener.open('http://127.0.0.1:%s%s'%(port,path),timeout=.5) as response:return json.load(response)

def camera():
 v=get(8790,'/health')
 assert not v['camera_error'] and not v['detector_error'] and v['identity_recognition']
 return {k:v.get(k) for k in ['pid','detection_hz','identity_recognition','camera_error','detector_error']}

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

try:
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==base['boot_id']
 before=unit('aura-avatar-ui.service');report['before']=before
 assert before['ActiveState']=='active' and before['WorkingDirectory']==str(root)
 assert base['launcher_path'] in before['ExecStart'] and base['config_path'] in before['ExecStart']
 assert digest(root/'tools/board_avatar_gtk.py')==base['gui_sha256']
 assert digest(base['config_path'])==base['startup_config_sha256']
 assert digest(base['launcher_path'])==base['launcher_sha256']
 assert not dropin.exists()
 gui=get(8783,'/api/state')
 assert gui.get('phase')=='IDLE' and not gui.get('playing'), 'UI busy; no installation performed'
 report['camera_before']=camera();report['camera_unit_before']=unit('aura-camera-ui.service')
 original=json.loads(Path(base['config_path']).read_text())
 for rel,sha in original['component_sha256'].items():assert digest(root/rel)==sha,rel
 for rel,item in payload['files'].items():
  assert rel and not Path(rel).is_absolute() and '..' not in Path(rel).parts
  assert not (root/rel).exists(),rel
  raw=base64.b64decode(item['base64']);assert hashlib.sha256(raw).hexdigest()==item['sha256']
  if rel.endswith('.py'):compile(raw,rel,'exec')
 startup.mkdir(exist_ok=False)
 for rel,item in payload['files'].items():
  p=root/rel;p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as out:out.write(base64.b64decode(item['base64']))
  os.chmod(p,0o600 if rel.endswith('.local.json') else 0o644)
 launcher=Path(base['launcher_path']).read_text()
 old="source = root/'aura/tools/board_avatar_gtk.py'";new="source = root/'aura/tools/board_avatar_pan.py'"
 assert launcher.count(old)==1;launcher=launcher.replace(old,new)
 (startup/'launcher.py').write_text(launcher)
 config=dict(original,gui_sha256=payload['files']['tools/board_avatar_pan.py']['sha256'])
 config['component_sha256']=dict(original['component_sha256'],**{rel:item['sha256'] for rel,item in payload['files'].items()})
 config['display_retrain_off_seconds']=2
 (startup/'config.json').write_text(json.dumps(config,indent=2)+'\n')
 report['preflight']=json.loads(command([sys.executable,'-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight']))
 tests=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests/framework','-p','test_manual_pan.py','-v'],cwd=str(root),capture_output=True,text=True,timeout=15)
 (HERE/'board-policy-tests.txt').write_text(tests.stdout+tests.stderr)
 assert tests.returncode==0,tests.stderr[-1400:]
 # Recheck immediately before the only service mutation.
 assert unit('aura-avatar-ui.service')==before, 'Live UI changed during preparation'
 assert digest(base['config_path'])==base['startup_config_sha256']
 gui=get(8783,'/api/state');assert gui.get('phase')=='IDLE' and not gui.get('playing')
 dropin.parent.mkdir(parents=True,exist_ok=True)
 content='[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+str(startup/'launcher.py')+' --config '+str(startup/'config.json')+'\n'
 with dropin.open('x') as out:out.write(content)
 changed=True
 command(['systemctl','daemon-reload'])
 command(['systemctl','restart','--no-block','aura-avatar-ui.service'])
 deadline=time.monotonic()+125
 state=None
 while time.monotonic()<deadline:
  try:
   state=get(8783,'/api/state')
   if state.get('manual_pan',{}).get('state')=='FAULT':raise RuntimeError(state['manual_pan'].get('error','Motion initialization failed'))
   if state.get('manual_pan',{}).get('state')=='READY' and unit('aura-avatar-ui.service')['ActiveState']=='active':break
  except (OSError,ValueError):pass
  time.sleep(.4)
 else:raise RuntimeError('New UI or manual pan readiness timed out')
 report['after']=unit('aura-avatar-ui.service');report['camera_after']=camera();report['camera_unit_after']=unit('aura-camera-ui.service')
 assert report['camera_unit_before']==report['camera_unit_after'] and report['camera_before']['pid']==report['camera_after']['pid']
 for rel,sha in original['component_sha256'].items():assert digest(root/rel)==sha,rel
 report['original_component_count_unchanged']=len(original['component_sha256'])
 report['manual_pan']=state['manual_pan'];assert not state['manual_pan']['history']
 final=state['manual_pan']['readback'];assert final['flags']==0 and final['lease_left_ms']==0
 report['ui']={k:state.get(k) for k in ['phase','playing','ui_page','ui_layer','backend']}
 report['display_retrain_off_seconds']=config['display_retrain_off_seconds']
 report['status']='INSTALLED_READY_NO_PWM_NO_CENTER_CALIBRATION'
except BaseException as exc:
 report.update(status='FAILED',error=type(exc).__name__+': '+str(exc))
 (HERE/'failure-traceback.txt').write_text(traceback.format_exc())
 if changed:
  try:
   assert dropin.read_text()==content
   dropin.unlink();command(['systemctl','daemon-reload']);command(['systemctl','restart','--no-block','aura-avatar-ui.service'])
   report['rollback']='Original launcher restored and restart requested; readiness requires separate check'
  except BaseException as rollback:report['rollback_error']=str(rollback)
finally:
 report['boot_after']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
 (HERE/'deployment-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(report,ensure_ascii=False),flush=True)
