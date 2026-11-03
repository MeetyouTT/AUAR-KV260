"""Classify fixed frontend protocol errors without exporting raw error text."""
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[3]/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
REMOTE=r'''
import ast,http.client,json,pathlib
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/runtime/aura')
codes=set()
for rel in ('board/runtime/audio/board_frontend_auto.py','board/runtime/audio/board_frontend_process.py'):
 tree=ast.parse((root/rel).read_bytes())
 codes.update(n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.startswith('frontend_') and n.value.replace('_','').isalnum())
c=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
try:
 c.request('GET','/api/state');r=c.getresponse();v=json.loads(r.read(1048577));assert r.status==200
finally:c.close()
out={}
for key in ('local_recording','local_transcription','audio_frontend','handsfree_dialogue'):
 row=v.get(key,{})
 if isinstance(row,dict):
  error=row.get('error','');out[key]=dict(error_code=error if error in codes or error=='' else 'other',error_present=bool(error))
print(json.dumps(out))
'''
if __name__=='__main__':
 value=json.loads(ssh('python3 -B -',REMOTE,timeout=15));(HERE/'capture_control_failure.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');print(json.dumps(value))
