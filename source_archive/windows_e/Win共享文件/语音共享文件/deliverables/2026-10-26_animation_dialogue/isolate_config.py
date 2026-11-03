"""Freeze candidate configuration instead of sharing mutable production files."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
script=r'''
import hashlib,json,os,shutil,subprocess,uuid
from pathlib import Path
c=CANDIDATE;root=Path(c['runtime']);source=Path(c['source_runtime']);stage=Path(c['stage'])
link=root/'aura/config'
if link.is_symlink():assert link.resolve()==(source/'aura/config').resolve()
else:assert link.is_dir() and link.resolve().is_relative_to(stage.resolve())
original_cfg=Path('/home/root/aura-pan-current-20261024/16a07283/gui-manual-bound-v1/startup/config.json')
pre_original=subprocess.run(['python3','-B',str(original_cfg.with_name('launcher.py')),'--config',str(original_cfg),'--preflight'],
    env=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin'),capture_output=True,text=True,timeout=25)
assert pre_original.returncode==0,pre_original.stdout+pre_original.stderr
cfg=json.loads(original_cfg.read_text())
refreshed=[]
for package in ('tools','board','common','host'):
    for src in (source/'aura'/package).rglob('*.py'):
        relative=src.relative_to(source/'aura').as_posix()
        if relative in c['changes']:continue
        target=root/'aura'/relative
        assert target.resolve().is_relative_to(root.resolve()),'Refuse to modify a symlink into the original runtime'
        raw=src.read_bytes()
        if not target.exists() or target.read_bytes()!=raw:
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);refreshed.append(relative)
current={}
for p in (source/'aura/config').rglob('*'):
    if not p.is_file():continue
    assert p.stat().st_size<2_000_000,'Unexpected large config resource'
    current[p.relative_to(source/'aura/config').as_posix()]=p.read_bytes()
pan='pan_manual.local.json'
actual=hashlib.sha256(current[pan]).hexdigest()
assert cfg['component_sha256']['config/'+pan]==actual,'Original live config is not pinned; do not borrow it'
if link.is_symlink():link.unlink();link.mkdir()
for name,raw in current.items():
    p=link/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
cfg['runtime']=str(root);cfg['component_sha256']=dict(cfg.get('component_sha256',{}))
for name in list(cfg['component_sha256']):
    if name.startswith(('config/','tests/framework/')) or name in c['changes']:
        cfg['component_sha256'][name]=hashlib.sha256((root/'aura'/name).read_bytes()).hexdigest()
    else:assert hashlib.sha256((root/'aura'/name).read_bytes()).hexdigest()==cfg['component_sha256'][name],name
for name in c['changes']:cfg['component_sha256'][name]=hashlib.sha256((root/'aura'/name).read_bytes()).hexdigest()
path=Path(c['startup'])/'config.json'
shutil.copy2(path,path.with_name('config.before-isolation.json'))
path.write_text(json.dumps(cfg,indent=2))
pre=subprocess.run(['python3','-B',str(path.with_name('launcher.py')),'--config',str(path),'--preflight'],
    env=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin'),capture_output=True,text=True,timeout=25)
assert pre.returncode==0,pre.stdout+pre.stderr
value={'candidate_config_is_independent':True,'original_config_unchanged':hashlib.sha256((source/'aura/config'/pan).read_bytes()).hexdigest()==actual,
       'pan_config_sha256':actual,'config_file_count':len(current),'preflight':pre.stdout,'production_changed':False,
       'unchanged_components_refreshed_from_current_original':refreshed}
(stage/'config_isolation.json').write_text(json.dumps(value,indent=2));print(json.dumps(value))
'''.replace('CANDIDATE',repr(c))
compile(script,'<candidate-config>','exec')
value=json.loads(ssh('python3 -B -',script,timeout=40))
(HERE/'config_isolation.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value))
