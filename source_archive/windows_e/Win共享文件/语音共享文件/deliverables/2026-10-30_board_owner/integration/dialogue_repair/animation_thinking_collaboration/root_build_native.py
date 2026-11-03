"""Root-only bounded isolated native build. Never installs or opens display/audio."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import zipfile

HERE=Path(__file__).resolve().parent
REPAIR=HERE.parent
PROJECT=REPAIR.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

if __name__=='__main__':
    handoff_raw=(HERE/'HANDOFF.json').read_bytes()
    assert hashlib.sha256(handoff_raw).hexdigest()=='75e80fefba9519c77ed6bcb54e7293791c6a2f5944f404842aa0171a5ba69b54'
    handoff=json.loads(handoff_raw)
    archive=HERE/'native_build_source.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest()=='935cb9b30f726fbb0c118b8723dd2d82df8ca23f47b680914f86f29392348aab'
    expected={k:handoff['helper_pins'][k] for k in ('build_native_isolated.py','NATIVE_BASELINE.json','tests/native_eye_gate.cpp')}
    expected['SOURCE_MANIFEST.json']=handoff['source_manifest_sha256']
    expected.update({'candidate/'+k:v['after_sha256'] for k,v in handoff['files'].items() if k.startswith('native/')})
    files=[]
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist())==set(expected)
        for rel,pin in expected.items():
            raw=z.read(rel);assert hashlib.sha256(raw).hexdigest()==pin
            files.append(dict(relative_path=rel,sha256=pin,bytes=len(raw),base64=base64.b64encode(raw).decode()))
    source=REPAIR/'frontend_allocation_candidate/public_probe/root_run_abba.py'
    spec=importlib.util.spec_from_file_location('_reviewed_root_slot',source)
    base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    stage='/home/root/aura-animation-thinking-20261031/935cb9b30f726fbb'
    old='/home/root/aura-public-frontend-allocation-20261031/c7988d2439fbb0d7'
    assert base.REMOTE.count(old)==1 and base.REMOTE.count('timeout=85')==1
    remote=base.REMOTE.replace(old,stage).replace('timeout=85','timeout=250')
    assert remote.count('before=guard.metadata(args)')==1
    remote=remote.replace('before=guard.metadata(args)','before=guard.metadata(args,allow_background=True)')
    installed=json.loads((REPAIR.parent/'production_business_acceptance/spec.json').read_bytes())
    assert installed['startup_sha256']=='bf6cdd70768ea5fac4e5be874a387f444c0834d67db5e7a2a744671d9019d63c'
    root='/home/root/aura-board-business-20261030/production-5259eab11e42af13/runtime/aura/assets/yuki'
    values=dict(STAGE=stage,FILES=files,BOOT=installed['boot_id'],EXPECTED=installed['startup_sha256'],
        SLOT='isolated-native-thinking-build',ARM='candidate-not-installed',ARGV=[
        'timeout','--signal=TERM','--kill-after=5s','240s','/usr/bin/python3','-B',stage+'/build_native_isolated.py',
        '--native-root','/home/root/aura-yuki-validation-20261030/native_integration',
        '--model',root+'/model.runtime.json','--resx',root+'/yuk_0.ems.resx.json','--resource-root',root])
    result=json.loads(ssh('python3 -B -','\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+remote,timeout=285))
    result.update(native_bundle_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        source_handoff_sha256=hashlib.sha256(handoff_raw).hexdigest(),
        root_runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        stage=stage,production_installed=False,display_opened=False)
    output=HERE/('ACTUAL_NATIVE_BUILD_'+str(time.time_ns())+'.json')
    with output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(output=str(output),status=result['result'].get('status'),exit_code=result['exit_code'],
        elapsed_seconds=result['elapsed_seconds'],manual_pause_preserved=result['manual_pause_preserved'],
        owners_unchanged=result['owners_unchanged'])))
