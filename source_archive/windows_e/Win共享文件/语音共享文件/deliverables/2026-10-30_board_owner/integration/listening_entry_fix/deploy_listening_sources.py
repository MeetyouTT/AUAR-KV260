"""Update reviewed source/config only after the formal UI naturally exits."""
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
ACCEPTANCE=HERE.parent/'production_business_acceptance'
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

SOURCES={
 'tools/board_avatar_gtk.py':('listening_entry_fix/automatic_preference','30b563bd46a4c5bba9c84a3bd52bb3cdd28126dfe04504568935dea1599dd701','5ab20a5b86a6982b75447933ce87e9be5b96cb5cc560fa1026c69b574f070fc5'),
 'tools/production_listening.py':('listening_entry_fix/automatic_preference','d5f9dd7bbb978962a49be633325c6d66580da323f17384f1ca423bc76475e3fe',None),
 'tools/production_business_ui.py':('safe_capture_diagnostics','c7a1c7b6e6259c1fb74be831d7272704fb20119c86345b50b79234d5f3adf973','46c55f4da84c3ffd7d3db43858466f922ef053790ce2b40791f38532dca51837'),
 'tools/production_board_business_gui.py':('production_frontend_capacity_candidate','1d4cdb9dd9179476e34fd8b9574b497615f597dbbd082d873d3fdedb619e391d','29fa2d5b664db3e1b92583a93fcdad6283d8dae2a6b28b90ef8a141e15fd0a25'),
 'tools/production_frontend_selection.py':('production_frontend_capacity_candidate','c9d095bb722a8dd0096ffdb373910ae364e0e4cd12dcb4d0fdc20ac55bf627a2',None),
 'board/runtime/audio/board_capture_priority.py':('production_frontend_capacity_candidate','f98aeb83285df389417cd3da98d7c95920417ca342926718a31b88926afe1931',None),
 'board/runtime/audio/board_gtcrn_reuse.py':('production_frontend_capacity_candidate','fd6e095d66e9a2b93e9fc738c93ccb8559daea02faa0f6d3d055d65c53de03a9',None),
}

