import hashlib,json,subprocess,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
root=Path('/home/root/aura-video-cpu-20261023/66cde810eb059dce')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(root/'gui_trial.py')=='1b782de0126abbbe6550050e41bfb2db22137449daf0c779285279e8cfee12b3'
sys.path.insert(0,str(root));import gui_trial as g
meta=json.loads((root/'session.json').read_text());g.verify(root,meta)
assert meta['camera_pid']==588727
recovery=Path('/home/root/aura-native-wait-20261023/recovery/cdb172e26c91629f/report.json')
prior=json.loads(recovery.read_text());assert prior['complete'] and prior['passed']
camera=g.camera();assert camera['pid']==588727
g.retained().single_owner(camera['pid'])
accepted=json.loads((root/'report.json').read_text());runtime=Path(accepted['runtime'])
sources={str(p.relative_to(runtime/'aura')):sha(p) for p in (runtime/'aura').rglob('*.py') if '__pycache__' not in p.parts}
assert sources==accepted['gui_sources_after']
services={}
for unit in (g.CAMERA,g.GUI,'xserver-nodm.service'):
    raw=g.command(['systemctl','show',unit,'-p','MainPID','-p','ActiveState','-p','NRestarts'])
    services[unit]=dict(line.split('=',1) for line in raw.splitlines())
    assert services[unit]['ActiveState']=='active'
assert services[g.CAMERA]['MainPID']=='588727' and services[g.GUI]['MainPID']=='588755'
state=g.ui()
units=['aura-external-sched-216391c02cc6e719.service','aura-availability-recovery-cdb172e26c91629f.service',
       prior['guard']+'.timer','aura-video-trial-66cde810eb059dce.service',meta['guard']+'.timer']
states={unit:g.prop(unit,'ActiveState') for unit in units}
paths={
'identity_config':'/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-sface-int8-9025bd49fe52-333217/board_identity.sface_int8.json',
'identity_database':'/home/root/.local/share/aura/sface-int8-12b2ff5c7de15713-333217.sqlite3',
'old_windows_database':'/home/root/.local/share/aura/identities.sqlite3',
'vart':'/usr/lib/python3.9/site-packages/vart.so'}
checks={name:sha(path) for name,path in paths.items()}
passed=(camera['identity_ready'] and camera['worker_alive'] and not camera['worker_faults']
        and camera['face_backend']=='DPU_YUNET_INT8' and not camera['owner_fenced']
        and all(not row['disabled'] for row in camera['optional'].values())
        and all(value=='inactive' for value in states.values()))
print(json.dumps({'read_only':True,'passed':passed,'snapshot_mono_ns':time.monotonic_ns(),
'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'services':services,'current_camera':camera,
'unit_sha256':sha(g.UNIT),'gui_runtime':str(runtime),'gui_python_files_verified':len(sources),
'source_hashes':checks,'preference_sha256':sha(g.PREF),'rollback_check':g.restore(root,'check'),
'gui_session_camera_pid':meta['camera_pid'],'unit_states':states,
'ui':{key:state.get(key) for key in ('phase','audio_output_state','playing','paused','ui_page')},
'microphone_open':state.get('handsfree_dialogue',{}).get('microphone_open'),
'preview':state.get('ui_runtime',{}).get('preview_metrics'),'avatar':state.get('avatar_display'),
'usb_audio_warning_delta_since_recovery':g.retained().audio_warnings(prior['kernel_cursor']),
'counter_scope':'Same new camera PID after one explicit recovery; prior process faults remain archived'}))
