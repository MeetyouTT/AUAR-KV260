"""Journal one reviewed listening revision with no live UI or business writer."""
import argparse
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

REMOTE=r'''
import ast,base64,fcntl,hashlib,json,os,pathlib,subprocess,sys
Path=pathlib.Path
sha=lambda raw:hashlib.sha256(raw).hexdigest()
encoded=lambda v:(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
root=Path(SPEC['target']);control=root.parent/'control-production-v1'
assert root==Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13') and root.resolve()==root
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==SPEC['boot_id']
assert REVISION['stage'].startswith(('automatic-listening-v','response-latency-v')) and '/' not in REVISION['stage'] and '..' not in REVISION['stage']
assert set(REVISION['business_options'])<=set(('frontend_process','frontend_capture_process','frontend_optimization','capture_priority_nice','frontend_threads','asr_threads'))
assert 'wake_word_required' not in REVISION or type(REVISION['wake_word_required']) is bool
assert 'conversation_mode' not in REVISION or REVISION['conversation_mode'] in ('half_duplex','interruptible')
gui_options=REVISION.get('gui_options',{})
assert isinstance(gui_options,dict) and set(gui_options)<=set(('voice_barge_in',))
assert all(type(v) is bool for v in gui_options.values())
def read(p,pin=None):
 p=Path(p);assert p.is_file() and not p.is_symlink() and p.resolve()==p
 raw=p.read_bytes();assert pin is None or sha(raw)==pin
 return raw
def create(p,raw):
 fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
def replace(p,raw):
 tmp=p.with_name(p.name+'.listening-revision-new');create(tmp,raw);os.replace(str(tmp),str(p))
 fd=os.open(str(p.parent),os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
with open('/run/aura-production-publisher.lock','a') as publication:
 fcntl.flock(publication,fcntl.LOCK_EX|fcntl.LOCK_NB)
 unit=dict(x.split('=',1) for x in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SendSIGKILL','-p','TimeoutStopUSec','-p','Job'],text=True).splitlines() if '=' in x)
 assert unit['MainPID']=='0' and unit['ActiveState']=='inactive' and unit['SendSIGKILL']=='no' and unit['TimeoutStopUSec']=='infinity' and not unit['Job']
 journal=json.loads(read(control/'state.json'));assert journal['phase']=='NORMAL_CLOSED' and journal['guard_removed'] is False and journal['active_root']==str(root)
 read(journal['guard'],journal['guard_sha256'])
 startup_path=root/'startup/config.json';old_startup=read(startup_path,SPEC['startup_sha256']);startup=json.loads(old_startup)
 assert len(startup['component_sha256'])==SPEC['component_pins']
 for rel,pin in startup['component_sha256'].items():read(root/'runtime/aura'/rel,pin)
 cfgpath=root/'runtime/aura/config/board_avatar_gtk.json';old_cfg=read(cfgpath,startup['component_sha256']['config/board_avatar_gtk.json']);cfg=json.loads(old_cfg)
 assert cfg['board_business']['data_origin']=='board' and cfg['board_business']['retention_enabled'] is True
 private=Path(cfg['board_business']['private_root']);assert private==Path('/home/root/.local/share/aura-board-business')
 sys.path.insert(0,str(root/'runtime/aura'))
 from common.board_production_bootstrap import verify_production_bootstrap
 proof=verify_production_bootstrap(private,cfg['board_business']['bootstrap_receipt'],cfg['board_business']['bootstrap_receipt_sha256']);assert proof['profiles_migration_verified'] is True
 with open(private/'writer.lock','a') as writer:
  fcntl.flock(writer,fcntl.LOCK_EX|fcntl.LOCK_NB)
  manifest_path=root/'production_source_manifest.json';old_manifest=read(manifest_path,REVISION['before_manifest_sha256']);manifest=json.loads(old_manifest)
  stage=control/REVISION['stage'];stage.mkdir(mode=0o700);backup=stage/'before';backup.mkdir(mode=0o700)
  for name,raw in [('startup-config.json',old_startup),('gui-config.json',old_cfg),('production-source-manifest.json',old_manifest)]:create(backup/name,raw)
  new_files={}
  for rel,item in PAYLOAD.items():
   assert not Path(rel).is_absolute() and '..' not in Path(rel).parts and rel.endswith('.py')
   raw=base64.b64decode(item['base64']);assert sha(raw)==item['sha256'];ast.parse(raw,feature_version=(3,9))
   before=item['before_sha256'];path=root/'runtime/aura'/rel
   if before is None:assert rel not in startup['component_sha256'] and not path.exists()
   else:
    assert startup['component_sha256'][rel]==before
    original=read(path,before);dest=backup/rel;dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True);create(dest,original)
   assert path.parent.resolve()==path.parent and path.parent.is_dir()
   new_files[rel]=raw;startup['component_sha256'][rel]=item['sha256'];manifest['component_pins'][rel]=item['sha256']
   manifest['files']['runtime/aura/'+rel]=dict(sha256=item['sha256'],bytes=len(raw))
  cfg['board_business'].update(REVISION['business_options']);cfg.update(gui_options);cfgraw=encoded(cfg);cfgpin=sha(cfgraw)
  create(stage/'effective-gui-config.json',cfgraw);startup['component_sha256']['config/board_avatar_gtk.json']=cfgpin
  manifest['component_pins']['config/board_avatar_gtk.json']=cfgpin;manifest['files']['runtime/aura/config/board_avatar_gtk.json']=dict(sha256=cfgpin,bytes=len(cfgraw))
  startupraw=encoded(startup);manifest['files']['startup/config.json']=dict(sha256=sha(startupraw),bytes=len(startupraw))
  manifest.update(configuration_path=str(stage/'effective-gui-config.json'),configuration_sha256=cfgpin,
   listening_revision=dict(previous_startup_sha256=SPEC['startup_sha256'],stage=REVISION['stage'],default_automatic_listening=True,
    explicit_pause_persisted=True,business_options=REVISION['business_options'],private_data_replayed=False,original_queue_frames=8))
  if 'wake_word_required' in REVISION:
   manifest['listening_revision']['wake_word_required']=REVISION['wake_word_required']
  if 'conversation_mode' in REVISION:
   manifest['listening_revision']['conversation_mode']=REVISION['conversation_mode']
  if gui_options:manifest['listening_revision']['gui_options']=gui_options
  manifest_raw=encoded(manifest)
  create(stage/'intent.json',encoded(dict(previous_startup_sha256=SPEC['startup_sha256'],new_startup_sha256=sha(startupraw),source_files={r:sha(v) for r,v in new_files.items()},private_data_replayed=False)))
  for rel,raw in new_files.items():
   path=root/'runtime/aura'/rel
   if path.exists():replace(path,raw)
   else:create(path,raw)
  replace(cfgpath,cfgraw);replace(startup_path,startupraw);replace(manifest_path,manifest_raw)
  result=dict(status='LISTENING_REVISION_INSTALLED_UI_STOPPED',target=str(root),stage=REVISION['stage'],startup_sha256=sha(startupraw),component_pins=len(startup['component_sha256']),
   configuration_sha256=cfgpin,source_manifest_sha256=sha(manifest_raw),source_files={r:sha(v) for r,v in new_files.items()},automatic_listening=True,retention_enabled=True,
   private_data_replayed=False,business_options=REVISION['business_options'])
  if 'wake_word_required' in REVISION:result['wake_word_required']=REVISION['wake_word_required']
  if 'conversation_mode' in REVISION:result['conversation_mode']=REVISION['conversation_mode']
  if gui_options:result['gui_options']=gui_options
  create(stage/'completed.json',encoded(result));print(json.dumps(result))
'''

