"""Isolate code from the active voice runtime; no services or models changed."""
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

names=['aura/board/runtime/audio/capture.py','aura/board/runtime/audio/automatic_capture.py',
       'aura/board/runtime/audio/vad.py','aura/tools/board_recording.py',
       'aura/tools/board_avatar_worker.py','aura/tools/board_avatar_gtk.py','aura/config/board_avatar_gtk.json']
files={name:base64.b64encode((ROOT/name).read_bytes()).decode() for name in names}
for name in ('test_automatic_conversation.py','test_audio_capture.py','test_board_recording.py',
             'test_transcription.py','test_board_avatar_worker.py'):
    files['tests/'+name]=base64.b64encode((ROOT/'aura/tests/framework'/name).read_bytes()).decode()
release=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()[:12]
remote=r'''
import base64,hashlib,json,os,re,shutil,subprocess,urllib.request
from pathlib import Path
p=PAYLOAD
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
match=re.search(r'^ExecStart=.*?--config (\S+)\s*$',unit,re.M)
assert match,'Unknown current launcher'
old_config=Path(match.group(1));config=json.loads(old_config.read_text());source=Path(config['runtime'])
assert source.is_dir() and source.is_absolute()
stage=Path('/home/root/aura-automatic-conversation-20261018')/('candidate-'+p['release'])
assert stage.parent==Path('/home/root/aura-automatic-conversation-20261018')
stage.mkdir(parents=True,exist_ok=False);runtime=stage/'runtime'
changes={name:base64.b64decode(data,validate=True) for name,data in p['files'].items() if name.startswith('aura/')}
changed=set(changes)
for package in ('tools','board','common','host'):
    for path in (source/'aura'/package).rglob('*.py'):
        changes.setdefault(str(path.relative_to(source)),path.read_bytes())
def overlay(src,dst,prefix=''):
    dst.mkdir(parents=True,exist_ok=True)
    for item in src.iterdir():
        name=prefix+item.name;target=dst/item.name
        if name in changes:target.write_bytes(changes[name])
        elif any(key.startswith(name+'/') for key in changes):overlay(item,target,name+'/')
        elif prefix=='' and item.name.endswith('_settings.json'):shutil.copy2(item,target)
        else:target.symlink_to(item,target_is_directory=item.is_dir())
    for name,raw in changes.items():
        if not name.startswith(prefix):continue
        target=runtime/name
        if target.exists():continue
        target.parent.mkdir(parents=True,exist_ok=True)
        assert runtime.resolve() in target.parent.resolve().parents or target.parent.resolve()==runtime.resolve()
        target.write_bytes(raw)
overlay(source,runtime)
for name,data in p['files'].items():
    if name.startswith('aura/'):continue
    target=stage/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(base64.b64decode(data))
for name in changes:
    if name.endswith('.py'):compile((runtime/name).read_bytes(),str(runtime/name),'exec')
environment=dict(os.environ,PYTHONPATH=str(runtime/'aura'),PYTHONDONTWRITEBYTECODE='1')
tests=subprocess.run(['python3','-B','-m','unittest','discover','-s',str(stage/'tests'),'-v'],env=environment,capture_output=True,text=True,timeout=90)
(stage/'tests_board.log').write_text(tests.stdout+tests.stderr)
if tests.returncode:raise RuntimeError((tests.stdout+tests.stderr)[-5000:])
check=subprocess.run(['python3','-B',str(runtime/'aura/tools/board_avatar_gtk.py'),'--check'],env=environment,capture_output=True,text=True,timeout=45)
(stage/'preflight.log').write_text(check.stdout+check.stderr)
if check.returncode:raise RuntimeError((check.stdout+check.stderr)[-3000:])
camera=json.load(urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=4))
result={'status':'CANDIDATE_TESTED_NOT_ACTIVATED','stage':str(stage),'runtime':str(runtime),'source_runtime':str(source),'old_config':str(old_config),
        'files':{name:hashlib.sha256(changes[name]).hexdigest() for name in changed},'board_tests_passed':True,'preflight':json.loads(check.stdout),
        'camera':camera,'board_services_modified':False,'speech_models_installed':False}
(stage/'candidate.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''.replace('PAYLOAD',repr({'release':release,'files':files}))
result=json.loads(ssh('python3 -',remote,timeout=160))
(HERE/'candidate.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
log=ssh('cat '+result['stage']+'/tests_board.log')
(HERE/'tests_board.log').write_text(log,encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('preflight','camera')},ensure_ascii=True))
