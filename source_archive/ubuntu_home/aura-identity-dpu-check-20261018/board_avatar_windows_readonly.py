"""Identify mapped UI windows; do not raise, focus or change pages."""
import json,os,re,subprocess
from pathlib import Path
env=dict(os.environ,DISPLAY=':0')
def cmd(args):
 p=subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=4)
 return {'rc':p.returncode,'text':p.stdout[-3000:]}
clients=cmd(['xprop','-root','_NET_CLIENT_LIST','_NET_ACTIVE_WINDOW','_NET_CURRENT_DESKTOP'])
ids=list(dict.fromkeys(re.findall(r'0x[0-9a-fA-F]+',clients['text'])))
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'root':clients,
 'windows':{w:cmd(['xprop','-id',w,'_NET_WM_NAME','WM_NAME','WM_CLASS','_NET_WM_PID','_NET_WM_STATE','_NET_WM_DESKTOP','WM_STATE']) for w in ids},
 'files_modified':0,'window_actions_sent':0,'display_commands_sent':0,'movement_commands_sent':0}
print(json.dumps(v,ensure_ascii=False),flush=True)
