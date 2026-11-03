"""Run the frozen axis inventory once; export metadata only, without actuation."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path('E:\\Win共享文件\\语音共享文件\\deliverables\\2026-10-31_visual_axis_maintenance\\evidence')
PROJECT = HERE.parents[2]
REPAIR = PROJECT / 'deliverables/2026-10-30_board_owner/integration/dialogue_repair'
sys.path.insert(0, str(REPAIR))
import probe

BUNDLE = HERE.parent / 'reviews/platform_receipt_v2/probe_bundle_v2'
EXPECTED = {
    'run_readonly_probe.py': 'a7fd7aefab3a4910a4865f15cb6d86d4cceb7d078662674a9265b8ebbdd9b89d',
    'probe_policy.json': 'f9da974e1869a84ee04a522aec347c7c30195a073ca71f40a213733144af376c',
}
payload = {}
for name, sha in EXPECTED.items():
    raw = (BUNDLE / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == sha, 'local_pin_mismatch'
    payload[name] = base64.b64encode(raw).decode('ascii')

REMOTE = r'''
import base64, hashlib, http.client, json, pathlib, subprocess, sys, tempfile
PAYLOAD = __PAYLOAD__
EXPECTED = __EXPECTED__
def paused_guard():
    connection = http.client.HTTPConnection('127.0.0.1', 8783, timeout=3)
    try:
        connection.request('GET', '/api/state')
        response = connection.getresponse()
        raw = response.read(1048577)
        assert response.status == 200 and len(raw) <= 1048576
        state = json.loads(raw)
    finally:
        connection.close()
    handsfree = state.get('handsfree_dialogue', {})
    valid = (handsfree.get('enabled') is False and
             handsfree.get('microphone_open') is False and
             handsfree.get('state') == 'PAUSED' and
             state.get('playing') is False)
    assert valid, 'paused_guard_failed'
    return {'paused': True, 'microphone_open': False, 'playing': False}
try:
    before = paused_guard()
    diagnostic_dir = pathlib.Path(tempfile.mkdtemp(prefix='aura-axis-readonly-v24-', dir='/tmp'))
    for name, value in PAYLOAD.items():
        raw = base64.b64decode(value, validate=True)
        assert hashlib.sha256(raw).hexdigest() == EXPECTED[name]
        with (diagnostic_dir / name).open('xb') as handle:
            handle.write(raw)
    process = subprocess.run([sys.executable, '-B', str(diagnostic_dir / 'run_readonly_probe.py')],
                             capture_output=True, text=True, timeout=40)
    assert len(process.stdout) <= 262144 and process.returncode == 0, 'probe_execution_failed'
    observation = json.loads(process.stdout)
    assert observation.get('schema') == 'aura-axis-platform-readonly-1'
    after = paused_guard()
    output = dict(schema='aura-root-axis-readonly-execution-1',
                  status='ROOT_READONLY_EXECUTED', observation=observation,
                  listening_before=before, listening_after=after,
                  supplied_sha256=EXPECTED, diagnostic_files_written=2,
                  production_files_written=0, service_commands_sent=0,
                  motion_commands_sent=0, private_media_or_identity_exported=False)
except Exception:
    output = dict(schema='aura-root-axis-readonly-execution-1', status='ROOT_READONLY_FAILED',
                  production_files_written=0, service_commands_sent=0, motion_commands_sent=0)
print(json.dumps(output, allow_nan=False, separators=(',', ':')))
'''
remote = REMOTE.replace('__PAYLOAD__', repr(payload)).replace('__EXPECTED__', repr(EXPECTED))
output = probe.ssh('python3 -B -', remote, timeout=55)
data = json.loads(output)
raw = (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
path = HERE / ('takeover_platform_v2_%d.json' % time.time_ns())
with path.open('xb') as handle:
    handle.write(raw)
observation = data.get('observation', {})
print(json.dumps(dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(),
                     status=data.get('status'), observation_status=observation.get('status'),
                     observations_valid=observation.get('observations_valid'),
                     platform=observation.get('platform'), bindings=observation.get('bindings'),
                     file_states={state: sum(row.get('state') == state for row in observation.get('files', []))
                                  for state in sorted({row.get('state') for row in observation.get('files', [])})},
                     manual_driver_states=[row.get('state') for row in observation.get('manual_driver_files', [])]),
                 ensure_ascii=False))