def main():
    p=argparse.ArgumentParser();p.add_argument('revision',type=Path);a=p.parse_args()
    revision=json.loads(a.revision.read_text(encoding='utf-8'))
    spec=json.loads((ACCEPTANCE/'spec.json').read_text(encoding='utf-8'))
    assert spec['startup_sha256']==revision['before_startup_sha256']
    payload={}
    for rel,item in revision['sources'].items():
        path=(PROJECT/item['source']).resolve();assert path.is_relative_to(PROJECT.resolve()) and path.suffix=='.py'
        raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==item['sha256']
        payload[rel]=dict(sha256=item['sha256'],before_sha256=item['before_sha256'],base64=base64.b64encode(raw).decode())
    result=json.loads(ssh('python3 -B -','SPEC='+repr(spec)+'\nREVISION='+repr(revision)+'\nPAYLOAD='+repr(payload)+'\n'+REMOTE,timeout=90))
    (HERE/('actual_'+revision['stage']+'.json')).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    spec.update(**{k:result[k] for k in ('startup_sha256','component_pins','configuration_sha256','automatic_listening')})
    if 'wake_word_required' in result:spec['wake_word_required']=result['wake_word_required']
    if 'conversation_mode' in result:spec['conversation_mode']=result['conversation_mode']
    (ACCEPTANCE/'spec.json').write_text(json.dumps(spec,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))

if __name__=='__main__':main()
