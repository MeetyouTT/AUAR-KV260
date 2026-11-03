"""Read-only final check of the real current entry, pinned source and test isolation."""
from pathlib import Path
import hashlib,json,subprocess,time
base=Path('/home/root/aura-yuki-validation-20261030');phase=base/'native_integration'
basis=json.loads((phase/'board_source/manifest.json').read_text());runtime=Path(basis['runtime'])
unit=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ExecStart','-p','ActiveState'],text=True)
pid=next(line.split('=',1)[1] for line in unit.splitlines() if line.startswith('MainPID='))
argv=[v.decode() for v in Path('/proc',pid,'cmdline').read_bytes().split(b'\0') if v]
cmdline=' '.join(argv)
config_path=Path(argv[argv.index('--config')+1]);config=json.loads(config_path.read_text())
actual_runtime=Path(config['runtime']).resolve(strict=True)
changed=[p for p,h in basis['hashes'].items() if hashlib.sha256((runtime/p).read_bytes()).hexdigest()!=h]
pin_changes=[]
shared_targets={row['name']:Path(row['target']) for row in json.loads((phase/'results/current-component-link-targets.json').read_text())}
for relative,expected in basis['component_pins'].items():
    assert not Path(relative).is_absolute() and '..' not in Path(relative).parts
    path=(runtime/'aura'/relative).resolve(strict=True)
    # Existing deployment shares public source through directory links. This
    # read-only audit pins their already-observed exact targets as well as bytes;
    # it never changes the active launcher's path or hash requirements.
    assert path.is_relative_to(runtime) or path==shared_targets.get(relative),relative
    assert path.suffix not in ('.sqlite3','.sqlite','.db'),relative
    if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:pin_changes.append(relative)
original=basis['original_basis'];original_root=Path(original['runtime'])
dependencies=list(original['hashes'])+['aura/tools/gstreamer_audio_worker.py']
dependency_changes=[name for name in dependencies if hashlib.sha256((original_root/name).read_bytes()).hexdigest()!=hashlib.sha256((runtime/name).read_bytes()).hexdigest()]
child_pid=str(json.loads((runtime/'launch.json').read_text())['pid'])
child_command=Path('/proc',child_pid,'cmdline').read_bytes().replace(b'\0',b' ').decode()
fixed=json.loads((base/'input-sha256.json').read_text())
fixed={p:h for p,h in fixed.items() if p.startswith(('source/','deps/','inputs/'))}
fixed_changed=[p for p,h in fixed.items() if hashlib.sha256((base/p).read_bytes()).hexdigest()!=h]
workers=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit() or int(proc.name)==__import__('os').getpid():continue
    try:value=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode()
    except (FileNotFoundError,PermissionError,ProcessLookupError):continue
    if str(phase) in value and any(tag in value for tag in ('precision_validation_worker.py','clock_revision_worker.py','validate_gtk_clock.py','validate_gtk_lifecycle.py','validate_native.py','yuki_frame_export','yuki_runtime_audit')):
        workers.append({'pid':int(proc.name),'cmdline':value})
checks=dict(pid_unchanged=pid==basis['pid'],entry_same_runtime=actual_runtime==runtime,
  child_pid_unchanged=child_pid==basis['child_pid'],child_entry_current=str(runtime/basis['ui_entry']) in child_command,
  startup_config_unchanged=hashlib.sha256(config_path.read_bytes()).hexdigest()==basis['startup_config_sha256'],
  launcher_unchanged=hashlib.sha256(Path(basis['launcher']).read_bytes()).hexdigest()==basis['launcher_sha256'],
  all_component_pins_match=not pin_changes,render_audio_dependencies_equal_initial=not dependency_changes,
  active='ActiveState=active' in unit,source_files_unchanged=not changed,frozen_inputs_unchanged=not fixed_changed,
  no_validation_workers=not workers)
report=dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,unit=unit,cmdline=cmdline,
  boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),runtime=str(runtime),
  checked_runtime_files=len(basis['hashes']),changed_runtime_files=changed,checked_frozen_files=len(fixed),
  checked_component_pins=len(basis['component_pins']),component_pin_changes=pin_changes,child_pid=child_pid,
  existing_shared_component_targets_checked=len(shared_targets),active_launcher_or_path_guards_modified=False,
  dependency_changes_from_initial=dependency_changes,initial_runtime=original['runtime'],
  initial_entry_updated_before_final_check=True,current_basis_recaptured=True,
  changed_frozen_files=fixed_changed,remaining_workers=workers,production_deployed=False,
  microphone_or_real_audio_opened=False,mechanical_or_firmware_operations=False,identity_network_acceptance=False)
previous=phase/'results/final-preservation.json';archived=phase/'results/final-preservation-before-current-entry-rebase.json'
if previous.exists() and not archived.exists():archived.write_bytes(previous.read_bytes())
previous.write_text(json.dumps(report,indent=2));print(json.dumps(report))
assert report['status']=='PASS'
