"""Clone the accepted runtime for a two-line layout correction; keep it running."""
import base64
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-18_board_dialogue'))
from board_ssh import ssh

c = json.loads((HERE / 'candidate.json').read_text(encoding='utf-8'))
gui = (HERE / 'candidate_source/tools/board_avatar_gtk.py').read_text(encoding='utf-8')
script = r'''
import base64,hashlib,json,os,shutil,subprocess,uuid
from pathlib import Path
c=CANDIDATE;source=Path(c['runtime']);old_stage=Path(c['stage']);gui=base64.b64decode(GUI)
assert c['startup'] in subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart'],text=True)
assert json.loads((old_stage/'deployment.json').read_text())['status']=='COMMITTED'
assert json.loads((old_stage/'fps_persisted.json').read_text())['accepted_fps']==16
cfg=json.loads((Path(c['startup'])/'config.json').read_text())
for rel,digest in cfg['component_sha256'].items():assert hashlib.sha256((source/'aura'/rel).read_bytes()).hexdigest()==digest,rel
stage=old_stage.parent/('layout-'+uuid.uuid4().hex);stage.mkdir();root=stage/'runtime';files={}
for package in ('tools','board','common','host'):
    for p in (source/'aura'/package).rglob('*.py'):files['aura/'+p.relative_to(source/'aura').as_posix()]=p.read_bytes()
for p in (source/'aura/config').rglob('*'):
    if p.is_file():files['aura/config/'+p.relative_to(source/'aura/config').as_posix()]=p.read_bytes()
files['aura/tools/board_avatar_gtk.py']=gui
def clone(src,dst,prefix=''):
    dst.mkdir()
    for item in src.iterdir():
        rel=prefix+item.name;target=dst/item.name
        if item.name=='__pycache__' or prefix=='' and item.name in ('managed-runs','launch.json','stage.log'):continue
        if rel in files:target.write_bytes(files[rel])
        elif any(n.startswith(rel+'/') for n in files):clone(item,target,rel+'/')
        elif prefix=='' and item.name.endswith('_settings.json'):shutil.copy2(item,target)
        else:target.symlink_to(item,target_is_directory=item.is_dir())
clone(source,root);(root/'managed-runs').mkdir()
startup=stage/'startup';startup.mkdir();shutil.copy2(Path(c['startup'])/'launcher.py',startup/'launcher.py')
cfg['runtime']=str(root);cfg['component_sha256']['tools/board_avatar_gtk.py']=hashlib.sha256(gui).hexdigest()
(startup/'config.json').write_text(json.dumps(cfg,indent=2))
pre=subprocess.run(['python3','-B',str(startup/'launcher.py'),'--config',str(startup/'config.json'),'--preflight'],env=dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin'),capture_output=True,text=True,timeout=25)
assert pre.returncode==0,pre.stdout+pre.stderr
changed=[]
for rel in c['changes']:
    if (root/'aura'/rel).read_bytes()!=(source/'aura'/rel).read_bytes():changed.append(rel)
assert changed==['tools/board_avatar_gtk.py']
new=dict(c,stage=str(stage),runtime=str(root),startup=str(startup),fps=16,previous_candidate=c,
         layout_only_changed=changed,gui_text_sha256=hashlib.sha256(gui.decode().encode()).hexdigest(),production_changed=False)
(stage/'candidate.json').write_text(json.dumps(new,indent=2))
print(json.dumps({'candidate':new,'preflight':pre.stdout.strip(),'core_sources_unchanged':True,'production_changed':False}))
'''.replace('CANDIDATE', repr(c)).replace('GUI', repr(base64.b64encode(gui.encode()).decode()))
v = json.loads(ssh('python3 -B -', script, timeout=50))
(HERE / 'candidate_initial.json').write_text(json.dumps(c, indent=2), encoding='utf-8')
(HERE / 'candidate.json').write_text(json.dumps(v.pop('candidate'), indent=2), encoding='utf-8')
(HERE / 'layout_preparation.json').write_text(json.dumps(v, indent=2), encoding='utf-8')
print(json.dumps(v))
