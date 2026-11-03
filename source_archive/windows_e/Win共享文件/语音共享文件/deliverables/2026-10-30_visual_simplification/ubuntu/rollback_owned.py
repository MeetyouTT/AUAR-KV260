"""Rollback only this transaction's exact override; also used by its watchdog."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess

from board_state import capture, digest
from workflow_common import atomic_json


def rollback(stage):
    stage = Path(stage)
    with (stage/'decision.lock').open('a') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        if (stage/'commit.json').exists():
            return dict(status='SKIPPED_COMMITTED')
        tx = json.loads((stage/'transaction.json').read_text())
        baseline = json.loads((stage/'baseline.json').read_text())
        override = Path(tx['override'])
        if not override.exists() and not override.is_symlink():
            result = dict(status='NO_OWN_OVERRIDE')
            atomic_json(stage/'rollback.json',result)
            return result
        assert not override.is_symlink(), 'Own override was replaced with a link'
        assert digest(override) == tx['override_sha256'], 'Own override was modified; rollback deferred'
        effective = subprocess.check_output(['systemctl','show','aura-avatar-ui.service',
                                             '-p','ExecStart'],text=True,timeout=10)
        assert str(stage/'startup/config.json') in effective, 'Concurrent unit update; rollback deferred'
        assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == baseline['boot']
        for name,sha in baseline['prior_overrides'].items():
            assert digest(name) == sha, 'Prior override modified; rollback deferred'
        assert digest(baseline['pending_config']) == baseline['pending_config_sha256']
        assert digest(baseline['pending_launcher']) == baseline['pending_launcher_sha256']
        override.unlink()
        subprocess.run(['systemctl','daemon-reload'],check=True,timeout=15)
        subprocess.run(['systemctl','restart','aura-avatar-ui.service'],check=True,timeout=120)
        after = capture()
        assert after['safe'] and not after['mismatches']
        assert after['actual_config'] == baseline['pending_config']
        assert after['actual_runtime'] == baseline['pending']['runtime']
        assert after['camera_proc']['pid'] == baseline['camera_proc']['pid']
        assert after['camera_proc']['start_ticks'] == baseline['camera_proc']['start_ticks']
        for key in ('boot','mechanical_sha256','settings','firmware','fdt_sha256','vart'):
            assert after[key] == baseline[key], key
        result = dict(status='ROLLED_BACK',actual_config=after['actual_config'],
                      actual_runtime=after['actual_runtime'],safe=True,
                      microphone_open=False,motion_command_sent=False)
        atomic_json(stage/'rollback.json',result)
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage',required=True)
    args = parser.parse_args()
    try:
        result = rollback(args.stage)
    except Exception as exc:
        result = dict(status='ROLLBACK_DEFERRED',error=type(exc).__name__+': '+str(exc))
        atomic_json(Path(args.stage)/'rollback.json',result)
    print(json.dumps(result))
    raise SystemExit(0 if result['status'] != 'ROLLBACK_DEFERRED' else 1)
