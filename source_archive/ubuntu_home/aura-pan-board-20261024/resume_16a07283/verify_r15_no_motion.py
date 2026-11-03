import hashlib,json,os,subprocess,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura'
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');P=F/'continuous-v10r15';V=F/'continuous-v10r15-verify'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def manual():
 with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:return json.load(f)['manual_pan']
before=manual();assert before['state']=='READY' and not before['automatic_following']
assert before['readback']['flags']==0 and before['readback']['lease_left_ms']==0
assert all(hashlib.sha256(Path(x['destination']).read_bytes()).hexdigest()==x['sha256'] for x in json.loads((P/'deployment-manifest.json').read_text())['files'])
mc=json.loads((A/'config/pan_manual.local.json').read_text());driver_root=Path(mc['release_manifest']).parent
replay=subprocess.run(['/usr/bin/python3','-B',str(V/'replay_cached_ack.py'),'--baseline-root',str(F/'continuous-v10r14'),
 '--candidate-root',str(P),'--driver-root',str(driver_root)],capture_output=True,text=True,timeout=12)
assert replay.returncode==0,replay.stderr[-1200:]
bench=subprocess.run(['/usr/bin/python3','-B',str(V/'benchmark_live_writer.py'),'--report',str(F/'continuous-v10r14/runs/ui-46817777160192/trial.json'),
 '--output-parent',str(V)],env=dict(os.environ,PYTHONPATH=str(P)),capture_output=True,text=True,timeout=12)
assert bench.returncode==0,bench.stderr[-1200:]
after=manual();assert after['state']=='READY' and not after['automatic_following'] and before['readback']==after['readback']
print(json.dumps({'status':'R15_KV260_SOFTWARE_ISOLATION_PASS','paired_driver_replay':json.loads(replay.stdout),
 'live_writer_benchmark':json.loads(bench.stdout),'readback':after['readback'],
 'motor_commands_sent':0,'service_restarted':False,'physical_smoothness_verified':False}))
