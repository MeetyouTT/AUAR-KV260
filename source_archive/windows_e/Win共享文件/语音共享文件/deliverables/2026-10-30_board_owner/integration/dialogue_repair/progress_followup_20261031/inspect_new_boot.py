"""Read public startup sources and bounded failure metadata after a board reboot."""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE = r'''
import hashlib,json,pathlib,re,subprocess,time
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
out={'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'mono':time.monotonic(),'files':{}}
for rel in ['startup/launcher.py','startup/config.json','runtime/aura/config/board_avatar_gtk.json']:
 raw=(root/rel).read_bytes()
 assert len(raw)<262144
 out['files'][rel]={'sha256':hashlib.sha256(raw).hexdigest(),'content':raw.decode('utf8')}
log=subprocess.check_output(['journalctl','-b','-u','aura-avatar-ui.service','--no-pager','-n','100','-o','cat'],text=True,timeout=5)
frames=[];errors=[]
for line in log.splitlines():
 m=re.search(r'File "([^"\n]+\.py)", line (\d+), in ([A-Za-z0-9_<>]+)',line)
 if m: frames.append({'file':pathlib.Path(m[1]).name,'line':int(m[2]),'function':m[3]})
 m=re.fullmatch(r'([A-Za-z]+(?:Error|Exception))(?:: ([a-zA-Z_][a-zA-Z0-9_]{0,100}))?',line.strip())
 if m: errors.append({'class':m[1],'code':m[2]})
out['journal']={'lines':len(log.splitlines()),'frames':frames[-12:],'errors':errors[-8:]}
cfg=json.loads(out['files']['runtime/aura/config/board_avatar_gtk.json']['content'])
out['business_config_keys']=sorted(cfg.get('board_business',{}))
out['unit']=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','ExecMainStatus','-p','Restart','-p','SendSIGKILL','-p','TimeoutStopUSec','-p','DropInPaths','-p','ExecStart'],text=True,timeout=5).splitlines()
ops=pathlib.Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
pid=int(subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True))
path=ops/('native-run-'+out['boot_id']+'-'+str(pid))/'config.json'
raw=path.read_bytes();camera=json.loads(raw)
out['camera']={'pid':pid,'runtime_path':str(path),'runtime_sha256':hashlib.sha256(raw).hexdigest(),'native_seed':camera.get('native_execution',{}).get('seed')}
print(json.dumps(out))
'''

if __name__ == '__main__':
    value = json.loads(ssh('python3 -B -', REMOTE, timeout=25))
    destination = HERE / ('new_boot_diagnostic_' + str(time.time_ns()) + '.json')
    destination.write_text(json.dumps(value, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'file':str(destination), **{k:v for k,v in value.items() if k!='files'},
                     'source_hashes':{k:v['sha256'] for k,v in value['files'].items()}}))
