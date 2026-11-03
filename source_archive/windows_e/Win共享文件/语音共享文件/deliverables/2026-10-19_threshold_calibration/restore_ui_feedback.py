"""Reload idle existing UI after PC recovery so feedback/start readiness recovers."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((ROOT/'deliverables/2026-10-19_windows_face_features/candidate.json').read_text(encoding='utf-8'))
remote=r'''
import json,subprocess,time,urllib.request
from pathlib import Path
c=CANDIDATE
get=lambda port,path,host='127.0.0.1':json.load(urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=4))
pc=get(8792,'/health','192.168.50.1');assert pc['ready'] and pc['identity_features']['ready'] and not pc['busy']
before=get(8783,'/api/state');assert before['phase']=='IDLE' and not before['playing']
assert not before['automatic_conversation']['enabled'] and before['local_recording']['state']!='RECORDING'
assert not before['local_transcription']['service']['pending']
camera=get(8790,'/health');unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
assert c['startup']+'/config.json' in unit
args=Path('/proc/%d/cmdline'%camera['pid']).read_bytes().decode().split('\0')
config_path=Path(args[args.index('--config')+1]);cfg=json.loads(Path(json.loads(config_path.read_text())['identity']['config']).read_text())
assert cfg['threshold']==.8
if before['automatic_conversation']['can_start']:
 result={'status':'UI_FEEDBACK_ALREADY_READY','ui_restarted':False,'current_camera_pid':camera['pid']}
else:
 old_pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','--property=MainPID','--value'],text=True).strip()
 subprocess.run(['systemctl','restart','--no-block','aura-avatar-ui.service'],check=True,capture_output=True,text=True,timeout=20)
 deadline=time.monotonic()+190
 while time.monotonic()<deadline:
  try:
   after=get(8783,'/api/state')
   if (after['phase']=='IDLE' and after['audio_output_state']=='IDLE_READY'
       and after['automatic_conversation']['can_start']):break
  except (OSError,KeyError,ValueError):pass
  time.sleep(1)
 else:raise RuntimeError('Existing UI did not recover feedback readiness')
 after_camera=get(8790,'/health');assert after_camera['pid']==camera['pid']
 assert subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)==unit
 new_pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','--property=MainPID','--value'],text=True).strip()
 assert new_pid!=old_pid
 result={'status':'IDLE_UI_FEEDBACK_RESTORED','ui_restarted':True,'old_ui_pid':old_pid,'new_ui_pid':new_pid,
   'current_camera_pid':camera['pid'],'camera_not_restarted':True}
final=get(8783,'/api/state');result.update(client_date='2026-10-19',threshold=.8,
 automatic_can_start=final['automatic_conversation']['can_start'],automatic_enabled=final['automatic_conversation']['enabled'],
 ui_phase=final['phase'],feedback_ready=final['local_transcription']['service']['feedback_ready'],
 feedback_error=final['local_transcription']['service']['feedback_error'],recording_started=False,playback_started=False,
 models_or_settings_changed=False,identity_database_written=False)
print(json.dumps(result))
'''.replace('CANDIDATE',repr(c),1)
r=json.loads(ssh('python3 -B -',remote,timeout=230))
(HERE/'threshold_080_ui_recovery.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=True))
