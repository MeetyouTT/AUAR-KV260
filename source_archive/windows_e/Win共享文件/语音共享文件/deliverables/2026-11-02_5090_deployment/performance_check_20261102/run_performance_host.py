"""Run a bounded passive observer; store technical measurements only."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
current = json.loads((OUT/'DEPLOYMENT_CURRENT.json').read_text(encoding='utf-8'))
expected = {'camera_pid':current['camera_owner']['pid'],
            'gui_pid':current['gui_owners']['supervisor']['pid'],
            'gtk_pid':current['gui_owners']['gtk']['pid']}
source = (HERE/'collect_board_performance.py').read_text(encoding='utf-8')
code = 'EXPECTED = '+repr(expected)+'\n'+source
compile(code,'<board-performance-observer>','exec')
helper = OUT.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec = importlib.util.spec_from_file_location('perf_transport',helper)
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
result = json.loads(transport.ssh('/usr/bin/python3 -B -I -S -',code,timeout=55))
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%H%M%S')
destination = HERE/('BOARD_PERFORMANCE_'+stamp+'.json')
with destination.open('x',encoding='utf-8') as stream:
    json.dump({'host_finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'collector_sha256_lf':hashlib.sha256(code.encode()).hexdigest(),'board_result':result},stream,indent=2)
    stream.write('\n')
print(json.dumps({'receipt':str(destination),'duration_seconds':result['duration_seconds'],
    'samples':len(result['snapshots']),'health_samples':len(result['health_samples']),
    'startup_unchanged':result['startup_before_sha256']==result['startup_after_sha256']}))
