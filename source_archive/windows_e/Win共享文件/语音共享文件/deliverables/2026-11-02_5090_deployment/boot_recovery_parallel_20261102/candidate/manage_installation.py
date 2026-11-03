"""Review, install or withdraw ONLY this package. Default command is a plan.

No SSH, stop/start/restart/reboot, enable/disable, DFX or Native-state operation.
Installation and rollback use one daemon-reload; no running entry is replaced.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

from recovery_rules import (CAMERA, GUI, Hold, digest, encoded, require, require_no_owners)
from boot_recovery import (PACKAGE_ROOT, STATE_ROOT, Recovery, create, fcntl, fsync_directory,
                           owner_scan, process, regular, replace_known, unit)

HERE = Path(__file__).resolve().parent
PYTHON_FILES = ('recovery_rules.py', 'boot_recovery.py', 'capture_contract.py', 'manage_installation.py', 'original_history_gate.py')


def payload(contract_raw):
    result = {(PACKAGE_ROOT / name).as_posix(): (HERE / name).read_bytes() for name in PYTHON_FILES}
    result[(PACKAGE_ROOT / 'contract.json').as_posix()] = contract_raw
    result[(PACKAGE_ROOT / 'cpu_adapters.reference.json').as_posix()] = (HERE / 'cpu_adapters.reference.json').read_bytes()
    for path in (HERE / 'systemd').rglob('*'):
        if path.is_file():
            result['/etc/systemd/system/' + path.relative_to(HERE / 'systemd').as_posix()] = path.read_bytes()
    return result


def board_only():
    require(platform.system() == 'Linux' and platform.machine() == 'aarch64'
            and os.geteuid() == 0 and sys.dont_write_bytecode, 'LATER_BOARD_ROOT_INSTALL_ONLY')


def source_recheck(contract):
    require(contract.get('schema') == 'aura-boot-recovery-contract-1'
            and contract.get('fresh_handoff_approved') is True, 'INERT_OR_UNREVIEWED_CONTRACT')
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    require(contract['installed_boot_id'] == boot, 'INSTALL_REQUIRES_FRESH_SAME_BOOT_CAPTURE')
    probe = object.__new__(Recovery)
    probe.contract = contract
    probe.contract_sha = digest(encoded(contract))
    probe.activation = {'installed_files': {}}
    probe.source_snapshot()
    probe.original_release()
    handoff = contract['installation_handoff']
    for role in ('camera_owner', 'gui_supervisor', 'gtk_owner'):
        require(process(handoff[role]['pid']) == handoff[role], 'INSTALL_OWNER_CHANGED_RECAPTURE')
    require(int(unit(CAMERA)['MainPID']) == handoff['camera_owner']['pid']
            and int(unit(GUI)['MainPID']) == handoff['gui_supervisor']['pid'], 'INSTALL_RUNNING_ENTRY_CHANGED')
    for role in ('idstop_report_pin', 'fresh_history_receipt_pin', 'fresh_history_expected_pin', 'normal_stop_adapter_pin', 'full_history_adapter_pin'):
        pin = handoff[role]
        require(digest(regular(pin['path'])) == pin['sha256'], 'INSTALL_REVIEWED_EVIDENCE_CHANGED')


def fresh_directory(path):
    require(not os.path.lexists(path) and path.parent.resolve() == path.parent, 'INSTALL_PATH_EXISTS_OR_REDIRECTS')
    path.mkdir(mode=0o700)
    fsync_directory(path.parent)


def ensure_parent(path):
    path = Path(path)
    missing = []
    while not path.exists():
        missing.append(path)
        path = path.parent
    require(path.resolve() == path and not path.is_symlink(), 'INSTALL_PARENT_REDIRECTED')
    for parent in reversed(missing):
        parent.mkdir(mode=0o755)
        fsync_directory(parent.parent)


def reload_and_verify():
    result = subprocess.run(['systemctl', 'daemon-reload'], capture_output=True, timeout=15)
    require(result.returncode == 0, 'DAEMON_RELOAD_FAILED_NO_RESTART')
    for name, helper, dependency in ((CAMERA, 'camera-check', 'aura-original-wide-prepare.service'),
                                     (GUI, 'bind-camera', CAMERA)):
        props = unit(name)
        extra = subprocess.run(['systemctl', 'show', name, '--property=ExecStartPre,Requires,After'], capture_output=True, timeout=5)
        require(extra.returncode == 0, 'NEW_EFFECTIVE_DEPENDENCIES_UNAVAILABLE')
        merged = dict(line.split('=', 1) for line in extra.stdout.decode().splitlines() if '=' in line)
        require(str(PACKAGE_ROOT / 'boot_recovery.py') + ' ' + helper in merged.get('ExecStartPre', '')
                and dependency in merged.get('Requires', '').split()
                and dependency in merged.get('After', '').split(), 'LATER_DROPIN_MASKED_NEW_BARRIER')
        if name == CAMERA:
            require(all(props.get(k) == v for k, v in {'Restart': 'no', 'KillMode': 'process', 'SendSIGKILL': 'no', 'TimeoutStopUSec': 'infinity'}.items()), 'NATIVE_STOP_BOUNDARY_CHANGED')
        else:
            require(props.get('TimeoutStartUSec') == 'infinity', 'OUTER_GUI_START_TIMEOUT_MAY_KILL_BINDING_HELPER')


def verify_unit_graph():
    # Reads unit definitions only. Run against the ACTUAL target version and
    # all retained drop-ins, before writing any activation receipt.
    paths = ['/etc/systemd/system/aura-original-wide-prepare.service', '/etc/systemd/system/aura-boot-ready.service',
             unit(CAMERA)['FragmentPath'], unit(GUI)['FragmentPath']]
    require(all(paths), 'ORIGINAL_UNIT_FRAGMENT_UNAVAILABLE_FOR_VERIFY')
    result = subprocess.run(['systemd-analyze', 'verify', '--man=no'] + paths, capture_output=True, timeout=25)
    require(result.returncode == 0, 'TARGET_SYSTEMD_UNIT_GRAPH_NOT_VERIFIED_NO_ACTIVATION')


def install(contract_raw):
    board_only()
    contract = json.loads(contract_raw)
    require(encoded(contract) == contract_raw, 'CANONICAL_CAPTURE_CONTRACT_REQUIRED')
    source_recheck(contract)
    files = payload(contract_raw)
    require(not PACKAGE_ROOT.exists() and not STATE_ROOT.exists(), 'PREVIOUS_INSTALLATION_RECONCILE_FIRST')
    for target in files:
        require(not os.path.lexists(target), 'REFUSE_OVERWRITING_ANY_EXISTING_FILE')
    ensure_parent(PACKAGE_ROOT.parent)
    ensure_parent(STATE_ROOT.parent)
    fresh_directory(PACKAGE_ROOT)
    fresh_directory(STATE_ROOT)
    before = STATE_ROOT / 'installation-before'
    before.mkdir(mode=0o700)
    for name, sources in contract['original_units'].items():
        directory = before / name
        directory.mkdir(mode=0o700)
        index = {}
        for number, (path, pin) in enumerate(sorted(sources['source_sha256'].items())):
            raw = regular(path)
            require(digest(raw) == pin, 'PREINSTALL_BACKUP_SOURCE_CHANGED')
            filename = str(number) + '.original.raw'
            create(directory / filename, raw)
            index[path] = dict(sha256=pin, original_bytes_file=filename)
        create(directory / 'index.json', encoded(index))
    intent = dict(schema='aura-boot-install-intent-1', boot_id=contract['installed_boot_id'],
                  contract_sha256=digest(contract_raw), monotonic_ns=time.monotonic_ns(),
                  added_files={p: digest(raw) for p, raw in files.items()}, overwritten_files=[], service_restart_requested=False)
    create(STATE_ROOT / 'install-intent.json', encoded(intent))
    source_recheck(contract)  # Capture and compare every original source again before writes.
    for target, raw in files.items():
        path = Path(target)
        ensure_parent(path.parent)
        create(path, raw)
    source_recheck(contract)
    verify_unit_graph()
    activation = dict(schema='aura-boot-recovery-activation-1', enabled=True,
                      contract_sha256=digest(contract_raw), installed_files=intent['added_files'])
    create(PACKAGE_ROOT / 'activation.json', encoded(activation))
    try:
        reload_and_verify()
    except BaseException:
        # Disable this package only. Leave all sources, services and jobs untouched.
        require(regular(PACKAGE_ROOT / 'activation.json') == encoded(activation), 'ACTIVATION_CHANGED_DURING_INSTALL')
        (PACKAGE_ROOT / 'activation.json').unlink()
        fsync_directory(PACKAGE_ROOT)
        raise
    receipt = dict(schema='aura-boot-recovery-installation-1', status='INSTALLED_FOR_NEXT_BOOT_NOT_COLD_BOOT_ACCEPTED',
                   boot_id=contract['installed_boot_id'], contract_sha256=digest(contract_raw), added_files=intent['added_files'],
                   activation_sha256=digest(encoded(activation)), stopped_started_restarted_or_rebooted=False,
                   original_default_firmware_changed=False, original_sources_overwritten=False,
                   cold_boot_accepted=False)
    create(STATE_ROOT / 'installed.json', encoded(receipt))
    return receipt


def no_live_helpers_or_loader_jobs():
    for name in (CAMERA, GUI):
        require(unit(name).get('ControlPID', '0') == '0', 'ORIGINAL_SERVICE_PRESTART_HELPER_ACTIVE')
    for name in ('aura-original-wide-prepare.service', 'aura-boot-ready.service'):
        current = unit(name)
        require(current.get('MainPID', '0') == '0' and current.get('ControlPID', '0') == '0' and not current.get('Job'), 'BOOT_HELPER_STILL_ACTIVE')
    jobs = subprocess.run(['systemctl', 'list-units', '--all', '--no-legend', '--no-pager', 'aura-boot-wide-*.service'], capture_output=True, timeout=5)
    require(jobs.returncode == 0, 'CANNOT_AUDIT_EXISTING_DFX_JOBS')
    for line in jobs.stdout.decode().splitlines():
        parts = line.split()
        if not parts:
            continue
        name = next((p for p in parts if p.startswith('aura-boot-wide-') and p.endswith('.service')), None)
        require(name is not None, 'UNKNOWN_DFX_UNIT_LIST_SHAPE')
        current = unit(name)
        require(current.get('MainPID', '0') == '0' and not current.get('Job')
                and current.get('SubState') in {'dead', 'exited', 'failed'}, 'DFX_JOB_PENDING_OR_UNKNOWN_NO_ROLLBACK')


def lock_state():
    path = STATE_ROOT / 'operation.lock'
    require(path.parent.resolve() == path.parent and not path.is_symlink(), 'STATE_LOCK_REDIRECTED')
    handle = path.open('a+')
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    return handle


def withdraw():
    board_only()
    operation_lock = lock_state()
    no_live_helpers_or_loader_jobs()
    receipt = json.loads(regular(STATE_ROOT / 'installed.json'))
    activation = PACKAGE_ROOT / 'activation.json'
    require(digest(regular(activation)) == receipt['activation_sha256'], 'OWN_ACTIVATION_CHANGED')
    targets = {p: pin for p, pin in receipt['added_files'].items() if p.startswith('/etc/systemd/system/')}
    for path, pin in targets.items():
        require(digest(regular(path)) == pin, 'OWN_SYSTEMD_FILE_CHANGED_REFUSE_WITHDRAWAL')
    # Review and validate the ENTIRE withdrawal set before changing the first byte.
    activation.unlink()
    fsync_directory(activation.parent)
    for path, pin in targets.items():
        require(digest(regular(path)) == pin, 'WITHDRAWAL_CAS_CHANGED')
        Path(path).unlink()
        fsync_directory(Path(path).parent)
    result = subprocess.run(['systemctl', 'daemon-reload'], capture_output=True, timeout=15)
    require(result.returncode == 0, 'WITHDRAWAL_RELOAD_FAILED_NO_RESTART')
    value = dict(status='OWN_STARTUP_BARRIERS_WITHDRAWN_NO_SERVICE_ACTION', startup_ui_and_selected_binding_retained=True,
                 package_and_state_retained_for_provenance=True, default_firmware_restored_by_no_change=True,
                 next_original_boot_may_load_benchmark=True)
    create(STATE_ROOT / 'withdrawn.json', encoded(value))
    return value


def rollback_binding(directory):
    board_only()
    operation_lock = lock_state()
    no_live_helpers_or_loader_jobs()
    directory = Path(directory)
    require(directory.resolve() == directory and STATE_ROOT / 'boots' in directory.parents, 'BINDING_ROLLBACK_PATH')
    intent = json.loads(regular(directory / 'intent.json'))
    require(intent['contract_sha256'] == digest(regular(PACKAGE_ROOT / 'contract.json')), 'BINDING_ROLLBACK_CONTRACT_CHANGED')
    require(intent['boot_id'] == Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'BINDING_ROLLBACK_BOOT_CHANGED')
    for name in (CAMERA, GUI):
        current = unit(name)
        require(current['MainPID'] == '0' and current['ActiveState'] == 'inactive'
                and current['SubState'] == 'dead' and not current['Job'] and current['Result'] == 'success', 'NORMAL_SERVICE_SHUTDOWN_REQUIRED')
    require_no_owners(owner_scan())
    contract = json.loads(regular(PACKAGE_ROOT / 'contract.json'))
    startup_path = Path(contract['startup_path'])
    ui_path = Path(contract['runtime_aura']) / 'config/board_avatar_gtk.json'
    pairs = [(ui_path, regular(directory / 'ui.before.json'), regular(directory / 'ui.after.json')),
             (startup_path, regular(directory / 'startup.before.json'), regular(directory / 'startup.after.json'))]
    for (path, before, after), prefix in zip(pairs, ('ui', 'startup')):
        require(digest(before) == intent[prefix + '_before_sha256'] and digest(after) == intent[prefix + '_after_sha256'], 'BINDING_ROLLBACK_SEALED_BYTES_CHANGED')
        require(regular(path) in {before, after}, 'NEWER_SOURCE_CONFLICT_NO_BINDING_ROLLBACK')
    active_path = STATE_ROOT / 'active-source.json'
    prior_active = regular(directory / 'active-source.before.json')
    require(digest(prior_active) == intent['active_before_sha256'], 'BEFORE_ACTIVE_LEDGER_BYTES_CHANGED')
    current_active = regular(active_path) if active_path.exists() else b'null\n'
    committed_path = directory / 'committed.json'
    committed = regular(committed_path) if committed_path.exists() else None
    sealed_after = regular(directory / 'active-source.after.json')
    require(digest(sealed_after) == intent['active_after_sha256'], 'AFTER_ACTIVE_LEDGER_SEALED_BYTES_CHANGED')
    require(committed is None or committed == sealed_after, 'COMMITTED_LEDGER_DIFFERS_FROM_SEALED_AFTER')
    require(current_active == prior_active or current_active == sealed_after, 'NEWER_ACTIVE_LEDGER_CONFLICT')
    for path, before, after in pairs:
        if regular(path) == after:
            replace_known(path, after, before)
    if current_active != prior_active:
        if prior_active == b'null\n':
            require(regular(active_path) == sealed_after, 'ACTIVE_LEDGER_CHANGED')
            active_path.unlink()
            fsync_directory(active_path.parent)
        else:
            replace_known(active_path, sealed_after, prior_active)
    return dict(status='EXACT_BINDING_BYTES_RESTORED_GUI_LEFT_STOPPED', original_camera_reader_state_untouched=True,
                fresh_binding_required_before_next_gui_start=True, service_action_requested=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', default='plan', choices=['plan', 'install', 'withdraw', 'rollback-binding'])
    parser.add_argument('--contract', type=Path, default=HERE / 'contract.example.json')
    parser.add_argument('--binding-directory', type=Path)
    args = parser.parse_args()
    if args.action == 'plan':
        raw = args.contract.read_bytes()
        value = dict(status='LOCAL_REVIEW_PLAN_ONLY', candidate_activated=False,
                     fresh_contract=bool(json.loads(raw).get('fresh_handoff_approved')),
                     add_files={p: digest(data) for p, data in payload(raw).items()}, replace_existing_files=[],
                     startup_order=['original repaired ZOCL', 'original repaired DFX daemon/default',
                                    'original client list/remove/load + ID_STOP_ONLY', 'original Native camera',
                                    'fresh selected binding + original verifier', 'original GUI launcher', 'READY observer'],
                     rollback='withdraw own systemd files only; optional exact binding rollback requires normal shutdown',
                     service_or_hardware_action_requested=False)
    elif args.action == 'install':
        value = install(regular(args.contract))
    elif args.action == 'withdraw':
        value = withdraw()
    else:
        require(args.binding_directory is not None, 'BINDING_DIRECTORY_REQUIRED')
        value = rollback_binding(args.binding_directory)
    print(json.dumps(value, sort_keys=True))


if __name__ == '__main__':
    main()
