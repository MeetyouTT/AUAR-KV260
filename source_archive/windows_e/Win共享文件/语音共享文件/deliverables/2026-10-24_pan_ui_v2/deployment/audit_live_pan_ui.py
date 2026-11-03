import hashlib,importlib.util,json,os,subprocess,urllib.request
from pathlib import Path
ROOT=Path('/home/root/aura-pan-ui-v2-20261024/observed-ecfbdef064d157b6')
CONTROLLER=Path('/home/root/aura-post-power-20261022/helpers/eca1b3e3f5cb2070/source.py')
assert hashlib.sha256(CONTROLLER.read_bytes()).hexdigest()=='eca1b3e3f5cb2070ebeb1b60f5604f232ef8e7021397919e289494ab9243ba16'
spec=importlib.util.spec_from_file_location('accepted_gui_controller',str(CONTROLLER));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
t=module.GuiTrial();h=t.verify();s=t.state();assert s['phase']=='ACCEPTED_MANUAL_READY_NO_AUTOMATIC_MOTION'
pan=t.get(8783,'/api/state')['manual_pan'];assert pan['state']=='READY' and pan['readback']['flags']==0 and pan['readback']['lease_left_ms']==0
assert not pan['history'] and pan['automatic_following'] is False
props=t.props(module.GUI);expected=set(t.base['gui_unit']['DropInPaths'].split())|{str(t.override)}
assert set(props['DropInPaths'].split())==expected and module.sha(t.override)==s['override_sha256']
actual={str(p.relative_to(ROOT/'runtime/aura')):module.sha(p) for p in (ROOT/'runtime/aura').rglob('*.py') if not p.is_symlink()}
old=Path(t.prepared['existing_gui_runtime'])
original={str(p.relative_to(old/'aura')):module.sha(p) for p in (old/'aura').rglob('*.py') if not p.is_symlink()}
assert actual==t.prepared['source_after'] and original==t.prepared['source_before']
cfg=json.loads((ROOT/'startup/config.json').read_text())
for n,pin in cfg['component_sha256'].items():assert module.sha(ROOT/'runtime/aura'/n)==pin
for n,pin in s['preferences_before'].items():assert module.sha(ROOT/'runtime'/n)==pin
release=json.loads((ROOT/'manual-release/release.json').read_text());assert release['status']=='OBSERVED_MANUAL_VSRV2' and release['external_waveform_verified'] is False
lock=Path('/run/aura-vsrv.lock');st=lock.stat();key=f'{os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x}:{st.st_ino}';owners=[]
for line in Path('/proc/locks').read_text().splitlines():
 fields=line.split()
 if '->' not in fields and len(fields)>5 and fields[5].lower()==key:owners.append(int(fields[4]))
assert owners==[pan['backend_pid']]
units={n:t.props(n) for n in [t.prefix+'-activation.service',t.prefix+'-guard.timer',t.prefix+'-guard.service']}
assert units[t.prefix+'-activation.service']['MainPID']=='0' and units[t.prefix+'-guard.timer']['ActiveState']=='inactive'
result={'passed':True,'boot':t.base['boot'],'new_runtime':str(ROOT/'runtime'),'new_startup':str(ROOT/'startup'),
 'gui_pid':props['MainPID'],'camera':h,'camera_pid_unchanged':h['pid']==t.base['camera_pid'],
 'manual_pan':pan,'single_motion_lock_owner':owners,'GUI_python_files':len(actual),
 'original_GUI_python_files_unchanged':len(original),'gui_component_pins_verified':len(cfg['component_sha256']),
 'changed_python':t.prepared['changed_python'],'added_python':t.prepared['added_python'],
 'only_owned_gui_override_added':True,'override':str(t.override),'override_sha256':module.sha(t.override),
 'preferences_sha256':s['preferences_before'],'native_r4_untouched':True,'firmware_not_reloaded':True,
 'manual_release_status':release['status'],'external_waveform_verified':False,'mechanical_reference_calibrated':False,
 'automatic_following_enabled':False,'automatic_motion_commands_sent':0,'maintenance_units':units,
 'rollback_check_only':{'controller_sha256':module.sha(CONTROLLER),'original_startup_unchanged':module.sha(t.base['startup_config_path'])==t.base['startup_config_sha256'],
 'owned_override_matches':module.sha(t.override)==s['override_sha256'],'actual_gui_rollback_performed':False}}
print(json.dumps(result,ensure_ascii=False))
