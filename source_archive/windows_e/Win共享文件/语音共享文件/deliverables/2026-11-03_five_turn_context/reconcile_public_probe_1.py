"""Read only: identify import failure before any inference request."""
import importlib, json, sys, http.client
from pathlib import Path
cfg=json.loads(Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json').read_bytes())
sys.path.insert(0,str(Path(cfg['runtime'])/'aura'))
checks=[]
for name in ('common.board_memory','common.character_profile','common.model_inference_wire','board.runtime.board_memory_policy','board.runtime.board_dialogue','board.runtime.compact_request_adapter'):
    try:importlib.import_module(name);checks.append(dict(module=name,ok=True))
    except Exception as e:checks.append(dict(module=name,ok=False,error_type=type(e).__name__,detail=str(e)[:150]))
c=http.client.HTTPConnection('192.168.50.1',8797,timeout=3)
try:
    c.request('GET','/health');r=c.getresponse();health=json.loads(r.read(1000000))
finally:c.close()
print(json.dumps(dict(status='PUBLIC_PROBE_RECONCILED',imports=checks,health=health,control_writes=0,inference_requests=0)))
