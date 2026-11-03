"""Clone current board sources, preserving motion/config and one native sink."""
import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;AURA=HERE.parents[1]/'aura'
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
baseline=json.loads((HERE/'baseline.json').read_text(encoding='utf-8'))
snapshot=json.loads((HERE/'snapshot_verification.json').read_text(encoding='utf-8'));assert snapshot['status']=='PASS'
names=['common/portrait_wire.py','board/runtime/portrait_offload.py','tools/realtime_controller.py',
       'tools/streaming_controller.py','tools/board_avatar_worker.py','tools/portrait_host.py','tools/portrait_renderer.py']
changes={n:(AURA/n).read_text(encoding='utf-8') for n in names}
changes['tools/board_avatar_gtk.py']=(HERE/'candidate_source/tools/board_avatar_gtk.py').read_text(encoding='utf-8')
tests={p.relative_to(AURA).as_posix():p.read_text(encoding='utf-8') for p in (AURA/'tests/framework').glob('*.py')}
overlay_names=['tools/board_model_host.py','tools/voice_channel_source.py','tools/profile_control.py','tools/profile_cli.py',
    'tools/selected_voice_service.py','tools/voice_worker_transport.py','tools/owned_speech_process.py','tools/voice_service_health.py',
    'common/profile_memory.py','common/conversation_context.py','common/voice_service_capabilities.py','common/memory_commands.py',
    'config/board_dialogue_model.json','config/voice_latency.json','config/profile_access.local.json','board/runtime/audio/omnivoice_voice.py']
