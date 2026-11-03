"""Read only public production source/config via the verified existing SSH helper."""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[2]
HELPER = OUT.parent / '2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec = importlib.util.spec_from_file_location('strict_original_board_ssh', HELPER)
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
remote = r'''
import datetime,hashlib,json
from pathlib import Path
root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
startup=root/'startup/config.json'
initial=startup.read_bytes()
sources={}
for relative in ('runtime/aura/board/runtime/board_dialogue_client.py',
                 'runtime/aura/common/board_timeline_clock.py',
                 'runtime/aura/board/runtime/board_business.py',
                 'runtime/aura/tools/production_board_business_gui.py'):
    data=(root/relative).read_bytes()
    sources[relative]={'sha256':hashlib.sha256(data).hexdigest(),'source':data.decode('utf-8')}
config=json.loads(initial)
allowed={'model_port','timeout_ms','asr_threads','frontend_threads','frontend_process',
         'frontend_capture_process','capture_priority_nice','retention_enabled'}
filtered=[]
def visit(value):
    if isinstance(value,dict):
        business=value.get('board_business')
        if isinstance(business,dict):
            filtered.append({k:v for k,v in business.items() if k in allowed and type(v) in (int,float,bool)})
        for child in value.values():visit(child)
    elif isinstance(value,list):
        for child in value:visit(child)
visit(config)
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'startup_sha256':hashlib.sha256(initial).hexdigest(),
    'startup_unchanged_during_read':startup.read_bytes()==initial,
    'filtered_public_startup_options':filtered,'sources':sources,
    'only_public_source_and_startup_reads':True,'production_mutations':False}))
'''
data = json.loads(transport.ssh('python3 -B -', remote, timeout=25))
for relative, entry in data['sources'].items():
    target = HERE / 'current_public_source' / relative.removeprefix('runtime/aura/')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(entry.pop('source').encode('utf-8'))
    assert hashlib.sha256(target.read_bytes()).hexdigest() == entry['sha256']
(HERE / 'SOURCE_METADATA.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(data, ensure_ascii=False))
