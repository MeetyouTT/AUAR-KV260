"""One isolated retry-only short trial, with fake tests before service mutation."""
import ast
import base64
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
HELPERS=Path('/home/ghmd/aura-identity-dpu-check-20261018')
BASE=HELPERS/'board_thread_switch_live_20261022.py'
assert hashlib.sha256(BASE.read_bytes()).hexdigest()=='a439f630bfeb7d86fe93133dd7f287cb30a248a011ecf48950ad4692b5e5694d'
candidate=Path('/home/ghmd/aura-yunet-retry-integration-20261022')
rows=json.loads((candidate/'candidate-manifest.json').read_text())['sources']
names=['candidate/aura/'+name for name,row in rows.items() if row['changed']]+['tests/bootstrap.py','tests/test_yunet_retry.py']
data={name:(candidate/name).read_bytes() for name in names}
hashes={name:hashlib.sha256(raw).hexdigest() for name,raw in data.items()}
for name,row in rows.items():assert hashlib.sha256((candidate/'candidate/aura'/name).read_bytes()).hexdigest()==row['candidate_sha256']
source=BASE.read_text().replace('215c4292-ce84-4828-9827-83c32ba66564','7924ac9f-311d-4fcd-98be-57bf023cf1aa')
source=source.replace("(usb/'devnum').read_text().strip()=='4'", "(usb/'devnum').read_text().strip()=='3'")
source=source.replace('thread-switch-live','postpower-retry-live').replace('thread-switch-launches','postpower-retry-launches')
source=source.replace('AURA_RUN_THREAD_SWITCH_LIVE','AURA_RUN_POSTPOWER_RETRY')
source=source.replace('THREAD_SWITCH_DUAL_MODEL_120S_ALWAYS_RESTORED','YUNET_RETRY_5MS_DUAL_MODEL_120S_ALWAYS_RESTORED')
def replace(old,new):
 global source
 assert source.count(old)==1,(old[:90],source.count(old))
 source=source.replace(old,new)
replace("    path=candidate/'board/vision/ui_camera_service.py'", '''
    import base64,gzip
    for name,encoded in RETRY_PAYLOAD.items():
        raw=gzip.decompress(base64.b64decode(encoded));assert hashlib.sha256(raw).hexdigest()==RETRY_HASHES[name]
        target=(candidate/name[len('candidate/aura/'):]) if name.startswith('candidate/aura/') else folder/name
        target.parent.mkdir(parents=True,exist_ok=True);assert not target.is_symlink();target.write_bytes(raw)
    baseline=folder/'baseline/aura/board/identity/face_targets.py';baseline.parent.mkdir(parents=True,exist_ok=True)
    baseline.write_bytes((BASE/'aura/board/identity/face_targets.py').read_bytes())
    check_source=FAKE_TEST_WORKER.replace('ROOT_VALUE',repr(str(folder))).replace('AURA_VALUE',repr(str(candidate)))
    check_path=folder/'check_fake_tests.py';check_path.write_text(check_source)
    checked=subprocess.run(['/usr/bin/python3','-B',str(check_path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    (folder/'fake-tests.stderr.txt').write_bytes(checked.stderr)
    (folder/'fake-tests.stdout.json').write_bytes(checked.stdout)
    assert checked.returncode==0,'Isolated candidate tests failed: '+checked.stderr.decode(errors='replace')[-500:]
    checked_result=json.loads(checked.stdout);assert checked_result['run']==39 and checked_result['passed'] and checked_result['skipped']==0
    face_source=candidate/'board/identity/camera_faces.py';text=face_source.read_text()
    old="minimum_score=config['minimum_face_score'],minimum_pixels=config['minimum_face_pixels'])"
    new="minimum_score=config['minimum_face_score'],minimum_pixels=config['minimum_face_pixels'],slot_retry=True)"
    assert text.count(old)==1;text=text.replace(old,new);ast.parse(text);face_source.write_text(text)
    path=candidate/'board/vision/ui_camera_service.py'
''')
wrapper=Path('/home/ghmd/aura-gil-trial-20261022/gil_camera_launcher.py').read_text()
wrapper=wrapper.replace('/home/root/aura-dpu-vision-20261021/gil-switch-live','/home/root/aura-dpu-vision-20261021/postpower-retry-live')
replace('    assert updated!=original_unit', '''
    launcher=folder/'gil_camera_launcher.py';launcher.write_bytes(base64.b64decode(RETRY_WRAPPER))
    assert digest(launcher)==RETRY_WRAPPER_SHA
    target=str(candidate/'tools/board_camera_motion.py');assert digest(target)=='1e0e6f0b8881c2d4d4cf81a2527e79d063e673eeba1d069e33bdde2608303005'
    text=updated.decode();assert text.count(target)==1
    text=text.replace(target,str(launcher)+' '+target)
    text=text.replace('[Service]\\n','[Service]\\nEnvironment="AURA_EXPERIMENT_GIL_MS=5"\\n')
    updated=text.encode()
    assert updated!=original_unit
''')
replace("'runqueue_time_collected':False,'requested_observation_s':120}",
 "'runqueue_time_collected':False,'requested_observation_s':120,'retry_hashes':RETRY_HASHES,\n        'retry_enabled':True,'gil_seconds':.005,'fake_candidate_tests':checked_result,\n        'freshness_wiring_sha256':digest(face_source)}")
