"""Check a disposable Python import; no production or audio operations."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import importlib.util,json,subprocess,sys
s=importlib.util.find_spec('onnxruntime')
r=subprocess.run([sys.executable,'-B','-c','import onnxruntime as o;print(o.__version__)'],capture_output=True,text=True,timeout=12)
print(json.dumps({'python':sys.executable,'package_origin':s.origin,'simple_import_returncode':r.returncode,
 'stdout':r.stdout[-1200:],'stderr':r.stderr[-1600:],'production_changed':False}))
'''
r=json.loads(ssh('python3 -B -',remote,timeout=20))
(HERE/'board_runtime_diagnostic.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(json.dumps(r))
