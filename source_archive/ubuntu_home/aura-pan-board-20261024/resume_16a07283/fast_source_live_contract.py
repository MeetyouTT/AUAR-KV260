import hashlib,json,subprocess,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/face-source-v16')
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as f:return json.load(f)
s=json.loads((R/'state.json').read_text());h=get(8790,'/health');u=get(8783,'/api/state');p=get(8790,'/v1/motion/face/observation')
face=h['identity']['face_targets'];assert h['pid']==s['current_camera_pid'] and h['identity']['ready']
assert face['ready'] and not face['fault_latched'] and not face['error'] and face['backend']=='DPU_YUNET_INT8'
assert not h['dpu_schedule']['owner_fenced'] and all(not h['dpu_schedule']['optional'][k]['disabled'] for k in ('yunet','sface'))
stages=p.get('detector_stages',{});assert 'fast_input_encode' in stages.get('stages',{}) and 'fast_network_forward' in stages.get('stages',{})
m=u['manual_pan'];assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
assert all(hashlib.sha256(Path(n).read_bytes()).hexdigest()==v for n,v in json.loads((P/'deployment-manifest.json').read_text())['pins'].items())
print(json.dumps({'status':'FAST_INPUT_LIVE_NATIVE_CONTRACT_PASS','camera_pid':h['pid'],'gui_pid':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip(),
 'face_backend':face['backend'],'face_worker_faults':face['worker_faults'],'current_face_state':p['state'],
 'stages':stages,'detector_timing':p.get('detector_timing'),'manual_readback':m['readback'],'preview':u['ui_runtime'].get('preview_metrics'),
 'primary_overruns':h['dpu_schedule']['primary_period_overruns'],'optional_overruns':{k:h['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')},'actuator_commands':0}))
