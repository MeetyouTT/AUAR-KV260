"""Readonly dynamic baseline; preserve later GUI/mechanical releases exactly."""
import datetime,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
script=r'''
import hashlib,json,re,subprocess,urllib.request
from pathlib import Path
def unit(name):
 raw=subprocess.check_output(['systemctl','show',name,'-p','ActiveState','-p','SubState','-p','MainPID','-p','ExecStart','-p','NRestarts'],text=True)
 return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)
v={'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'ui_service':unit('aura-avatar-ui.service'),
   'camera_service':unit('aura-camera-ui.service'),'read_only':True}
match=re.search(r'--config\s+([^ ;]+)',v['ui_service']['ExecStart']);assert match,'No actual launcher config'
path=Path(match[1]);cfg=json.loads(path.read_text());root=Path(cfg['runtime'])
v.update(actual_config=str(path),actual_runtime=str(root),config_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),pins=cfg['component_sha256'])
v['hash_mismatches']=[n for n,h in v['pins'].items() if hashlib.sha256((root/'aura'/n).read_bytes()).hexdigest()!=h]
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as response:s=json.load(response)
pan=s.get('manual_pan',{});hf=s.get('handsfree_dialogue',{})
v['phase']=s.get('phase');v['playing']=s.get('playing');v['audio_output_state']=s.get('audio_output_state');v['error']=s.get('error')
v['listening']=hf.get('enabled');v['microphone_open']=hf.get('microphone_open')
v['pan_keys']=sorted(pan)
v['pan']={k:pan.get(k) for k in ('state','pulse_us','automatic_following','busy','moving','active_motion','motion_active','error','fault_reason')}
v['settings']={k:s.get('ui_settings',{}).get(k) for k in ('available','pending','volume','muted')}
v['display']=s.get('avatar_display');v['portrait_offload']={k:s.get('portrait_offload',{}).get(k) for k in ('mode','selected','target_fps','fallback_fps','error')}
v['camera_epoch']=s.get('visual_session',{}).get('camera_epoch') if isinstance(s.get('visual_session'),dict) else None
v['preflight_ready']=bool(v['ui_service']['ActiveState']=='active' and not v['hash_mismatches'] and v['phase']=='IDLE'
 and v['playing'] is False and v['audio_output_state']=='IDLE_READY' and not v['error'] and v['listening'] is False and v['microphone_open'] is False
 and pan.get('automatic_following') is False and pan.get('state') in ('READY','FAULT','HOLD','IDLE','DISABLED')
 and not any(pan.get(k) for k in ('busy','moving','active_motion','motion_active')) and not v['settings']['pending'])
print(json.dumps(v))
'''
value=json.loads(ssh('python3 -B -',script,timeout=20))
value['checked_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(H/'board_baseline.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:value[k] for k in ('boot','actual_runtime','preflight_ready','pan','phase')}))
