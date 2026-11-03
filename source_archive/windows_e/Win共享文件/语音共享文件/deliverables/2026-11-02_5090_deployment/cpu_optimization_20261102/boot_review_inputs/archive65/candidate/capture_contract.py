"""LATER read-only board capture. No service action, Native restore or store open.

The current main owner supplies one fresh metadata handoff after identity returns
maintenance rights and the main/axis/CPU windows finish original wide restoration.
Do not run this offline candidate against a live device from this task.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

from recovery_rules import (APP, CAMERA, CLIENT, CLIENT_SHA, DAEMON_SHA, GUI, Hold,
                            digest, encoded, owner, require, verify_idstop, verify_platform)
from boot_recovery import (CHECKPOINT, RELEASE, create, get_metadata, original_verify,
                           platform_metadata, process, regular, unit)

OPS = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')


def pinned(pin):
    raw = regular(pin['path'])
    require(digest(raw) == pin['sha256'], 'FRESH_HANDOFF_PIN_CHANGED')
    return raw


def capture(expected):
    require(platform.system() == 'Linux' and platform.machine() == 'aarch64' and os.geteuid() == 0
            and sys.dont_write_bytecode, 'BOARD_READONLY_CAPTURE_ONLY')
    require(expected.get('schema') == 'aura-boot-install-handoff-1', 'FRESH_MAIN_HANDOFF_REQUIRED')
    for name in ('identity_explicitly_returned_maintenance', 'main_axis_cpu_window_completed', 'all_other_writers_frozen',
                 'auxiliary_loader_startup_reviewed'):
        require(expected.get(name) is True, 'MAINTENANCE_RIGHTS_NOT_RETURNED')
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    require(expected['boot_id'] == boot, 'CAPTURE_BOOT_CHANGED')
    source = expected['startup_pin']
    startup_raw = pinned(source)
    startup = json.loads(startup_raw)
    aura = Path(startup['runtime']) / 'aura'
    require(len(startup['component_sha256']) == 380, 'FRESH_380_COMPONENT_CLOSURE_REQUIRED')
    for relative, pin in startup['component_sha256'].items():
        require(not Path(relative).is_absolute() and '..' not in Path(relative).parts
                and digest(regular(aura / relative)) == pin, 'CURRENT_COMPONENT_DIFFERS')
    camera = owner(expected['camera_owner'])
    supervisor = owner(expected['gui_supervisor'])
    gtk = owner(expected['gtk_owner'])
    require(process(camera['pid']) == camera and process(supervisor['pid']) == supervisor
            and process(gtk['pid']) == gtk, 'FRESH_OWNER_CHANGED')
    require(int(unit(CAMERA)['MainPID']) == camera['pid'] and int(unit(GUI)['MainPID']) == supervisor['pid'], 'FRESH_SERVICE_OWNER_CHANGED')
    verify_platform(platform_metadata(), APP)
    manifest_raw = regular(RELEASE / 'candidate-manifest.json')
    manifest_sha = digest(manifest_raw)
    stop = json.loads(pinned(expected['idstop_report_pin']))
    verify_idstop(stop, boot, manifest_sha)
    history = json.loads(pinned(expected['fresh_history_receipt_pin']))
    require(history.get('schema') == 'aura-fresh-final-history-validation-1'
            and history.get('status') == 'ORIGINAL_CURRENT_FINAL_AND_COMPLETE_HISTORY_VERIFIED'
            and history.get('boot_id') == boot
            and history.get('original_load_business_checkpoint_called') is True
            and history.get('complete_ordered_history_verified') is True
            and history.get('all_required_current_boot_cumulative_lower_bounds_checked') is True
            and history.get('checkpoint_or_marker_written') is False, 'CPU_ORIGINAL_FRESH_FULL_HISTORY_PROOF_REQUIRED')
    # Reuse the CPU adapters by exact reference, without copying/reimplementing them.
    references = json.loads(regular(Path(__file__).resolve().parent / 'cpu_adapters.reference.json'))['adapters']
    for role in ('normal_stop_adapter_pin', 'full_history_adapter_pin'):
        reference = references[role]
        require(Path(expected[role]['path']).name == reference['filename']
                and expected[role]['sha256'] == reference['sha256'], 'CPU_ADAPTER_REVIEW_VERSION_CHANGED_REVIEW_PACKAGE')
        pinned(expected[role])
    health = get_metadata(8790, '/health')
    require(health.get('pid') == camera['pid'] and health.get('board_boot_id') == boot
            and health.get('motion_command_emitted') is False, 'CURRENT_CAMERA_PROVENANCE')
    handoff = (health.get('dpu_schedule') or {}).get('protection_handoff') or {}
    require(handoff.get('mode') == 'native_exact_same_boot'
            and handoff.get('seed_sha256') == history['checkpoint_pin']['sha256'], 'CURRENT_CAMERA_MUST_CONSUME_REVIEWED_FRESH_FINAL')
    ui_path = aura / 'config/board_avatar_gtk.json'
    ui_raw = regular(ui_path)
    ui = json.loads(ui_raw)
    selected_pin = ui['board_business']['face_readback']
    selected = json.loads(pinned(selected_pin))
    original_verify(aura, selected)
    require(selected['board_boot_id'] == boot and selected['camera_pid'] == camera['pid']
            and selected['camera_start_ticks'] == camera['birth_ticks'], 'CURRENT_SELECTED_OWNER_REQUIRED')
    run = OPS / ('native-run-' + boot + '-' + str(camera['pid'])) / 'config.json'
    require(selected['camera_config'] == str(run), 'CURRENT_RUN_CONFIG_REQUIRED')
    config = json.loads(regular(run))
    native = config['native_execution']
    require(native['checkpoint_output'] == str(CHECKPOINT) and native.get('allow_new_kernel_boot') is True, 'ORIGINAL_NEW_BOOT_MECHANISM_REQUIRED')
    files = {}

    def keep(path, pin=None):
        value = digest(regular(path))
        require(pin is None or value == pin, 'CAMERA_PUBLIC_SOURCE_PIN_CHANGED')
        files[str(path)] = value

    for path, pin in selected['source_sha256'].items():
        keep(path, pin)
    native_manifest = dict(path=native['source_manifest'], sha256=native['source_manifest_sha256'])
    python_manifest = json.loads(pinned(native_manifest))
    python_root = Path(native_manifest['path']).parent / 'aura'
    actual = {str(p.relative_to(python_root)): digest(regular(p)) for p in python_root.rglob('*.py')}
    require(actual == python_manifest['files'], 'FULL_NATIVE_PYTHON_SOURCE_SET_CHANGED')
    for relative, pin in actual.items():
        keep(python_root / relative, pin)
    keep(native_manifest['path'], native_manifest['sha256'])
    operator = OPS / 'pan-face-edge-v5/native-operator-v1'
    for name in ('runtime-manifest.json', 'source-manifest.json'):
        raw = regular(operator / name)
        keep(operator / name)
        for path, pin in json.loads(raw)['files'].items():
            keep(Path(path) if Path(path).is_absolute() else operator / path, pin)
    meta = json.loads(regular(OPS / 'meta.json'))
    for path, pin in meta['source_pins'].items():
        keep(OPS / path, pin)
    for path in (OPS / 'meta.json', OPS / 'state.json', Path(source['path']).with_name('launcher.py'),
                 Path('/etc/dfx-mgrd/daemon.conf'), Path('/etc/dfx-mgrd/default_firmware'), Path('/usr/bin/xlnx-firmware-detect'),
                 Path('/usr/local/lib/kv260-runtime-repair/load-repaired-zocl.sh')):
        keep(path)
    require(json.loads(regular(OPS / 'state.json'))['phase'] in {'NATIVE_READY', 'OBSERVING', 'ACCEPTED'}, 'OLD_RESCUE_STATE_MUST_NOT_RESTORE_OWNERS')
    require(digest(regular(CLIENT)) == CLIENT_SHA, 'ORIGINAL_CLIENT_CHANGED')
    daemon = unit('dfx-mgr.service')
    require(process(daemon['MainPID'], executable=True)['executable_sha256'] == DAEMON_SHA, 'ORIGINAL_REPAIRED_DAEMON_CHANGED')
    units = {}
    for name in (CAMERA, GUI, 'dfx-mgr.service', 'kv260-repaired-zocl.service'):
        current = unit(name)
        paths = {current['FragmentPath']} | set(current['DropInPaths'].split())
        require('' not in paths, 'ORIGINAL_UNIT_SOURCE_MISSING')
        units[name] = dict(source_sha256={p: digest(regular(p)) for p in paths})
        if name in {CAMERA, GUI, 'dfx-mgr.service'}:
            result = subprocess.run(['systemctl', 'is-enabled', name], capture_output=True, timeout=5)
            require(result.returncode == 0 and result.stdout.strip() == b'enabled', 'ORIGINAL_BOOT_SERVICE_NOT_ENABLED')
    absent_units = []
    auxiliary = unit('dpu-auto-config.service')
    if auxiliary.get('LoadState') == 'not-found':
        absent_units.append('dpu-auto-config.service')
    else:
        paths = {auxiliary['FragmentPath']} | set(auxiliary['DropInPaths'].split())
        require('' not in paths and expected.get('auxiliary_loader_source_pins'), 'GENERATED_LOADER_PUBLIC_SOURCE_METADATA_REQUIRED')
        units['dpu-auto-config.service'] = dict(source_sha256={p: digest(regular(p)) for p in paths})
        for pin in expected['auxiliary_loader_source_pins']:
            keep(pin['path'], pin['sha256'])
    contract = dict(schema='aura-boot-recovery-contract-1', fresh_handoff_approved=True, installed_boot_id=boot,
                    startup_path=source['path'], runtime_aura=str(aura), component_count=len(startup['component_sha256']),
                    native_ops_root=str(OPS), native_manifest=native_manifest,
                    listening_preference_path='/home/root/.local/share/aura-board-business/listening_preference.json',
                    immutable_files=files, original_units=units, absent_platform_units=absent_units,
                    installation_handoff=copy_handoff(expected),
                    initial_source_state=dict(contract_sha256='INITIAL_CONTRACT', startup_sha256=digest(startup_raw),
                                              ui_sha256=digest(ui_raw), selected_pin=selected_pin,
                                              selected_sources=selected['source_sha256'],
                                              predecessor=dict(boot_id=boot, camera_owner=camera)))
    require(pinned(source) == startup_raw and process(camera['pid']) == camera and process(supervisor['pid']) == supervisor
            and process(gtk['pid']) == gtk, 'SOURCE_OR_OWNER_CHANGED_DURING_CAPTURE')
    return contract


def copy_handoff(expected):
    # Only explicit metadata keys; never copy arbitrary text or API documents.
    keys = ('boot_id', 'camera_owner', 'gui_supervisor', 'gtk_owner', 'startup_pin', 'idstop_report_pin',
            'fresh_history_receipt_pin', 'normal_stop_adapter_pin', 'full_history_adapter_pin')
    return {key: expected[key] for key in keys}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--handoff', type=Path, required=True)
    parser.add_argument('--handoff-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = json.loads(pinned(dict(path=str(args.handoff), sha256=args.handoff_sha256)))
    contract = capture(value)
    create(args.output, encoded(contract))
    print(json.dumps(dict(status='FRESH_READONLY_CONTRACT_CAPTURED_NOT_INSTALLED', contract_sha256=digest(encoded(contract)),
                          original_components_verified=contract['component_count'], board_mutations=False)))


if __name__ == '__main__':
    main()
