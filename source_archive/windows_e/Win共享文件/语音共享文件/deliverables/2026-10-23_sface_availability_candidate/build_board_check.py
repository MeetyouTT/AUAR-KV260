"""Package isolated in-memory checks; never replace production code or restart."""
import ast
import base64
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARENT = json.loads((ROOT/'PARENT_RELEASE.json').read_text())
PROOF = json.loads((ROOT/'dependency-source-proof.json').read_text())
CHANGED = ('board/vision/dpu_sface.py', 'board/identity/camera_faces.py',
           'board/identity/live.py', 'board/identity/spoken_query.py')
pins = {}
files = {}
for name in CHANGED:
    before = (ROOT/'baseline/aura'/name).read_bytes()
    pins[name] = hashlib.sha256(before).hexdigest()
    after = (ROOT/'candidate/aura'/name).read_bytes()
    assert before != after
    ast.parse(after)
    files['candidate/aura/'+name] = base64.b64encode(after).decode()
assert all(pins[name] == PARENT['candidate_pins'][name] for name in CHANGED[:3])
assert pins[CHANGED[3]] == PROOF['files']['gui_spoken_query']['sha256']
files['tests/test_feature_availability.py'] = base64.b64encode((ROOT/'tests/test_feature_availability.py').read_bytes()).decode()
bootstrap = '''import sys
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,PARENT_AURA)
import board.identity,board.vision
for package,suffix in ((board.identity,'board/identity'),(board.vision,'board/vision')):
 package.__path__.insert(0,str(HERE/'candidate/aura'/suffix))
'''.replace('PARENT_AURA', repr(PARENT['release']+'/aura'))
files['tests/bootstrap.py'] = base64.b64encode(bootstrap.encode()).decode()
data = json.dumps(files, sort_keys=True, separators=(',', ':')).encode()
prefix = 'PAYLOAD='+repr(base64.b64encode(gzip.compress(data, mtime=0)).decode())+'\n'
prefix += 'PAYLOAD_SHA='+repr(hashlib.sha256(data).hexdigest())+'\n'
prefix += 'PARENT='+repr(PARENT)+'\nBASELINE_PINS='+repr(pins)+'\n'
prefix += 'GUI_SPOKEN_PATH='+repr(PROOF['files']['gui_spoken_query']['path'])+'\n'
body = '''import ast,base64,builtins,gzip,hashlib,io,json,sqlite3,subprocess,sys,time,unittest,urllib.request
from pathlib import Path
sys.dont_write_bytecode=True
assert not sys.flags.optimize
BOOT='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
unit=Path('/etc/systemd/system/aura-camera-ui.service')
assert hashlib.sha256(unit.read_bytes()).hexdigest()==PARENT['unit_sha256']
def source_hashes():
 result={}
 for name,digest in BASELINE_PINS.items():
  path=Path(GUI_SPOKEN_PATH) if name.endswith('/spoken_query.py') else Path(PARENT['release'])/'aura'/name
  assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
  result[name]=digest
 return result
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def snapshot():
 with op.open('http://127.0.0.1:8790/health',timeout=3) as response:h=json.load(response)
 i=h['identity'];s=h['dpu_schedule']
 return {'camera_pid':h['pid'],'yolo_hz':h['detection_hz'],'backend':i['backend'],'identity_ready':i['ready'],
  'yunet':s['optional']['yunet'],'sface':s['optional']['sface'],
  'gaps':i['face_targets']['freshness_metrics']['counters']['observed_gap_intervals'],
  'gui_pid':int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value']))}
source_hashes();before=snapshot()
assert before['backend']=='DPU_SFACE_INT8' and before['identity_ready']
source=Path(sys._getframe().f_code.co_filename);digest=hashlib.sha256(source.read_bytes()).hexdigest()
root=Path('/home/root/aura-sface-availability-20261023')/digest[:16]
assert root.parent.resolve()==root.parent
root.mkdir(parents=True,exist_ok=True,mode=0o700);assert root.resolve()==root
assert not (root/'report.json').exists(),'Do not overwrite earlier checks'
raw=gzip.decompress(base64.b64decode(PAYLOAD));assert hashlib.sha256(raw).hexdigest()==PAYLOAD_SHA
for name,value in json.loads(raw).items():
 path=root/name;assert '..' not in Path(name).parts and root in path.parents
 data=base64.b64decode(value);ast.parse(data)
 path.parent.mkdir(parents=True,exist_ok=True);assert path.parent.resolve()==path.parent and not path.is_symlink()
 with path.open('xb') as stream:stream.write(data)
 path.chmod(0o600)
sys.path.insert(0,str(root/'tests'))
original_import=builtins.__import__;original_connect=sqlite3.connect;memory_connections=[]
def isolated_import(name,*args,**kwargs):
 if name.split('.')[0] in ('vart','xir'):raise AssertionError('Real DPU runtime forbidden in isolation')
 return original_import(name,*args,**kwargs)
def memory_only(path,*args,**kwargs):
 assert str(path)==':memory:','Only synthetic in-memory identity storage is permitted'
 memory_connections.append(True);return original_connect(path,*args,**kwargs)
text=io.StringIO();started=time.monotonic()
try:
 builtins.__import__=isolated_import;sqlite3.connect=memory_only
 suite=unittest.defaultTestLoader.discover(str(root/'tests'),pattern='test_feature_availability.py')
 result=unittest.TextTestRunner(stream=text,verbosity=2).run(suite)
finally:
 builtins.__import__=original_import;sqlite3.connect=original_connect
elapsed=time.monotonic()-started
(root/'tests.log').write_text(text.getvalue())
after=snapshot();source_hashes()
assert hashlib.sha256(unit.read_bytes()).hexdigest()==PARENT['unit_sha256']
unchanged=before['camera_pid']==after['camera_pid'] and before['gui_pid']==after['gui_pid']
report={'scope':'ISOLATED_SYNTHETIC_SFACE_AVAILABILITY_AND_VOICE_CONSUMER',
 'helper_sha256':digest,'root':str(root),'boot':BOOT,'parent_unit_sha256':PARENT['unit_sha256'],
 'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'duration_s':elapsed,
 'in_memory_stores':len(memory_connections),'production_before':before,'production_after':after,
 'production_sources_unchanged':source_hashes(),'production_pids_unchanged':unchanged,
 'candidate_deployed':False,'real_dpu_runtime_allowed':False,'real_identity_database_opened':False,
 'passed':result.wasSuccessful() and result.testsRun==16 and unchanged,
 'test_log_sha256':hashlib.sha256(text.getvalue().encode()).hexdigest()}
with (root/'report.json').open('x') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report))
'''
target=ROOT/'board_isolated_check.py'
target.write_text(prefix+body)
ast.parse(target.read_text())
manifest={'helper_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'payload_sha256':hashlib.sha256(data).hexdigest(),
          'candidate_source_hashes':{name:hashlib.sha256((ROOT/'candidate/aura'/name).read_bytes()).hexdigest() for name in CHANGED},
          'baseline_pins':pins,'expected_tests':16,'production_deployment':False}
(ROOT/'isolated-check-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'helper_sha256':manifest['helper_sha256'],'helper_bytes':target.stat().st_size,'files':len(files)}))
