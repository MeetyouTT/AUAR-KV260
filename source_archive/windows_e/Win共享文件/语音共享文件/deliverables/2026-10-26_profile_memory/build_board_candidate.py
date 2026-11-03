"""Transplant only this task's hunks onto the actual board source snapshot."""
import ast,difflib,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;AURA=HERE.parents[1]/'aura'
names=['board/runtime/audio/voice_channel.py','board/runtime/audio/channel_jobs.py','tools/board_avatar_gtk.py']
files={};changes={}
for name in names:
    before=(HERE/'before/aura'/name).read_text(encoding='utf-8').splitlines(keepends=True)
    after=(AURA/name).read_text(encoding='utf-8').splitlines(keepends=True)
    actual=(HERE/'board_base'/name).read_text(encoding='utf-8')
    patches=0
    for group in difflib.SequenceMatcher(None,before,after,autojunk=False).get_grouped_opcodes(2):
        old=''.join(before[group[0][1]:group[-1][2]])
        new=''.join(after[group[0][3]:group[-1][4]])
        if actual.count(old)!=1:raise RuntimeError('Board context mismatch: '+name)
        actual=actual.replace(old,new,1);patches+=1
    ast.parse(actual);files[name]=actual;changes[name]=patches
for name in ('common/profile_access.py','common/profile_selection.py','tools/profile_selection_ui.py'):
    files[name]=(AURA/name).read_text(encoding='utf-8');ast.parse(files[name])
for name,text in files.items():
    p=HERE/'board_candidate'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
value={'base':json.loads((HERE/'board_base.json').read_text(encoding='utf-8')),
       'patch_hunks':changes,'sha256':{name:hashlib.sha256(text.encode()).hexdigest() for name,text in files.items()},
       'production_deployed':False}
(HERE/'board_candidate.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({'candidate_ready':True,'files':len(files),'patch_hunks':changes,'production_deployed':False}))
