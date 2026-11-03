"""Stage the latest candidate first, then exercise cancellation on real hardware."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
candidate=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
remote=r'''
import json,subprocess
from pathlib import Path
stage=Path(STAGE)
result=subprocess.run(['python3','-B',str(stage/'cancellation_runner.py'),'--stage',str(stage)],
                      capture_output=True,text=True,timeout=210)
path=stage/'cancellation.json'
report=json.loads(path.read_text()) if path.is_file() else {'status':'FAIL_NO_REPORT'}
report['runner_exit_code']=result.returncode
report['runner_output_tail']=(result.stdout+result.stderr)[-3000:]
print(json.dumps(report))
'''.replace('STAGE',repr(candidate['stage']))
report=json.loads(ssh('python3 -',remote,timeout=220))
(HERE/'cancellation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
if report.get('runner_exit_code') or not report.get('status','').startswith('PASS_'):raise SystemExit(1)
