"""Stage only small test sources in a new isolated directory; never start motion."""
import base64,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
source=HERE/'pan_candidate'
files={p.relative_to(source).as_posix():p.read_text(encoding='utf-8') for p in sorted(source.rglob('*.py'))}
digest=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
payload=base64.b64encode(json.dumps(files).encode()).decode()
script=r'''
import base64,hashlib,io,json,os,sys,unittest,urllib.request
from pathlib import Path
files=json.loads(base64.b64decode('PAYLOAD'))
root=Path('/home/root/aura-system-auto-tests-20261026/DIGEST')
root.mkdir(parents=True,exist_ok=False)
for relative,text in files.items():
    p=(root/relative).resolve();p.relative_to(root)
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
lib=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v10r10/libaura_trajectory.so')
assert hashlib.sha256(lib.read_bytes()).hexdigest()=='d08abd38232b6b7040b84befdd45c925a53885774ece339bdc1bf21f5adedd7a'
os.environ['AURA_TEST_TRAJECTORY']=str(lib)
os.environ['PYTHONDONTWRITEBYTECODE']='1';sys.dont_write_bytecode=True
before=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
sys.path[:0]=[str(root/'continuous_v10r11'),str(root)]
guard=[True]
def audit(event,args):
    if not guard[0]:return
    if event in ('socket.connect','socket.bind','subprocess.Popen','os.system','os.exec'):
        raise RuntimeError('External activity forbidden in FakeDevice tests: '+event)
    if event=='open' and isinstance(args[0],str) and args[0].startswith('/dev/'):
        raise RuntimeError('Device access forbidden in FakeDevice tests')
    if event=='ctypes.dlopen' and args[0] not in (None,str(lib)):
        raise RuntimeError('Only verified trajectory math library is allowed')
sys.addaudithook(audit)
out=io.StringIO()
suite=unittest.defaultTestLoader.discover(str(root/'continuous_v10r11'),pattern='test_*.py')
result=unittest.TextTestRunner(stream=out,verbosity=2).run(suite)
guard[0]=False
value={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,
       'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
       'source_digest':'DIGEST','stage':str(root),'native_library':str(lib),
       'native_library_sha256':hashlib.sha256(lib.read_bytes()).hexdigest(),
       'physical_motion':False,'production_source_changed':False,'network_in_tests':False,
       'boot_unchanged':before==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
       'log':out.getvalue()}
(root/'result.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value))
'''.replace('PAYLOAD',payload).replace('DIGEST',digest[:16])
raw=ssh('python3 -B -',script,timeout=40)
value=json.loads(raw)
(HERE/'motion_board_fake_device.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in value.items() if k!='log'}))
if value['status']!='PASS':print(value['log']);raise SystemExit(1)
