assert ACTION in ('start','ready')

import fcntl,hashlib,http.client,json,os,re,sys,time
from pathlib import Path
TOOLS='/home/root/aura-character-xuefei-20261030/tools-c97bdb5e87268e2f'
assert hashlib.sha256((Path(TOOLS)/'formal_publish.py').read_bytes()).hexdigest()=='c97bdb5e87268e2fb846b171b9b0bb97cac98baa2664e733173912e73071956b'
sys.path.insert(0,TOOLS);import formal_publish as c
os.environ['PATH']='/usr/sbin:/usr/bin:/sbin:/bin'
p=c.parse(c.read(TOOLS+'/policy.json','b550e2a2307d97b52ba598a9e992f96ecacb53de05babf438d551a942de2996d'))
PREFIX=Path('/home/root/aura-board-business-20261030')
BASE=Path('/home/root/aura-character-xuefei-20261030/f94fca2c94288acb')
CONTROL=PREFIX/'control-production-v1'
STATE=CONTROL/'state.json'
def need(v,code):c.need(v,code)
def atomic(path,raw):
 path=Path(path);tmp=path.with_name(path.name+'.tmp-'+str(os.getpid()))
 c.create(tmp,raw);os.replace(str(tmp),str(path))
 fd=os.open(str(path.parent),os.O_DIRECTORY|os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
def save(j):atomic(STATE,c.encoded(j))
def journal():return c.parse(c.read(STATE))
def boot():
 actual=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
 need(actual==SPEC['boot_id']==p['boot_id'],'fresh_boot_changed')
 need(c.same(c.process(p['camera']['pid']),p['camera']),'camera_owner_changed')
 return actual
def source():
 root=Path(SPEC['target'])
 need(root.parent==PREFIX and root.resolve()==root and root!=CONTROL,'canonical_production_root_required')
 raw=c.read(root/'startup/config.json',SPEC['startup_sha256']);cfg=c.parse(raw)
 need(cfg['runtime']==str(root/'runtime') and len(cfg['component_sha256'])==SPEC['component_pins'],'source_config_changed')
 for rel,pin in cfg['component_sha256'].items():c.read(root/'runtime/aura'/c.relative(rel),pin)
 need(SPEC.get('native_library_sha256')=='b2432e75a75e4dbdebee8e89a141a68ba00671c33b2b258b81ce16794b2c73d2','reviewed_thinking_native_required')
 need(cfg['component_sha256']['tools/libaura_yuki.so']==SPEC['native_library_sha256'],'reviewed_native_changed')
 c.read(root/'startup/launcher.py','5b15a8cf1813935679e5f4d30eb788e9c8d6ae18826669009d06c92cba152e03')
 return root
def argv(root):return ['/usr/bin/python3','-B',str(root/'startup/launcher.py'),'--config',str(root/'startup/config.json')]
def listening_readonly_state():
 module=c.load_module(p['public_probe'],p['public_probe_sha256'],'_automatic_listening_readonly_state')
 return module._local_json(8783,'/api/state')

def state():
 if not SPEC.get('automatic_listening',False):return c.state(p)
 v=listening_readonly_state();h=v.get('handsfree_dialogue',{});pan=v.get('manual_pan',{})
 d=v.get('safe_capture_diagnostics',{});task=v.get('local_transcription',{}).get('state')
 need(v.get('phase')=='IDLE' and v.get('playing') is False
      and pan.get('automatic_following') is False and pan.get('state')=='FAULT'
      and 'pulse_us' in pan and pan['pulse_us'] is None,
      'idle_no_play_follow_fault_null_required')
 quiet_capture=(d.get('capture',{}).get('speech_active') is False or
     h.get('microphone_open') is False and d.get('capture_state') in ('IDLE','CANCELLED','CLOSED','ERROR'))
 need(h.get('conversation_entered') is False
      and h.get('state') in ('PAUSED','WAITING_WAKE','WAITING_SPEECH','COOLDOWN','WAITING_SERVICE')
      and quiet_capture
      and task not in ('TRANSCRIBING','GENERATING','PLAYING'),
      'no_active_speech_or_conversation_required_for_normal_close')
 return v

def ready_state():
 if not SPEC.get('automatic_listening',False):return state()
 v=listening_readonly_state();h=v.get('handsfree_dialogue',{});pan=v.get('manual_pan',{})
 need(v.get('playing') is False and pan.get('automatic_following') is False
      and pan.get('state')=='FAULT' and 'pulse_us' in pan and pan['pulse_us'] is None,
      'no_play_follow_fault_null_required')
 preference=Path('/home/root/.local/share/aura-board-business/listening_preference.json')
 enabled=True
 if preference.exists():
  value=c.parse(c.read(preference))
  need(set(value)=={'version','enabled'} and type(value['version']) is int and value['version']==1
       and type(value['enabled']) is bool,'valid_explicit_listening_preference_required')
  enabled=value['enabled']
 need(h.get('enabled') is enabled,'listening_preference_not_restored')
 if enabled:
  d=v.get('safe_capture_diagnostics',{})
  wake_required=SPEC.get('wake_word_required',True)
  if not wake_required:
   need(h.get('wake_word_required') is False and h.get('entry_mode')=='direct_speech'
        and h.get('wake_words')==[],'direct_speech_policy_not_active')
  if SPEC.get('conversation_mode')=='half_duplex':
   need(h.get('conversation_mode')=='half_duplex' and h.get('voice_barge_in') is False
        and v.get('voice_barge_in',{}).get('enabled') is False,'half_duplex_policy_not_active')
  need(h.get('microphone_open') is True and h.get('state')==('WAITING_WAKE' if wake_required else 'WAITING_SPEECH')
       and d.get('error_code')=='none' and d.get('capture',{}).get('input_ready') is True
       and d.get('audio_frontend',{}).get('frames',0)>=25,'automatic_capture_not_ready')
 else:
  need(h.get('microphone_open') is False and h.get('state')=='PAUSED','explicit_user_pause_not_honored')
 return v
def owner(root):
 u=c.show();sup=c.process(int(u['MainPID']))
 need(u['ActiveState']=='active' and not u.get('Job') and sup and sup['argv']==argv(root),'exact_live_supervisor_required')
 launch=c.parse(c.read(root/'runtime/launch.json'));child=c.process(launch['pid'])
 need(child and child['ppid']==sup['pid'] and child['argv'][:3]==['/usr/bin/python3','-B',str(root/'runtime/aura/tools/board_avatar_pan.py')],'exact_live_gtk_required')
 return u,sup,child
def guarded(j):
 boot();u=c.show();c.read(j['guard'],j['guard_sha256'])
 need(u['Restart']=='no' and u['SendSIGKILL']=='no' and u['TimeoutStopUSec']=='infinity' and not u.get('Job'),'no_force_guard_required')
 expected=set(j['original_properties']['DropInPaths'].split())|{j['guard']}
 if j.get('persistent_sha256'):
  c.read(j['persistent'],j['persistent_sha256']);expected.add(j['persistent'])
 need(set(u['DropInPaths'].split())==expected,'dropin_set_changed')
 for path,pin in j['original_unit_sha256'].items():c.read(path,pin)
 return u
def inactive(j):
 u=guarded(j)
 need(u['MainPID']=='0' and u['ActiveState']=='inactive','ownerless_unit_required')
 if j.get('closing'):
  need(not c.same(c.process(j['closing']['owner']['pid']),j['closing']['owner']) and not c.same(c.process(j['closing']['supervisor']['pid']),j['closing']['supervisor']),'old_owner_alive')
 return u
def guard():
 boot();source();v=state()
 if STATE.exists():
  j=journal();need(j.get('guard_removed') and j['phase']=='COMMITTED','existing_unfinished_transaction')
  root=Path(j['active_root']);u,sup,child=owner(root)
  need(u['DropInPaths']==j['final_dropins'],'committed_dropins_changed')
  c.create(j['guard'],bytes.fromhex(j['guard_hex']));c.command(['/bin/systemctl','daemon-reload'])
  j.update(guard_removed=False,phase='GUARDED',closing=None);save(j);guarded(j)
  return dict(status='EXISTING_PRODUCTION_GUARDED',main_pid=sup['pid'])
 need(c.sha(c.read(BASE/'startup/config.json'))=='4c78824ba9c1c04bb95389a49b64215a7f624a323becae637bc8d4e7c4db4d7e','appearance_baseline_changed')
 u,sup,child=owner(BASE)
 need(u['Restart']=='no' and u['SendSIGKILL']=='yes' and u['TimeoutStopUSec']=='25s','baseline_stop_policy_changed')
 paths=u['DropInPaths'].split();n=max(len(re.match('z*',Path(x).name).group()) for x in paths)+1
 fragment=c.command(['/bin/systemctl','show','aura-avatar-ui.service','--property=FragmentPath','--value']).strip()
 need(fragment=='/etc/systemd/system/aura-avatar-ui.service','base_unit_path_changed')
 persistent='/etc/systemd/system/aura-avatar-ui.service.d/'+'z'*n+'-aura-board-business-20261030.conf'
 guardpath='/run/systemd/system/aura-avatar-ui.service.d/'+'z'*(n+1)+'-aura-board-business-safe-20261030.conf'
 need(not Path(persistent).exists() and not Path(guardpath).exists(),'new_owned_dropins_required')
 raw=b'[Service]\nRestart=no\nSendSIGKILL=no\nTimeoutStopSec=infinity\nTimeoutStartSec=180s\n'
 CONTROL.mkdir(mode=0o700,parents=False)
 j=dict(schema=1,phase='GUARD_INTENT',boot_id=SPEC['boot_id'],active_root=str(BASE),original_properties=u,
  original_unit_sha256={x:c.sha(c.read(x)) for x in paths+[fragment]},guard=guardpath,guard_sha256=c.sha(raw),guard_hex=raw.hex(),
  persistent=persistent,guard_removed=False,baseline_supervisor=sup,baseline_child=child,private_root='/home/root/.local/share/aura-board-business')
 save(j);Path(guardpath).parent.mkdir(mode=0o755,parents=True,exist_ok=True);c.create(guardpath,raw)
 c.command(['/bin/systemctl','daemon-reload']);guarded(j);j['phase']='GUARDED';save(j)
 return dict(status='BASELINE_GUARDED_NO_CLOSE',main_pid=sup['pid'])
def window():
 j=journal();guarded(j);state();root=Path(j['active_root']);u,sup,child=owner(root)
 x=c.load_module(p['x11_source'],p['x11_sha256'],'_production_x11').X11(':0')
 try:
  rows=x.windows(child['pid']);need(len(rows)==1 and rows[0]['normal'] and rows[0]['delete_supported'],'one_normal_delete_window_required')
  proof=dict(boot_id=boot(),supervisor=sup,owner=child,window={k:rows[0][k] for k in ('window_id','title_sha256')},guard_sha256=j['guard_sha256'])
  need(c.same(c.process(child['pid']),child),'gtk_changed_during_review')
  return proof
 finally:x.close()
def close():
 proof=window();need(c.sha(c.encoded(proof))==TOKEN and proof['window']['window_id']==WINDOW,'exact_review_token_required')
 need(window()==proof,'window_changed_before_close')
 j=journal();j.update(phase='CLOSE_INTENT',closing=proof);save(j)
 x=c.load_module(p['x11_source'],p['x11_sha256'],'_production_close').X11(':0')
 try:
  rows=x.windows(proof['owner']['pid'])
  need(len(rows)==1 and rows[0]['window_id']==WINDOW and rows[0]['title_sha256']==proof['window']['title_sha256'] and rows[0]['delete_supported'],'exact_window_changed')
  need(c.same(c.process(proof['owner']['pid']),proof['owner']),'gtk_owner_changed');state();x.send_delete(WINDOW)
 finally:x.close()
 end=time.monotonic()+45
 while time.monotonic()<end:
  u=c.show()
  if u['MainPID']=='0' and u['ActiveState']=='inactive' and not u.get('Job') and not c.same(c.process(proof['owner']['pid']),proof['owner']) and not c.same(c.process(proof['supervisor']['pid']),proof['supervisor']):
   j['phase']='NORMAL_CLOSED';save(j);return dict(status='GTK_AND_SUPERVISOR_NATURALLY_EXITED',forced_action=False)
  time.sleep(.2)
 return dict(status='NORMAL_CLOSE_PENDING_GUARD_RETAINED',forced_action=False)
def start():
 j=journal();inactive(j);root=source();c.command(argv(root)+['--preflight'],timeout=25)
 paths=[str(root/'runtime/aura'),
  '/home/root/aura-board-owner-candidate-20261030/fft-ee19b936d17aa451/deps',
  '/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps',
  '/home/root/aura-board-owner-candidate-20261030/webrtcvad-wheels-2.0.14-127741474d07c52f/deps']
 need(all(Path(x).is_dir() and Path(x).resolve()==Path(x) for x in paths),'reviewed_arm_dependencies_missing')
 environment={'PYTHONPATH':':'.join(paths),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1',
  'PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1'}
 need(all(re.fullmatch(r'[A-Za-z0-9_./:-]+',value) for value in environment.values()),'bounded_systemd_environment_required')
 raw=('[Service]\nExecStart=\nExecStart='+' '.join(argv(root))+'\nTimeoutStartSec=180s\n'+
  ''.join('Environment='+key+'='+value+'\n' for key,value in environment.items())).encode()
 if Path(j['persistent']).exists():c.read(j['persistent'],c.sha(raw))
 else:c.create(j['persistent'],raw)
 j.update(persistent_sha256=c.sha(raw),phase='START_INTENT',target=str(root),target_startup_sha256=SPEC['startup_sha256'],target_pins=SPEC['component_pins']);save(j)
 c.command(['/bin/systemctl','daemon-reload']);u=guarded(j)
 need(c.exec_argv(u['ExecStart'])==' '.join(argv(root)),'production_exec_not_selected')
 c.command(['/bin/systemctl','--no-block','start','aura-avatar-ui.service']);j['phase']='STARTING';j['active_root']=str(root);save(j)
 return dict(status='PRODUCTION_NORMAL_START_REQUESTED',root=str(root),physical_audio_opened=False)
def ready():
 j=journal();root=source();need(str(root)==j['target'],'target_changed')
 end=time.monotonic()+180;last='not_ready';stable=None
 while time.monotonic()<end:
  try:
   guarded(j);u,sup,child=owner(root);v=ready_state();b=v.get('board_business',{});pair=v.get('character_pair',{});d=v.get('avatar_display',{})
   need(pair.get('state')=='READY' and pair.get('prompt_sha256')=='11b1b4d04c55ac110969fd5dd7ffb37f29b29bbc26d9c7906e454d4f69af654e' and pair.get('production_selected') is True,'selected_persona_not_ready')
   need(d.get('kind')=='native_yuki_egl' and d.get('frames',0)>0 and d.get('visible') is True,'native_display_not_ready')
   need(b.get('mode')=='board-business-board' and b.get('data_origin')=='board' and b.get('production_cutover') is True and b.get('started') is True and b.get('closed') is False,'production_business_not_ready')
   need(b.get('writer',{}).get('held') is True and b.get('receipt',{}).get('verified') is True and b.get('receipt',{}).get('profiles_migration_verified') is True,'production_receipt_not_ready')
   need(b.get('speaker',{}).get('ready') is True and b.get('speaker',{}).get('data_origin')=='board','board_speaker_not_ready')
   need(b.get('retention',{}).get('enabled') is bool(SPEC['retention_enabled']),'retention_selection_changed')
   need(b.get('retention',{}).get('running') is bool(SPEC['retention_enabled']),'retention_worker_not_in_selected_state')
   if SPEC.get('automatic_listening',False) and v.get('handsfree_dialogue',{}).get('enabled') is True:
    diagnostics=v['safe_capture_diagnostics'];armed=diagnostics.get('counters',{}).get('armed');frames=diagnostics['audio_frontend']['frames']
    if stable is None or stable['armed']!=armed:
     stable=dict(at=time.monotonic(),armed=armed,frames=frames)
     time.sleep(.5);continue
    need(frames>stable['frames'],'automatic_capture_not_progressing')
    stable['frames']=frames
    if time.monotonic()-stable['at']<5.:
     time.sleep(.5);continue
   break
  except (ValueError,OSError,TimeoutError) as exc:
   stable=None;last=str(exc) if isinstance(exc,ValueError) else type(exc).__name__;time.sleep(.5)
 else:return dict(status='READINESS_PENDING_GUARD_RETAINED',reason=last,forced_action=False)
 raw=c.read(j['guard'],j['guard_sha256'])
 try:
  Path(j['guard']).unlink();c.command(['/bin/systemctl','daemon-reload'])
  final=c.show()
  need(final['MainPID']==str(sup['pid']) and not final.get('Job') and c.exec_argv(final['ExecStart'])==' '.join(argv(root)),'final_owner_changed')
  for k in ('Restart','SendSIGKILL','TimeoutStopUSec'):need(final[k]==j['original_properties'][k],'stop_policy_not_restored')
 except Exception:
  if not Path(j['guard']).exists():c.create(j['guard'],raw)
  c.read(j['guard'],j['guard_sha256'])
  j.update(phase='POSTCHECK_FAILED_GUARDED',guard_removed=False);save(j)
  c.command(['/bin/systemctl','daemon-reload']);raise
 j.update(phase='COMMITTED',guard_removed=True,final_supervisor=sup,final_child=child,final_dropins=final['DropInPaths']);save(j)
 h=v.get('handsfree_dialogue',{})
 return dict(status='PRODUCTION_BOARD_BUSINESS_READY',root=str(root),main_pid=sup['pid'],gtk_pid=child['pid'],data_origin='board',retention_enabled=SPEC['retention_enabled'],automatic_listening=SPEC.get('automatic_listening',False),listening_enabled=h.get('enabled'),listening_state=h.get('state'),physical_microphone_opened=h.get('microphone_open') is True,physical_audio_played=False,guard_removed=True)
boot()
with open('/run/aura-production-publisher.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 if ACTION=='guard':result=guard()
 elif ACTION=='window-inspect':
  proof=window();result=dict(status='WINDOW_INSPECTED_NO_CLOSE',window=proof['window'],review_token=c.sha(c.encoded(proof)))
 elif ACTION=='normal-close':result=close()
 elif ACTION=='start':result=start()
 elif ACTION=='ready':result=ready()
 else:raise ValueError('unknown_action')
print(json.dumps(result,ensure_ascii=True))
