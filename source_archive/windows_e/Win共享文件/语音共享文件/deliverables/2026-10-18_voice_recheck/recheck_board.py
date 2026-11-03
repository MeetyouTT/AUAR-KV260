"""Retest the existing isolated board receiver without changing board services."""
import json
from pathlib import Path
import sys
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

previous=json.loads((ROOT/'deliverables/2026-10-18_voice_channel/actual_board_channel.json').read_text(encoding='utf-8'))
stage=previous['board_stage']
run_id=uuid.uuid4().hex[:12]
remote=r'''
import json,subprocess,sys,urllib.request
from pathlib import Path
stage=Path(STAGE)
report=stage/REPORT_NAME
result=subprocess.run([sys.executable,'-B',str(stage/'aura/tools/probe_voice_channel.py'),
    '--wav',str(stage/'data/historical.wav'),'--rounds','2','--report',str(report)],
    capture_output=True,text=True,timeout=210)
if result.returncode:raise RuntimeError(result.stderr[-2000:])
data=json.loads(report.read_text())
u=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
data.update(board_stage=str(stage),board_services_modified=False,board_models_installed=False,
            board_after={'phase':u.get('phase'),'playing':u.get('playing'),'error':u.get('error')})
print(json.dumps(data))
'''.replace('STAGE',repr(stage)).replace('REPORT_NAME',repr('recheck-'+run_id+'.json'))
report=json.loads(ssh('python3 -',remote,timeout=225))
(HERE/'actual_board_probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':report['status'],'same_tcp_connection':report['same_tcp_connection'],
                  'first_pcm_ms':[t['first_pcm_ms'] for t in report['turns']],
                  'total_ms':[t['total_ms'] for t in report['turns']],
                  'board_after':report['board_after']}))
