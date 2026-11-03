#!/usr/bin/env python3
"""Check embedded remote syntax and the exact UART wrapper line lengths offline."""
import ast
import base64
import gzip
import json
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parents[1]
transport = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
tree = ast.parse(transport.read_text())
method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'command')
wrapper = ast.literal_eval(method.body[0].value)
loader = ast.parse((ROOT/'scripts/uart_load.py').read_text())
constants = {n.targets[0].id:ast.literal_eval(n.value) for n in loader.body
    if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)
    and n.targets[0].id in ('COMMON','PREPARE','EXTRACT','INSTALL','UNLOAD','LOAD','RESTORE')}
burst = ast.parse((ROOT/'scripts/uart_burst.py').read_text())
snippets = [n.value.value for n in ast.walk(burst) if isinstance(n,ast.AugAssign)
    and isinstance(n.target,ast.Name) and n.target.id == 'source' and isinstance(n.value,ast.Constant)]
operation = next(x for x in snippets if 'action=sys.argv[3]' in x)
stop = next(x for x in snippets if "package/'board/probe.py'),'--stop'" in x)
ident = json.loads((ROOT/'evidence/source_identity.json').read_text())
dest = '/home/root/aura-square10-stage/20261005T000000.000000Z/aura-square10-stage.tar.gz'
sha = '0'*64

def wire_length(source, marker, action=None):
    source = source.replace('BUILD_ID_PLACEHOLDER',hex(int(ident['build_id'],16)))
    compile(source, '<reviewed-remote>', 'exec')
    data = base64.b64encode(gzip.compress(source.encode(),mtime=0)).decode()
    code = 'import base64,gzip;exec(gzip.decompress(base64.b64decode('+repr(data)+')))'
    command = 'python3 -B -c '+shlex.quote(code)+' '+shlex.quote(dest)+' '+sha
    if action:
        command += ' '+action
    wire = 'python3 -B -c '+shlex.quote(wrapper)+' '+shlex.quote(base64.b64encode(command.encode()).decode())+' '+marker
    assert len(wire.encode()) <= 3800, (marker,len(wire))
    return len(wire.encode())

lengths = {k:wire_length(constants['COMMON']+v,'PWM_LOAD_'+k)
    for k,v in constants.items() if k != 'COMMON'}
for action in ('inspect','scratch','start','stop'):
    lengths[action] = wire_length(constants['COMMON']+operation,'PWM_'+action.upper(),action)
for index in range(1,5):
    lengths['watch_'+str(index)] = wire_length(constants['COMMON']+operation,'PWMW'+str(index),'inspect')
lengths['restore'] = wire_length(constants['COMMON']+stop+constants['RESTORE'],'PWM_RESTORE','restore')
for p in (ROOT/'scripts').glob('*.py'):
    ast.parse(p.read_text())
report = {'passed':True,'wire_lengths':lengths,'limit':3800,
    'transport_sha256':__import__('hashlib').sha256(transport.read_bytes()).hexdigest(),
    'board_accessed':False}
(ROOT/'evidence/transport_review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
