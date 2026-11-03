"""Pin effective board renderer code and verify existing Windows visual assets."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[1];AURA=PROJECT/'aura'
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
baseline=json.loads((HERE/'baseline.json').read_text(encoding='utf-8'))
sources=['tools/demo_script.py','board/runtime/fsm.py','board/interaction/avatar_player.py','tools/facial_layers.py']
shared=['tools/demo_stage.py','board/interaction/avatar_assets.py','board/interaction/avatar_timing.py',
        'tools/realtime_facials.py','tools/mouth_compositor.py','tools/idle_body_compositor.py','tools/board_avatar_affine.py']
script=r'''
import hashlib,json
from pathlib import Path
root=Path(ROOT);assets={}
for directory in ('aura/assets/avatar','deliverables/2026-10-06_avatar_reuse','deliverables/2026-10-06_voice_blink'):
    for p in (root/directory).rglob('*'):
        if p.is_file() and p.suffix.lower() in ('.png','.json','.webp'):
            assets[p.relative_to(root).as_posix()]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
print(json.dumps({'sources':{n:(root/'aura'/n).read_text() for n in SOURCES},
                 'shared':{n:hashlib.sha256((root/'aura'/n).read_text().encode()).hexdigest() for n in SHARED},'assets':assets}))
'''.replace('ROOT',repr(baseline['runtime'])).replace('SOURCES',repr(sources)).replace('SHARED',repr(shared))
value=json.loads(ssh('python3 -B -',script,timeout=180))
snapshot=HERE/'renderer_snapshot';snapshot.mkdir(exist_ok=True);hashes={}
for name,text in value['sources'].items():
    p=snapshot/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='\n')
    hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
for name,digest in value['shared'].items():
    assert hashlib.sha256((AURA/name).read_text(encoding='utf-8').encode()).hexdigest()==digest,('Shared renderer code differs',name)
different=[]
for name,item in value['assets'].items():
    path=PROJECT/name
    if not path.is_file() or path.stat().st_size!=item['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:different.append(name)
assert not different,('Windows visual asset mismatch',different[:10],len(different))
revision=hashlib.sha256(json.dumps({'sources':hashes,'shared':value['shared'],'assets':value['assets']},sort_keys=True).encode()).hexdigest()
manifest={'revision':revision,'sources':hashes,'project_sources':value['shared'],'assets':value['assets']}
(snapshot/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
config={'listen':'192.168.50.1','port':8796,'snapshot':str(snapshot),'width':423,'height':438,'background':'#101820'}
tokens=json.loads((AURA/'ui/ui_tokens.json').read_text(encoding='utf-8'));config['background']=tokens['colors']['panel_bg']
(HERE/'host_config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
report={'status':'PASS','revision':revision,'snapshot_sources':len(hashes),'matching_project_sources':len(shared),
        'matching_visual_assets':len(value['assets']),'asset_bytes':sum(x['bytes'] for x in value['assets'].values()),
        'models_or_assets_copied':False,'production_changed':False}
(HERE/'snapshot_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
