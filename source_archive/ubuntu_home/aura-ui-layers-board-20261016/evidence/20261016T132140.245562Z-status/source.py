"""Read-only diagnosis of the GUI after the replacement."""
import json
from pathlib import Path
import subprocess
import urllib.request

root=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
def run(args):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
    return {'exit_code':p.returncode,'output':p.stdout[-6000:]}
result={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'services':run(['systemctl','show','aura-avatar-ui.service','aura-camera-ui.service','-p','Id','-p','ActiveState','-p','SubState','-p','MainPID','-p','NRestarts']),
        'journal':run(['journalctl','-u','aura-avatar-ui.service','-n','15','--no-pager'])}
for name,url in [('ui','http://127.0.0.1:8783/api/state'),('camera','http://127.0.0.1:8790/health')]:
    try:
        with urllib.request.urlopen(url,timeout=3) as r:value=json.load(r)
        if name=='ui':value={k:value.get(k) for k in ('ui_layer','ui_page','ui_pages','phase','playing','paused','error','local_recording','ui_settings','ui_tick_ms')}
        result[name]=value
    except Exception as exc:result[name]={'error':str(exc)}
if (root/'stage.log').exists():result['stage_log']=(root/'stage.log').read_text()[-6500:]
print(json.dumps(result,ensure_ascii=False))
