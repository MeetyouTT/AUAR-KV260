"""Test pause/resume and turn cancellation without speech or model requests."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE=r'''
import hashlib,http.client,json,pathlib,subprocess,time
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
gtk=json.loads((root/'runtime/launch.json').read_bytes())['pid']
cfg=json.loads((root/'runtime/aura/config/board_avatar_gtk.json').read_bytes())
capture_process=cfg['board_business'].get('frontend_capture_process',False)
def owned_audio_processes():
 workers=[];recorders=[]
 for path in pathlib.Path('/proc').iterdir():
  if not path.name.isdigit():continue
  try:
   stat=(path/'stat').read_text();parts=stat[stat.rfind(')')+2:].split();parent=int(parts[1]);name=(path/'comm').read_text().strip()
   if parent==gtk and name=='python3' and b'board_frontend_process' in (path/'cmdline').read_bytes():workers.append(int(path.name))
   if name=='arecord':recorders.append((int(path.name),parent))
  except (OSError,ValueError):pass
 owners=set(workers) if capture_process else {gtk}
 return dict(workers=workers,recorders=[pid for pid,parent in recorders if parent in owners])
def state():
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
 try:
  c.request('GET','/api/state');r=c.getresponse();raw=r.read(1048577);assert r.status==200 and len(raw)<=1048576
  return json.loads(raw)
 finally:c.close()
def command(value):
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
 try:
  c.request('POST','/api/command',body=json.dumps(value),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
  r=c.getresponse();raw=r.read(65537);assert r.status==200 and len(raw)<=65536
 finally:c.close()
def wait(predicate):
 end=time.monotonic()+12
 while time.monotonic()<end:
  v=state()
  if predicate(v):return v
  time.sleep(.2)
 raise RuntimeError('control_semantics_state_not_ready')
def active(v):
 h=v.get('handsfree_dialogue',{});d=v.get('safe_capture_diagnostics',{})
 return (h.get('enabled') is True and h.get('microphone_open') is True
  and h.get('state')==('WAITING_WAKE' if WAKE_REQUIRED else 'WAITING_SPEECH')
  and (WAKE_REQUIRED or h.get('wake_word_required') is False and h.get('entry_mode')=='direct_speech' and h.get('wake_words')==[])
  and v.get('playing') is False and d.get('error_code')=='none' and d.get('capture',{}).get('input_ready') is True
  and d.get('audio_frontend',{}).get('frames',0)>=10)
def preference():
 p=pathlib.Path('/home/root/.local/share/aura-board-business/listening_preference.json')
 assert not p.is_symlink() and p.is_file() and p.stat().st_size<=4096
 v=json.loads(p.read_bytes());assert set(v)=={'version','enabled'} and v['version']==1 and type(v['enabled']) is bool
 return v['enabled']
v=wait(active);assert v['handsfree_dialogue'].get('conversation_entered') is False
before_processes=owned_audio_processes()
command(dict(type='conversation_toggle'))
paused=wait(lambda s:s.get('handsfree_dialogue',{}).get('enabled') is False and s.get('handsfree_dialogue',{}).get('microphone_open') is False)
pause_pref=preference() is False
paused_processes=owned_audio_processes()
restore=paused.get('safe_capture_diagnostics',{}).get('capture_priority',{})
command(dict(type='conversation_toggle'));resumed=wait(active);resume_pref=preference() is True
before=resumed['safe_capture_diagnostics']['counters']['armed']
command(dict(type='event',event='cancel'))
cancelled=wait(lambda s:active(s) and s['safe_capture_diagnostics']['counters']['armed']>before)
unit=dict(x.split('=',1) for x in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID'],text=True).splitlines() if '=' in x)
final_processes=owned_audio_processes()
out=dict(root=str(root),startup_sha256=hashlib.sha256((root/'startup/config.json').read_bytes()).hexdigest(),main_pid=int(unit['MainPID']),gtk_pid=gtk,
 pause_preference_false_observed=pause_pref,resume_preference_true_observed=resume_pref,
 cancel_rearm_passed=active(cancelled) and preference() is True,
 pause_closed_microphone=paused['handsfree_dialogue']['microphone_open'] is False,
 capture_priority_restored_on_pause=(None if capture_process else restore.get('restoration_confirmed') is True and restore.get('restored_nice')==0),
 frontend_capture_process=capture_process,pause_released_owned_arecord=not paused_processes['recorders'],
 model_worker_reused_on_rearm=(before_processes['workers']==paused_processes['workers']==final_processes['workers']),
 actual_restart_pause_verified=False,operator_dialogue_acceptance=False,raw_audio_saved_or_transferred=False,
 final_listening_enabled=cancelled['handsfree_dialogue']['enabled'],final_listening_state=cancelled['handsfree_dialogue']['state'])
out['wake_word_required']=WAKE_REQUIRED
print(json.dumps(out))
'''

if __name__=='__main__':
    spec=json.loads((HERE.parent/'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    value=json.loads(ssh('python3 -B -','WAKE_REQUIRED='+repr(spec.get('wake_word_required',True))+'\n'+REMOTE,timeout=45))
    (HERE/'actual_control_semantics.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(value))
