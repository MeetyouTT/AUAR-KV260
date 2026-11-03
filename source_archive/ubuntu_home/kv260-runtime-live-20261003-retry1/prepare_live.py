#!/usr/bin/env python3
"""Prepare independent reviewed UART manifests; never open UART here."""
import ast
import base64
import gzip
import hashlib
import json
from pathlib import Path
import shlex

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'evidence'
CONFIG = Path('/home/ghmd/kv260-runtime-submission-20261002/payload_v2/config')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def wire(code):
    compile(code, 'reviewed_action', 'exec')
    encoded = base64.b64encode(gzip.compress(code.encode(), mtime=0)).decode()
    command = 'python3 -B -c ' + shlex.quote('import base64,gzip;exec(gzip.decompress(base64.b64decode(' + repr(encoded) + ')))')
    assert len(command)*4/3+850 < 3900, len(command)
    return command

def manifest(name, entries):
    path = EVIDENCE / (name + '.commands.json')
    assert not path.exists()
    sources = ROOT / 'action_sources'
    sources.mkdir(exist_ok=True)
    rows = []
    for key, code, timeout in entries:
        p = sources / (name+'.'+key+'.py')
        assert not p.exists()
        p.write_text(code)
        rows.append({'id':key,'command':wire(code),'timeout':timeout})
    path.write_text(json.dumps(rows, indent=2)+'\n')

def preflight():
    original = Path('/home/ghmd/kv260-dfx-manager-repair-20261002/scripts/prepare_board_preflight.py')
    tree = ast.parse(original.read_text())
    code = next(n.value.value for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in n.targets) and isinstance(n.value,ast.Constant))
    code += "\nassert not [c for c in clients if c['target'] in ['/dev/dri/card1','/dev/dri/renderD128']],'ZOCL clients present'\nassert (mod/'refcnt').read_text().strip()=='0' and not list((mod/'holders').iterdir())\nassert os.readlink('/proc/%d/exe'%pid)=='/usr/bin/dfx-mgrd'\nassert not subprocess.check_output(['systemctl','show','dfx-mgr.service','--property=DropInPaths','--value'],text=True).strip()\n"
    inputs = json.loads((CONFIG/'baseline_inputs.json').read_text())
    entries = [('inventory',code,180)]
    items = list(inputs.items())
    for index in range(0,len(items),9):
        part = dict(items[index:index+9])
        text = "import json,hashlib\nfrom pathlib import Path\nexpected="+repr(part)+"\nactual={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in expected}\nprint(json.dumps(actual,indent=2),flush=True)\nassert actual==expected,'Baseline file hash differs'\n"
        entries.append(('hashes-'+str(index//9),text,120))
    entries.append(('kernel',"import subprocess\nsubprocess.run(['dmesg'],check=True)\n",180))
    manifest('preflight',entries)

if __name__=='__main__':
    preflight()
