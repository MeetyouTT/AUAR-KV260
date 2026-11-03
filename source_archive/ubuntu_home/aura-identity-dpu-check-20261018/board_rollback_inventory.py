"""Find retained GUI releases and rollback receipts without changing services."""
import hashlib,json,subprocess
from pathlib import Path
def cmd(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
 return {'rc':p.returncode,'text':p.stdout[-9000:]}
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'unit':cmd(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ExecStart','-p','ActiveState','-p','NRestarts']),
 'unit_sources':cmd(['systemctl','cat','aura-avatar-ui.service']), 'releases':[],
 'xorg_sha256':hashlib.sha256(Path('/etc/X11/xorg.conf').read_bytes()).hexdigest(),
 'files_modified':0,'movement_commands_sent':0}
for name in ['/home/root/aura-render24-budget-20261020','/home/root/aura-render24-rgb565-20261020','/home/root/aura-listening-timing-20261020','/home/root/aura-pan-manual-ui-20261020','/home/root/aura-voice-barge-in-20261020','/home/root/aura-display-startup-fix-20261020']:
 root=Path(name)
 if not root.exists():continue
 for p in root.glob('*/startup/config.json'):
  c=json.loads(p.read_text());launcher=p.with_name('launcher.py')
  v['releases'].append({'config':str(p),'runtime':c.get('runtime'),'config_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
   'launcher_sha256':hashlib.sha256(launcher.read_bytes()).hexdigest(),'gui_sha256':c.get('gui_sha256'),
   'display_retrain_off_seconds':c.get('display_retrain_off_seconds'),
   'layout_sha256':{k:h for k,h in c.get('component_sha256',{}).items() if k in ['tools/board_avatar_gtk.py','tools/native_video.py','tools/native_pixels.cpp','ui/board_touch_layout.json']}})
 for p in list(root.glob('*/*.json'))[:15]:
  if p.stat().st_size>40000:continue
  if any(k in p.name for k in ['manifest','trial','rollback','candidate','commit','result','before']):
   try:
    value=json.loads(p.read_text());v.setdefault('receipts',[]).append({'path':str(p),'value':value})
   except ValueError:pass
print(json.dumps(v),flush=True)
