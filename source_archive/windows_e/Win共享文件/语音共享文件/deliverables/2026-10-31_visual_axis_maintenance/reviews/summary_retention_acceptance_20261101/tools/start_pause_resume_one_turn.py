"""New pause/resume release adapter for the unchanged accepted 8ebb observer and graceful cleanup."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,time

HERE=Path(__file__).resolve().parents[1];PROJECT=HERE.parents[3]
JOINT=HERE.parent/'joint_performance_20261101'
BALANCE=PROJECT/'deliverables/2026-10-30_board_owner/integration/dialogue_repair/joint_balance_20261101'
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import KEY


def main():
 p=argparse.ArgumentParser()
 p.add_argument('--ready-evidence',type=Path,required=True)
 p.add_argument('--output-directory',type=Path)
 a=p.parse_args()
 observer=(JOINT/'remote/live_observer_caption_accepted.py').read_bytes()
 assert hashlib.sha256(observer).hexdigest()=='8ebb76746cb87bd3608671848cc8087d724e24d4282f2933a3c15b4879bd4819'
 pkg=HERE/'package/pause_resume';manifest_raw=(pkg/'BUNDLE_MANIFEST.json').read_bytes()
 assert hashlib.sha256(manifest_raw).hexdigest()=='248a731aa2c820e274be0809c44734b9dc37f04b77ee76e311f928d8401deaf7'
 for name,pin in json.loads(manifest_raw)['files'].items():assert hashlib.sha256((pkg/name).read_bytes()).hexdigest()==pin
 spec=json.loads((pkg/'candidate_spec.json').read_bytes())
 assert spec['startup_sha256']=='ec12fccfdd3e8446e9c761e161167e00187e6fcf90372aa7e52c9865cc23c56f'
 actual=json.loads(a.ready_evidence.read_bytes())['result']
 assert actual['status']=='PRODUCTION_BOARD_BUSINESS_READY' and actual['startup_sha256']==spec['startup_sha256']
 camera=spec['camera_owner'];owners={'camera':dict(pid=camera['camera_pid'],birth_ticks=int(camera['camera_start_ticks']),command_sha256=camera['camera_cmdline_sha256'])}
 for key in ('supervisor','gtk'):
  owner=actual[key];owners[key]=dict(pid=owner['pid'],birth_ticks=int(owner['birth']),command_sha256=owner['cmdline_sha256'])
 common=(JOINT/'remote/common.py').read_text('utf-8').replace('8ff79452570385921e06c098b5d42c2ea1ef5dfb84d81dfa7f53a9295373d0e8',spec['source_manifest_sha256'])
 source=(pkg/'camera_binding_runtime.py').read_text('utf-8')+'\n'+common+'\n'
 source+='STARTUP_SHA='+repr(spec['startup_sha256'])+'\nEXPECTED_OWNERS='+repr(owners)+'\n'
 source+=(HERE/'remote/selection_scope_metadata.py').read_text('utf-8')+'\n'
 source+='OBSERVER_SOURCE='+repr(observer.decode('utf-8'))+'\n'+REMOTE
 artifacts=a.output_directory.resolve() if a.output_directory else HERE
 assert artifacts.is_relative_to(PROJECT/'deliverables/2026-10-31_visual_axis_maintenance')
 folder=artifacts/'evidence'/('normal_ec12_trial_'+str(time.time_ns()));folder.mkdir(parents=True)
 evidence=folder/'metadata.jsonl';rows=[]
 args=['C:/Windows/System32/OpenSSH/ssh.exe','-i',str(KEY),'-o','IdentitiesOnly=yes','-o','BatchMode=yes',
       '-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=4','root@192.168.50.2','python3 -B -']
 process=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',
                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 process.stdin.write(source);process.stdin.close()
 with evidence.open('x',encoding='utf-8') as f:
  for line in process.stdout:
   row=json.loads(line);rows.append(row);f.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n');f.flush()
   if row.get('kind')=='ready':
    ready=dict(row,source_sha256=hashlib.sha256(source.encode()).hexdigest(),observer_sha256=hashlib.sha256(observer).hexdigest(),
               evidence_path=str(evidence),trial_directory=str(folder),expected_owners=owners)
    path=folder/'READY.json';path.write_text(json.dumps(ready,indent=2)+'\n',encoding='utf-8')
    (artifacts/'LIVE_LATEST.json').write_text(json.dumps(dict(status='READY_FOR_ONE_NEW_TURN',ready=str(path),evidence=str(evidence)),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='READY_FOR_ONE_NEW_TURN',ready=str(path),evidence=str(evidence)),ensure_ascii=False),flush=True)
   final_state=row.get('proof',{}).get('state',{})
   if (row.get('kind')=='final_guard' and final_state.get('listening_state')=='PAUSED'
       and final_state.get('microphone_open') is False and final_state.get('playing') is False):
    (folder/'FINAL_PAUSED.json').write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
 code=process.wait(timeout=10);error=process.stderr.read()
 accepted_complete=any(r.get('kind')=='complete' and r.get('status')=='ONE_NEW_TURN_COMPLETE' for r in rows)
 scope_kept=any(r.get('kind')=='selection_after_pause' and r.get('same_scope') is True for r in rows)
 final_ok=any(r.get('kind')=='final_guard' and r.get('one_new_turn_complete') is True and r.get('scope_preserved') is True for r in rows)
 result=dict(status='ONE_NEW_TURN_COMPLETE_SAME_SCOPE' if code==0 and accepted_complete and scope_kept and final_ok else 'OBSERVER_PROCESS_ERROR' if code else 'TRIAL_INCOMPLETE',exit_code=code,stderr_present=bool(error),
             terminal_events=[r for r in rows if r.get('kind') in ('complete','final_guard','observer_exception')],
             samples=sum(r.get('kind')=='sample' for r in rows),evidence=str(evidence),
             source_sha256=hashlib.sha256(source.encode()).hexdigest(),private_text_audio_images_saved=False)
 if error:result['error_class']='REMOTE_SCRIPT_ERROR'  # no arbitrary remote stderr is archived
 path=folder/'RESULT.json';path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 (artifacts/'LIVE_LATEST.json').write_text(json.dumps(dict(status=result['status'],result=str(path),evidence=str(evidence)),indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False),flush=True)


REMOTE=r'''
def current_guard():
 assert os.geteuid()==0 and os.uname().machine=='aarch64'
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
 assert digest(BUSINESS/'startup/config.json')==STARTUP_SHA
def assert_safe(value):
 s=safe_state(value);r=s['readback']
 assert s['following'] is False and s['pan_state']=='READY'
 assert r['flags']==0 and r['lease_left_ms']==0 and r['active'] is False and r['armed'] is False
 paused=(s['listening_enabled'] is False and s['listening_state']=='PAUSED' and s['microphone_open'] is False and s['playing'] is False)
 # When already enabled, attach read-only and let the reviewed observer wait
 # for its READY state. It ignores an initial in-flight request and never
 # toggles an enabled listener or interrupts its answer at startup.
 enabled=(s['listening_enabled'] is True and type(s['microphone_open']) is bool and type(s['playing']) is bool)
 assert paused or enabled
 return s
before,_,_=preflight()
print(json.dumps(dict(kind='guard_before',proof=before)),flush=True)
def ui_command(data):
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
 try:
  c.request('POST','/api/command',body=json.dumps(data),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
  r=c.getresponse();raw=r.read(100001);assert r.status==200 and len(raw)<=100000
  assert json.loads(raw).get('ok') is True
 finally:c.close()
scope_before=selection_scope_metadata()
print(json.dumps(dict(kind='selection_before_enable',**scope_before)),flush=True)
import builtins
scope_ready=None
def isolated_observer_print(*args,**kwargs):
 global scope_ready
 if len(args)==1 and isinstance(args[0],str):
  event=json.loads(args[0])
  if event.get('kind')=='ready':
   scope_ready=selection_scope_metadata()
   match=scope_ready['scope_token']==scope_before['scope_token']
   builtins.print(json.dumps(dict(kind='selection_after_enable',same_scope=match,**scope_ready)),flush=True)
   assert match,'CONTINUE_CHANGED_SCOPE'
 builtins.print(*args,**kwargs)
live_ns={'EXPECTED_STARTUP':STARTUP_SHA,'EXPECTED_BOOT':BOOT,'print':isolated_observer_print}
failure=None
try:
 if before['state']['listening_enabled'] is False:ui_command(dict(type='conversation_toggle'))
 exec(compile(OBSERVER_SOURCE,'<reviewed-live-observer-49fdf19>','exec'),live_ns)
except Exception as exc:
 failure=type(exc).__name__
 print(json.dumps(dict(kind='observer_exception',error_class=failure)),flush=True)
one_complete=bool(live_ns.get('completed'))
def settle_and_pause_after_observation():
 # The sampler's deadline never authorizes cancelling an in-flight answer.
 # Drain without extending the 180-second sampling window. If it cannot settle,
 # return an explicit pending cleanup and preserve the running answer.
 deadline=time.monotonic()+120
 while True:
  v=get_json(8783,'/api/state')
  task=v.get('local_transcription',{}).get('state')
  active=(v.get('playing') is True or v.get('phase') in ('THINKING','SPEAKING')
          or task in ('TRANSCRIBING','GENERATING','PLAYING'))
  if not active:break
  if time.monotonic()>=deadline:return dict(status='ANSWER_STILL_ACTIVE_CLEANUP_PENDING',pause_sent=False)
  time.sleep(.2)
 sent=v.get('handsfree_dialogue',{}).get('enabled') is True
 if sent:ui_command(dict(type='conversation_toggle'))
 return dict(status='NORMAL_PAUSE_REQUESTED' if sent else 'ALREADY_PAUSED',pause_sent=sent)
# Main chat requested a pause after the full target ACK, and a graceful drain
# on timeout. No cancellation command is ever issued by this observer cleanup.
try:
 cleanup=settle_and_pause_after_observation()
 print(json.dumps(dict(kind='observation_cleanup',**cleanup)),flush=True)
except Exception as exc:
 print(json.dumps(dict(kind='cleanup_error',error_class=type(exc).__name__)),flush=True)
end=time.monotonic()+8
while time.monotonic()<end:
 v=get_json(8783,'/api/state');h=v.get('handsfree_dialogue',{})
 if h.get('enabled') is False and h.get('state')=='PAUSED' and h.get('microphone_open') is False and v.get('playing') is False:break
 time.sleep(.2)
def current_guard():
 assert os.geteuid()==0 and os.uname().machine=='aarch64'
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
 assert digest(BUSINESS/'startup/config.json')==STARTUP_SHA
def assert_safe(value):
 s=safe_state(value);r=s['readback'];assert s['following'] is False and s['pan_state']=='READY'
 assert r['flags']==0 and r['lease_left_ms']==0 and r['active'] is False and r['armed'] is False
 assert type(s['listening_enabled']) is bool and type(s['microphone_open']) is bool
 return s
try:
 after,v,h=preflight()
 scope_final=selection_scope_metadata()
 print(json.dumps(dict(kind='selection_after_pause',same_scope=scope_final['scope_token']==scope_before['scope_token'],**scope_final)),flush=True)
 print(json.dumps(dict(kind='final_guard',proof=after,one_new_turn_complete=one_complete,
  scope_preserved=scope_final['scope_token']==scope_before['scope_token'] and scope_ready is not None and scope_ready['scope_token']==scope_before['scope_token'],
  renderer_worker_fault_count=v.get('avatar_renderer',{}).get('worker_faults',{}).get('count'),
  listening_preference_enabled=document('/home/root/.local/share/aura-board-business/listening_preference.json').get('enabled'),
  microphone_was_user_authorized=True,acoustic_first_sound_measured=False)),flush=True)
except Exception as exc:
 print(json.dumps(dict(kind='final_guard',status='FAILED',error_class=type(exc).__name__,one_new_turn_complete=one_complete)),flush=True)
'''


if __name__=='__main__':main()
