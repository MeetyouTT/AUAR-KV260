"""Audio-independent original motor entry; this step performs status reads only."""
STARTUP_SHA='ec12fccfdd3e8446e9c761e161167e00187e6fcf90372aa7e52c9865cc23c56f'
assert os.geteuid()==0 and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert digest(BUSINESS/'startup/config.json')==STARTUP_SHA
assert digest(BUSINESS/'production_source_manifest.json')=='b144536398bcaa6fdda2f36f9c14decced7e2f766f03e55714853674d8cfdd0d'
wide_active();verify_wide_files()
startup=document(BUSINESS/'startup/config.json');assert len(startup['component_sha256'])==380
assert all(digest(BUSINESS/'runtime/aura'/path)==pin for path,pin in startup['component_sha256'].items())
pref=document('/home/root/.local/share/aura-board-business/listening_preference.json');assert pref==dict(version=1,enabled=False)
unit=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=MainPID,ActiveState,Job'],capture_output=True,text=True,timeout=4)
u=dict(line.split('=',1) for line in unit.stdout.splitlines() if '=' in line)
assert u['MainPID']=='0' and not u.get('Job')
control=Path('/home/root/aura-pan-wide-20261028/control-10282601')
assert digest(control/'deployment-manifest.json')=='5c8206ee626c91c9f311ee870245813e169ac14e554e2579554c74489066f562'
consumer=document(control/'deployment-manifest.json');assert len(consumer['files'])==25
assert all(digest(row['destination'])==row['sha256'] for row in consumer['files'])
manual=document(BUSINESS/'runtime/aura/config/pan_manual.local.json');face=document(manual['face_follow_config'])
assert Path(face['release_root'])==control
direction=document(face['arguments']['direction-evidence']);assert direction['axis_camera_mirrored_control_polarity']==1
for process in Path('/proc').iterdir():
 if not process.name.isdigit():continue
 try:args=(process/'cmdline').read_bytes().split(b'\0')
 except OSError:continue
 assert str(control/'run_face_motion.py').encode() not in args,'existing_motion_runner'
 assert str(BUSINESS/'runtime/aura/tools/board_avatar_pan.py').encode() not in args,'existing_gui_owner'
h=get_json(8790,'/health');pid=h['pid'];proc=Path('/proc')/str(pid)
owner=dict(pid=pid,birth_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),command_sha256=digest(proc/'cmdline'))
assert owner==dict(pid=430894,birth_ticks=4011213,command_sha256='acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd')
assert h['camera_error']==h['detector_error']==h['identity']['error']==''
assert h['dpu_schedule']['owner_fenced'] is False
sys.path.insert(0,str(RELEASE/'driver'))
from vsrv_driver import VSRVDriver
from vsrv_transport import NativeRegisters
manifest=document(RELEASE/'candidate-manifest.json')
with NativeRegisters(RELEASE/'driver/libvsrv.so',manifest['payload_files']['libvsrv.so'],BOOT,manifest['runtime_files']) as io:
 rb=VSRVDriver(io,0x10282601,BOOT).status()
assert rb['flags']==0 and rb['lease_left_ms']==0 and rb['active'] is False and rb['armed'] is False
observations=[]
for _ in range(3):
 p=get_json(8790,'/v1/motion/face/observation');box=(p.get('target') or {}).get('box');width=p.get('frame_width')
 center=(box[0]+box[2]/2)/width if box and width else None
 observations.append(dict(state=p.get('state'),source_frame_id=p.get('source_frame_id'),source_age_ms=round(time.monotonic()*1000)-p['source_mono_ms'] if type(p.get('source_mono_ms')) is int else None,
   face_center_ratio=center,face_left_ratio=box[0]/width if box and width else None))
 time.sleep(.15)
result=dict(status='AXIS_CAMERA_ORIGINAL_CONTROLLER_READY_NO_MOTION',observed_mono=time.monotonic(),boot=BOOT,
 startup_sha256=STARTUP_SHA,source_closure_380_match=True,camera_owner=owner,camera_errors_clear=True,
 original_controller_25_match=True,controller_root=str(control),control_polarity=1,firmware=firmware(),
 readback=rb,saved_microphone_enabled=False,gui_main_pid=0,observations=observations,
 current_zone=document(face['arguments']['zone-settings']),original_entry_arguments=face['arguments'],
 original_human_reference=document(face['arguments']['human-evidence']),motor_commands_sent=False,
 physical_angle_or_zero_measured=False)
print(json.dumps(result,allow_nan=False))
