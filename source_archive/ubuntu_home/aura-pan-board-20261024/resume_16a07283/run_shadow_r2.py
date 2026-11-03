import hashlib,json,subprocess
from pathlib import Path
S=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/shadow-v10r2')
R=Path('/home/root/aura-pan-current-20261024/16a07283');manifest=S/'manifest.json'
digest=hashlib.sha256(manifest.read_bytes()).hexdigest();assert digest=='51265395999f650b9e00465a5a56f7000d447113c0ff6d53de66db33cefd63ec'
p=subprocess.run(['/usr/bin/python3','-B',str(S/'run_shadow.py'),'--manifest-sha256',digest,
 '--settings',str(R/'face-zone-settings.json'),'--output',str(R/'shadow-v10r2-first.json'),
 '--duration','10','--confirmation','SHADOW_ONLY'],capture_output=True,text=True,timeout=20)
report=json.loads((R/'shadow-v10r2-first.json').read_text()) if (R/'shadow-v10r2-first.json').exists() else None
assert p.returncode==0,{'error':p.stderr[-1400:],'report':report}
print(json.dumps(report))
