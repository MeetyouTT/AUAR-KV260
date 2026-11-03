"""Apply only the frozen GTK and audio-consumer sources after WM_DELETE.

The original GUI configuration, face readback and all other components are
retained byte-for-byte. Partial failures retain the no-force guard and backups.
"""
import argparse
import ast
import json
from pathlib import Path
import time

import stability_common as common


APPLY_REMOTE = r'''
import ast,base64,contextlib

def apply_minor_closed():
 boot();j=journal();inactive(j)
 need(j.get('phase')=='NORMAL_CLOSED' and j.get('boot_id')==SPEC['boot_id']
      and j.get('guard_removed') is False and j.get('active_root')==EXACT_TARGET,'normal_closed_current_owner_required')
 need(c.show()['ActiveState']=='inactive','naturally_closed_unit_required')
 root=Path(EXACT_TARGET);old_startup_raw=c.read(root/'startup/config.json',BASE_STARTUP_SHA)
 old_startup=c.parse(old_startup_raw)
 need(old_startup==BASE_STARTUP_OBJECT and old_startup['component_sha256']==BASE_PINS,'exact_current_startup_required')
 for rel,pin in BASE_PINS.items():c.read(root/'runtime/aura'/c.relative(rel),pin)
 gui_raw=c.read(root/'runtime/aura/config/board_avatar_gtk.json',BASE_CONFIG_SHA)
 need(c.parse(gui_raw)==EXPECTED_GUI,'current_gui_configuration_changed')
 old_manifest_raw=c.read(root/'production_source_manifest.json',BASE_MANIFEST_SHA)
 manifest=c.parse(old_manifest_raw)
 need(manifest['component_pins']==BASE_PINS and manifest['configuration_sha256']==BASE_CONFIG_SHA,'current_manifest_closure_changed')
 c.read(manifest['configuration_path'],BASE_CONFIG_SHA)
 reviewed_face()
 need(set(PAYLOAD)==set(FROZEN_SOURCES)==set(SPEC['minor_overrides']),'exact_frozen_minor_payload_required')
 new_files={}
 for rel,item in PAYLOAD.items():
  row=FROZEN_SOURCES[rel]
  need(SPEC['minor_overrides'][rel]==row and item['before_sha256']==row['before_sha256']==BASE_PINS[rel],'minor_source_baseline_changed')
  raw=base64.b64decode(item['base64'],validate=True)
  need(c.sha(raw)==item['sha256']==row['sha256'] and 0<len(raw)<2097152,'bounded_frozen_source_required')
  ast.parse(raw,feature_version=(3,9));new_files[rel]=raw
 new_startup_raw=c.encoded(EXPECTED_STARTUP)
 need(c.sha(new_startup_raw)==SPEC['startup_sha256'],'proposed_startup_bytes_changed')
 manifest['component_pins']=SPEC['component_sha256']
 for rel,raw in new_files.items():manifest['files']['runtime/aura/'+rel]=dict(sha256=c.sha(raw),bytes=len(raw))
 manifest['files']['startup/config.json']=dict(sha256=c.sha(new_startup_raw),bytes=len(new_startup_raw))
 manifest['minor_revision']=dict(name=MINOR_REVISION,previous_startup_sha256=BASE_STARTUP_SHA,
   previous_manifest_sha256=BASE_MANIFEST_SHA,sources={rel:c.sha(raw) for rel,raw in new_files.items()},
   gui_configuration_sha256=BASE_CONFIG_SHA,private_data_replayed=False)
 manifest_raw=c.encoded(manifest)
 completed_spec=dict(SPEC,minor_state='APPLIED',source_manifest_sha256=c.sha(manifest_raw))
 private=Path('/home/root/.local/share/aura-board-business')
 lock_paths=[Path('/run/aura-avatar-ui.lock'),private/'writer.lock',private/'speaker/speaker-writer.lock']
 with contextlib.ExitStack() as stack:
  for path in lock_paths:
   fd=os.open(str(path),os.O_RDWR|os.O_NOFOLLOW)
   stream=stack.enter_context(os.fdopen(fd,'r+b'))
   fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
  ownerless(c.show());guarded(j);reviewed_face()
  sys.path.insert(0,str(root/'runtime/aura'))
  from common.board_production_bootstrap import verify_production_bootstrap
  cfg=EXPECTED_GUI['board_business']
  proof=verify_production_bootstrap(private,cfg['bootstrap_receipt'],cfg['bootstrap_receipt_sha256'])
  need(proof['profiles_migration_verified'] is True,'production_bootstrap_not_verified')
  stage=CONTROL/MINOR_REVISION;stage.mkdir(mode=0o700)
  backup=stage/'before';backup.mkdir(mode=0o700)
  for name,raw in [('startup-config.json',old_startup_raw),('gui-config.json',gui_raw),
                   ('production-source-manifest.json',old_manifest_raw),('publication-state.json',c.read(STATE))]:
   c.create(backup/name,raw)
  for rel,raw in new_files.items():
   original=c.read(root/'runtime/aura'/rel,BASE_PINS[rel]);destination=backup/rel
   destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True);c.create(destination,original)
   destination=stage/'after'/rel;destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True);c.create(destination,raw)
  c.create(stage/'applied-spec.json',c.encoded(completed_spec))
  c.create(stage/'prepared-startup.json',new_startup_raw);c.create(stage/'prepared-manifest.json',manifest_raw)
  j.update(phase='MINOR_SOURCE_INSTALL_INTENT',minor_stage=str(stage),target_startup_sha256=SPEC['startup_sha256'])
  save(j)
  for rel,raw in new_files.items():atomic(root/'runtime/aura'/rel,raw)
  atomic(root/'startup/config.json',new_startup_raw);atomic(root/'production_source_manifest.json',manifest_raw)
  SPEC.update(minor_state='APPLIED',source_manifest_sha256=completed_spec['source_manifest_sha256'])
  source();ownerless(c.show());guarded(j)
  need(c.read(root/'runtime/aura/config/board_avatar_gtk.json',BASE_CONFIG_SHA)==gui_raw,'gui_configuration_changed_during_apply')
  j.update(phase='NORMAL_CLOSED',target_startup_sha256=SPEC['startup_sha256'],target_pins=379)
  save(j)
 return dict(status='MINOR_SOURCES_APPLIED_UI_STOPPED',spec=completed_spec,
   source_files={rel:c.sha(raw) for rel,raw in new_files.items()},backup_directory=str(backup),
   production_bootstrap_verified=True,profiles_migration_verified=True,
   gui_configuration_bytes_unchanged=True,private_data_replayed=False,ui_started=False,service_stop_or_kill=False)

with open('/run/aura-production-publisher.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 result=apply_minor_closed()
print(json.dumps(result,ensure_ascii=True))
'''


