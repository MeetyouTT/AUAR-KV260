"""Pending ARM verification. Never run while the user retains a parallel test."""
import base64,json,sys,uuid
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
progress=json.loads((H/'PROGRESS.json').read_text(encoding='utf-8-sig'))
if progress['user_hold_board']:raise SystemExit('User retains the board test; ARM execution is deferred.')
baseline=json.loads((H/'board_baseline.json').read_text(encoding='utf-8'))
assert baseline['preflight_ready'] and not baseline['hash_mismatches']
sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'));from board_ssh import ssh
files={p.relative_to(H/'candidate_source').as_posix():base64.b64encode(p.read_bytes()).decode()
       for p in (H/'candidate_source').rglob('*.py')}
for name in ('tools/profile_control.py','tools/device_client.py','tools/visual_question_host.py',
    'tools/voice_channel_source.py','tools/dialogue_stream.py','tools/native_grammar.py',
    'common/profile_memory.py','common/profile_access.py','common/conversation_store.py',
    'common/conversation_context.py','common/memory_commands.py','common/timeline_config.py'):
    files[name]=base64.b64encode((A/name).read_bytes()).decode()
for path in (A/'common').glob('*.py'):
    name=path.relative_to(A).as_posix()
    if name not in files:files[name]=base64.b64encode(path.read_bytes()).decode()
for name in ('test_timeline.py','test_summaries.py'):files[name]=base64.b64encode((H/name).read_bytes()).decode()
stage='/home/root/aura-summary-tests-20261028/'+uuid.uuid4().hex
script=r'''
import base64,hashlib,json,os,subprocess,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
config=json.loads(Path(CONFIG).read_text())
assert config['component_sha256']==PINS and config['runtime']==ROOT
assert all(hashlib.sha256((Path(ROOT)/'aura'/name).read_bytes()).hexdigest()==value for name,value in PINS.items())
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as response:state=json.load(response)
assert state['phase']=='IDLE' and state['audio_output_state']=='IDLE_READY'
assert state['handsfree_dialogue']['enabled'] is False and state['handsfree_dialogue']['microphone_open'] is False
assert state['manual_pan']['automatic_following'] is False
stage=Path(STAGE);assert not stage.exists();stage.mkdir(parents=True)
for name,value in FILES.items():
 target=stage/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(base64.b64decode(value))
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
raise SystemExit(pytest.main(['-q',str(H/'test_timeline.py'),str(H/'test_summaries.py'),'--junitxml='+str(H/'tests.xml')]))
""".replace('AURA',repr(ROOT+'/aura'))
(stage/'run.py').write_text(runner)
result=subprocess.run(['python3','-B',str(stage/'run.py')],cwd=ROOT+'/aura',
    env=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin'),capture_output=True,text=True,timeout=120)
print(json.dumps({'stage':str(stage),'returncode':result.returncode,'log':result.stdout+result.stderr}))
'''.replace('BOOT',repr(baseline['boot'])).replace('STAGE',repr(stage)).replace('CONFIG',repr(baseline['actual_config'])).replace('PINS',repr(baseline['pins'])).replace('ROOT',repr(baseline['actual_runtime'])).replace('FILES',repr(files))
result=json.loads(ssh('python3 -B -',script,timeout=135))
(H/'arm_tests.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(result['log']);assert result['returncode']==0
