import json,subprocess,re,urllib.request
from pathlib import Path
entry=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths'],text=True)
cfgpath=Path(re.search(r'--config (\S+) ',entry).group(1))
try:
 s=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5))
 state={k:s.get(k) for k in ('phase','audio_output_state','avatar_display','handsfree_dialogue','error')}
except Exception as e:state={'error':str(e)}
print(json.dumps({'effective':entry,'config_path':str(cfgpath),'config':json.loads(cfgpath.read_text()),'state':state}))
