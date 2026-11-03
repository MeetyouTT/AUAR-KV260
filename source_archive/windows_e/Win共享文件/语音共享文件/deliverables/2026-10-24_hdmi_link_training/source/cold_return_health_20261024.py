"""Read-only cold-boot evidence; no device commands or service changes."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.request

boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot == 'c5f247b9-76b9-40a3-85ca-96578055eb5c'
op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
r = dict(boot=boot, mono_ns=time.monotonic_ns(),
         uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]), services={})
for unit in ['aura-camera-ui.service', 'aura-avatar-ui.service', 'xserver-nodm.service']:
    text = subprocess.check_output(['systemctl', 'show', unit, '-p', 'ActiveState',
        '-p', 'SubState', '-p', 'MainPID', '-p', 'Result', '-p', 'NRestarts',
        '-p', 'ExecMainStatus', '-p', 'ExecMainCode'], text=True)
    r['services'][unit] = dict(row.split('=', 1) for row in text.splitlines() if '=' in row)
p = Path('/sys/class/drm/card0-DP-1')
r['display'] = {k: (p/k).read_text().strip() for k in ['status', 'enabled', 'dpms']}
for name, port, path in [('camera', 8790, '/health'), ('gui', 8783, '/api/state')]:
    try:
        with op.open('http://127.0.0.1:'+str(port)+path, timeout=3) as stream:
            h = json.load(stream)
        if name == 'gui':
            r[name] = {k: h.get(k) for k in ['phase', 'ui_page', 'playing', 'audio_output_state']}
            r['manual_pan'] = {k: v for k, v in (h.get('manual_pan') or {}).items()
                if k in ['state', 'ready', 'fault', 'fault_reason', 'automatic_following']}
        else:
            s = h['dpu_schedule']; i = h['identity']; f = i['face_targets']
            r[name] = {k: h.get(k) for k in ['pid', 'detected_frames', 'detection_hz',
                'capture_hz', 'camera_error', 'detector_error']}
            r[name].update(native_critical=s.get('native_critical'), native_abi=s.get('native_abi'),
                owner_fenced=s['owner_fenced'], primary_overruns=s['primary_period_overruns'],
                optional={k: {a: v.get(a) for a in ['calls', 'native_completed',
                    'native_failures', 'overruns', 'disabled', 'recovery']} for k, v in s['optional'].items()},
                face_worker_alive=f['worker_alive'], face_backend=f['backend'],
                sface_ready=i['feature_inference']['ready'],
                sface_completed=i['feature_inference']['completed'],
                face_gaps=f['freshness_metrics']['counters']['observed_gap_intervals'])
            handoff = s.get('protection_handoff') or {}
            r['protection_handoff'] = handoff
            archive = Path(handoff['archive_path']) if handoff.get('archive_path') else None
            if archive:
                raw = archive.read_bytes()
                r['archive_hash_verified'] = hashlib.sha256(raw).hexdigest() == handoff['archive_sha256']
                r['archive_checkpoint'] = json.loads(raw)['checkpoint']
    except Exception as exc:
        r[name+'_unavailable'] = type(exc).__name__+': '+str(exc)
old = Path('/home/root/aura-native-coldboot-20261024/3610d09e12307044/shutdown.json')
shutdown = json.loads(old.read_text())
r['previous_shutdown'] = {k: shutdown.get(k) for k in
    ['safe_to_disconnect_power', 'poweroff_scheduled', 'failure', 'checkpoint_sha256']}
r['previous_shutdown']['source_boot'] = shutdown['checkpoint']['seed']['boot_id']
r['previous_shutdown']['checkpoint_sha_matches_local_record'] = shutdown['checkpoint_sha256'] == \
    'e6eb4b0d2f1ccb7a2e7d05f22f43a5e1fe6e43fb33e5daafec665921365ee0a6'
if 'archive_checkpoint' in r:
    r['previous_checkpoint_exactly_archived'] = r.pop('archive_checkpoint') == shutdown['checkpoint']
print(json.dumps(r))
