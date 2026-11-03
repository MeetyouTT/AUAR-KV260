import hashlib,json,os,subprocess,urllib.request
from pathlib import Path
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5')
P=F/'continuous-v10r14';V=F/'continuous-v10r14-verify'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def manual():
 with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:return json.load(f)['manual_pan']
before=manual();assert before['state']=='READY' and not before['automatic_following']
assert before['readback']['flags']==0 and before['readback']['lease_left_ms']==0
manifest=json.loads((P/'deployment-manifest.json').read_text())
assert all(hashlib.sha256(Path(x['destination']).read_bytes()).hexdigest()==x['sha256'] for x in manifest['files'])
env=dict(os.environ,PYTHONPATH=str(P))
command=['/usr/bin/python3','-B',str(V/'replay_initial_pwm_budget.py'),'--compare',
 '--baseline-root',str(F/'continuous-v10r12'),'--candidate-root',str(P),
 '--trajectory-library',str(P/'libaura_trajectory.so')]
job=subprocess.run(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=20)
assert job.returncode==0,job.stderr[-700:]
replay=json.loads(job.stdout);assert replay['passed'] and len(replay['paired_scenarios'])==4
tests=subprocess.run(['/usr/bin/python3','-B','-m','unittest','discover','-s',str(V),'-p','test_session_shutdown.py'],
 env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=10)
assert tests.returncode==0 and 'Ran 8 tests' in tests.stderr,tests.stderr[-1000:]
after=manual();assert after['state']=='READY' and not after['automatic_following']
assert after['readback']==before['readback']
print(json.dumps({'status':'R14_BOARD_SOFTWARE_ISOLATION_PASS','replay':replay,
 'shutdown_tests':8,'shutdown_output':tests.stderr,'readback_before':before['readback'],
 'readback_after':after['readback'],'physical_motor_verified':False,'motor_commands_sent':0,
 'scope':'KV260 ARM trajectory library and pure fake PWM/reader, no MMIO or new DPU owner'}))
