"""Pack the exact candidate and device-free fault tests for a short board check."""
import ast
import base64
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
paths = list((ROOT/'candidate').rglob('*.py'))
paths += [ROOT/'tests/test_bounded_recovery.py']
paths += [ROOT/'baseline/aura/board/vision/dpu_vision_schedule.py']
files = {}
for path in paths:
    raw = path.read_bytes(); ast.parse(raw)
    files[str(path.relative_to(ROOT))] = {'sha256': hashlib.sha256(raw).hexdigest(),
                                        'base64': base64.b64encode(raw).decode()}
raw = json.dumps(files, sort_keys=True, separators=(',', ':')).encode()
payload = base64.b64encode(gzip.compress(raw, mtime=0)).decode()
seal = hashlib.sha256(raw).hexdigest()
prefix = 'PAYLOAD='+repr(payload)+'\nPAYLOAD_SHA='+repr(seal)+'\n'
body = '''import ast,base64,gzip,hashlib,importlib.util,io,json,platform,sys,time,unittest,urllib.request
from pathlib import Path
sys.dont_write_bytecode=True
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
unit=Path('/etc/systemd/system/aura-camera-ui.service')
unit_sha=hashlib.sha256(unit.read_bytes()).hexdigest()
assert unit_sha=='af337bce5d7f274b35cb79046078220ca6e3fbdbdcdb1d62570e106289dc6f7b'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def health():
 with op.open('http://127.0.0.1:8790/health',timeout=3) as response:return json.load(response)
before=health()
raw=gzip.decompress(base64.b64decode(PAYLOAD));assert hashlib.sha256(raw).hexdigest()==PAYLOAD_SHA
root=Path('/home/root/aura-yunet-bounded-recovery-20261023')/('preflight-'+PAYLOAD_SHA[:16])
root.mkdir(parents=True,exist_ok=True);assert root.resolve()==root
files=json.loads(raw)
for name,meta in files.items():
 path=root/name;assert root in path.parents and '..' not in Path(name).parts
 data=base64.b64decode(meta['base64']);assert hashlib.sha256(data).hexdigest()==meta['sha256'];ast.parse(data)
 path.parent.mkdir(parents=True,exist_ok=True);assert path.parent.resolve()==path.parent and not path.is_symlink()
 if path.exists():assert path.read_bytes()==data
 else:
  with path.open('xb') as stream:stream.write(data)
spec=importlib.util.spec_from_file_location('_bounded_board_tests',root/'tests/test_bounded_recovery.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
suite=unittest.defaultTestLoader.loadTestsFromModule(module)
output=io.StringIO();started=time.monotonic()
result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
duration=time.monotonic()-started
assert result.wasSuccessful(),output.getvalue()
assert not any(name in sys.modules for name in ('vart','xir','numpy','cv2','gi'))
from board.vision.dpu_vision_schedule import DpuVisionSchedule
assert Path(sys.modules[DpuVisionSchedule.__module__].__file__).resolve()==root/'candidate/aura/board/vision/dpu_vision_schedule.py'
spec=importlib.util.spec_from_file_location('_bounded_original_schedule',root/'baseline/aura/board/vision/dpu_vision_schedule.py')
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
def measure(factory,notify):
 s=factory();s.next_primary=time.monotonic()+3600
 start=time.monotonic_ns();cpu=time.thread_time_ns()
 for _ in range(500):
  with s.optional('yunet') as acquired:
   assert acquired
   if notify:s.native_completed('yunet')
 return {'per_call_wall_ms':(time.monotonic_ns()-start)/500e6,
         'per_call_thread_cpu_ms':(time.thread_time_ns()-cpu)/500e6}
costs={'original':measure(original.DpuVisionSchedule,False),
       'enabled':measure(lambda:DpuVisionSchedule(yunet_recovery=True),True)}
extra=costs['enabled']['per_call_thread_cpu_ms']-costs['original']['per_call_thread_cpu_ms']
assert extra<.5
after=health();assert before['pid']==after['pid'] and hashlib.sha256(unit.read_bytes()).hexdigest()==unit_sha
print(json.dumps({'scope':'DEVICE_FREE_RECOVERY_POLICY_ON_KV260','passed':True,
 'tests_run':result.testsRun,'test_names':[line.split(' ... ')[0] for line in output.getvalue().splitlines() if line.startswith('test_')],
 'test_duration_s':duration,'payload_sha256':PAYLOAD_SHA,'source_files_verified':len(files),
 'python_version':platform.python_version(),'machine':platform.machine(),
 'actual_dpu_jobs':0,'runtime_changed':False,'camera_pid_before':before['pid'],'camera_pid_after':after['pid'],
 'face_backend_before':before['identity']['face_targets']['backend'],
 'face_backend_after':after['identity']['face_targets']['backend'],
 'unit_sha256':unit_sha,'costs':costs,'added_thread_cpu_ms':extra,
 'cost_scope':'500 empty synthetic slots per mode; no VART or real frames; not whole-board CPU savings'}))
'''
target = ROOT/'board_preflight.py'
target.write_text(prefix+body)
ast.parse(target.read_text())
(ROOT/'board-preflight-manifest.json').write_text(json.dumps({
    'helper_sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'payload_sha256': seal,
    'files': {name: meta['sha256'] for name, meta in files.items()}}, indent=2)+'\n')
print(json.dumps({'helper': str(target), 'source_files': len(files), 'payload_sha256': seal}))
