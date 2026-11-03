import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
p=Path('/home/root/aura-audio-recovery-20261021/a0572918fbcedf0c/result.json')
r=json.loads(p.read_text());assert r.get('explicit_camera_restart_while_audio_closed')
assert r['protected_before']==r['protected_after'] and r['preference_sha_before']==r['preference_sha_after']
assert r['after']['xhci_warning_count']==0 and r['after']['journal_query_complete']
assert r['guard_timer_active']=='inactive'
assert r['units_before']['xserver-nodm.service']==r['units_after']['xserver-nodm.service']
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def camera():
 with op.open('http://127.0.0.1:8790/health',timeout=2) as f:return json.load(f)
first=camera();started=time.monotonic();time.sleep(5);last=camera();end=time.monotonic()
assert first['pid']==last['pid']==r['explicit_camera_restart_while_audio_closed']['after_pid']
assert last['detected_frames']>first['detected_frames'] and not last['camera_error'] and not last['detector_error']
face=last['identity']['face_targets'];assert face['backend']=='DPU_YUNET_INT8' and face['ready']
job=last['dpu_schedule']['optional']['yunet'];assert not job['disabled'] and job['overruns']==0
assert hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()=='84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c'
raw=subprocess.check_output(['journalctl','-k','-n','1000','-o','json','--no-pager'],timeout=5).decode();fresh=0;latest=None
for line in raw.splitlines():
 try:x=json.loads(line)
 except ValueError:continue
 if "HC couldn't access mem fast enough for slot 4 ep 3" in x.get('MESSAGE',''):
  t=int(x['__MONOTONIC_TIMESTAMP'])/1e6;latest=max(latest or 0,t);fresh+=int(t>=started)
assert fresh==0
print(json.dumps({'scope':'Read-only independent acceptance using SAME new camera PID count delta after controlled recovery order',
 'original_script_complete':r['complete'],'original_script_error':r.get('error'),
 'original_counter_comparison_crossed_camera_processes':r['camera_before']['pid']!=r['after']['camera']['pid'],
 'independent_acceptance_passed':True,'camera_pid':last['pid'],
 'ui_pid':r['units_after']['aura-avatar-ui.service']['MainPID'],'xserver_pid':r['units_after']['xserver-nodm.service']['MainPID'],
 'yolo_hz':(last['detected_frames']-first['detected_frames'])/(end-started),
 'backend':face['backend'],'optional_schedule':last['dpu_schedule'],
 'after_recovery_warning_count':r['after']['xhci_warning_count'],'fresh_warnings_in_current_tail_window':fresh,
 'latest_retained_warning_age_s':end-latest if latest else None,
 'protected_files_preferences_and_original_unit_preserved':True,'root_cause_fixed':False}))
