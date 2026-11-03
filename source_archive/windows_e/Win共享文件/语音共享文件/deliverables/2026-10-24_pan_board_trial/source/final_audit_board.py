import hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path('/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4-r2')
CONTROLLER=Path('/home/root/aura-post-power-20261022/helpers/ded9704ecc463a50/source.py')
assert hashlib.sha256(CONTROLLER.read_bytes()).hexdigest()=='ded9704ecc463a5040ff59056efa71321eb104b6aa0d9f047e9e80fb14662c45'
spec=importlib.util.spec_from_file_location('owned_pan_audit',str(CONTROLLER))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
t=module.Trial(ROOT);t.verify();state=t.state()
assert state['phase']=='CANDIDATE_STOPPED_RETAINED_PHYSICAL_FEEDBACK_PENDING'
assert t.active()==[module.APP] and t.firmware()==module.APP+'.bit.bin'
manifest=t.manifest
for name,pin in manifest['runtime_files'].items():assert module.sha(name)==pin
config=json.loads(Path(t.base['camera_config']).read_text());native=config['native_execution']
source_manifest=Path(native['source_manifest']);assert module.sha(source_manifest)==native['source_manifest_sha256']
sources=json.loads(source_manifest.read_text())['files'];camera_root=Path(t.base['services'][module.CAMERA]['WorkingDirectory'])
actual={str(p.relative_to(camera_root)):module.sha(p) for p in camera_root.rglob('*.py') if not p.is_symlink()}
assert sources==actual
assert module.sha(native['library'])==native['library_sha256']
gui=json.loads(Path(t.base['gui_config']).read_text());gui_root=Path(gui['runtime'])/'aura'
assert module.sha(gui_root/'tools/board_avatar_pan.py')==gui['gui_sha256']
for name,pin in gui['component_sha256'].items():assert module.sha(gui_root/name)==pin
h=t.brief(t.get(8790,'/health'));g=t.get(8783,'/api/state')
assert h['native_critical'] and not h['owner_fenced'] and h['worker_alive'] and h['identity_ready']
assert all(not h['optional'][k]['disabled'] for k in ['yunet','sface'])
sys.path.insert(0,str(ROOT/'driver'))
from vsrv_transport import NativeRegisters
from vsrv_driver import VSRVDriver
with NativeRegisters(ROOT/'driver/libvsrv.so',manifest['payload_files']['libvsrv.so'],t.base['boot_id'],manifest['runtime_files']) as io:
    d=VSRVDriver(io,0x778d2512,t.base['boot_id']);registers=d.status()
    assert registers['flags']==0 and registers['lease_left_ms']==0 and registers['width_us']==1425
    stopped=d.stop()
units={name:t.props(name) for name in [module.CAMERA,module.GUI,t.prefix+'-activation.service',t.prefix+'-guard.timer',t.prefix+'-guard.service']}
assert units[t.prefix+'-activation.service']['MainPID']=='0'
assert units[t.prefix+'-guard.timer']['ActiveState']=='inactive'
result={'passed':True,'boot_id':t.base['boot_id'],'firmware':t.firmware(),'active_app':t.active(),
 'camera':h,'gui':{k:g.get(k) for k in ['phase','audio_output_state','playing']},
 'gui_manual_pan':{k:g.get('manual_pan',{}).get(k) for k in ['state','error','pulse_us','automatic_following']},
 'services':units,'registers_before':registers,'registers_final':stopped,'camera_source_files_verified':len(actual),
 'native_library_sha256':native['library_sha256'],'camera_config_sha256':module.sha(t.base['camera_config']),
 'gui_config_sha256':module.sha(t.base['gui_config']),'gui_entry_sha256':gui['gui_sha256'],
 'gui_main_sha256':module.sha(gui_root/'tools/board_avatar_gtk.py'),
 'gui_component_pins_verified':len(gui['component_sha256']),
 'identity_database_sha256':module.sha(t.base['database_path']),'original_existing_service_files_unchanged':True,
 'gui_source_unchanged':True,'activation_and_guard_exited':True,'new_ARM_or_COMMIT_sent':False,
 'physical_observation_pending':True,'external_waveform_verified':False,
 'automatic_following_enabled':False,'product_pan_driver_migrated':False,
 'board_wall_clock_untrusted':True}
print(json.dumps(result))
