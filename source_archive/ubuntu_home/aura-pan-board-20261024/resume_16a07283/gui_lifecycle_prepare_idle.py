import hashlib,importlib.util,json,time,urllib.request
from pathlib import Path
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/gui-lifecycle-v2')
assert hashlib.sha256((P/'gui_lifecycle_deploy.py').read_bytes()).hexdigest()=='5d934d3ce07fdb52f18f63dd3be2215daaea90898ca45cc1288e85f5fd5041ba'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));end=time.monotonic()+18;stable=None
while time.monotonic()<end:
 with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
 ready=u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY'
 if ready:
  if stable is None:stable=time.monotonic()
  if time.monotonic()-stable>=1:break
 else:stable=None
 time.sleep(.2)
else:raise RuntimeError('No stable idle window; GUI not changed')
s=importlib.util.spec_from_file_location('gui_lifecycle_deploy',P/'gui_lifecycle_deploy.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.main('prepare')
