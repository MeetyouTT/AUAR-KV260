"""Apply the reviewed five-source closure while the new-boot UI is ownerless.

Default prepares source and validates the local proposed spec without SSH.
The resulting APPLIED spec contains the actual source-manifest fingerprint.
"""
import argparse
import ast
import base64
import json
from pathlib import Path
import sys
import time

import publish_newboot as publish


APPLY_REMOTE = r'''
import ast,base64,contextlib

def apply_closed():
 boot();j=journal();inactive(j)
 need(j.get('phase')=='NEW_BOOT_OWNERLESS' and j.get('boot_id')==SPEC['boot_id']
      and j.get('guard_removed') is False and j.get('active_root')==EXACT_TARGET,'newboot_ownerless_guard_required')
 root=Path(EXACT_TARGET);old_startup_raw=c.read(root/'startup/config.json',BASE_STARTUP_SHA)
 old_startup=c.parse(old_startup_raw)
 need(old_startup==BASE_STARTUP_OBJECT and old_startup['component_sha256']==BASE_PINS,'exact_v18_startup_required')
 for rel,pin in BASE_PINS.items():c.read(root/'runtime/aura'/c.relative(rel),pin)
 old_gui_raw=c.read(root/'runtime/aura/config/board_avatar_gtk.json',BASE_CONFIG_SHA)
 need(c.parse(old_gui_raw)==BASE_GUI_OBJECT,'exact_v18_gui_required')
 old_manifest_raw=c.read(root/'production_source_manifest.json',BASE_MANIFEST_SHA)
 manifest=c.parse(old_manifest_raw)
 need(manifest['component_pins']==BASE_PINS,'exact_v18_manifest_closure_required')
 reviewed_face()
 need(set(PAYLOAD)==set(SPEC['source_overrides']),'payload_keys_changed')
 new_files={}
 for rel,item in PAYLOAD.items():
  row=SPEC['source_overrides'][rel]
  need(item['before_sha256']==row['before_sha256']==BASE_PINS[rel],'source_baseline_changed')
  raw=base64.b64decode(item['base64'],validate=True)
  need(c.sha(raw)==item['sha256']==row['sha256'] and 0<len(raw)<2097152,'bounded_reviewed_python_source_required')
  ast.parse(raw,feature_version=(3,9));new_files[rel]=raw
 new_gui_raw=c.encoded(EXPECTED_GUI);new_startup_raw=c.encoded(EXPECTED_STARTUP)
 need(c.sha(new_gui_raw)==SPEC['configuration_sha256'] and c.sha(new_startup_raw)==SPEC['startup_sha256'],'proposed_configuration_bytes_changed')
 stage=CONTROL/('newboot-'+SPEC['boot_id']+'-sources')
 manifest['configuration_sha256']=c.sha(new_gui_raw)
 manifest['configuration_path']=str(stage/'prepared-gui.json')
 manifest['component_pins']=SPEC['component_sha256']
 for rel,raw in new_files.items():manifest['files']['runtime/aura/'+rel]=dict(sha256=c.sha(raw),bytes=len(raw))
 manifest['files']['runtime/aura/config/board_avatar_gtk.json']=dict(sha256=c.sha(new_gui_raw),bytes=len(new_gui_raw))
 manifest['files']['startup/config.json']=dict(sha256=c.sha(new_startup_raw),bytes=len(new_startup_raw))
 manifest['new_boot_recovery']=dict(previous_boot_id=PREVIOUS_BOOT,boot_id=SPEC['boot_id'],
   previous_startup_sha256=BASE_STARTUP_SHA,face_readback_sha256=SPEC['face_readback']['sha256'],
   sources={rel:c.sha(raw) for rel,raw in new_files.items()},private_data_replayed=False)
 manifest_raw=c.encoded(manifest);completed_spec=dict(SPEC,source_manifest_sha256=c.sha(manifest_raw))
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
  cfg=BASE_GUI_OBJECT['board_business']
  proof=verify_production_bootstrap(private,cfg['bootstrap_receipt'],cfg['bootstrap_receipt_sha256'])
  need(proof['profiles_migration_verified'] is True,'production_bootstrap_not_verified')
  stage.mkdir(mode=0o700);backup=stage/'before';backup.mkdir(mode=0o700)
  for name,raw in [('startup-config.json',old_startup_raw),('gui-config.json',old_gui_raw),
                   ('production-source-manifest.json',old_manifest_raw),('publication-state.json',c.read(STATE))]:
   c.create(backup/name,raw)
  for rel,raw in new_files.items():
   original=c.read(root/'runtime/aura'/rel,BASE_PINS[rel]);destination=backup/rel
   destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True);c.create(destination,original)
   destination=stage/'after'/rel;destination.parent.mkdir(mode=0o700,parents=True,exist_ok=True);c.create(destination,raw)
  c.create(stage/'applied-spec.json',c.encoded(completed_spec))
  c.create(stage/'prepared-startup.json',new_startup_raw);c.create(stage/'prepared-gui.json',new_gui_raw)
  c.create(stage/'prepared-manifest.json',manifest_raw)
  j.update(phase='NEW_BOOT_SOURCE_INSTALL_INTENT',new_boot_stage=str(stage),target_startup_sha256=SPEC['startup_sha256'])
  save(j)
  for rel,raw in new_files.items():atomic(root/'runtime/aura'/rel,raw)
  atomic(root/'runtime/aura/config/board_avatar_gtk.json',new_gui_raw)
  atomic(root/'startup/config.json',new_startup_raw);atomic(root/'production_source_manifest.json',manifest_raw)
  SPEC['source_manifest_sha256']=completed_spec['source_manifest_sha256']
  source();ownerless(c.show());guarded(j)
  j.update(phase='NEW_BOOT_OWNERLESS',target_startup_sha256=SPEC['startup_sha256'],target_pins=379)
  save(j)
 return dict(status='NEW_BOOT_SOURCES_APPLIED_UI_STOPPED',spec=completed_spec,
   source_files={rel:c.sha(raw) for rel,raw in new_files.items()},backup_directory=str(backup),
   production_bootstrap_verified=True,profiles_migration_verified=True,
   private_data_replayed=False,ui_started=False,service_stop_or_kill=False)

with open('/run/aura-production-publisher.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 result=apply_closed()
print(json.dumps(result,ensure_ascii=True))
'''


