"""Reuse the audited idle-only UI transaction with a one-file candidate."""
import ast,json,xml.etree.ElementTree as ET
from pathlib import Path
from maintenance import H,read,save,capture,same
from board_guard import SCRIPT,ssh
b=read('board_stage_baseline.json');same(b,capture());same(b,capture())
c=read('board_candidate.json');assert c['changed']==['board/runtime/device_observer.py']
assert read('services_ready.json')['status']=='READY'
suite=ET.parse(H/'tests.xml').getroot()
assert all(int(s.get('failures',0))==0 and int(s.get('errors',0))==0 for s in suite.iter('testsuite'))
# Only the reviewed remote transaction body is reused. Its historical top-level
# installer, manifests and original baseline are never executed or overwritten.
tree=ast.parse((H.parent/'2026-10-29_parallel_interaction/deploy_final_board.py').read_text(encoding='utf-8'))
body=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'def stable(v):' in n.value)
body=body.replace('-aura-identity-bridge-20261030.conf','-aura-board-vision-20261030.conf')
body=body.replace('BASE',repr(b)).replace('CANDIDATE',repr(c)).replace('GUARD',repr(SCRIPT))
assert not (H/'board_deployment.json').exists(),'Do not replay a committed UI transaction'
v=json.loads(ssh('python3 -B -',body,timeout=200));save('board_deployment.json',v)
print(json.dumps({k:v.get(k) for k in ('status','runtime','pins','optimized_launcher_preserved','camera_process_unchanged','error','rollback_error')}))
raise SystemExit(0 if v['status']=='COMMITTED' else 1)