replace("single_owner(state['pid']);first=state;started=time.monotonic();first_cpu=cpu()", '''
        single_owner(state['pid'])
        startup=json.loads((folder/('process-setting-'+str(state['pid'])+'.json')).read_text())
        assert startup['actual_start_seconds']==startup['previous_seconds']==.005
        report['process_setting']=startup
        assert state['face_targets']['slot_retry']['enabled']
        first=state;started=time.monotonic();first_cpu=cpu()
''')
replace("assert digest(path)==report['candidate_ui_sha256']", "assert digest(path)==report['candidate_ui_sha256']\n        assert digest(face_source)==report['freshness_wiring_sha256']")
replace("report['passed']=True;report['observation_status']='OBSERVER_120S_RUNTIME_ONLY_NOT_ROOT_CAUSE_OR_GAIN_PROOF'", '''
        diag=state['pipeline_metrics']['optional_diagnostics'];counters=diag['counters']['yunet']
        retry=state['face_targets']['slot_retry']
        assert counters['native_failed']==retry['withdrawn_after_slot'],'Unexpected native failure'
        assert not diag['diagnostic_errors']
        assert not any(event.get('hardcap_exceeded') or event.get('guard_exceeded') for event in diag['fault_events'])
        first_diag=first['pipeline_metrics']['optional_diagnostics']['counters']['yunet']
        report['native_completed_delta']=counters['native_completed']-first_diag['native_completed']
        report['observed_yunet_hz']=report['native_completed_delta']/elapsed
        assert report['observed_yunet_hz']>=2 and report['native_completed_delta']>=100
        report['published_delta']=state['face_targets']['processed']-first['face_targets']['processed']
        ages=[row['face_targets']['source_age_ms'] for row in report['samples']]
        report['sampled_freshness']={'samples':len(ages),'maximum_ms':max(ages),
            'at_or_over_ttl':sum(age>=1000 for age in ages),'scope':'sparse health snapshots; not per-publication coverage'}
        report['throughput_and_protection_passed']=True
        report['passed']=all(0<=age<1000 for age in ages)
        report['observation_status']='RETRY_5MS_SHORT_WITH_SEPARATE_FRESHNESS_GATE_NOT_SPEEDUP_PROOF'
''')
worker='''import importlib.abc,io,json,os,sys,unittest,unittest.mock
from pathlib import Path
root=Path(ROOT_VALUE);aura=AURA_VALUE
for name in ('AURA_SHARED_SOURCE','AURA_LIVE_SOURCE','AURA_DPU_SOURCE','AURA_FROZEN_SOURCE'):os.environ[name]=aura
sys.path.insert(0,str(root/'tests'))
class DenyDevices(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in ('vart','xir','cv2','gi','serial','requests'):raise ImportError('No device imports in fake checks')
def audit(event,args):
 if event.startswith('socket.') or event in ('subprocess.Popen','os.system'):raise RuntimeError('No device/network/subprocess')
 if event=='open' and args and isinstance(args[0],(str,bytes)) and os.fsdecode(args[0]).startswith('/dev/'):
  raise RuntimeError('No device opens')
sys.meta_path.insert(0,DenyDevices());sys.addaudithook(audit)
suite=unittest.defaultTestLoader.discover(str(root/'tests'),pattern='test_yunet_retry.py')
stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
print(json.dumps({'run':r.testsRun,'passed':r.wasSuccessful(),'skipped':len(r.skipped),
 'failures':len(r.failures),'errors':len(r.errors),'output':stream.getvalue(),'new_native_jobs':0}))
sys.exit(0 if r.wasSuccessful() else 1)
'''
prefix='RETRY_PAYLOAD='+repr({name:base64.b64encode(gzip.compress(raw,mtime=0)).decode() for name,raw in data.items()})+'\n'
prefix+='RETRY_HASHES='+repr(hashes)+'\nFAKE_TEST_WORKER='+repr(worker)+'\n'
prefix+='RETRY_WRAPPER='+repr(base64.b64encode(wrapper.encode()).decode())+'\nRETRY_WRAPPER_SHA='+repr(hashlib.sha256(wrapper.encode()).hexdigest())+'\n'
source=prefix+source
ast.parse(source)
target=HELPERS/'board_postpower_retry_live_usb3_20261022.py'
if target.exists():assert target.read_text()==source
else:target.write_text(source)
manifest={'helper':str(target),'sha256':hashlib.sha256(source.encode()).hexdigest(),'payload':hashes,
 'seconds':120,'gil_seconds':.005,'retry_enabled':True,'freshness_observer_enabled':False,
 'protection_30ms_5ms_unchanged':True,'boot':'7924ac9f-311d-4fcd-98be-57bf023cf1aa'}
(ROOT/'retry-live-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest))
