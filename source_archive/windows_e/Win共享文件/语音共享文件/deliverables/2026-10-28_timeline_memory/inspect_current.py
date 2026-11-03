"""Read-only revalidation after a physical reconnect/reboot, without changing any binding."""
import datetime,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
candidate=json.loads((H.parent/'2026-10-28_device_skills/candidate.json').read_text(encoding='utf-8'))
script=r'''
import hashlib,json,re,subprocess,sys,urllib.request
from pathlib import Path
c=CANDIDATE
def show(unit):
 raw=subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','-p','SubState','-p','MainPID','-p','ExecStart','-p','NRestarts'],text=True)
 return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
v={'boot':boot,'prior_boot':c['boot'],'rebooted':boot!=c['boot'],
 'uptime_seconds':float(Path('/proc/uptime').read_text().split()[0]),'ui_service':show('aura-avatar-ui.service'),
 'camera_service':show('aura-camera-ui.service'), 'read_only':True,'microphone_enabled_by_probe':False,'motion_command':False}
command=v['ui_service']['ExecStart'];match=re.search(r'--config\s+([^ ;]+)',command)
if not match:raise ValueError('No readable config in actual UI entry')
config_path=Path(match[1]);cfg=json.loads(config_path.read_text());root=Path(cfg['runtime'])
v['actual_runtime']=str(root);v['actual_config']=str(config_path)
v['expected_entry']=str(root)==c['runtime'] and str(config_path.parent)==c['startup']
v['component_pins_unchanged']=cfg['component_sha256']==c['pins']
v['hash_mismatches']=[n for n,h in cfg['component_sha256'].items() if hashlib.sha256((root/'aura'/n).read_bytes()).hexdigest()!=h]
v['component_count']=len(cfg['component_sha256'])
try:
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as f:s=json.load(f)
 v['ui']={k:s.get(k) for k in ('phase','playing','error','audio_output_state','handsfree_dialogue','device_observer','visual_social','portrait_offload','avatar_display')}
 v['mechanical']={k:s.get('manual_pan',{}).get(k) for k in ('state','pulse_us','automatic_following','error','fault_reason')}
 v['mixer']={k:s.get('ui_settings',{}).get(k) for k in ('available','pending','volume','muted')}
except Exception as exc:v['ui_error']=type(exc).__name__+': '+str(exc)[:200]
v['windows_from_board']={}
for name,port in (('asr',8791),('dialogue',8792),('devices',8812)):
 try:
  with urllib.request.urlopen('http://192.168.50.1:%d/health'%port,timeout=3) as f:r=json.load(f)
  v['windows_from_board'][name]={k:r[k] for k in ('ready','busy','service_revision','source_fingerprint','speaker_ready','speaker_calibrated','visual_error') if k in r}
 except Exception as exc:v['windows_from_board'][name]={'error':type(exc).__name__+': '+str(exc)[:160]}
if v['expected_entry'] and not v['hash_mismatches']:
 try:
  sys.path.insert(0,str(root/'aura'))
  from board.runtime.visual_capture import current_frame
  frame,jpeg=current_frame(boot)
  v['camera_frame']={'board_boot_id':frame['board_boot_id'],'camera_epoch':frame['camera_epoch'],'frame_id':frame['frame_id'],
    'bytes':len(jpeg),'age_at_capture_ms':frame['observed_mono_ms']-frame['captured_mono_ms']}
 except Exception as exc:v['camera_error']=type(exc).__name__+': '+str(exc)[:200]
v['audio_cards']=Path('/proc/asound/cards').read_text() if Path('/proc/asound/cards').exists() else None
v['journal']=subprocess.check_output(['journalctl','-b','-u','aura-avatar-ui.service','-n','12','--no-pager'],text=True)
print(json.dumps(v))
'''.replace('CANDIDATE',repr(candidate))
v=json.loads(ssh('python3 -B -',script,timeout=35))
v['checked_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
ui=v.get('ui',{});hf=ui.get('handsfree_dialogue',{});pan=v.get('mechanical',{})
v['ready_for_readonly_completion']=bool(v['expected_entry'] and v['component_pins_unchanged'] and not v['hash_mismatches']
 and v['ui_service']['ActiveState']=='active' and ui.get('phase')=='IDLE' and ui.get('audio_output_state')=='IDLE_READY'
 and not ui.get('error') and hf.get('enabled') is False and hf.get('microphone_open') is False
 and hf.get('entry_mode')=='wake_word' and hf.get('visual_required') is False
 and pan.get('automatic_following') is False and pan.get('state')=='FAULT' and pan.get('pulse_us') is None
 and ui.get('portrait_offload',{}).get('mode')=='remote' and 'camera_frame' in v
 and v['windows_from_board'].get('dialogue',{}).get('service_revision')=='voice-timeline-20261028-r1'
 and v['windows_from_board'].get('dialogue',{}).get('ready') is True
 and v['windows_from_board'].get('devices',{}).get('speaker_ready') is True)
target=H/'runtime_current.json';target.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(v,ensure_ascii=True))
