"""Verify the restored running source closure and advance local current receipts."""
import hashlib
import json
import os
import sys
from pathlib import Path

import minor_common as publication

HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE/'applied_spec_1793496827180069100.json'
READY_PATH = HERE/'actual_ready_1793496905162312800.json'
spec = json.loads(publication.pinned(SPEC_PATH,'c46d44e8583a8ccb8e02d9321b5c6edb9a681474913ba2689dd681d912c50cb2'))
publication.validate_spec(spec)
ready = json.loads(READY_PATH.read_bytes())
assert ready['status']=='PRODUCTION_BOARD_BUSINESS_READY' and ready['guard_removed']
assert ready['listening_enabled'] and ready['physical_microphone_opened']
sys.path.insert(0,str(publication.previous_publisher().PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE = r'''
import hashlib,json,pathlib,subprocess,time
root=pathlib.Path(SPEC['target']);sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==SPEC['boot_id']
startup=(root/'startup/config.json').read_bytes();assert sha(startup)==SPEC['startup_sha256']
pins=json.loads(startup)['component_sha256'];assert pins==SPEC['component_sha256'] and len(pins)==379
for rel,pin in pins.items():
 path=root/'runtime/aura'/rel;assert path.resolve()==path and sha(path.read_bytes())==pin
manifest_raw=(root/'production_source_manifest.json').read_bytes();assert sha(manifest_raw)==SPEC['source_manifest_sha256']
manifest=json.loads(manifest_raw)
assert manifest['component_pins']==pins and manifest['configuration_sha256']==SPEC['configuration_sha256']
assert sha(pathlib.Path(manifest['configuration_path']).read_bytes())==SPEC['configuration_sha256']
assert sha((root/'runtime/aura/config/board_avatar_gtk.json').read_bytes())==SPEC['configuration_sha256']
assert sha(pathlib.Path(SPEC['face_readback']['path']).read_bytes())==SPEC['face_readback']['sha256']
unit=dict(line.split('=',1) for line in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','ExecMainStatus','-p','NRestarts','-p','DropInPaths'],text=True).splitlines())
assert unit['MainPID']==str(READY['main_pid']) and unit['ActiveState']=='active' and unit['SubState']=='running'
control=json.loads((root.parent/'control-production-v1/state.json').read_bytes())
assert control['phase']=='COMMITTED' and control['guard_removed'] and unit['DropInPaths']==control['final_dropins']
def identity(pid):
 path=pathlib.Path('/proc')/str(pid);fields=(path/'stat').read_text().rsplit(')',1)[1].split()
 return {'pid':int(pid),'birth_ticks':int(fields[19]),'command_sha256':sha((path/'cmdline').read_bytes())}
camera=identity(SPEC['camera_owner']['camera_pid'])
assert str(camera['birth_ticks'])==SPEC['camera_owner']['camera_start_ticks'] and camera['command_sha256']==SPEC['camera_owner']['camera_cmdline_sha256']
print(json.dumps({'status':'MINOR_UI_WORKER_SOURCE_AND_SERVICE_VERIFIED','observed_mono':time.monotonic(),
 'boot_id':SPEC['boot_id'],'root':str(root),'startup_sha256':SPEC['startup_sha256'],
 'source_manifest_sha256':SPEC['source_manifest_sha256'],'configuration_sha256':SPEC['configuration_sha256'],
 'component_pins':pins,'unit':unit,'supervisor':identity(READY['main_pid']),'gtk':identity(READY['gtk_pid']),
 'camera':camera,'private_data_exported':False,'current_publication_committed':True}))
'''
value = json.loads(ssh('python3 -B -','SPEC='+repr(spec)+'\nREADY='+repr(ready)+'\n'+REMOTE,timeout=60))
directory = HERE/'minor_evidence'
directory.mkdir()
for name,path in {'spec.json':SPEC_PATH,'ready.json':READY_PATH,
                  'installed.json':HERE/'actual_apply_1793496827180069100.json'}.items():
    (directory/name).write_bytes(path.read_bytes())
(directory/'source_mapping.json').write_bytes(publication.encoded(value))
canonical = HERE.parent.parent/'production_business_acceptance'
for name,source in [('spec.json',SPEC_PATH),('actual_ready.json',READY_PATH)]:
    destination = canonical/name
    (directory/('previous_canonical_'+name)).write_bytes(destination.read_bytes())
    temporary = destination.with_name(destination.name+'.newboot-tmp')
    with temporary.open('xb') as stream:
        stream.write(source.read_bytes());stream.flush();os.fsync(stream.fileno())
    os.replace(temporary,destination)
print(json.dumps({'evidence':str(directory),**{key:value[key] for key in (
    'status','observed_mono','boot_id','startup_sha256','source_manifest_sha256','supervisor','gtk','camera')}}))
