import hashlib,json,subprocess,urllib.request
from pathlib import Path
d={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'services':{}}
for unit in ['aura-camera-ui.service','aura-avatar-ui.service']:
    raw=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','ExecStart','-p','FragmentPath'],text=True,timeout=4)
    props=dict(v.split('=',1) for v in raw.splitlines() if '=' in v);pid=props['MainPID']
    props['cmdline']=(Path('/proc')/pid/'cmdline').read_bytes().decode().split(chr(0))
    d['services'][unit]=props
p=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/meta.json');m=json.loads(p.read_text())
d['candidate_config']=m['candidate_config'];c=json.loads(Path(m['candidate_config']).read_text())
d['native_execution']=c.get('native_execution')
print(json.dumps(d))