def payload_for(spec):
    result = {}
    for rel,row in spec['source_overrides'].items():
        raw=publish.pinned(row['local_source'],row['sha256'])
        result[rel] = dict(before_sha256=row['before_sha256'],sha256=row['sha256'],base64=base64.b64encode(raw).decode())
    return result


def build_remote(spec):
    remote=publish.build_remote(spec)
    anchor="\nboot()\nwith open('/run/aura-production-publisher.lock','a') as lock:"
    if remote.count(anchor)!=1:
        raise ValueError('unique_publisher_dispatch_anchor_required')
    remote=remote.split(anchor,1)[0]
    remote=publish.replace_once(remote,"assert ACTION in ('guard-failed','guard','window-inspect','normal-close','start','ready')", "assert ACTION=='start'")
    pins,startup,gui=publish.inputs()
    values=dict(BASE_PINS=pins,BASE_STARTUP_OBJECT=startup,BASE_GUI_OBJECT=gui,
        BASE_STARTUP_SHA=publish.BASE_STARTUP,BASE_CONFIG_SHA=publish.BASE_CONFIG,BASE_MANIFEST_SHA=publish.BASE_MANIFEST)
    remote='\n'.join(key+'='+repr(value) for key,value in values.items())+'\n'+remote+'\n'+APPLY_REMOTE
    ast.parse(remote,feature_version=(3,9))
    return remote


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec',type=Path,required=True)
    parser.add_argument('--spec-sha256',required=True)
    parser.add_argument('--execute-root-only',action='store_true')
    args=parser.parse_args()
    spec=publish.validate_spec(json.loads(publish.pinned(args.spec,args.spec_sha256)),'start')
    if spec['source_manifest_sha256']!='0'*64:
        raise ValueError('proposed_spec_required')
    remote=build_remote(spec);payload=payload_for(spec)
    if not args.execute_root_only:
        print(json.dumps(dict(status='DRY_NEW_BOOT_APPLY_VALIDATED_NO_SSH',remote_sha256=publish.sha(remote.encode()),
            source_files={rel:row['sha256'] for rel,row in payload.items()},source_count=len(payload))))
        return
    sys.path.insert(0,str(publish.REPAIR/'release_v18_candidate'))
    from v18_common import publisher_script,ssh_json
    values=dict(SPEC=spec,ACTION='start',TOKEN=None,WINDOW=None,PAYLOAD=payload)
    result=ssh_json(publisher_script(remote,values),timeout=180)
    suffix=str(time.time_ns())
    output=publish.HERE/('actual_apply_'+suffix+'.json')
    with output.open('xb') as stream:stream.write(publish.encoded(result))
    if result.get('status')!='NEW_BOOT_SOURCES_APPLIED_UI_STOPPED':
        raise ValueError('new_boot_apply_incomplete')
    final_spec=publish.validate_spec(result['spec'],'start')
    final_path=publish.HERE/('applied_spec_'+suffix+'.json');raw=publish.encoded(final_spec)
    with final_path.open('xb') as stream:stream.write(raw)
    print(json.dumps(dict(status=result['status'],output=str(output),spec=str(final_path),spec_sha256=publish.sha(raw)),ensure_ascii=True))


if __name__=='__main__':
    main()
