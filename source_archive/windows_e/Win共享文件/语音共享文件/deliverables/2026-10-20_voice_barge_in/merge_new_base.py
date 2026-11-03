"""Merge only the interruption GUI/config changes into a newly inspected base.

Never copies the old GUI wholesale over a newer renderer. A missing or ambiguous
context fails before candidate preparation or deployment.
"""
import base64,difflib,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
base=json.loads((HERE/'board_baseline.json').read_text(encoding='utf-8'))
remote=r'''
import base64,json,re,subprocess
from pathlib import Path
base=BASE
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
cfgpath=Path(re.search(r'--config (\S+)',unit).group(1));root=Path(json.loads(cfgpath.read_text())['runtime'])
assert str(root)==base['runtime'] and unit==base['ui_unit']
old=Path('/home/root/aura-handsfree-dialogue-20261020/resume-049c88498ae0/runtime')
names=['aura/tools/board_avatar_gtk.py','aura/config/board_avatar_gtk.json']
print(json.dumps({'current':{n:base64.b64encode((root/n).read_bytes()).decode() for n in names},
 'original_gui':base64.b64encode((old/names[0]).read_bytes()).decode()}))
'''.replace('BASE',repr(base),1)
r=json.loads(ssh('python3 -B -',remote,timeout=20))
name='aura/tools/board_avatar_gtk.py';old=base64.b64decode(r['original_gui']).decode().replace('\r\n','\n').splitlines(keepends=True)
ours=(ROOT/name).read_text(encoding='utf-8').splitlines(keepends=True)
current=base64.b64decode(r['current'][name]).decode().replace('\r\n','\n');changes=0
matcher=difflib.SequenceMatcher(a=old,b=ours,autojunk=False)
for tag,i,j,k,l in reversed(matcher.get_opcodes()):
 if tag=='equal':continue
 start=max(0,i-3);end=min(len(old),j+3)
 before=''.join(old[start:end]);after=''.join(old[start:i]+ours[k:l]+old[j:end])
 assert current.count(before)==1,('New renderer changed interruption patch context',tag,i,j)
 current=current.replace(before,after,1);changes+=1
compile(current,name,'exec')
merged=HERE/'merged_sources'/name;merged.parent.mkdir(parents=True,exist_ok=True)
merged.write_text(current,encoding='utf-8',newline='\n')
name='aura/config/board_avatar_gtk.json';config=json.loads(base64.b64decode(r['current'][name]))
assert config.get('handsfree_dialogue') and config.get('persistent_audio') and config.get('streaming_conversation')
config['voice_barge_in']=True
merged=HERE/'merged_sources'/name;merged.parent.mkdir(parents=True,exist_ok=True)
merged.write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
report={'runtime':base['runtime'],'gui_patch_groups':changes,'new_renderer_gui_preserved':True,
 'config_preserved_except_voice_barge_in':True,'files':{p.relative_to(HERE/'merged_sources').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE/'merged_sources').rglob('*') if p.is_file()}}
(HERE/'merge_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
