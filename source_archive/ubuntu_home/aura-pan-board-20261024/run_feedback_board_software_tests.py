"""Run fixture/FakeDevice tests on target PS; never open physical registers."""
import json,os,subprocess,urllib.request
from pathlib import Path
OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');M=OPS/'pan-face-edge-v5/continuous-v2r2'
meta=json.loads((OPS/'meta.json').read_text());env=dict(os.environ,PYTHONPATH=str(M)+':'+str(Path(meta['candidate_root'])/'aura'),PYTHONDONTWRITEBYTECODE='1')
p=subprocess.run(['/usr/bin/python3','-B','-m','unittest','discover','-s',str(M/'verification'),'-p','test_*.py','-v'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=20)
print(json.dumps({'status':'TARGET_PS_SOFTWARE_TESTS_PASS' if p.returncode==0 else 'TARGET_PS_SOFTWARE_TESTS_FAILED',
 'exit_code':p.returncode,'scope':'synthetic frames and FakeDevice; not physical motion acceptance','physical_actuator_access':False,
 'result':p.stderr[-6000:]}))
assert p.returncode==0
