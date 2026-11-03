"""Resolve ExecStart config runtime, inspect renderer trial pan history only."""
import base64,gzip,hashlib,json,subprocess
from pathlib import Path
c=Path('/home/root/aura-render24-rgb565-20261020/887c4b6b2b5d')
config=json.loads((c/'startup/config.json').read_text());root=Path(config['runtime'])/'aura'
v={'runtime':str(root),'candidate':json.loads((c/'candidate.json').read_text()),'hashes':{},'processes':[],'trial_pans':[]}
for rel in ['board/motion/manual.py','board/motion/manual_process.py','board/motion/manual_vsrv.py','tools/pan_controls.py','tools/board_avatar_gtk.py','tools/native_pixels.cpp','tools/libaura_pixels.so']:
 v['hashes'][rel]=hashlib.sha256((root/rel).read_bytes()).hexdigest()
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  args=(p/'cmdline').read_bytes()
  if str(root/'tools/board_avatar_pan.py').encode() in args:v['processes'].append({'pid':p.name,'cmd':args.replace(b'\0',b' ').decode()})
 except OSError:pass
trial=json.loads((c/'trial.json').read_text())
v['trial_state']=trial.get('state');v['gate']=trial.get('gate')
def scan(x,path=''):
 if isinstance(x,dict):
  if 'manual_pan' in x:
   pan=x['manual_pan'];row={'path':path,'pan':pan}
   row.update({k:x.get(k) for k in ['sequence','ui_tick_ms','ui_page','at','elapsed','time','mono'] if k in x});v['trial_pans'].append(row)
  for k,y in x.items():
   if k!='manual_pan':scan(y,path+'/'+k)
 elif isinstance(x,list):
  for i,y in enumerate(x):scan(y,path+'/'+str(i))
scan(trial)
if len(v['trial_pans'])>30:v['trial_pans']=v['trial_pans'][:1]+v['trial_pans'][-29:]
v['interlock']=json.loads(Path('/home/root/aura-pan-incident-20261020/lock-status.json').read_text())
print(json.dumps(v),flush=True)
