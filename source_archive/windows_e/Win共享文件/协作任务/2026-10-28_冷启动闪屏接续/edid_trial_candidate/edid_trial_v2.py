"""One supervised, reversible EDID experiment. Default invocation only inspects."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import uuid
import urllib.request

ROOT = Path('/run/aura-hdmi-edid-trials')
OVERRIDE = Path('/sys/kernel/debug/dri/0/DP-1/edid_override')
CONNECTOR = Path('/sys/class/drm/card0-DP-1')
FORCE = Path('/sys/kernel/debug/dri/0/DP-1/force')
STATE = Path('/sys/kernel/debug/dri/0/state')
REFERENCE_SHA = '727d3e1893df759c757c35232f9465b670a64d6de2011b586de48c6446e17c35'
REFERENCE = bytes.fromhex(
    '00ffffffffffff00048104000100000001110103800f09000a00000000000000'
    '00000000000045c0010101010101010101010101010124130020415818203060'
    '3a009a5600000018000000100000000000000000000000000000000000100000'
    '0000000000000000000000000000001000000000000000000000000000000087'
)
TIMING = '49000 1024 1072 1168 1312 600 603 613 624'
UNITS = {'gui': 'aura-avatar-ui.service', 'x': 'xserver-nodm.service',
         'camera': 'aura-camera-ui.service'}


def validate_reference(blob):
    if (len(blob) != 128 or blob[:8] != bytes.fromhex('00ffffffffffff00')
            or blob[126] != 0 or sum(blob) % 256
            or hashlib.sha256(blob).hexdigest() != REFERENCE_SHA):
        raise ValueError('Only the measured 128-byte panel EDID is accepted')


def run(args, timeout=15):
    p = subprocess.run(args, env=dict(os.environ, DISPLAY=':0'),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError('Command failed: %r: %s' % (args, p.stdout[-400:]))
    return p.stdout


def identity(unit):
    text = run(['systemctl', 'show', unit, '-p', 'MainPID', '-p', 'ActiveState'], 4)
    value = dict(line.split('=', 1) for line in text.splitlines() if '=' in line)
    pid = int(value['MainPID'])
    birth = None
    if pid:
        birth = int((Path('/proc') / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()[19])
    return {'pid': pid, 'birth': birth, 'state': value['ActiveState']}


def display_power_state(q, kernel_dpms, active):
    match = re.search(r'Monitor is (\w+)', q)
    return {'display_on': kernel_dpms == 'On' and active,
            'xset_monitor_report': match.group(1) if match else None,
            'kernel_dpms': kernel_dpms}


def snapshot():
    q = run(['xset', 'q'], 4)
    saver = re.search(r'timeout:\s*(\d+)\s+cycle:\s*(\d+)', q)
    dpms = re.search(r'Standby:\s*(\d+)\s+Suspend:\s*(\d+)\s+Off:\s*(\d+)', q)
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state', timeout=3) as r:
        u = json.load(r)
    raw = (CONNECTOR / 'edid').read_bytes()
    drm = STATE.read_text()
    return {'boot': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'owners': {key: identity(unit) for key, unit in UNITS.items()},
            'override_hex': OVERRIDE.read_bytes().hex(), 'force': FORCE.read_text().strip(),
            'edid_bytes': len(raw), 'edid_sha256': hashlib.sha256(raw).hexdigest(),
            **display_power_state(q, (CONNECTOR / 'dpms').read_text().strip(), '\n\tactive=1\n' in drm),
            'dpms_enabled': 'DPMS is Enabled' in q,
            'saver': [int(v) for v in saver.groups()] if saver else None,
            'dpms': [int(v) for v in dpms.groups()] if dpms else None,
            'mode_ok': TIMING in drm and '\n\tactive=1\n' in drm,
            'drm_state_sha256': hashlib.sha256(drm.encode()).hexdigest(),
            'ui_idle': (u.get('phase') == 'IDLE' and not u.get('playing')
                        and u.get('audio_output_state') == 'IDLE_READY'
                        and not u.get('pending_job')
                        and u.get('manual_pan', {}).get('automatic_following') is False
                        and u.get('handsfree_dialogue', {}).get('enabled') is False
                        and u.get('handsfree_dialogue', {}).get('microphone_open') is False),
            'page': u.get('ui_page')}


def validate_before(state, expected):
    if state['boot'] != expected['boot']:
        raise ValueError('Boot changed')
    for key in ('gui', 'x'):
        owner = state['owners'][key]
        if (owner['pid'] != expected[key] or owner['pid'] <= 0
                or owner['birth'] is None or owner['state'] != 'active'):
            raise ValueError('Expected active owner differs: ' + key)
    if state['override_hex'] or state['edid_bytes'] != 0:
        raise ValueError('Requires the missing-EDID fault; preserve any existing override')
    if state['force'] != 'unspecified':
        raise ValueError('Connector was already forced')
    if not state['display_on'] or not state['mode_ok'] or not state['ui_idle']:
        raise ValueError('Requires awake original timing and idle UI with motion/listening off')
    if state['saver'] is None or state['dpms'] is None:
        raise ValueError('Cannot preserve current idle policy')


def restoration_decision(boot, original_boot, override):
    if boot != original_boot:
        return 'new_boot_no_writes'
    if override not in (b'', REFERENCE):
        raise ValueError('Override changed by another actor; do not overwrite it')
    return 'clear_own_override' if override else 'already_clear'


def save(path, value):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=str(path.parent),
                                         prefix='.edid-', delete=False) as f:
            temporary = Path(f.name)
            json.dump(value, f, indent=2)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def mode_on():
    run(['xrandr', '--output', 'DP-1', '--mode', '1024x600', '--pos', '0x0', '--primary'])


def stop_timer(timer):
    unit = timer + '.timer'
    try:
        run(['systemctl', 'stop', unit], 4)
        return {'timer_stopped': True, 'timer_already_absent': False}
    except RuntimeError:
        text = run(['systemctl', 'show', unit, '-p', 'LoadState', '-p', 'ActiveState'], 4)
        value = dict(line.split('=', 1) for line in text.splitlines() if '=' in line)
        if value.get('LoadState') != 'not-found' or value.get('ActiveState') != 'inactive':
            raise
        return {'timer_stopped': True, 'timer_already_absent': True}


def restore(transaction):
    if transaction.parent != ROOT or transaction.resolve() != transaction:
        raise ValueError('Invalid transaction path')
    meta = json.loads((transaction / 'meta.json').read_text())
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    current = OVERRIDE.read_bytes()
    decision = restoration_decision(boot, meta['before']['boot'], current)
    result = {'decision': decision, 'restored': False, 'physical_panel_verified': False}
    if decision == 'new_boot_no_writes':
        save(transaction / 'restored.json', result)
        return result
    previous_path = transaction / 'restored.json'
    if previous_path.exists():
        previous = json.loads(previous_path.read_text())
        if previous.get('restored'):
            if current:
                raise ValueError('Completed trial cannot claim a new override')
            result = dict(previous, already_restored=True)
            result.update(stop_timer(meta['timer']))
            save(previous_path, result)
            return result
    if decision == 'clear_own_override':
        with OVERRIDE.open('wb', buffering=0) as f:
            if f.write(b'reset') != 5:
                raise RuntimeError('EDID reset write incomplete')
        (CONNECTOR / 'status').write_text('detect')
    same_x = identity(UNITS['x']) == meta['before']['owners']['x']
    if same_x:
        drm = STATE.read_text()
        if TIMING not in drm or '\n\tactive=1\n' not in drm:
            mode_on()
        before = meta['before']
        run(['xset', 's'] + [str(v) for v in before['saver']], 4)
        run(['xset', 'dpms'] + [str(v) for v in before['dpms']], 4)
        run(['xset', '+dpms' if before['dpms_enabled'] else '-dpms'], 4)
        run(['xset', 's', 'reset'], 4)
    result.update(restored=OVERRIDE.read_bytes() == b'', same_x_owner=same_x,
                  idle_policy_restored=same_x, sysfs_edid_bytes=len((CONNECTOR / 'edid').read_bytes()))
    if result['restored']:
        result.update(stop_timer(meta['timer']))
    save(transaction / 'restored.json', result)
    return result


def apply_trial(expected):
    validate_reference(REFERENCE)
    before = snapshot()
    validate_before(before, expected)
    transaction = ROOT / uuid.uuid4().hex
    transaction.mkdir(mode=0o700)
    timer = 'aura-edid-restore-' + transaction.name
    source = Path(__file__).resolve()
    meta = {'before': before, 'timer': timer, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'edid_sha256': REFERENCE_SHA, 'reset_seconds': 2, 'rollback_seconds': 180}
    save(transaction / 'meta.json', meta)
    run(['systemd-run', '--quiet', '--unit=' + timer, '--on-active=180s',
         '--timer-property=AccuracySec=1s', '--property=Type=oneshot',
         '--property=TimeoutStartSec=60s', '/usr/bin/python3', '-B', str(source),
         '--restore', str(transaction)], 5)
    try:
        # Only this short trial suppresses idle blanking; rollback restores the saved values.
        run(['xset', 's', 'off'], 4)
        run(['xset', '-dpms'], 4)
        with OVERRIDE.open('wb', buffering=0) as f:
            if f.write(REFERENCE) != len(REFERENCE):
                raise RuntimeError('EDID write incomplete')
        (CONNECTOR / 'status').write_text('detect')
        if OVERRIDE.read_bytes() != REFERENCE:
            raise RuntimeError('Override readback differs')
        run(['xrandr', '--output', 'DP-1', '--off'])
        time.sleep(2)
        mode_on()
        after = snapshot()
        if not after['mode_ok'] or after['override_hex'] != REFERENCE.hex():
            raise RuntimeError('Software mode/override verification failed')
        if after['owners'] != before['owners']:
            raise RuntimeError('Service owner changed during trial')
        result = {'transaction': str(transaction), 'before': before, 'after': after,
                  'software_verified': True, 'physical_panel_verified': False,
                  'edid_source': 'injected measured reference, not a fresh physical EDID read',
                  'restore_timer': timer, 'automatic_rollback_seconds': 180}
        save(transaction / 'applied.json', result)
        return result
    except BaseException as exc:
        error = {'error': type(exc).__name__, 'detail': str(exc)[:400]}
        try:
            error['rollback'] = restore(transaction)
        except Exception as recovery_error:
            error['rollback_error'] = type(recovery_error).__name__ + ': ' + str(recovery_error)[:300]
        save(transaction / 'failed.json', error)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--apply', action='store_true')
    group.add_argument('--restore', type=Path)
    parser.add_argument('--expected-boot')
    parser.add_argument('--expected-gui', type=int)
    parser.add_argument('--expected-x', type=int)
    args = parser.parse_args()
    if os.uname().machine != 'aarch64':
        parser.error('Board execution only')
    validate_reference(REFERENCE)
    if not args.apply and args.restore is None:
        print(json.dumps({'mode': 'inspect_only', 'state': snapshot(), 'mutations': 0}))
        return
    if args.apply and not all((args.expected_boot, args.expected_gui, args.expected_x)):
        parser.error('Explicit currently measured boot, GUI PID and X PID are required')
    if ROOT.exists() and (ROOT.is_symlink() or ROOT.resolve() != ROOT):
        raise ValueError('Transaction root redirects')
    ROOT.mkdir(mode=0o700, exist_ok=True)
    with (ROOT / 'operation.lock').open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.restore is not None:
            result = restore(args.restore)
        else:
            result = apply_trial({'boot': args.expected_boot, 'gui': args.expected_gui, 'x': args.expected_x})
    print(json.dumps(result))


if __name__ == '__main__':
    main()
