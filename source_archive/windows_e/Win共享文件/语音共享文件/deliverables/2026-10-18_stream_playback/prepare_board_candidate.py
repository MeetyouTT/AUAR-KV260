"""Create an isolated source overlay; unchanged resources are linked, not copied."""
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

names=['aura/tools/gstreamer_audio_engine.py','aura/tools/gstreamer_audio.py','aura/tools/gstreamer_audio_worker.py',
       'aura/tools/gstreamer_persistent_engine.py','aura/tools/streaming_controller.py','aura/tools/board_recording.py',
       'aura/tools/board_avatar_gtk.py','aura/common/voice_channel.py','aura/common/asr_wire.py',
       'aura/board/runtime/audio/voice_channel.py','aura/board/runtime/audio/channel_jobs.py']
files={name:base64.b64encode((ROOT/name).read_bytes()).decode() for name in names}
files['integration_runner.py']=base64.b64encode((HERE/'integration_runner.py').read_bytes()).decode()
files['cancellation_runner.py']=base64.b64encode((HERE/'cancellation_runner.py').read_bytes()).decode()
for name in ('math_input.wav','chat_input.wav'):files['data/'+name]=base64.b64encode((HERE/name).read_bytes()).decode()
release=hashlib.sha256(('source-overlay-v2\n'+json.dumps(files,sort_keys=True)).encode()).hexdigest()[:12]
payload={'files':files,'release':release}
remote=r'''
import base64,hashlib,json,os,shutil,subprocess
from pathlib import Path
p=PAYLOAD
source=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
stage=Path('/home/root/aura-stream-playback-20261018')/('candidate-'+p['release'])
stage.mkdir(parents=True,exist_ok=True)
changes={k:base64.b64decode(v) for k,v in p['files'].items() if k.startswith('aura/')}
changed_names=set(changes)
# Python entry points resolve __file__ and prepend their own source root.
# Real copies of code keep those imports inside this candidate; large assets
# remain links. No model data is copied or introduced on the board.
for package in ('tools','board','common','host'):
    for path in (source/'aura'/package).rglob('*.py'):
        changes.setdefault(str(path.relative_to(source)),path.read_bytes())
cfg=json.loads((source/'aura/config/board_avatar_gtk.json').read_text())
cfg.update(persistent_audio=True,streaming_conversation=True)
changes['aura/config/board_avatar_gtk.json']=(json.dumps(cfg,indent=2)+'\n').encode()
changed_names.add('aura/config/board_avatar_gtk.json')
runtime=stage/'runtime'
def overlay(src,dst,prefix=''):
    dst.mkdir(parents=True,exist_ok=True)
    for item in src.iterdir():
        name=prefix+item.name;target=dst/item.name
        if name in changes:
            if target.is_symlink():raise RuntimeError('Candidate target is unexpectedly linked')
            target.write_bytes(changes[name])
        elif any(key.startswith(name+'/') for key in changes):overlay(item,target,name+'/')
        elif target.exists() or target.is_symlink():continue
        elif prefix=='' and item.name.endswith('_settings.json'):shutil.copy2(item,target)
        else:target.symlink_to(item,target_is_directory=item.is_dir())
    for name,raw in changes.items():
        if not name.startswith(prefix):continue
        target=runtime/name
        if target.exists():continue
        target.parent.mkdir(parents=True,exist_ok=True)
        if runtime.resolve() not in target.parent.resolve().parents and target.parent.resolve()!=runtime.resolve():
            raise RuntimeError('Candidate write escaped source overlay')
        target.write_bytes(raw)
overlay(source,runtime)
for name,value in p['files'].items():
    if name.startswith('aura/'):continue
    target=stage/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(base64.b64decode(value))
for name in changes:
    if name.endswith('.py'):compile((runtime/name).read_bytes(),str(runtime/name),'exec')
check=subprocess.run(['python3','-B',str(runtime/'aura/tools/board_avatar_gtk.py'),'--check'],capture_output=True,text=True,timeout=45)
(stage/'preflight.log').write_text(check.stdout+check.stderr)
if check.returncode:raise RuntimeError((check.stdout+check.stderr)[-3000:])
report={'status':'CANDIDATE_STAGED_NOT_ACTIVATED','stage':str(stage),'runtime':str(runtime),
        'files':{name:hashlib.sha256(changes[name]).hexdigest() for name in sorted(changed_names)},
        'isolated_code_files':sum(name.endswith('.py') for name in changes),'board_services_modified':False}
(stage/'manifest.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
'''.replace('PAYLOAD',repr(payload))
result=json.loads(ssh('python3 -',remote,timeout=70))
(HERE/'candidate.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result))
