import hashlib,json,os,subprocess,urllib.request
from pathlib import Path
G=Path('/home/root/aura-pan-current-20261024/16a07283/gui-manual-bound-v1')
A=G/'runtime/aura';V=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/gui-lifecycle-v2-verify')
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def manual():
 with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:return json.load(f)['manual_pan']
before=manual();assert before['state']=='READY' and not before['automatic_following']
assert before['readback']['flags']==0 and before['readback']['lease_left_ms']==0
pins=json.loads((G/'startup/config.json').read_text())['component_sha256']
assert all(hashlib.sha256((A/n).read_bytes()).hexdigest()==h for n,h in pins.items())
assert pins['tools/face_pan_controls.py']=='3ebb1b32368c8f12864e0f13da68853e4d9653e4279eada124eb337c5ca9d7ee'
env=dict(os.environ,AURA_LIFECYCLE_TEST_TOOLS=str(A/'tools'))
job=subprocess.run(['/usr/bin/python3','-B','-m','unittest','discover','-s',str(V),'-p','test_*.py'],
 env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15)
assert job.returncode==0 and 'Ran 22 tests' in job.stderr,job.stderr[-1800:]
after=manual();assert after['state']=='READY' and not after['automatic_following'] and after['readback']==before['readback']
print(json.dumps({'status':'GUI_LIFECYCLE_BOARD_22_PASS','tests_output':job.stderr,'gui_pins':len(pins),
 'readback_before':before['readback'],'readback_after':after['readback'],'motor_commands_sent':0,
 'scope':'installed GUI class with fake motor factory; one unrelated child termination; no real motor child or MMIO'}))
