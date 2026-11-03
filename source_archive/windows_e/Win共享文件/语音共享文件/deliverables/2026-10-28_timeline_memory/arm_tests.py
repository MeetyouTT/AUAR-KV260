"""Run the portable memory core in an isolated board folder; no live DB or UI edits."""
import base64,hashlib,json,sys,uuid
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
before=json.loads((H/'runtime_before.json').read_text(encoding='utf-8'))
files={str(p.relative_to(H/'candidate_source')).replace('\\','/'):base64.b64encode(p.read_bytes()).decode()
       for p in (H/'candidate_source').rglob('*') if p.is_file()}
files['test_timeline.py']=base64.b64encode((H/'test_timeline.py').read_bytes()).decode()
for name in ('tools/profile_control.py','common/profile_memory.py','common/profile_access.py',
             'common/conversation_store.py','common/conversation_context.py','common/memory_commands.py',
             'tools/visual_question_host.py'):
    files[name]=base64.b64encode((H.parents[1]/'aura'/name).read_bytes()).decode()
stage='/home/root/aura-timeline-tests-20261028/'+uuid.uuid4().hex
script=r'''
import base64,hashlib,json,os,subprocess,sys
from pathlib import Path
stage=Path(STAGE);root=Path(ROOT)/'aura'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert not stage.exists();stage.mkdir(parents=True)
for name,data in FILES.items():
 p=stage/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(data))
runner=r"""
import importlib,sys,types
from pathlib import Path
H=Path(__file__).resolve().parent;A=Path(AURA)
sys.path.insert(0,str(A))
for name in ('common','tools'):
 p=importlib.import_module(name);p.__path__=[str(H/name),str(A/name)]
name='tools.board_model_host';module=types.ModuleType(name);module.__file__=str(A/'tools/board_model_host.py');module.__package__='tools'
sys.modules[name]=module
exec(compile((H/'tools/board_model_host.py').read_text(),str(H/'tools/board_model_host.py'),'exec'),module.__dict__)
import pytest
raise SystemExit(pytest.main(['-q',str(H/'test_timeline.py'),'--junitxml='+str(H/'tests.xml')]))
""".replace('AURA',repr(str(root)))
(stage/'run.py').write_text(runner)
result=subprocess.run(['python3','-B',str(stage/'run.py')],cwd=root,
 env=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin'),text=True,capture_output=True,timeout=90)
(stage/'test.log').write_text(result.stdout+result.stderr)
print(json.dumps({'stage':str(stage),'returncode':result.returncode,'log':result.stdout+result.stderr,
 'files':{n:hashlib.sha256((stage/n).read_bytes()).hexdigest() for n in FILES},'production_database_used':False}))
'''.replace('STAGE',repr(stage)).replace('ROOT',repr(before['actual_runtime'])).replace('BOOT',repr(before['boot'])).replace('FILES',repr(files))
result=json.loads(ssh('python3 -B -',script,timeout=105))
(H/('arm_tests_'+stage.rsplit('/',1)[-1]+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(H/'arm_tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(result['log']);assert result['returncode']==0
