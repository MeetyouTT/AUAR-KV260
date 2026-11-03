"""Seal public source provenance and pause-preserving publication receipts."""
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
REPAIR=HERE.parent
PROJECT=HERE.parents[4]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE=r'''
import hashlib,json,pathlib,subprocess,time
p=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
sha=lambda b:hashlib.sha256(b).hexdigest()
raw=(p/'startup/config.json').read_bytes();startup=json.loads(raw)
assert sha(raw)=='bf6cdd70768ea5fac4e5be874a387f444c0834d67db5e7a2a744671d9019d63c'
pins=startup['component_sha256'];assert len(pins)==378
for rel,pin in pins.items():assert sha((p/'runtime/aura'/rel).read_bytes())==pin
manifest=(p/'production_source_manifest.json').read_bytes()
assert sha(manifest)=='e488f45660e78904d04ba57fe4210e2bcf9eeffa6282219096e9d7b6115df718'
cfg=json.loads((p/'runtime/aura/config/board_avatar_gtk.json').read_bytes())
unit=dict(x.split('=',1) for x in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','ExecMainStatus','-p','NRestarts'],text=True).splitlines())
def identity(pid):
 s=pathlib.Path('/proc/%s/stat'%pid).read_text().rsplit(')',1)[1].split()
 return dict(pid=int(pid),birth_ticks=int(s[19]))
assert unit['ActiveState']=='active' and unit['SubState']=='running'
print(json.dumps(dict(status='V16_SOURCE_AND_SERVICE_VERIFIED',observed_mono=time.monotonic(),
 boot_id=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 root=str(p),startup_sha256=sha(raw),source_manifest_sha256=sha(manifest),
 component_pins=pins,unit=unit,supervisor=identity(unit['MainPID']),camera=identity(260102),
 private_data_exported=False)))
'''

if __name__=='__main__':
    result=json.loads(ssh('python3 -B -',REMOTE,timeout=60))
    out=HERE/'v16_evidence';out.mkdir(exist_ok=True)
    sources={
        'ready.json':REPAIR.parent/'production_business_acceptance/actual_ready.json',
        'spec.json':REPAIR.parent/'production_business_acceptance/spec.json',
        'installed.json':REPAIR.parent/'listening_entry_fix/actual_automatic-listening-v16-small-asr.json',
        'observation.json':REPAIR/'v16_small_ready.json',
    }
    for name,path in sources.items():
        raw=path.read_bytes();dest=out/name
        if dest.exists():assert dest.read_bytes()==raw
        else:dest.write_bytes(raw)
    ready=json.loads((out/'ready.json').read_bytes())
    assert ready['status']=='PRODUCTION_BOARD_BUSINESS_READY' and ready['guard_removed']
    assert ready['listening_enabled'] is False and ready['physical_microphone_opened'] is False
    dest=out/'source_mapping.json'
    assert not dest.exists()
    dest.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],directory=str(out),supervisor=result['supervisor'],camera=result['camera'],listening='PAUSED',files=list(sources)+['source_mapping.json'])))
