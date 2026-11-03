"""Read current owners and configuration before an operator-requested power test."""
import hashlib,json,subprocess,urllib.request
from pathlib import Path
def get(port,path):
    with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4) as r:return json.load(r)
def props(unit):
    s=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','Result','-p','ExecMainStatus','-p','Restart','-p','KillMode','-p','SendSIGKILL','-p','TimeoutStopUSec','-p','FragmentPath'],text=True,timeout=4)
    return dict(v.split('=',1) for v in s.splitlines() if '=' in v)
def owner(unit):
    v=props(unit);pid=int(v['MainPID']);assert pid>0
    p=Path('/proc')/str(pid);args=(p/'cmdline').read_bytes().decode().split(chr(0))
    birth=int((p/'stat').read_text().rsplit(')',1)[1].split()[19])
    cfg=Path(args[args.index('--config')+1]) if '--config' in args else Path(json.loads(Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/meta.json').read_text())['candidate_config'])
    raw=cfg.read_bytes()
    return {'unit':v,'pid':pid,'birth':birth,'config':str(cfg),'config_sha256':hashlib.sha256(raw).hexdigest(),'unit_sha256':hashlib.sha256(Path(v['FragmentPath']).read_bytes()).hexdigest(),'entry':args[2],'entry_sha256':hashlib.sha256(Path(args[2]).read_bytes()).hexdigest()}
h=get(8790,'/health');u=get(8783,'/api/state')
d={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'camera':owner('aura-camera-ui.service'),'gui':owner('aura-avatar-ui.service')}
d['camera_health']={k:h.get(k) for k in ['pid','capture_frames','capture_hz','detection_hz','camera_error','detector_error']}
d['schedule']={k:h['dpu_schedule'].get(k) for k in ['native_critical','owner_fenced','primary_calls','primary_period_overruns']}
d['optional']={k:{f:v.get(f) for f in ['calls','overruns','disabled']} for k,v in h['dpu_schedule']['optional'].items()}
d['ui']={k:u.get(k) for k in ['phase','audio_output_state','playing','pending_job','ui_page']}
d['pan']={k:u['manual_pan'].get(k) for k in ['state','automatic_following','pulse_us']}
d['handsfree']={k:u['handsfree_dialogue'].get(k) for k in ['enabled','microphone_open']}
d['recording_state']=u['local_recording']['state'];d['transcription_pending']=u['local_transcription'].get('service',{}).get('pending')
c=json.loads(Path(d['camera']['config']).read_text());d['checkpoint_output']=c['native_execution']['checkpoint_output']
d['operation_lock_exists']=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/operation.lock').exists()
d['camera_entry_source']=Path(d['camera']['entry']).read_text()
print(json.dumps(d))
