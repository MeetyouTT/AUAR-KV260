"""Measure native incompatibility cost without generating tokens."""
import importlib.util,json,sys,threading,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;AURA=HERE.parents[1]/'aura'
sys.path.insert(0,str(AURA))
from tools.dialogue_stream import stream_body
spec=importlib.util.spec_from_file_location('candidate_native',HERE/'candidate_source/tools/native_grammar.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.__file__=str(AURA/'tools/native_grammar.py')
config=json.loads((AURA/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
model=config.get('model')
if not model:
 import urllib.request
 with urllib.request.urlopen('http://127.0.0.1:11435/api/tags',timeout=4) as r:model=json.load(r)['models'][0]['name']
body=stream_body(model,[],'你好',reply_first=True)
rows=[]
for _ in range(3):
 started=time.perf_counter()
 try:
  result=m.prepare('http://127.0.0.1:11435',body,8,threading.Event());status=result[2]
 except Exception as e:status={'error':type(e).__name__+': '+str(e)}
 rows.append(dict(elapsed_ms=(time.perf_counter()-started)*1000,**status))
v={'measurements':rows,'generated_tokens':False,'production_code_changed':False,'other_models_unloaded':False}
(HERE/'native_preparation_probe.json').write_text(json.dumps(v,indent=2),encoding='utf-8');print(json.dumps(v))

