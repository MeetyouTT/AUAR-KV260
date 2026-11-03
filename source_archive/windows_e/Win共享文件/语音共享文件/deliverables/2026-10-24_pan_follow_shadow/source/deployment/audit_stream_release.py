"""Final read-only source, service and current checkpoint audit."""
import hashlib,json,subprocess,urllib.request
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');SH=OPS/'pan-follow-shadow-stream-v2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(port,path):
 o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def unit(n):
 v=subprocess.check_output(['systemctl','show',n,'-p','MainPID','-p','ActiveState','-p','Result','-p','Restart','-p','KillMode','-p','SendSIGKILL','-p','TimeoutStopUSec','-p','ExecStart'],text=True)
 return dict(x.split('=',1) for x in v.splitlines() if '=' in x)
s=json.loads((SH/'stage-state.json').read_text());m=json.loads((SH/'deployment-manifest.json').read_text());meta=json.loads((OPS/'meta.json').read_text())
assert all(sha(f['destination'])==f['sha256'] for f in m['files'])
assert all(sha(OPS/k)==v for k,v in meta['source_pins'].items())
assert sha(s['dropin'])==s['dropin_sha256']
app=Path(meta['candidate_root'])/'aura';assert sha(app/'board/vision/ui_camera_service.py')==meta['candidate_ui_sha256']
c=unit('aura-camera-ui.service');g=unit('aura-avatar-ui.service');h=get(8790,'/health');u=get(8783,'/api/state');d=h['dpu_schedule'];i=h['identity']
assert int(c['MainPID'])==h['pid']==s['camera_pid'] and c['ActiveState']=='active'
assert 'native_entry_pan_stream_v2.py' in c['ExecStart'] and c['Restart']=='no' and c['KillMode']=='process' and c['SendSIGKILL']=='no' and c['TimeoutStopUSec']=='infinity'
assert g['MainPID']==str(s['gui_pid']) and g['ActiveState']=='active' and u['phase']=='IDLE'
assert d['native_critical'] and not d['owner_fenced'] and i['face_targets']['worker_alive']
assert not u['manual_pan']['automatic_following']
cfg=json.loads(Path(meta['candidate_config']).read_text());cp=Path(cfg['native_execution']['checkpoint_output']);doc=json.loads(cp.read_text())
assert sha(cp)==s['checkpoint_sha256'] and doc['seed']['source_pid']==s['stop_source_pid']
assert doc['seed']['boot_id']==s['boot'] and not doc['seed']['fenced'] and not any(doc['auxiliary']['pending_result_tokens'])
print(json.dumps({'boot':s['boot'],'camera_pid':h['pid'],'gui_pid':int(g['MainPID']),
 'active_entry':'native_entry_pan_stream_v2.py','release_files_verified':len(m['files']),'native_source_pins_verified':len(meta['source_pins']),
 'camera_source_sha256':sha(app/'board/vision/ui_camera_service.py'),'dropin_sha256':sha(s['dropin']),
 'native_entry_original_sha256':sha(OPS/'native_entry.py'),'fresh_checkpoint_source_pid':doc['seed']['source_pid'],'fresh_checkpoint_sha256':sha(cp),
 'counter_handoff_same_boot_verified':True,'primary_overruns_current_domain':d['primary_period_overruns'],
 'source_and_checkpoint_audit_passed':True,'full_business_health_passed':bool(i['ready'] and all(not d['optional'][k]['disabled'] for k in ('yunet','sface'))),
 'identity_ready':i['ready'],'owner_fenced':d['owner_fenced'],'optional':{k:{'overruns':d['optional'][k]['overruns'],'disabled':d['optional'][k]['disabled'],'phase':d['optional'][k]['recovery']['phase']} for k in ('yunet','sface')},'manual_state':u['manual_pan']['state'],
 'manual_error':u['manual_pan'].get('error'),'firmware_name':Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode(),
 'physical_actuation_enabled':False,'register_access_by_audit':False},sort_keys=True))
