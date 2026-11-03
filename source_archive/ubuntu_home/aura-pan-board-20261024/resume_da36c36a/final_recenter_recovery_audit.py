import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/da36c36a');G=R/'gui-reference-bound-v2';A=G/'runtime/aura'
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v11r1')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(P/'deployment-manifest.json')=='524ad777aec14dc2d853708412bcef4f75e1e6937d528674cc154b361b8ce76d'
assert all(sha(x['destination'])==x['sha256'] for x in json.loads((P/'deployment-manifest.json').read_text())['files'])
startup=json.loads((G/'startup/config.json').read_text());assert all(sha(A/n)==v for n,v in startup['component_sha256'].items())
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as f:return json.load(f)
samples=[]
for _ in range(5):
 h=get(8790,'/health');u=get(8783,'/api/state');m=u['manual_pan'];v=u['ui_runtime']['preview_metrics']
 samples.append(dict(camera_pid=h['pid'],capture_frames=h['capture_frames'],preview_frame_id=(v.get('frame_reference') or {}).get('frame_id'),
  preview_error=v.get('error'),preview_active=v.get('sink_active'),automatic_following=m['automatic_following'],primary_overruns=h['dpu_schedule']['primary_period_overruns']))
 time.sleep(1)
assert len({x['capture_frames'] for x in samples})==5 and len({x['preview_frame_id'] for x in samples})==5
assert all(x['preview_active'] and not x['preview_error'] for x in samples)
follow=m.get('face_follow') or {};report=None
if follow.get('report'):
 p=Path(follow['report']);p.relative_to(P/'runs');report=json.loads(p.read_text())
 assert report['consumer_manifest_sha256']==sha(P/'deployment-manifest.json')
control=(report or {}).get('result',{}).get('control') or {}
assert control.get('recenter_on_edge') is True and control.get('target_center_ratio')==.5
display=json.loads((R/'face-zone-display-status.json').read_text())
result=dict(status='VIDEO_RECOVERED_V11_RECENTER_RUNNING' if m['automatic_following'] else 'VIDEO_RECOVERED_V11_RECENTER_STOPPED',
 boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),camera_pid=h['pid'],
 gui_pid=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True)),
 controller='continuous-v11r1',controller_manifest_sha256=sha(P/'deployment-manifest.json'),control_files=24,gui_pins=len(startup['component_sha256']),
 automatic_following=m['automatic_following'],manual_state=m['state'],samples=samples,display=display,
 controller_state=(report or {}).get('result'),control_parameters=(report or {}).get('control_parameters'),
 input_summary=(report or {}).get('input_summary'),report=follow.get('report'),
 primary_overruns=h['dpu_schedule']['primary_period_overruns'],optional_overruns={k:v['overruns'] for k,v in h['dpu_schedule']['optional'].items()},
 identity_ready=h['identity']['ready'],mechanical_angle_measured=False,physical_recenter_smoothness_accepted=False,
 operator_feedback_after_replug='朝向没有变，已连接好线，继续任务',animation_dialogue_base_preserved='d6d1617467724213b3d9fd3d11530a47',
 audit_motion_commands=0)
(R/'current-recenter-status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result))
