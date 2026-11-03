import hashlib,json,subprocess,urllib.request
from pathlib import Path
def get(port,path):
 with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4) as r:return json.load(r)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
h=get(8790,'/health');u=get(8783,'/api/state');pid=h['pid']
d={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'camera_pid':pid,'camera_cmdline':(Path('/proc')/str(pid)/'cmdline').read_bytes().decode().split(chr(0)),'capture_hz':h.get('capture_hz'),'detection_hz':h.get('detection_hz'),'camera_error':h.get('camera_error'),'detector_error':h.get('detector_error'),'dpu_schedule':h['dpu_schedule'],'ui_activity':{k:u.get(k) for k in ['phase','audio_output_state','playing','pending_job','avatar_command_pending']},'manual_pan':{k:u.get('manual_pan',{}).get(k) for k in ['state','automatic_following','pulse_us','target_us']},'handsfree':{k:u.get('handsfree_dialogue',{}).get(k) for k in ['enabled','microphone_open']}}
base=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');m=json.loads((base/'meta.json').read_text());d['ops_state']=json.loads((base/'state.json').read_text());d['ops_sha']=sha(base/'boot_ops.py');d['ops_expected_sha']=m['source_pins']['boot_ops.py'];d['candidate_config_path']=m['candidate_config'];c=json.loads(Path(m['candidate_config']).read_text());d['candidate_config_sha']=sha(m['candidate_config']);d['native_execution']=c['native_execution'];d['checkpoint']=json.loads(Path(c['native_execution']['checkpoint_output']).read_text())
d['startup_marker']=json.loads(Path('/run/aura-display-startup.json').read_text())
d['display_config_files']={str(p):{'sha256':sha(p),'text':p.read_text()} for p in Path('/etc/X11/xorg.conf.d').glob('*.conf') if 'aura' in p.name}
d['services_enabled']={s:subprocess.run(['systemctl','is-enabled',s],stdout=subprocess.PIPE,text=True).stdout.strip() for s in ['aura-camera-ui.service','aura-avatar-ui.service']}
print(json.dumps(d))
