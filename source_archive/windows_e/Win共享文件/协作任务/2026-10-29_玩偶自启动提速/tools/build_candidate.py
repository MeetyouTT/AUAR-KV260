#!/usr/bin/env python3
"""Build an isolated next-boot startup-speed candidate from the live board config."""
import base64
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATE = ROOT/'candidate'
REMOTE_RELEASE = '/home/root/aura-avatar-startup-speed-20261029'
DROPIN_NAME = 'z'*64+'-aura-avatar-startup-speed-20261029.conf'
DROPIN_PATH = '/etc/systemd/system/aura-avatar-ui.service.d/'+DROPIN_NAME

assert hashlib.sha256((CANDIDATE/'config.json').read_bytes()).hexdigest() == \
    '12af11467b3ca0c0a1e6b57ac203e887d658a9799a159e39dfa90dbff60037d4'

dropin = (
    '[Service]\n'
    'ExecStart=\n'
    'ExecStart=/usr/bin/python3 -B '+REMOTE_RELEASE+'/launcher.py --config '+
    REMOTE_RELEASE+'/config.json\n'
)
(CANDIDATE/'dropin.conf').write_text(dropin, encoding='utf-8')

files = {}
for name in ('launcher.py', 'config.json', 'dropin.conf'):
    data = (CANDIDATE/name).read_bytes()
    files[name] = {
        'bytes': len(data),
        'sha256': hashlib.sha256(data).hexdigest(),
        'base64': base64.b64encode(data).decode('ascii'),
    }

manifest = {
    'task': 'AURA avatar startup speed 2026-10-29',
    'board_boot_id_at_audit': '605eaf50-c66a-4559-bfc9-5ae177e0f305',
    'service': 'aura-avatar-ui.service',
    'active_launcher_before_sha256': 'cd1680220b60f6120db1bc847ca59cfd445796ff37e48a3ba93efca65eddfd98',
    'fixed_launcher_base_sha256': 'ea68cb074bef23f5c71ec80d020fbac38c597009ab430cd3bd89eb836ef3105c',
    'active_config_sha256': '12af11467b3ca0c0a1e6b57ac203e887d658a9799a159e39dfa90dbff60037d4',
    'observed_startup_seconds': {
        'systemd_start_job': 14.324,
        'launcher_process': 17.896,
        'gtk_child_start': 45.380,
        'gui_ready': 90.804,
        'display_setup_elapsed': 26.182,
        'gui_initialization_after_child_start': 45.424,
    },
    'display_config': {
        'edid_grace_seconds': 15,
        'display_stable_seconds': 3,
        'display_retrain_off_seconds': 2,
        'all_preserved': True,
        'physical_panel_verified': False,
    },
    'component_inventory': {'count': 279, 'total_bytes': 2053383},
    'optimization': 'Start GTK once the current output is on the pinned mode, or on the exact previously verified timing with the named touch device while EDID grace continues. Keep display stability/recovery and gate systemd READY on both GUI and display setup.',
    'activation': 'Install a new lexically-last systemd drop-in and daemon-reload only. Do not restart the currently active GUI or reboot.',
    'rollback': 'Remove only the new drop-in after verifying its recorded SHA256, then run systemctl daemon-reload. The already-running GUI remains untouched.',
    'dropin_path': DROPIN_PATH,
    'remote_release': REMOTE_RELEASE,
    'files': {name: {key: value for key, value in record.items() if key != 'base64'}
              for name, record in files.items()},
}
(ROOT/'release_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n',
                                          encoding='utf-8')
payload = gzip.compress(json.dumps(files, ensure_ascii=False, separators=(',', ':')).encode('utf-8'), mtime=0)
(ROOT/'candidate_bundle.gz').write_bytes(payload)
print(json.dumps({'release': REMOTE_RELEASE, 'dropin': DROPIN_PATH,
                  'bundle_bytes': len(payload), 'files': manifest['files']},
                 ensure_ascii=False, indent=2))
