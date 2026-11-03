"""Full-model source-engine A/B inputs; no browser, board, or source mutation.

Both start from the exact EMS JSON/resx and apply the existing controlled PSB's
nine byte edits (ten logical paths due to a source alias). Only the no-combo
input removes the 43 meshCombinator fields. Sources and six-expression rig stay
unchanged; a complete JSON/resource/PSB readback audit is written here.
"""
from pathlib import Path
import copy
import hashlib
import json
import struct
import subprocess
import sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
sys.path.insert(0,str(BASE/'native_integration/mesh_fixtures_diagnosis'))
from inspect_psb import Reader

TOOL=Path('D:/share、/项目开发/美冬本地女友项目/assets/fuyukiss/_freemote/toolkit/PsBuild.exe')
SOURCE=BASE/'inputs/ems/yuk_0.ems.json'
RESX=BASE/'inputs/ems/yuk_0.ems.resx.json'
original=json.loads(SOURCE.read_text(encoding='utf8'))
resx=json.loads(RESX.read_text(encoding='utf8'))
control=json.loads((HERE/'manifest.json').read_text(encoding='utf8'))
rig=json.loads((HERE/'controlled-rig.json').read_text(encoding='utf8'))
old_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (SOURCE,RESX,HERE/'controlled-rig.json',HERE/'model.psb')}

def pointer(doc,path):
    for token in path.split('/')[1:]:
        token=token.replace('~1','/').replace('~0','~')
        doc=doc[int(token)] if isinstance(doc,list) else doc[token]
    return doc

controlled=copy.deepcopy(original)
edits=[]
for edit in control['edits']:
    for path in edit.get('affected_paths',[edit['path']]):
        parent,_,key=path.rpartition('/')
        before=pointer(controlled,path)
        pointer(controlled,parent)[key]=edit['stored_after']
        edits.append(dict(path=path,before=before,after=edit['stored_after'],source_byte_edit=edit['path']))
assert len(control['edits'])==9 and len(edits)==10

no_combo=copy.deepcopy(controlled)
removed=[]
def remove(x,path=''):
    if isinstance(x,dict):
        if 'meshCombinator' in x:
            removed.append(dict(path=path+'/meshCombinator',value=x.pop('meshCombinator')))
        for k,v in x.items():remove(v,path+'/'+k)
    elif isinstance(x,list):
        for i,v in enumerate(x):remove(v,path+'/'+str(i))
remove(no_combo)
assert len(removed)==43

def differences(a,b,path=''):
    if isinstance(a,dict) and isinstance(b,dict):
        result=[]
        for k in sorted(a.keys()|b.keys()):
            if k not in a or k not in b:result.append(path+'/'+k)
            else:result+=differences(a[k],b[k],path+'/'+k)
        return result
    if isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
        return [d for i,(x,y) in enumerate(zip(a,b)) for d in differences(x,y,path+'/'+str(i))]
    return [] if a==b else [path]

assert set(differences(controlled,no_combo))=={r['path'] for r in removed}
assert set(differences(original,controlled))=={e['path'] for e in edits}
resx['Resources']['0']='../../inputs/ems/yuk_0.ems/tex-texture.png'
resx_text=json.dumps(resx,ensure_ascii=False,indent=2)
report={'scope':'full-model original-engine control inputs; not executed here',
    'source_json':str(SOURCE),'source_resx':str(RESX),'source_changes':False,
    'source_nine_byte_edits':control['edits'],'common_ten_logical_field_edits':edits,
    'alias_note':'Original PSB aliases eyeControl[0].enabled and blinkEnabled to the same scalar; both logical fields must be zero to reproduce the existing controlled file.',
    'pair_json_difference_count':43,'pair_json_difference_paths':[r['path'] for r in removed],
    'removed_mesh_combinators':removed,'resx_identical_between_pair':True,
    'rig_six_expressions_unchanged':True,'outputs':{},'checks':{}}
