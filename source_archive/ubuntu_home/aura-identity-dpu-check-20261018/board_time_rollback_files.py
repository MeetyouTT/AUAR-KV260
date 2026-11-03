"""Restore the exact pre-05:02 startup files; preserve business runtime/data."""
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot=='c7d18dbf-2cd2-40b1-9534-b3de305e847a'
release=Path('/home/root/aura-display-startup-fix-20261020/48280631334c')
startup=Path('/home/root/aura-render24-budget-20261020/e06409743174/startup')
config=startup/'config.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cmd(args,timeout=8):return subprocess.check_output(args,stderr=subprocess.STDOUT,text=True,timeout=timeout)
def unit(name):return cmd(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','NRestarts','-p','ExecStart'])
assert sha(config)=='eb5b8e02589728e72466a7d5ea575cbf08f62bdbce72cda4b3015865b304e49f'
assert str(startup/'launcher.py') in unit('aura-avatar-ui.service')
records=json.loads((release/'backup/files.json').read_text());manifest=json.loads((release/'manifest.json').read_text())
for record in records:
 assert sha(Path(record['target']))==manifest['payload'][record['source']]
 assert sha(release/'backup'/record['source'])==record['sha256']
assert sha(release/'install.py')=='c4bddf817479b317ce0561702ad95d7e43d18a3ed4a59fdb5f44ea3ee2727640'
preflight=cmd([sys.executable,'-B',str(release/'backup/launcher.py'),'--config',str(config),'--preflight'],timeout=12)
out=Path('/home/root/aura-ui-time-rollback-20261021')/('before-'+str(os.getpid()));out.mkdir(parents=True,exist_ok=False)
for record in records:shutil.copy2(record['target'],str(out/record['source']))
shutil.copy2(str(config),str(out/'config.json'))
before={name:unit(name) for name in ['aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service']}
v={'boot_id':boot,'backup':str(out),'before':before,'preflight':json.loads(preflight),'movement_commands_sent':0,'business_runtime_modified':False,'user_data_modified':False,'status':'PREPARED'}
stopped=False
try:
 cmd(['systemctl','stop','aura-avatar-ui.service'],timeout=28);stopped=True
 v['rollback']=json.loads(cmd([sys.executable,'-B',str(release/'install.py'),'rollback']))
 assert sha(config)=='eb5b8e02589728e72466a7d5ea575cbf08f62bdbce72cda4b3015865b304e49f'
 for record in records:assert sha(Path(record['target']))==record['sha256']
 v['targets']={record['target']:sha(Path(record['target'])) for record in records}
 v['status']='FILES_ROLLED_BACK_WAITING_DISPLAY_RESTART'
except Exception as exc:
 v.update(status='ROLLBACK_FILES_FAILED',error=str(exc))
 if stopped:cmd(['systemctl','start','--no-block','aura-avatar-ui.service'])
(out/'result.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(v),flush=True)
