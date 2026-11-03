"""Copy one already installed public diagnostic's source, never execute it."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
transport=HERE.parents[1]/'2026-10-18_board_dialogue/board_ssh.py'
spec=importlib.util.spec_from_file_location('axis_diag_source_transport',transport)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
source="""import hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='903cfade-b93c-48fa-804e-379be1967313'
root=Path('/home/root/aura-pan-wide-20261028/control-10282601')
manifest=json.loads((root/'deployment-manifest.json').read_bytes())
path=root/'run_input_diagnostics.py'
raw=path.read_bytes()
entry=next(x for x in manifest['files'] if x['destination']==str(path))
assert hashlib.sha256(raw).hexdigest()==entry['sha256']
print(json.dumps({'path':str(path),'sha256':entry['sha256'],'text':raw.decode(),'executed':False,'board_mutations':False}))
"""
value=json.loads(module.ssh('python3 -B -',source,timeout=20))
target=HERE/'input_diagnostics_original_source.json'
with target.open('x',encoding='utf-8') as stream:
    json.dump({'host_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'board_result':value},stream,ensure_ascii=False,indent=2)
    stream.write('\n')
snapshot=HERE/'original_sources'/(value['sha256'][:12]+'__run_input_diagnostics.py')
snapshot.write_text(value['text'],encoding='utf-8')
print(value['text'])
