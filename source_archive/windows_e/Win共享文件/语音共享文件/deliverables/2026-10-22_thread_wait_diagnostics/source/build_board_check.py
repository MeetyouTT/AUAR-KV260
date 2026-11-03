"""Only read calling-thread counters and run synthetic diagnostics on KV260."""
import ast
import base64
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
files={name:(ROOT/'candidate/aura/board/vision'/name).read_bytes()
    for name in ('pipeline_metrics.py','thread_sched_metrics.py','dpu_vision_schedule.py')}
tests=ROOT/'timing-tests/tests/test_thread_sched_metrics.py'
test_source=tests.read_text().replace("import board.vision\nboard.vision.__path__.insert(0,'/implementation/candidate/aura/board/vision')\n",'')
sources={'board/vision/'+name:base64.b64encode(gzip.compress(raw,mtime=0)).decode() for name,raw in files.items()}
sources['test_thread_sched_metrics.py']=base64.b64encode(gzip.compress(test_source.encode(),mtime=0)).decode()
hashes={'board/vision/'+name:hashlib.sha256(raw).hexdigest() for name,raw in files.items()}
hashes['test_thread_sched_metrics.py']=hashlib.sha256(test_source.encode()).hexdigest()
prefix='SOURCES='+repr(sources)+'\nHASHES='+repr(hashes)+'\n'
body=r'''
import ast,base64,builtins,gzip,hashlib,importlib,io,json,os,statistics,sys,threading,time,unittest,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='215c4292-ce84-4828-9827-83c32ba66564'
ORIGINAL=Path('/home/root/aura-dpu-vision-20261021/runtime/81fdb11903abb71e-live-134783/aura')
assert hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()=='84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def health():
    with op.open('http://127.0.0.1:8790/health',timeout=3) as f:v=json.load(f)
    return {k:v.get(k) for k in ('pid','detected_frames','camera_error','detector_error')}
before=health();root=Path('/home/root/aura-thread-sched-check-20261022')/HASHES['board/vision/thread_sched_metrics.py'][:16]
root.mkdir(parents=True,exist_ok=True)
for name,blob in SOURCES.items():
    raw=gzip.decompress(base64.b64decode(blob));assert hashlib.sha256(raw).hexdigest()==HASHES[name]
    ast.parse(raw);target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
    assert not target.is_symlink()
    if target.exists():assert target.read_bytes()==raw
    else:
        with target.open('xb') as f:f.write(raw)
sys.path.insert(0,str(ORIGINAL));sys.path.insert(0,str(root))
import board.vision
board.vision.__path__.insert(0,str(root/'board/vision'))
original_import=builtins.__import__
def guarded(name,*args,**kwargs):
    if name.split('.')[0] in ('xir','vart'):raise AssertionError('No native inference bindings allowed in this check')
    return original_import(name,*args,**kwargs)
builtins.__import__=guarded
for name in ('pipeline_metrics','thread_sched_metrics','dpu_vision_schedule'):
    module=importlib.import_module('board.vision.'+name)
    assert Path(module.__file__).resolve()==root/'board/vision'/(name+'.py')
from board.vision.pipeline_metrics import OptionalDiagnostics
from board.vision.thread_sched_metrics import ThreadSwitchProbe as ThreadSchedProbe
tests=importlib.import_module('test_thread_sched_metrics')
buffer=io.StringIO();test_result=unittest.TextTestRunner(stream=buffer,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
assert test_result.wasSuccessful(),buffer.getvalue()
assert test_result.testsRun==21
def stats(values):
    ordered=sorted(values);n=len(ordered)
    return {'count':n,'mean_ms':statistics.mean(ordered)/1e6,'p50_ms':ordered[n//2]/1e6,
        'p95_ms':ordered[min(n-1,int(n*.95))]/1e6,'max_ms':max(ordered)/1e6}
def bench(enabled):
    probe=ThreadSchedProbe() if enabled else None
    diag=OptionalDiagnostics(enabled=True,thread_probe=probe)
    costs=[];reads=[]
    for _ in range(200):
        started=time.monotonic_ns()
        trace=diag.begin('yunet',True,'deadline',20,time.monotonic()+.1)
        diag.native_mark('yunet','execute_start');diag.native_mark('yunet','execute_return')
        diag.native_mark('yunet','wait_start');diag.native_mark('yunet','wait_end',0)
        diag.finish('yunet',trace,.1,-90,0,False,False,False)
        costs.append(time.monotonic_ns()-started)
    if probe:probe.close()
    return {'instrumentation_wall':stats(costs),'observer':probe.snapshot() if probe else {'enabled':False}}
base=bench(False);observed=bench(True)
probe=ThreadSchedProbe();diag=OptionalDiagnostics(enabled=True,thread_probe=probe)
trace=diag.begin('yunet',True,'deadline',20,time.monotonic()+.1)
diag.native_mark('yunet','execute_start');time.sleep(.015)
diag.native_mark('yunet','execute_return');diag.native_mark('yunet','wait_start');diag.native_mark('yunet','wait_end',0)
diag.finish('yunet',trace,16,-80,0,False,False,False)
sample=diag.snapshot()['maximum_normal_trace']
probe.close()
assert sample['probe_same_thread']==1 and 'probe_execute_runqueue_ns_delta' not in sample
assert sample['probe_execute_voluntary_delta']>=1
assert sample['execute_wall_ms']>=10
assert probe.snapshot()['samples']==2
all_reads_available=(not observed['observer']['disabled_after_slow_read'] and observed['observer']['samples']==400)
increment=observed['instrumentation_wall']['mean_ms']-base['instrumentation_wall']['mean_ms']
overhead_ok=all_reads_available and increment<.5 and observed['instrumentation_wall']['p95_ms']<1.
after=health();assert after['pid']==before['pid'] and after['detected_frames']>before['detected_frames']
assert not after['camera_error'] and not after['detector_error']
print(json.dumps({'scope':'BOARD_READONLY_COUNTERS_SYNTHETIC_DIAGNOSTICS_AND_OVERHEAD_ONLY',
    'source_hashes':HASHES,'synthetic_tests':21,'test_output':buffer.getvalue(),
    'baseline':base,'with_observer':observed,'incremental_mean_ms':increment,
    'overhead_prerequisite_passed':overhead_ok,'overhead_acceptance_limit_ms':.5,
    'synthetic_sleep_trace':sample,'board_python':sys.version.split()[0],
    'camera_before':before,'camera_after':after,'actual_dpu_jobs':0,
    'production_sources_or_config_modified':False,'root_cause_verified':False,
    'observed_dpu_fault_with_this_probe':False,'kernel_settings_modified':False,
    'observer_mode':'CONTEXT_SWITCHES_ONLY_NO_RUNQUEUE_TIMING','all_reads_available':all_reads_available}),flush=True)
assert overhead_ok,'Observer overhead prerequisite not passed'
'''
source=prefix+body;ast.parse(source)
target=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_thread_sched_check_20261022_v5.py')
if target.exists():assert target.read_text()==source,'Use a new board-helper revision for changed code'
else:target.write_text(source)
(ROOT/'board-helper-manifest.json').write_text(json.dumps({'path':str(target),
    'sha256':hashlib.sha256(source.encode()).hexdigest(),'bytes':len(source),
    'source_hashes':hashes,'production_deployment':False},indent=2)+'\n')
print(json.dumps({'helper':str(target),'bytes':len(source)}))
