"""Inherit newer untouched motion/config files without changing hardware state."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'));baseline=json.loads((HERE/'baseline.json').read_text(encoding='utf-8'))
script=r'''
import hashlib,json,os,re,shutil,subprocess
from pathlib import Path
c=CANDIDATE;baseline=BASELINE;root=Path(c['runtime']);source=Path(c['source_runtime'])
effective=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','-p','DropInPaths'],text=True)
assert c['startup'] not in effective and str(Path(baseline['startup_config']).with_name('launcher.py')) in effective
for rel,digest in baseline['source_text_sha256'].items():
    assert hashlib.sha256((source/'aura'/rel).read_text().encode()).hexdigest()==digest,('Renderer base changed',rel)
refreshed=[];preserved={}
for package in ('tools','board','common','host'):
    for p in (source/'aura'/package).rglob('*.py'):
        rel=p.relative_to(source/'aura').as_posix()
        if rel in c['changes']:continue
        target=root/'aura'/rel;assert target.resolve().is_relative_to(root.resolve())
        raw=p.read_bytes()
        if not target.exists() or target.read_bytes()!=raw:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);refreshed.append(rel)
        preserved[rel]=hashlib.sha256(raw).hexdigest()
current_ui=json.loads((root/'aura/config/board_avatar_gtk.json').read_text())
for p in (source/'aura/config').rglob('*'):
    if p.is_file():
        target=root/'aura/config'/p.relative_to(source/'aura/config');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
ui_path=root/'aura/config/board_avatar_gtk.json';ui=json.loads(ui_path.read_text())
ui['portrait_offload']=current_ui['portrait_offload'];ui['stable_avatar_fps']=current_ui['stable_avatar_fps'];ui_path.write_text(json.dumps(ui,indent=2))
source_config=Path(baseline['startup_config']);startup=Path(c['startup']);cfg=json.loads(source_config.read_text());cfg['runtime']=str(root)
shutil.copy2(source_config.with_name('launcher.py'),startup/'launcher.py')
for rel in set(cfg['component_sha256'])|set(c['changes'])|{'tests/framework/test_portrait_offload.py'}:
    target=root/'aura'/rel
    if rel in c['changes'] or rel.startswith(('config/','tests/framework/')):
        if target.is_file():cfg['component_sha256'][rel]=hashlib.sha256(target.read_bytes()).hexdigest()
    else:assert hashlib.sha256(target.read_bytes()).hexdigest()==cfg['component_sha256'][rel],rel
(startup/'config.json').write_text(json.dumps(cfg,indent=2))
c['baseline_effective']=effective;c['unchanged_python_sha256']=preserved
c['original_pan_sha256']=hashlib.sha256((source/'aura/config/pan_manual.local.json').read_bytes()).hexdigest()
pre=subprocess.run(['python3','-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight'],env=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin'),capture_output=True,text=True,timeout=25)
assert pre.returncode==0,pre.stdout+pre.stderr
print(json.dumps({'candidate':c,'refreshed_untouched_sources':refreshed,'preflight':pre.stdout.strip(),'production_changed':False}))
'''.replace('CANDIDATE',repr(c)).replace('BASELINE',repr(baseline))
v=json.loads(ssh('python3 -B -',script,timeout=45))
(HERE/'candidate.json').write_text(json.dumps(v.pop('candidate'),indent=2),encoding='utf-8')
(HERE/'context_refresh.json').write_text(json.dumps(v,indent=2),encoding='utf-8');print(json.dumps(v))
