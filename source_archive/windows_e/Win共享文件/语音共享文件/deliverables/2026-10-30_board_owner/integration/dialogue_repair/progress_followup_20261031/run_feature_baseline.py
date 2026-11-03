"""Root-owned bounded run of the public v17 production-class integration cases."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
PROJECT = HERE.parents[4]
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

bundle = REPAIR / 'feature_trigger_collaboration/board_integration_v17'
expected_files = {
    'worker.py': '7d5ff31d1f56cb567fd630c35056a1a33f9d239f520ad92975f47e10149153df',
    'source_mapping.json': '348c435302e4e855d9bf4ef354f0b26d56ef9dfac64438a4fb11f70b5f6e63af',
}
files = []
for name, expected in expected_files.items():
    raw = (bundle / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected
    files.append(dict(relative_path=name, bytes=len(raw), sha256=expected,
                      base64=base64.b64encode(raw).decode()))

base_path = REPAIR / 'frontend_allocation_candidate/public_probe/root_run_abba.py'
module_spec = importlib.util.spec_from_file_location('bounded_feature_slot', base_path)
base = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(base)
stage = '/home/root/aura-public-features-20261031/' + expected_files['worker.py'][:16]
old_stage = '/home/root/aura-public-frontend-allocation-20261031/c7988d2439fbb0d7'
assert base.REMOTE.count(old_stage) == 1
remote = base.REMOTE.replace(old_stage, stage)
anchor = 'after=guard.metadata(args,allow_background=True)'
assert remote.count(anchor) == 1
remote = remote.replace(anchor, """result_path = stage / OUTPUT_NAME
if result_path.exists():
 assert result_path.resolve() == result_path and result_path.stat().st_size < 262144
 result['integration_result'] = json.loads(result_path.read_bytes())
""" + anchor)
run_id = str(time.time_ns())
output_name = 'ACTUAL_' + run_id + '.json'
installed = json.loads((REPAIR.parent / 'production_business_acceptance/spec.json').read_bytes())
assert installed['startup_sha256'] == '0cbc191b4bf9029b15a65ef15797e43e15459e06b88381025d28a2c9b573dd2a'
runtime = installed['target'] + '/runtime/aura'
arguments = ['timeout', '--signal=TERM', '--kill-after=5s', '60s', '/usr/bin/python3', '-B', '-s',
             stage + '/worker.py', '--runtime-root', runtime,
             '--startup-config', installed['target'] + '/startup/config.json',
             '--coordinated-slot', 'root-features-' + run_id, '--output', stage + '/' + output_name]
values = dict(STAGE=stage, FILES=files, BOOT=installed['boot_id'], EXPECTED=installed['startup_sha256'],
              SLOT='feature-production-class-baseline', ARM='v17', ARGV=arguments, OUTPUT_NAME=output_name)
result = json.loads(ssh('python3 -B -', '\n'.join(k + '=' + repr(v) for k, v in values.items()) + '\n' + remote,
                        timeout=125))
output = HERE / ('feature_baseline_' + run_id + '.json')
with output.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
integration = result['result'].get('integration_result', {})
print(json.dumps(dict(evidence=str(output), exit_code=result['exit_code'], status=integration.get('status'),
                      passed=integration.get('passed'), failed=integration.get('failed'),
                      failed_cases=[row['id'] for row in integration.get('cases', []) if row['status'] == 'FAIL'],
                      owners_unchanged=result['owners_unchanged'],
                      pause_preserved=result['manual_pause_preserved'])))
