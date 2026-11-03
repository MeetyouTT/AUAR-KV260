import ast
import base64
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;FIX=HERE/'py39_fix'
ARCHIVE=HERE.parents[2]/'2026-10-31_visual_axis_maintenance'
prefix=Path('deliverables/2026-11-02_5090_deployment/maintenance_original_axis_20261101/left_stop40_20261102')
files={}
for p in (FIX/'candidate').rglob('*.py'):files[(prefix/'candidate'/p.relative_to(FIX/'candidate')).as_posix()]=p.read_bytes()
files[(prefix/'before/continuous_face_control.py').as_posix()]=(FIX/'before/continuous_face_control.py').read_bytes()
files[(prefix/'test_left_episode.py').as_posix()]=(FIX/'test_left_episode.py').read_bytes()
for name in ('tests/fixtures/test_recenter.py','candidate/controller/test_hardware_slew.py'):
    files['deliverables/2026-10-31_visual_axis_maintenance/'+name]=(ARCHIVE/name).read_bytes()
payload={name:dict(data=base64.b64encode(data).decode(),sha256=hashlib.sha256(data).hexdigest()) for name,data in files.items()}
runner="""import datetime,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
import base64
payload=json.loads(base64.b64decode('FILES_BASE64'))
assert sys.version_info[:2]==(3,9)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='903cfade-b93c-48fa-804e-379be1967313'
with tempfile.TemporaryDirectory(prefix='aura-left40-pure39-') as tmp:
    sandbox=Path(tmp)
    for name,record in payload.items():
        rel=Path(name);assert not rel.is_absolute() and '..' not in rel.parts
        p=sandbox/rel;data=base64.b64decode(record['data'])
        assert hashlib.sha256(data).hexdigest()==record['sha256']
        p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    root=sandbox/'PREFIX_TEXT'
    archive=sandbox/'deliverables/2026-10-31_visual_axis_maintenance'
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    env['PYTHONPATH']=os.pathsep.join(map(str,(root,root/'candidate',archive/'tests/fixtures',archive/'candidate/controller')))
    code='import io,json,sys,unittest;import test_left_episode,test_hardware_slew;buf=io.StringIO();suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(test_left_episode),unittest.defaultTestLoader.loadTestsFromModule(test_hardware_slew)]);r=unittest.TextTestRunner(stream=buf,verbosity=2).run(suite);assert not any(x in sys.modules for x in ("vsrv_driver","vsrv_transport","batch_transport","deadline_driver","trajectory"));print(json.dumps(dict(tests_run=r.testsRun,failures=len(r.failures),errors=len(r.errors),skipped=len(r.skipped),log=buf.getvalue(),passed=r.wasSuccessful())));sys.exit(0 if r.wasSuccessful() else 1)'
    result=subprocess.run([sys.executable,'-B','-c',code],cwd=root,env=env,capture_output=True,text=True,timeout=15)
    tests=json.loads(result.stdout) if result.stdout.strip().startswith('{') else None
    out=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS' if result.returncode==0 else 'FAIL',
        python=sys.version,tests=tests,stderr=result.stderr,returncode=result.returncode,files_verified=len(payload),
        candidate_core_sha256=payload['PREFIX_TEXT/candidate/continuous_face_control.py']['sha256'],
        actuator_modules_imported=False,native_trajectory_imported=False,production_files_changed=False,hardware_commands_sent=False)
print(json.dumps(out))
""".replace('FILES_BASE64',base64.b64encode(json.dumps(payload).encode()).decode()).replace('PREFIX_TEXT',prefix.as_posix())
ast.parse(runner);p=FIX/'run_board_py39_pure.prepared.py';assert not p.exists();p.write_text(runner,encoding='utf-8')
print(json.dumps(dict(script_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source_files=len(files))))