def build_remote(spec):
    remote=common.publisher_remote(spec)
    anchor="\nboot()\nwith open('/run/aura-production-publisher.lock','a') as lock:"
    if remote.count(anchor)!=1:
        raise ValueError('unique_publisher_dispatch_anchor_required')
    remote=remote.split(anchor,1)[0]
    before=common.baseline()
    startup=common.previous_publisher().inputs()[1]
    startup['component_sha256']=before['component_sha256']
    values=dict(BASE_PINS=before['component_sha256'],BASE_STARTUP_OBJECT=startup,
        BASE_STARTUP_SHA=common.BASE_STARTUP_SHA,BASE_CONFIG_SHA=common.BASE_CONFIG_SHA,
        BASE_MANIFEST_SHA=common.BASE_MANIFEST_SHA,MINOR_REVISION=common.MINOR_REVISION,
        FROZEN_SOURCES=common.approved_sources())
    remote='\n'.join(key+'='+repr(value) for key,value in values.items())+'\n'+remote+'\n'+APPLY_REMOTE
    ast.parse(remote,feature_version=(3,9))
    return remote


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec',type=Path,required=True)
    parser.add_argument('--spec-sha256',required=True)
    parser.add_argument('--execute-root-only',action='store_true')
    args=parser.parse_args()
    spec=common.validate_spec(json.loads(common.pinned(args.spec,args.spec_sha256)),allow_proposed=True)
    if spec['minor_state']!='PROPOSED':
        raise ValueError('proposed_minor_spec_required')
    remote=build_remote(spec);payload=common.payload_for(spec)
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_MINOR_APPLY_VALIDATED_NO_SSH',remote_sha256=common.sha(remote.encode()),
            source_files={rel:row['sha256'] for rel,row in payload.items()},source_count=len(payload))))
        return
    result=common.execute_remote(remote,dict(SPEC=spec,ACTION='start',TOKEN=None,WINDOW=None,PAYLOAD=payload),timeout=225)
    suffix=str(time.time_ns());output=common.HERE/('actual_apply_'+suffix+'.json')
    common.write_new_json(output,result)
    if result.get('status')!='MINOR_SOURCES_APPLIED_UI_STOPPED':
        raise ValueError('minor_apply_incomplete')
    completed=common.validate_spec(result['spec'])
    spec_path=common.HERE/('applied_spec_'+suffix+'.json')
    digest=common.write_new_json(spec_path,completed)
    print(json.dumps(dict(status=result['status'],output=str(output),spec=str(spec_path),spec_sha256=digest),ensure_ascii=True))


if __name__=='__main__':
    main()
