"""Explicit post-handoff retention configuration update, only with no UI owner."""
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
REMOTE=r'''
import fcntl,hashlib,json,os,subprocess,sys
from pathlib import Path
root=Path(SPEC['target']);control=root.parent/'control-production-v1'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
encoded=lambda v:(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def create(p,raw):
 fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
def replace(p,raw):
 temp=p.with_name(p.name+'.retention-new');create(temp,raw);os.replace(str(temp),str(p))
u=dict(line.split('=',1) for line in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SendSIGKILL','-p','TimeoutStopUSec','-p','Job'],text=True).splitlines() if '=' in line)
assert u['MainPID']=='0' and u['ActiveState']=='inactive' and u['SendSIGKILL']=='no' and u['TimeoutStopUSec']=='infinity' and not u['Job']
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==SPEC['boot_id']
startup_path=root/'startup/config.json';raw=startup_path.read_bytes();assert sha(raw)==SPEC['startup_sha256'];startup=json.loads(raw)
cfgpath=root/'runtime/aura/config/board_avatar_gtk.json';cfgraw=cfgpath.read_bytes();assert sha(cfgraw)==startup['component_sha256']['config/board_avatar_gtk.json'];cfg=json.loads(cfgraw)
assert cfg['board_business']['retention_enabled'] is False
private=Path(cfg['board_business']['private_root']);diagnostics=json.loads((private/'diagnostics/latest_metadata.json').read_bytes())
assert diagnostics['metadata_only'] is True and diagnostics['body_saved'] is False and diagnostics['images_saved'] is False
sys.path.insert(0,str(root/'runtime/aura'))
from common.board_production_bootstrap import verify_production_bootstrap
proof=verify_production_bootstrap(private,cfg['board_business']['bootstrap_receipt'],cfg['board_business']['bootstrap_receipt_sha256'])
assert proof['profiles_migration_verified'] is True
lock=open(private/'writer.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
try:
 backup=control/'before-retention';backup.mkdir(mode=0o700)
 manifest_path=root/'production_source_manifest.json';manifest_raw=manifest_path.read_bytes();manifest=json.loads(manifest_raw)
 for name,body in [('startup-config.json',raw),('gui-config.json',cfgraw),('production-source-manifest.json',manifest_raw)]:create(backup/name,body)
 cfg['board_business']['retention_enabled']=True;new_cfg=encoded(cfg);cfg_sha=sha(new_cfg)
 incoming=root.parent/'incoming-production-dc87c7f9';value=json.loads((incoming/'config.json').read_bytes());value['board_business']['retention_enabled']=True
 effective_raw=encoded(value);effective_path=incoming/'config-retention-enabled.json';create(effective_path,effective_raw)
 startup['component_sha256']['config/board_avatar_gtk.json']=cfg_sha;new_startup=encoded(startup)
 manifest['files']['runtime/aura/config/board_avatar_gtk.json']={'sha256':cfg_sha,'bytes':len(new_cfg)}
 manifest['files']['startup/config.json']={'sha256':sha(new_startup),'bytes':len(new_startup)}
 manifest['component_pins']['config/board_avatar_gtk.json']=cfg_sha
 manifest.update(retention_enabled=True,configuration_sha256=sha(effective_raw),configuration_path=str(effective_path),
  retention_revision=dict(previous_startup_sha256=SPEC['startup_sha256'],approved_stage='receipt_and_formal_GUI_ready_metadata_only_close'))
 replace(cfgpath,new_cfg);replace(startup_path,new_startup);replace(manifest_path,encoded(manifest))
 result=dict(status='RETENTION_CONFIGURATION_ENABLED_UI_STOPPED',target=str(root),startup_sha256=sha(new_startup),component_pins=len(startup['component_sha256']),
  retention_enabled=True,configuration_sha256=sha(effective_raw),receipt_verified_after_live_store_write=True,
  source_manifest_sha256=sha(encoded(manifest)),metadata_only_close_verified=True,body_cleanup_started=False)
 print(json.dumps(result))
finally:lock.close()
'''
def main():
    spec=json.loads((HERE/'spec.json').read_text(encoding='utf-8'))
    assert spec['retention_enabled'] is False
    value=json.loads(ssh('python3 -B -','SPEC='+repr(spec)+'\n'+REMOTE,timeout=25))
    (HERE/'retention_enabled.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    assert value['status']=='RETENTION_CONFIGURATION_ENABLED_UI_STOPPED'
    (HERE/'spec_initial_retention_disabled.json').write_text(json.dumps(spec,indent=2)+'\n',encoding='utf-8')
    spec.update(startup_sha256=value['startup_sha256'],retention_enabled=True,configuration_sha256=value['configuration_sha256'])
    (HERE/'spec.json').write_text(json.dumps(spec,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(value))
if __name__=='__main__':main()