overlay={n:(AURA/n).read_text(encoding='utf-8-sig') for n in overlay_names}
data=base64.b64encode(json.dumps({'changes':changes,'tests':tests,'overlay':overlay}).encode()).decode()
script=r'''
import base64,hashlib,json,os,re,shutil,subprocess,uuid
from pathlib import Path
baseline=BASE;data=json.loads(base64.b64decode(DATA));source=Path(baseline['runtime'])
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==baseline['boot']
effective=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths'],text=True)
def semantic(text):return re.search(r'argv\[\]=(.*?);',text).group(1).strip(),next(x for x in text.splitlines() if x.startswith('DropInPaths='))
assert semantic(effective)==semantic(baseline['effective']),'Current UI changed; rebase before preparing'
for relative,digest in baseline['source_text_sha256'].items():
    assert hashlib.sha256((source/'aura'/relative).read_text().encode()).hexdigest()==digest,relative
config_path=Path(baseline['startup_config'])
pre=subprocess.run(['python3','-B',str(config_path.with_name('launcher.py')),'--config',str(config_path),'--preflight'],
    env=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin'),capture_output=True,text=True,timeout=25)
assert pre.returncode==0,pre.stderr+pre.stdout
stage=Path('/home/root/aura-windows-portrait-20261027')/uuid.uuid4().hex;stage.mkdir(parents=True)
root=stage/'runtime';files={}
for package in ('tools','board','common','host'):
    for p in (source/'aura'/package).rglob('*.py'):files['aura/'+p.relative_to(source/'aura').as_posix()]=p.read_bytes()
for rel,text in dict(data['changes'],**data['tests']).items():files['aura/'+rel]=text.encode()
for p in (source/'aura/config').rglob('*'):
    if p.is_file():files['aura/config/'+p.relative_to(source/'aura/config').as_posix()]=p.read_bytes()
def clone(src,dst,prefix=''):
    dst.mkdir()
    for item in src.iterdir():
        rel=prefix+item.name;target=dst/item.name
        if item.name=='__pycache__' or prefix=='' and item.name in ('managed-runs','launch.json','stage.log'):continue
        if rel in files:target.write_bytes(files[rel])
        elif any(n.startswith(rel+'/') for n in files):clone(item,target,rel+'/')
        elif prefix=='' and item.name.endswith('_settings.json'):shutil.copy2(item,target)
        else:target.symlink_to(item,target_is_directory=item.is_dir())
    for name,raw in files.items():
        if name.startswith(prefix) and '/' not in name[len(prefix):] and not (dst/name[len(prefix):]).exists():
            (dst/name[len(prefix):]).write_bytes(raw)
clone(source,root)
for rel,raw in files.items():
    path=root/rel
    if not path.exists():path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
(root/'managed-runs').mkdir()
ui_config=root/'aura/config/board_avatar_gtk.json';ui=json.loads(ui_config.read_text())
ui['portrait_offload']={'enabled':True,'host':'192.168.50.1','port':8796,'fps':12,'max_age_ms':150,'revision':REVISION}
ui['stable_avatar_fps']=12;ui_config.write_text(json.dumps(ui,indent=2))
startup=stage/'startup';startup.mkdir();shutil.copy2(config_path.with_name('launcher.py'),startup/'launcher.py')
cfg=json.loads(config_path.read_text());cfg['runtime']=str(root);pins=dict(cfg['component_sha256'])
for rel in set(data['changes'])|set(data['tests'])|{'config/board_avatar_gtk.json'}:
    if rel in pins or rel in data['changes'] or rel.startswith('config/'):
        pins[rel]=hashlib.sha256((root/'aura'/rel).read_bytes()).hexdigest()
cfg['component_sha256']=pins;(startup/'config.json').write_text(json.dumps(cfg,indent=2))
overlay=stage/'test_overlay'
for rel,text in data['overlay'].items():
    p=overlay/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
for package in ('common','tools'):(overlay/package/'__init__.py').write_text('from pkgutil import extend_path\n__path__=extend_path(__path__,__name__)\n')
for rel in ('common/profile_access.py','common/profile_selection.py','common/conversation_store.py','common/speech_motion.py',
            'board/runtime/audio/voice_channel.py','board/runtime/audio/selected_voice.py','board/runtime/audio/omnivoice_voice.py','tools/dialogue_stream.py'):
    p=overlay/rel;p.parent.mkdir(parents=True,exist_ok=True)
    if (root/'aura'/rel).exists():p.write_bytes((root/'aura'/rel).read_bytes())
(overlay/'config/profile_access.local.json').write_text(json.dumps({'control_key_file':'/nonexistent/profile-control.key'}))
pre=subprocess.run(['python3','-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight'],
    env=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin'),capture_output=True,text=True,timeout=25)
assert pre.returncode==0,pre.stdout+pre.stderr
preserved={p.relative_to(source/'aura').as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
    for package in ('tools','board','common','host') for p in (source/'aura'/package).rglob('*.py')
    if p.relative_to(source/'aura').as_posix() not in data['changes']}
assert all(hashlib.sha256((root/'aura'/rel).read_bytes()).hexdigest()==digest for rel,digest in preserved.items())
v={'stage':str(stage),'runtime':str(root),'startup':str(startup),'source_runtime':str(source),'boot':baseline['boot'],
   'baseline_effective':effective,'changes':list(data['changes']),'unchanged_python_sha256':preserved,'preflight':pre.stdout.strip(),
   'original_pan_sha256':hashlib.sha256((source/'aura/config/pan_manual.local.json').read_bytes()).hexdigest(),
   'revision':REVISION,'fps':12,'test_overlay':str(overlay),'production_changed':False}
(stage/'candidate.json').write_text(json.dumps(v,indent=2));print(json.dumps(v))
'''.replace('BASE',repr(baseline)).replace('DATA',repr(data)).replace('REVISION',repr(snapshot['revision']))
compile(script,'<portrait-candidate>','exec')
v=json.loads(ssh('python3 -B -',script,timeout=90));(HERE/'candidate.json').write_text(json.dumps(v,indent=2),encoding='utf-8')
print(json.dumps({k:x for k,x in v.items() if k not in ('unchanged_python_sha256','baseline_effective')}))
