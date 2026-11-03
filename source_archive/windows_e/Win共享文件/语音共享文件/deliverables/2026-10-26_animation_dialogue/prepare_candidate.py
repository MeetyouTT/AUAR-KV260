"""Clone current Python sources and overlay only reviewed UI/client changes."""
import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;AURA=HERE.parents[1]/'aura'
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
profile=HERE.parent/'2026-10-26_profile_memory'
changes={p.relative_to(profile/'board_candidate').as_posix():p.read_text(encoding='utf-8') for p in (profile/'board_candidate').rglob('*.py')}
changes['tools/motion_queue.py']=(AURA/'tools/motion_queue.py').read_text(encoding='utf-8')
names=['profile_memory','profile_frontend','animation_dialogue','board_avatar_worker','voice_worker_lifecycle',
       'voice_service_health','cached_voice','voice_channel','first_sentence_latency',
       'memory_controls','long_conversation','session_memory','voice_barge_in','barge_verification',
       'remote_frontend','automatic_conversation','listening_timing','history_reuse','thinking_feedback',
       'spoken_input','reply_quality','channel_jobs','conversation']
tests={str(p.relative_to(AURA)).replace('\\','/'):p.read_text(encoding='utf-8') for p in (AURA/'tests/framework').glob('*.py')}
overlay_names=['tools/board_model_host.py','tools/voice_channel_source.py','tools/profile_control.py',
    'tools/profile_cli.py','tools/selected_voice_service.py','tools/voice_worker_transport.py','tools/owned_speech_process.py',
    'tools/voice_service_health.py','common/profile_memory.py','common/conversation_context.py',
    'common/voice_service_capabilities.py','common/memory_commands.py','config/board_dialogue_model.json',
    'config/voice_latency.json','config/profile_access.local.json',
    'board/runtime/audio/omnivoice_voice.py']
overlay={n:(AURA/n).read_text(encoding='utf-8-sig') for n in overlay_names}
payload=base64.b64encode(json.dumps({'changes':changes,'tests':tests,'test_overlay':overlay,'names':names}).encode()).decode()
script=r'''
import base64,hashlib,json,os,shutil,subprocess,time,uuid
from pathlib import Path
data=json.loads(base64.b64decode('PAYLOAD'));expected=BASE
source=Path(expected['runtime']);config_path=Path(expected['startup_config'])
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==expected['boot']
for n,digest in expected['sha256'].items():
    assert hashlib.sha256((source/'aura'/n).read_text().encode()).hexdigest()==digest,('Source changed',n)
stage=Path('/home/root/aura-animation-dialogue-20261026')/uuid.uuid4().hex
stage.mkdir(parents=True,exist_ok=False);root=stage/'runtime'
files={}
for package in ('tools','board','common','host'):
    for p in (source/'aura'/package).rglob('*.py'):files['aura/'+p.relative_to(source/'aura').as_posix()]=p.read_bytes()
for n,text in data['changes'].items():files['aura/'+n]=text.encode()
for n,text in data['tests'].items():files['aura/'+n]=text.encode()
def clone(src,dst,prefix=''):
    dst.mkdir()
    for item in src.iterdir():
        relative=prefix+item.name;target=dst/item.name
        if item.name=='__pycache__' or (prefix=='' and item.name in ('managed-runs','launch.json','stage.log')):continue
        if relative in files:target.write_bytes(files[relative])
        elif any(n.startswith(relative+'/') for n in files):clone(item,target,relative+'/')
        elif prefix=='' and item.name.endswith('_settings.json'):shutil.copy2(item,target)
        else:target.symlink_to(item,target_is_directory=item.is_dir())
    for name,content in files.items():
        if name.startswith(prefix) and '/' not in name[len(prefix):] and not (dst/name[len(prefix):]).exists():
            (dst/name[len(prefix):]).write_bytes(content)
clone(source,root)
# Ensure newly introduced directories/files are present without editing any
# symlink into the original runtime.
for name,content in files.items():
    p=root/name
    if not p.exists():p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content)
(root/'managed-runs').mkdir()
startup=stage/'startup';startup.mkdir();shutil.copy2(config_path.with_name('launcher.py'),startup/'launcher.py')
cfg=json.loads(config_path.read_text());cfg['runtime']=str(root);cfg['component_sha256']=dict(cfg.get('component_sha256',{}))
for n in set(data['changes'])|set(data['tests']):
    if n in cfg['component_sha256'] or n in data['changes']:
        cfg['component_sha256'][n]=hashlib.sha256((root/'aura'/n).read_bytes()).hexdigest()
(startup/'config.json').write_text(json.dumps(cfg,indent=2))
overlay=stage/'test_overlay'
for name,text in data['test_overlay'].items():
    p=overlay/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
for package in ('common','tools'):
    p=overlay/package/'__init__.py';p.write_text("from pkgutil import extend_path\n__path__=extend_path(__path__,__name__)\n")
# The tested host resolves its fixed sources/config against this overlay.
for name in ('common/profile_access.py','common/profile_selection.py','common/conversation_store.py',
             'board/runtime/audio/voice_channel.py','board/runtime/audio/selected_voice.py','board/runtime/audio/omnivoice_voice.py',
             'tools/dialogue_stream.py'):
    p=overlay/name;p.parent.mkdir(parents=True,exist_ok=True)
    if (root/'aura'/name).exists():p.write_bytes((root/'aura'/name).read_bytes())
(overlay/'config/profile_access.local.json').write_text(json.dumps({'control_key_file':'/nonexistent/profile-control.key'}))
pre=subprocess.run(['python3','-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight'],
    env=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin'),capture_output=True,text=True,timeout=25)
assert pre.returncode==0,pre.stderr+pre.stdout
value=dict(stage=str(stage),runtime=str(root),startup=str(startup),source_runtime=str(source),
    baseline_effective=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths'],text=True),
    baseline_ui_pid=expected['ui_pid'],boot=expected['boot'],changes=list(data['changes']),test_names=data['names'],
    test_overlay=str(overlay),preflight=pre.stdout.strip(),production_changed=False,
    source_python_preserved=all((root/'aura'/n).read_bytes()==(source/'aura'/n).read_bytes()
        for n in [p.relative_to(source/'aura').as_posix() for package in ('tools','board','common','host')
                  for p in (source/'aura'/package).rglob('*.py')] if n not in data['changes']))
assert value['source_python_preserved']
(stage/'candidate.json').write_text(json.dumps(value,indent=2));print(json.dumps(value))
'''.replace('PAYLOAD',payload).replace('BASE',repr(json.loads((HERE/'runtime_before.json').read_text(encoding='utf-8'))))
value=json.loads(ssh('python3 -B -',script,timeout=60))
(HERE/'candidate.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value))
