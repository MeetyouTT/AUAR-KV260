import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'snapshot_fix_candidate.json').read_text())
test=base64.b64encode((HERE/'test_snapshot_fix.py').read_bytes()).decode()
remote=r'''
import json,subprocess,base64,os,copy,time,statistics,urllib.request
from pathlib import Path
root=Path(ROOT);test=root.parent/'test_snapshot_fix.py';test.write_bytes(base64.b64decode(TEST))
env=dict(os.environ,PYTHONPATH=str(root/'aura'),PYTHONDONTWRITEBYTECODE='1')
r=subprocess.run(['python3','-B',str(test)],env=env,capture_output=True,text=True,timeout=25)
assert r.returncode==0,r.stdout+r.stderr
import sys
sys.path.insert(0,str(root/'aura'))
from tools.board_avatar_worker import snapshot_copy
s=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5))
timings={}
for label,fn in [('deepcopy',copy.deepcopy),('snapshot_copy',snapshot_copy)]:
 values=[]
 for i in range(100):
  at=time.perf_counter();out=fn(s);values.append((time.perf_counter()-at)*1000)
 assert out==s
 timings[label]=statistics.median(values)
print(json.dumps(dict(passed=True,out=r.stdout,error=r.stderr,snapshot_median_ms=timings)))
'''.replace('ROOT',repr(c['runtime']),1).replace('TEST',repr(test),1)
r=json.loads(ssh('python3 -B -',remote,timeout=45));(HERE/'snapshot_fix_tests.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
