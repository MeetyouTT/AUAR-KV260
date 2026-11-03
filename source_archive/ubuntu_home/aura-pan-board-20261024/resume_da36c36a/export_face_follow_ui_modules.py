import base64,hashlib,json,re,subprocess
from pathlib import Path
x=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'],text=True)
config=Path(re.search(r'--config (/[^ ;]+)',x).group(1));startup=json.loads(config.read_text());app=Path(startup['runtime'])/'aura'
pins=startup['component_sha256'];chosen=[n for n in pins if Path(n).suffix=='.py' and any(t in n.lower() for t in ('pan_control','face_pan','manual_process','avatar_gtk','avatar_gui','startup/launcher'))]
payload={}
for name in sorted(chosen):
 p=app/name;raw=p.read_bytes();payload[name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'base64':base64.b64encode(raw).decode()}
print(json.dumps({'startup_config_sha256':hashlib.sha256(config.read_bytes()).hexdigest(),'runtime_root':str(app),
 'component_pins':len(pins),'selected_source_modules':payload},ensure_ascii=False))
