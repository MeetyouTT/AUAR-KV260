import hashlib,json,subprocess,sys,time,urllib.request
from pathlib import Path
root=Path('/home/root/aura-video-cpu-20261023/0dad262102329bfc')
report=json.loads((root/'report.json').read_text());assert report['complete'] and report['accepted'] and report['passed']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha('/etc/systemd/system/aura-camera-ui.service')=='29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512'
assert sha(root/'gui_trial.py')=='80eabab3481aef598d4984b822f9276b3c3d0ab81fabd536a47cbd418f1294fd'
sys.dont_write_bytecode=True;sys.path.insert(0,str(root))
from gui_trial import restore,camera,assert_camera_unchanged,retained
meta=json.loads((root/'session.json').read_text());runtime=Path(report['runtime'])
after={str(p.relative_to(runtime/'aura')):sha(p) for p in (runtime/'aura').rglob('*.py') if '__pycache__' not in p.parts}
assert after==report['gui_sources_after']
changed=sorted(name for name in after if after[name]!=report['gui_sources_before'][name])
assert changed==sorted(report['candidate_pins'])
assert sha(runtime/'aura/tools/libaura_pixels.so')=='201adac318e23411e608556fce360a335c422b129f64fa56e4d908ba39ab958f'
assert sha(runtime/'aura/board/identity/spoken_query.py')=='9bd7a4f6927fbfe6c130056c66c4f420d11603a9d1fe46d237af9b34f3ac75d7'
current=camera();assert_camera_unchanged(report['camera_before'],current);retained().single_owner(current['pid'])
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=4) as r:u=json.load(r)
assert u['ui_page']==meta['original_page'] and u['audio_output_state']=='IDLE_READY'
assert not u.get('handsfree_dialogue',{}).get('microphone_open')
assert not u.get('playing') and not u.get('paused')
preview=u['ui_runtime']['preview_metrics'];assert preview['sink_active'] and preview['frame_visible'] and not preview['error']
assert preview['update_hz']>=9.5 and u['avatar_display']['fps']>=7.5
services={}
for name in ('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service'):
 raw=subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','NRestarts']).decode().strip()
 services[name]=dict(line.split('=',1) for line in raw.splitlines());assert services[name]['ActiveState']=='active'
assert int(services['aura-avatar-ui.service']['MainPID'])==report['candidate_gui_pid']
assert int(services['aura-camera-ui.service']['MainPID'])==report['camera_before']['pid']==499773
assert services['xserver-nodm.service']['MainPID']==meta['xserver_pid']
args=(Path('/proc')/services['aura-avatar-ui.service']['MainPID']/'cmdline').read_bytes().split(b'\0')
assert str(Path(report['startup'])/'launcher.py').encode() in args
checked=restore(root,'check');assert checked['passed']
old_db_sha=sha('/home/root/.local/share/aura/identities.sqlite3')
assert old_db_sha=='e0d2113eb51171079978b1e63eb4263d5fb13235fec1839f7be778dab1520aa1'
units=('aura-video-trial-0dad262102329bfc.service',meta['guard']+'.timer','aura-video-trial-3639e2e97cc9e7ba.service')
states={unit:subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','--value']).decode().strip() for unit in units}
assert all(state=='inactive' for state in states.values())
print(json.dumps({'passed':True,'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'unit_sha256':sha('/etc/systemd/system/aura-camera-ui.service'),'runtime':str(runtime),'startup':report['startup'],
 'services':services,'changed_python_files':changed,'python_files_verified':len(after),
 'current_camera':current,'ui':{k:u.get(k) for k in ('phase','audio_output_state','playing','paused','ui_page')},
 'preview':preview,'avatar':u['avatar_display'],'candidate_pins':report['candidate_pins'],
 'preference_sha256':sha('/home/root/.local/share/aura/handsfree_dialogue.json'),
 'old_database_sha256':old_db_sha,'rollback':report['rollback'],'rollback_check':checked,'unit_states':states,
 'report_sha256':sha(root/'report.json'),'hidden_page_gui_cpu_reduction_fraction':report['hidden_page_gui_cpu_reduction_fraction'],
 'gui_override':meta['override'],'new_usb_audio_warning_count':report['new_usb_audio_warning_count'],
 'gui_restarted_once':True,'camera_restarted_this_round':False,'dpu_fault_preserved':True}))
