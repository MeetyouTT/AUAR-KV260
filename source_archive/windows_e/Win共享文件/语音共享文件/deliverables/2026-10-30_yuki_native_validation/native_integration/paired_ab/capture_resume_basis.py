"""Refresh task-owned boot/PID metadata after a read-only current-source audit.

Run only after the coordinator reopens the resource window. No production
configuration, services, identity payloads or device state are changed.
"""
from pathlib import Path
import hashlib,json,subprocess,urllib.request

phase=Path('/home/root/aura-yuki-validation-20261030/native_integration')
ab=phase/'paired_ab'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
basis_path=phase/'board_source/manifest.json';baseline_path=ab/'fresh-baseline.json'
basis=read(basis_path);baseline=read(baseline_path)
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
assert int(pid)>0
argv=[x.decode() for x in Path('/proc',pid,'cmdline').read_bytes().split(b'\0') if x]
config_path=Path(argv[argv.index('--config')+1]);startup=read(config_path)
runtime=Path(startup['runtime']).resolve(strict=True)
assert str(runtime)==basis['runtime']==baseline['runtime'],'Runtime changed: recapture reviewed sources first'
assert sha(config_path)==basis['startup_config_sha256'],'Startup config changed'
assert sha(basis['launcher'])==basis['launcher_sha256'],'Launcher changed'
changed=[name for name,h in basis['hashes'].items() if sha(runtime/name)!=h]
pins_changed=[name for name,h in basis['component_pins'].items() if sha(runtime/'aura'/name)!=h]
baseline_changed=[name for name,h in baseline['source_hashes'].items() if sha(runtime/'aura'/name)!=h]
assert not changed and not pins_changed and not baseline_changed,(changed,pins_changed,baseline_changed)
assert sha(runtime/'aura/config/board_avatar_gtk.json')==baseline['render_config_sha256']
assert sha(baseline['native_pixels_library']['path'])==baseline['native_pixels_library']['sha256']
child=str(read(runtime/'launch.json')['pid'])
child_argv=Path('/proc',child,'cmdline').read_bytes().replace(b'\0',b' ').decode()
assert str(runtime/basis['ui_entry']) in child_argv
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=2) as response:state=json.load(response)
portrait=state.get('portrait_offload',{});display=state.get('avatar_display',{});settings=state.get('ui_settings',{})
live={'portrait':{k:portrait[k] for k in ('mode','selected','ready','target_fps','fallback_fps','backend') if k in portrait},
      'display':{k:display[k] for k in ('kind','frames','fps','age_ms','target_fps','dropped','late','width','height') if k in display},
      'settings':{k:settings[k] for k in ('economy','fullscreen') if k in settings},
      'playing':bool(state.get('playing',False)),'paused':bool(state.get('paused',False))}
assert portrait.get('mode')=='remote' and portrait.get('target_fps')==16 and not live['playing'],'Actual old remote16 is not ready'
history=ab/'history'/('before-boot-'+basis.get('boot_id',baseline['boot_id']))
history.mkdir(parents=True,exist_ok=True)
for name,path in (('board-source-manifest.json',basis_path),('fresh-baseline.json',baseline_path)):
    if not (history/name).exists():(history/name).write_bytes(path.read_bytes())
camera_pid=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()
basis.update(pid=pid,child_pid=child,child_cmdline=child_argv,boot_id=boot,camera_pid=camera_pid,resume_source_audit='ALL_EXISTING_SOURCE_AND_COMPONENT_PINS_MATCH')
baseline.update(boot_id=boot,supervisor_pid=pid,child_pid=child,live_render=live)
basis_path.write_text(json.dumps(basis,indent=2));baseline_path.write_text(json.dumps(baseline,indent=2))
result=dict(status='PASS',boot_id=boot,supervisor_pid=pid,child_pid=child,runtime=str(runtime),
            camera_pid=camera_pid,checked_component_pins=len(basis['component_pins']),checked_runtime_files=len(basis['hashes']),
            source_changed=False,production_modified=False,live_render=live)
(ab/'resume-basis-check.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