REMOTE=r'''
import ast,base64,fcntl,hashlib,json,os,pathlib,subprocess,sys
Path=pathlib.Path
sha=lambda raw:hashlib.sha256(raw).hexdigest()
encoded=lambda obj:(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
root=Path(SPEC['target']);control=root.parent/'control-production-v1'
assert root==Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13') and root.resolve()==root
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==SPEC['boot_id']
def read(path,pin=None):
 path=Path(path);assert not path.is_symlink() and path.is_file() and path.resolve()==path
 raw=path.read_bytes();assert pin is None or sha(raw)==pin
 return raw
def create(path,raw):
 fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
def replace(path,raw):
 tmp=path.with_name(path.name+'.automatic-listening-new');create(tmp,raw);os.replace(str(tmp),str(path))
 fd=os.open(str(path.parent),os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
with open('/run/aura-production-publisher.lock','a') as publication:
 fcntl.flock(publication,fcntl.LOCK_EX|fcntl.LOCK_NB)
 unit=dict(line.split('=',1) for line in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SendSIGKILL','-p','TimeoutStopUSec','-p','Job'],text=True).splitlines() if '=' in line)
 assert unit['MainPID']=='0' and unit['ActiveState']=='inactive' and unit['SendSIGKILL']=='no' and unit['TimeoutStopUSec']=='infinity' and not unit['Job']
 journal=json.loads(read(control/'state.json'))
 assert journal['phase']=='NORMAL_CLOSED' and journal['guard_removed'] is False and journal['active_root']==str(root)
 read(journal['guard'],journal['guard_sha256'])
 startup_path=root/'startup/config.json';old_startup=read(startup_path,SPEC['startup_sha256']);startup=json.loads(old_startup)
 assert len(startup['component_sha256'])==SPEC['component_pins']
 for rel,pin in startup['component_sha256'].items():read(root/'runtime/aura'/rel,pin)
 cfgpath=root/'runtime/aura/config/board_avatar_gtk.json';old_cfg=read(cfgpath,startup['component_sha256']['config/board_avatar_gtk.json']);cfg=json.loads(old_cfg)
 assert cfg['board_business']['data_origin']=='board' and cfg['board_business']['retention_enabled'] is True
 private=Path(cfg['board_business']['private_root']);assert private==Path('/home/root/.local/share/aura-board-business')
 assert not (private/'listening_preference.json').exists(), 'unexpected_explicit_preference_requires_review'
 sys.path.insert(0,str(root/'runtime/aura'))
 from common.board_production_bootstrap import verify_production_bootstrap
 proof=verify_production_bootstrap(private,cfg['board_business']['bootstrap_receipt'],cfg['board_business']['bootstrap_receipt_sha256'])
 assert proof['profiles_migration_verified'] is True
 with open(private/'writer.lock','a') as writer:
  fcntl.flock(writer,fcntl.LOCK_EX|fcntl.LOCK_NB)
  manifest_path=root/'production_source_manifest.json'
  old_manifest=read(manifest_path,'cd1844eff9681979f5be65e8b87a8cd376432c07fa91f5638c2987ec7d5e83e1');manifest=json.loads(old_manifest)
  stage=control/'automatic-listening-v1';stage.mkdir(mode=0o700)
  backup=stage/'before';backup.mkdir(mode=0o700)
  create(backup/'startup-config.json',old_startup);create(backup/'gui-config.json',old_cfg);create(backup/'production-source-manifest.json',old_manifest)
  new_files={}
  for rel,item in PAYLOAD.items():
   assert '..' not in Path(rel).parts and not Path(rel).is_absolute()
   raw=base64.b64decode(item['base64']);assert sha(raw)==item['sha256'];ast.parse(raw,feature_version=(3,9))
   path=root/'runtime/aura'/rel;before=item['before_sha256']
   if before is None:assert rel not in startup['component_sha256'] and not path.exists()
   else:
    assert startup['component_sha256'][rel]==before
    original=read(path,before);dest=backup/rel;dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True);create(dest,original)
   assert path.parent.resolve()==path.parent and path.parent.is_dir()
   new_files[rel]=raw;startup['component_sha256'][rel]=item['sha256']
   manifest['files']['runtime/aura/'+rel]=dict(sha256=item['sha256'],bytes=len(raw))
   manifest['component_pins'][rel]=item['sha256']
  cfg['board_business'].update(frontend_optimization='baseline',capture_priority_nice=-10,frontend_threads=1)
  cfgraw=encoded(cfg);cfgpin=sha(cfgraw)
  create(stage/'effective-gui-config.json',cfgraw)
  startup['component_sha256']['config/board_avatar_gtk.json']=cfgpin
  manifest['component_pins']['config/board_avatar_gtk.json']=cfgpin
  manifest['files']['runtime/aura/config/board_avatar_gtk.json']=dict(sha256=cfgpin,bytes=len(cfgraw))
  startupraw=encoded(startup)
  manifest['files']['startup/config.json']=dict(sha256=sha(startupraw),bytes=len(startupraw))
  manifest.update(configuration_path=str(stage/'effective-gui-config.json'),configuration_sha256=cfgpin,
   listening_revision=dict(previous_startup_sha256=SPEC['startup_sha256'],default_automatic_listening=True,
    explicit_pause_persisted=True,internal_errors_do_not_persist_pause=True,frontend_optimization='baseline',
    capture_priority_nice=-10,original_queue_frames=8,combined_candidate_enabled=False))
  manifest_raw=encoded(manifest)
  create(stage/'intent.json',encoded(dict(previous_startup_sha256=SPEC['startup_sha256'],new_startup_sha256=sha(startupraw),source_files={r:sha(v) for r,v in new_files.items()},private_data_replayed=False)))
  for rel,raw in new_files.items():
   path=root/'runtime/aura'/rel
   if path.exists():replace(path,raw)
   else:create(path,raw)
  replace(cfgpath,cfgraw);replace(startup_path,startupraw);replace(manifest_path,manifest_raw)
  result=dict(status='AUTOMATIC_LISTENING_SOURCES_INSTALLED_UI_STOPPED',target=str(root),startup_sha256=sha(startupraw),
   component_pins=len(startup['component_sha256']),configuration_sha256=cfgpin,source_manifest_sha256=sha(manifest_raw),
   source_files={r:sha(v) for r,v in new_files.items()},automatic_listening=True,retention_enabled=True,
   private_data_replayed=False,frontend_optimization='baseline',capture_priority_nice=-10)
  create(stage/'completed.json',encoded(result))
  print(json.dumps(result))
'''

if __name__=='__main__':
    spec=json.loads((ACCEPTANCE/'spec.json').read_text(encoding='utf-8'))
    assert spec['startup_sha256']=='e34590df7ecd4f74046671c9458edd48ede45d1474b5fbeba63481edd4cb8759'
    payload={}
    for rel,(folder,pin,before) in SOURCES.items():
        raw=(HERE.parent/folder/'after/aura'/rel).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==pin
        payload[rel]=dict(sha256=pin,before_sha256=before,base64=base64.b64encode(raw).decode())
    script='SPEC='+repr(spec)+'\nPAYLOAD='+repr(payload)+'\n'+REMOTE
    value=json.loads(ssh('python3 -B -',script,timeout=90))
    (HERE/'actual_sources_installed.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    spec.update(**{k:value[k] for k in ('startup_sha256','component_pins','configuration_sha256','automatic_listening')})
    (ACCEPTANCE/'spec.json').write_text(json.dumps(spec,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(value))
