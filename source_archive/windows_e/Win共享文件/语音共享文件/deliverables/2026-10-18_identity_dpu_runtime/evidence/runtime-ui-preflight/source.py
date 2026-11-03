import hashlib,json,os,subprocess
from pathlib import Path
root=Path('/home/root/aura-adaptation-20261006/identity_dpu_runtime_20261018/96f86ddef3a96b93')
app=root/'candidate/runtime/aura'
p=root/'candidate/startup/config.json'
cfg=json.loads(p.read_text());cfg['gui_sha256']=hashlib.sha256((app/'tools/board_avatar_gtk.py').read_bytes()).hexdigest()
p.write_text(json.dumps(cfg,indent=2)+'\n')
env=dict(os.environ,DISPLAY=':0',PATH='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin')
process=subprocess.run(['python3','-B',str(root/'candidate/startup/launcher.py'),'--config',str(p),'--preflight'],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=18)
print(json.dumps({'status':'PREFLIGHT_PASS' if process.returncode==0 else 'PREFLIGHT_FAILED','exit_code':process.returncode,'output':process.stdout[-2500:],'config_keys':sorted(cfg.keys())}),flush=True)
