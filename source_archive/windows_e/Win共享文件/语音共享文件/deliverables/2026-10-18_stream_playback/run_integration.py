"""Run the staged board candidate and copy its bounded JSON evidence back."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

candidate = json.loads((HERE / 'candidate.json').read_text(encoding='utf-8'))
remote = r'''
import json, subprocess
from pathlib import Path
stage = Path(STAGE)
report = stage / 'integration.json'
command = ['python3', '-B', str(stage / 'integration_runner.py'), '--runtime', str(stage / 'runtime'),
           '--case', str(stage / 'data/chat_input.wav'), '--case', str(stage / 'data/math_input.wav'),
           '--report', str(report)]
result = subprocess.run(command, capture_output=True, text=True, timeout=270)
evidence = json.loads(report.read_text()) if report.is_file() else {'status': 'FAIL_NO_REPORT'}
evidence['runner_exit_code'] = result.returncode
evidence['runner_output_tail'] = (result.stdout + result.stderr)[-4000:]
print(json.dumps(evidence))
'''.replace('STAGE', repr(candidate['stage']))
result = json.loads(ssh('python3 -', remote, timeout=285))
(HERE / 'integration.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
summary = dict(result)
summary['cases'] = [{key: value for key, value in case.items() if key != 'samples'}
                    for case in result.get('cases', [])]
print(json.dumps(summary, ensure_ascii=False))
if result.get('runner_exit_code') or not result.get('status', '').startswith('PASS_'):
    raise SystemExit(1)
