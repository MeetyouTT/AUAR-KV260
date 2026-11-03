"""Inspect doll UI service, desktop launchers and X windows without changes."""
import json,os,shutil,subprocess,urllib.request
from pathlib import Path
def cmd(args):
 try:
  p=subprocess.run(args,env=dict(os.environ,DISPLAY=':0'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
  return {'rc':p.returncode,'text':p.stdout[-7000:]}
 except Exception as e:return {'error':str(e)}
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'service':cmd(['systemctl','show','aura-avatar-ui.service','-p','ActiveState','-p','SubState','-p','MainPID','-p','NRestarts','-p','UnitFileState','-p','ExecStart']),
 'graphical_target':cmd(['systemctl','get-default']),
 'journal':cmd(['journalctl','-b','-u','aura-avatar-ui.service','-n','8','--no-pager','-o','cat']),
 'desktop_search_roots':[], 'desktop_entries':[], 'files_modified':0,'display_commands_sent':0,'movement_commands_sent':0}
roots=['/usr/share/applications','/usr/local/share/applications','/home/root/.local/share/applications','/home/root/Desktop','/home/root/桌面']
for name in roots:
 root=Path(name);v['desktop_search_roots'].append({'path':name,'exists':root.exists()})
 if not root.is_dir():continue
 for p in root.glob('*.desktop'):
  raw=p.read_text(errors='replace')
  if any(s in (p.name+'\n'+raw).lower() for s in ['aura','avatar','汐蓝','玩偶']):
   v['desktop_entries'].append({'path':str(p),'fields':[s for s in raw.splitlines() if s.startswith(('Name=','Name[','Exec=','TryExec=','Hidden=','NoDisplay='))]})
for name in ['/home/root/.config/user-dirs.dirs','/etc/default/xserver-nodm']:
 p=Path(name)
 if p.exists():v[name]=p.read_text()[:2000]
v['window_tools']={name:shutil.which(name) for name in ['wmctrl','xprop','xwininfo']}
if shutil.which('wmctrl'):v['windows']=cmd(['wmctrl','-lx'])
elif shutil.which('xwininfo'):v['windows']=cmd(['xwininfo','-root','-tree'])
if shutil.which('xprop'):v['active_window']=cmd(['xprop','-root','_NET_ACTIVE_WINDOW','_NET_CLIENT_LIST'])
try:
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with opener.open('http://127.0.0.1:8783/api/state',timeout=2) as response:state=json.load(response)
 v['ui']={k:state.get(k) for k in ['phase','ui_page','backend','error']}
except Exception as e:v['ui']={'error':str(e)}
print(json.dumps(v,ensure_ascii=False),flush=True)