readers={}
for name,doc in [('rebuilt_combo',controlled),('rebuilt_no_combo',no_combo)]:
    folder=HERE/name;folder.mkdir(exist_ok=True)
    (folder/'model.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf8')
    (folder/'model.resx.json').write_text(resx_text,encoding='utf8')
    local_rig=copy.deepcopy(rig)
    local_rig['model']=f'/fixtures/{name}/model.psb'
    (folder/'rig.json').write_text(json.dumps(local_rig,ensure_ascii=False,indent=2),encoding='utf8')
    command=[str(TOOL),'-v','4','-p','ems','-ns','-o',str(folder/'model.psb'),str(folder/'model.json')]
    result=subprocess.run(command,cwd=folder,capture_output=True,text=True,errors='replace',timeout=120)
    (folder/'compile.log').write_text(result.stdout+result.stderr,encoding='utf8')
    if result.returncode:raise RuntimeError('PsBuild failed: '+name)
    reader=Reader(folder/'model.psb');inspect=reader.inspect();readers[name]=(reader,inspect)
    offs,_=reader.table(reader.u32(44));lens,_=reader.table(reader.u32(48));start=reader.u32(52)
    extra=[reader.data[start+o:start+o+n] for o,n in zip(offs,lens)]
    normal_o,_=reader.table(reader.u32(24));normal_n,_=reader.table(reader.u32(28));normal_s=reader.u32(32)
    normal=[reader.data[normal_s+o:normal_s+o+n] for o,n in zip(normal_o,normal_n)]
    report['outputs'][name]={'directory':str(folder),'model':local_rig['model'],
        'rig':str(folder/'rig.json'),'bytes':len(reader.data),'sha256':hashlib.sha256(reader.data).hexdigest(),
        'model_json_sha256':hashlib.sha256((folder/'model.json').read_bytes()).hexdigest(),
        'resx_json_sha256':hashlib.sha256((folder/'model.resx.json').read_bytes()).hexdigest(),
        'extra_count':len(extra),'extra_lengths':lens,
        'extra_sha256':[hashlib.sha256(v).hexdigest() for v in extra],
        'normal_resource_sha256':[hashlib.sha256(v).hexdigest() for v in normal],
        'normal_resource_lengths':normal_n,
        'resource_tags':inspect['resource_tags']}

combo,no=report['outputs']['rebuilt_combo'],report['outputs']['rebuilt_no_combo']
report['checks']['normal_resources_equal']=combo['normal_resource_sha256']==no['normal_resource_sha256']
report['checks']['extra_resources_equal']=combo['extra_sha256']==no['extra_sha256']
report['checks']['readback_pair_difference_paths']=differences(readers['rebuilt_combo'][1]['root'],readers['rebuilt_no_combo'][1]['root'])
report['checks']['readback_pair_only_43_combinator_removals']=set(report['checks']['readback_pair_difference_paths'])=={r['path'] for r in removed}
report['checks']['original_files_hashes_preserved']=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in old_hashes.items())
report['checks']['resx_files_identical']=(HERE/'rebuilt_combo/model.resx.json').read_bytes()==(HERE/'rebuilt_no_combo/model.resx.json').read_bytes()
def canonical(reader,value):
    if isinstance(value,dict):
        if set(value)=={'resource_kind','index'}:
            extra=value['resource_kind']=='extra'
            offs,_=reader.table(reader.u32(44 if extra else 24))
            lens,_=reader.table(reader.u32(48 if extra else 28))
            start=reader.u32(52 if extra else 32)
            index=value['index'];begin=start+offs[index]
            return {'resource_kind':value['resource_kind'],'bytes':lens[index],
                'sha256':hashlib.sha256(memoryview(reader.data)[begin:begin+lens[index]]).hexdigest()}
        return {k:canonical(reader,v) for k,v in value.items()}
    if isinstance(value,list):return [canonical(reader,v) for v in value]
    return value
original_reader=Reader(HERE/'model.psb')
original_inspect=original_reader.inspect()
original_semantic=canonical(original_reader,original_inspect['root'])
rebuilt_semantic=canonical(readers['rebuilt_combo'][0],readers['rebuilt_combo'][1]['root'])
source_diffs=differences(original_semantic,rebuilt_semantic)
report['checks']['controlled_original_vs_rebuilt_combo_semantic_difference_paths']=source_diffs
report['checks']['controlled_original_vs_rebuilt_combo_semantically_equal']=not source_diffs
report['checks']['texture_equal_to_controlled_original']=original_semantic['source']==rebuilt_semantic['source']
report['unused_resource_pruning_note']='PsBuild removes all 113 extra blocks when no meshCombinator references remain. Both input resx files retain byte-identical full ExtraFlattenArrays; decoded root semantic difference remains precisely the 43 field deletions.'
(HERE/'rebuilt-pair-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'outputs':{k:{f:v[f] for f in ['bytes','sha256','extra_count','normal_resource_lengths']}
                              for k,v in report['outputs'].items()},'checks':report['checks']},ensure_ascii=True,indent=2))
