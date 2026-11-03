import hashlib,json,subprocess
from pathlib import Path
S=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/shadow-v10r1')
R=Path('/home/root/aura-pan-current-20261024/16a07283');manifest=S/'manifest.json'
digest=hashlib.sha256(manifest.read_bytes()).hexdigest();assert digest=='f78e60013e8c909185ac2ea3fff254ee144015f6b5d100634e8ea67f26aaf150'
p=subprocess.run(['/usr/bin/python3','-B',str(S/'run_shadow.py'),'--manifest-sha256',digest,
 '--settings',str(R/'face-zone-settings.json'),'--output',str(R/'shadow-v10r1-first.json'),
 '--duration','10','--confirmation','SHADOW_ONLY'],capture_output=True,text=True,timeout=20)
report=json.loads((R/'shadow-v10r1-first.json').read_text()) if (R/'shadow-v10r1-first.json').exists() else None
assert p.returncode==0,{'error':p.stderr[-1400:],'report':report}
print(json.dumps(report))
