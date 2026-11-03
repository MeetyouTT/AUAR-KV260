"""Root: verify current public sources and preserve publication receipts."""
import argparse,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPAIR=HERE.parent
PROJECT=HERE.parents[4]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE=r'''
import hashlib,json,pathlib,subprocess,time
p=pathlib.Path(SPEC['target']);sha=lambda b:hashlib.sha256(b).hexdigest()
assert p==pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
boot=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot==SPEC['boot_id']
raw=(p/'startup/config.json').read_bytes();assert sha(raw)==SPEC['startup_sha256']
startup=json.loads(raw);pins=startup['component_sha256'];assert len(pins)==379
for rel,pin in pins.items():
 path=p/'runtime/aura'/rel;assert path.resolve()==path and sha(path.read_bytes())==pin
manifest=(p/'production_source_manifest.json').read_bytes();assert sha(manifest)==SPEC['source_manifest_sha256']
assert json.loads(manifest)['component_pins']==pins
cfgraw=(p/'runtime/aura/config/board_avatar_gtk.json').read_bytes();assert sha(cfgraw)==SPEC['configuration_sha256']
cfg=json.loads(cfgraw)
assert cfg['character_pair']['selection_sha256']==SPEC['character_pair_selection_sha256']
assert pins['tools/libaura_yuki.so']==SPEC['native_library_sha256']
assert cfg['board_business']['asr_variant']=='paraformer_small' and cfg['board_business']['asr_threads']==3
unit=dict(x.split('=',1) for x in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','ExecMainStatus','-p','NRestarts'],text=True).splitlines())
assert unit['ActiveState']=='active' and unit['SubState']=='running' and int(unit['MainPID'])==READY['main_pid']
def identity(pid):
 s=pathlib.Path('/proc/%s/stat'%pid).read_text().rsplit(')',1)[1].split()
 return dict(pid=int(pid),birth_ticks=int(s[19]))
camera=identity(260102);assert camera['birth_ticks']==784437
print(json.dumps(dict(status='V17_SOURCE_AND_SERVICE_VERIFIED',observed_mono=time.monotonic(),boot_id=boot,
 root=str(p),startup_sha256=sha(raw),source_manifest_sha256=sha(manifest),configuration_sha256=sha(cfgraw),
 component_pins=pins,unit=unit,supervisor=identity(unit['MainPID']),gtk=identity(READY['gtk_pid']),camera=camera,
 private_data_exported=False)))
'''

def main():
 p=argparse.ArgumentParser();p.add_argument('--ready',type=Path,required=True);p.add_argument('--installed',type=Path,required=True);a=p.parse_args()
 spec=json.loads((HERE/'v17_spec.json').read_bytes());ready=json.loads(a.ready.read_bytes())
 assert ready['status']=='PRODUCTION_BOARD_BUSINESS_READY' and ready['guard_removed']
 assert ready['listening_enabled'] is False and ready['physical_microphone_opened'] is False
 result=json.loads(ssh('python3 -B -','SPEC='+repr(spec)+'\nREADY='+repr(ready)+'\n'+REMOTE,timeout=60))
 out=HERE/'v17_evidence';out.mkdir()
 for name,path in {'spec.json':HERE/'v17_spec.json','ready.json':a.ready,'installed.json':a.installed,
                   'observation.json':REPAIR/'v17_ready.json'}.items():
  (out/name).write_bytes(path.read_bytes())
 (out/'source_mapping.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 # Canonical current receipts advance only after verification; original bytes remain archived.
 acceptance=REPAIR.parent/'production_business_acceptance'
 for name,new in [('spec.json',(out/'spec.json').read_bytes()),('actual_ready.json',(out/'ready.json').read_bytes())]:
  (out/('previous_canonical_'+name)).write_bytes((acceptance/name).read_bytes())
  (acceptance/name).write_bytes(new)
 print(json.dumps(dict(status=result['status'],directory=str(out),startup_sha256=result['startup_sha256'],
   source_manifest_sha256=result['source_manifest_sha256'],component_count=len(result['component_pins']),
   supervisor=result['supervisor'],gtk=result['gtk'],camera=result['camera'],pause_preserved=True)))

if __name__=='__main__':main()
