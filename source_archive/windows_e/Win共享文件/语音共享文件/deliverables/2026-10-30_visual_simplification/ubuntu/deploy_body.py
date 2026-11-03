"""Owned UI-only switch with an independent, exact-ownership rollback timer."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import urllib.request

stage = Path(STAGE)
for name,sha in OPS_SHA256.items():
    assert hashlib.sha256((stage/'ops'/name).read_bytes()).hexdigest() == sha, name
sys.path.insert(0,str(stage/'ops'))
from board_state import capture, digest
from workflow_common import atomic_json, require_idle

lock = Path('/run/aura-visual-simplification.lock').open('a')
fcntl.flock(lock.fileno(),fcntl.LOCK_EX | fcntl.LOCK_NB)
b = json.loads((stage/'baseline.json').read_text())
c = json.loads((stage/'candidate.json').read_text())
assert c == EXPECTED_CANDIDATE, 'Candidate record changed'
require_idle(capture(),c['baseline_signature'])
time.sleep(.7)
require_idle(capture(),c['baseline_signature'])
assert not (stage/'deployment.json').exists(), 'Do not replay a UI transaction'
root = stage/'runtime'
startup = stage/'startup'
assert digest(startup/'launcher.py') == b['pending_launcher_sha256'] == c['launcher_sha256']
assert digest(startup/'config.json') == c['config_sha256']
cfg = json.loads((startup/'config.json').read_text())
assert cfg['runtime'] == str(root)
assert {k:v for k,v in cfg.items() if k not in ('runtime','component_sha256')} == {
    k:v for k,v in b['pending'].items() if k not in ('runtime','component_sha256')}
assert set(cfg['component_sha256']) == set(b['pins'])
assert [n for n in b['pins'] if cfg['component_sha256'][n] != b['pins'][n]] == ['board/runtime/device_observer.py']
for name,sha in cfg['component_sha256'].items():
    assert digest(root/'aura'/name) == sha, name
for name in ('stage.log','managed-runs','launch.json'):
    assert not (root/name).exists() and not (root/name).is_symlink(), name

def private_integrity_snapshot():
    # Digests stay only in this process. Export equality/count, never identity data.
    files = set()
    camera = Path('/proc')/str(b['camera_proc']['pid'])
    for fd in (camera/'fd').iterdir():
        try:
            path = Path(os.readlink(fd))
            if path.name in ('identities.sqlite3','identities.sqlite3-wal') and path.is_file():
                files.add(path)
        except OSError:
            pass
    for directory in (Path('/home/root/.local/share/aura'),Path('/root/.local/share/aura')):
        for name in ('identities.sqlite3','identities.sqlite3-wal'):
            path = directory/name
            if path.is_file():
                files.add(path)
    return {str(p):digest(p) for p in files}

def camera_config_snapshot():
    files = {Path(b['camera_proc']['argv'][-1])}
    files.update(Path(p) for p in b['camera']['DropInPaths'].split())
    # The entry and adjacent published configuration are read only.
    files.update(Path(b['camera_proc']['argv'][-1]).parent.rglob('*.json'))
    return {str(p):digest(p) for p in files if p.is_file()}

def camera_progress():
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5) as r:
        value = json.load(r)
    preview = value.get('ui_runtime',{}).get('snapshot',{}).get('preview',{})
    return {key:preview.get(key) for key in ('camera_epoch','frame_id','frame_age_ms','valid')}

private_before = private_integrity_snapshot()
camera_configs_before = camera_config_snapshot()
progress_before = camera_progress()
for port in (8791,8792,8812):
    with urllib.request.urlopen('http://192.168.50.1:'+str(port)+'/health',timeout=5) as r:
        health = json.load(r)
    if port == 8792:
        assert health.get('ready') is True and not health.get('busy')
        assert health.get('service_revision') == 'voice-board-vision-20261030-r12'
        assert health.get('visual_processing',{}).get('semantic_model_enabled') is False
for port in (8795,8796):
    # These services speak bounded binary protocols, not HTTP health endpoints.
    with socket.create_connection(('192.168.50.1',port),timeout=5):
        pass

depth = max(len(re.match('z*',Path(p).name).group()) for p in b['prior_overrides'])+1
override = Path('/etc/systemd/system/aura-avatar-ui.service.d')/('z'*depth+'-aura-board-vision-ubuntu-20261030.conf')
content = ('[Service]\nExecStart=\nExecStart=/usr/bin/python3 -B '+str(startup/'launcher.py')
           +' --config '+str(startup/'config.json')+'\n').encode()
assert not override.exists() and not override.is_symlink()
transaction = dict(override=str(override),override_sha256=hashlib.sha256(content).hexdigest())
atomic_json(stage/'transaction.json',transaction)
rollback_path = stage/'ops/rollback_owned.py'
assert not rollback_path.exists()
rollback_path.write_text(ROLLBACK_SOURCE)
assert digest(rollback_path) == ROLLBACK_SHA256
from rollback_owned import rollback
timer_name = 'aura-visual-ubuntu-'+c['observer_sha256'][:12]
report = dict(status='PREPARING',runtime=str(root),previous_runtime=b['actual_runtime'],
              previous_pending_config=b['pending_config'],**transaction,
              watchdog_unit=timer_name,watchdog_seconds=300,
              microphone_opened=False,physical_playback=False,motion_command_sent=False)
atomic_json(stage/'deployment.json',report)
armed = False
try:
    require_idle(capture(),c['baseline_signature'])
    subprocess.run(['systemd-run','--unit='+timer_name,'--on-active=300s',
                    '--timer-property=AccuracySec=1s','/usr/bin/python3','-B',
                    str(rollback_path),'--stage',str(stage)],check=True,
                   stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=15)
    armed = True
    report['status'] = 'SWITCHING'
    atomic_json(stage/'deployment.json',report)
    with override.open('xb') as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    subprocess.run(['systemctl','daemon-reload'],check=True,timeout=15)
    subprocess.run(['systemctl','restart','aura-avatar-ui.service'],check=True,timeout=120)
    deadline = time.monotonic()+35
    last = ''
    while time.monotonic() < deadline:
        try:
            after = capture()
            assert after['actual_config'] == str(startup/'config.json')
            assert after['pending_config'] == after['actual_config']
            assert after['actual_runtime'] == str(root)
            assert after['safe'] and not after['mismatches']
            assert after['pins'] == cfg['component_sha256']
            assert after['actual_launcher_sha256'] == c['launcher_sha256']
            assert after['pending_launcher_sha256'] == c['launcher_sha256']
            assert after['camera_proc'] == b['camera_proc']
            assert after['state']['camera_epoch'] == b['state']['camera_epoch']
            assert after['state']['ui_link'] == 'READY'
            assert after['state']['portrait_offload']['mode'] == 'remote'
            for key in ('boot','mechanical_sha256','settings','firmware','fdt_sha256','vart'):
                assert after[key] == b[key], key
            for key in ('state','pulse_us','target_us','automatic_following'):
                assert after['pan'][key] == b['pan'][key],key
            assert all(digest(p) == sha for p,sha in b['prior_overrides'].items())
            observer = after['state']['device_observer']
            assert observer['enabled'] is False and observer['image_upload_enabled'] is False
            assert observer['sent'] == 0 and observer['retired_reason'] == 'semantic_vision_removed'
            Path(after['active_pointers']['stage.log']['resolved']).relative_to(root/'managed-runs')
            Path(after['launch']['session']).relative_to(root/'managed-runs')
            assert private_integrity_snapshot() == private_before
            assert camera_config_snapshot() == camera_configs_before
            break
        except Exception as exc:
            last = type(exc).__name__+': '+str(exc)
            time.sleep(.5)
    else:
        raise RuntimeError('Post-deploy readiness: '+last)
    time.sleep(2)
    latest = capture()
    assert latest['safe'] and not latest['mismatches']
    assert latest['actual_config'] == after['actual_config']
    assert latest['actual_proc']['start_ticks'] == after['actual_proc']['start_ticks']
    progress_after = camera_progress()
    if isinstance(progress_before.get('frame_id'),int) and isinstance(progress_after.get('frame_id'),int):
        assert progress_after['frame_id'] > progress_before['frame_id']
    with (stage/'decision.lock').open('a') as decision:
        fcntl.flock(decision.fileno(),fcntl.LOCK_EX)
        assert not (stage/'rollback.json').exists(), 'Rollback already occurred'
        assert digest(override) == transaction['override_sha256']
        report.update(status='COMMITTED',after=latest,pins=len(cfg['component_sha256']),
                      changed=['board/runtime/device_observer.py'],
                      prior_overrides_preserved=True,optimized_launcher_preserved=True,
                      camera_process_unchanged=True,camera_configuration_unchanged=True,
                      identity_store_files_compared=len(private_before),identity_store_files_unchanged=True,
                      camera_progress_before=progress_before,camera_progress_after=progress_after,
                      private_identity_hashes_exported=False)
        atomic_json(stage/'commit.json',dict(status='COMMITTED',config_sha256=c['config_sha256']))
        atomic_json(stage/'deployment.json',report)
except Exception as exc:
    report.update(status='FAILED',error=type(exc).__name__+': '+str(exc))
    try:
        outcome = rollback(stage)
        report['rollback'] = outcome
        if outcome['status'] in ('ROLLED_BACK','NO_OWN_OVERRIDE'):
            report['status'] = outcome['status']
    except Exception as rollback_error:
        report['rollback_error'] = type(rollback_error).__name__+': '+str(rollback_error)
finally:
    if armed and report['status'] in ('COMMITTED','ROLLED_BACK','NO_OWN_OVERRIDE'):
        stop = subprocess.run(['systemctl','stop',timer_name+'.timer'],
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=15)
        report['watchdog_stopped'] = stop.returncode == 0
    atomic_json(stage/'deployment.json',report)
print(json.dumps(report))
