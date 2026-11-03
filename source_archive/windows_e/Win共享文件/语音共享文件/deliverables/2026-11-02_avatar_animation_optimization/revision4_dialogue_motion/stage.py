from common import *
if __name__=='__main__':
    e=load(HERE/'validation/FRESH_BEFORE_R4.json');assert not e['bad_pins'] and e['component_count']==380
    assert e['component_sha256']['tools/libaura_yuki.so']==sha(BASE/'revision3_natural_lower_arm/board_results/build/libaura_yuki.so')
    assert e['component_sha256']['tools/native_yuki.py']==sha(HERE/'baseline/runtime/tools/native_yuki.py')
    names={}
    for folder in ('baseline','candidate','tests'):
        for p in (HERE/folder).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:names[p.relative_to(HERE).as_posix()]=p.read_bytes()
    for name in ('build.py','DEVICE_HANDOFF_R4.json'):names[name]=(HERE/name).read_bytes()
    names['expected.json']=(json.dumps(e)+'\n').encode()
    original=PROJECT/'deliverables/2026-10-30_board_owner/integration/dialogue_repair/animation_thinking_collaboration/NATIVE_BASELINE.json'
    names['original_native_pins.json']=original.read_bytes()
    identity=hashlib.sha256(b''.join(name.encode()+hashlib.sha256(data).digest() for name,data in sorted(names.items()))).hexdigest()
    stage='/home/root/aura-avatar-animation-20261102/r4-'+identity[:16]
    payload={k:base64.b64encode(v).decode() for k,v in names.items()}
    script='STAGE='+repr(stage)+'\nFILES='+repr(payload)+'\n'+'''from pathlib import Path
import base64,json
p=Path(STAGE);p.mkdir(parents=True,exist_ok=False)
for name,data in FILES.items():
 q=p/name;assert q.resolve().is_relative_to(p.resolve());q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(base64.b64decode(data))
print(json.dumps({'status':'R4_NEW_STAGE_CREATED','files':len(FILES)}))
'''
    save(HERE/'STAGE_INTENT.json',dict(stage=stage,files={k:hashlib.sha256(v).hexdigest() for k,v in names.items()},fresh_startup=e['startup_sha256'],handoff_id=load(HERE/'DEVICE_HANDOFF_R4.json')['handoff_id']))
    print(board(script).decode())
