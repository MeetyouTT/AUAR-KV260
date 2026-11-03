"""Explicit diagnostic copy, never silently changes the candidate/runtime model.

Discriminates the current FreeMote runtime's actual interpretation of the PSB's
additional combinator records from native frame-bp geometry. Original and generic
combinator implementations remain preserved for independent comparison.
"""
from pathlib import Path
import hashlib,json
BASE=Path(__file__).parent.parent;phase=BASE/'native_integration'
source=BASE/'inputs/ems/yuk_0.ems.json';document=json.loads(source.read_text(encoding='utf-8-sig'))
edits=[]
def walk(value,path=''):
    if isinstance(value,dict):
        if value.get('meshCombinator'):
            edits.append(path+'/meshCombinator');value['meshCombinator']=None
        for key,child in value.items():walk(child,path+'/'+key)
    elif isinstance(value,list):
        for i,child in enumerate(value):walk(child,path+'/'+str(i))
walk(document)
assert len(edits)==43
folder=phase/'bp_diagnostic';folder.mkdir(exist_ok=True)
(folder/'model.json').write_text(json.dumps(document,ensure_ascii=True),encoding='utf8')
for name in ('normal','smile','angry','sad','concern','shy'):
    values=json.loads((phase/('complete-'+name+'-parameters.json')).read_text(encoding='utf8'))
    # GeometryInstance begins at zero; omitted zeros stay exactly zero even when
    # removing optional records means their unused variable is no longer bound.
    (folder/(name+'-parameters.json')).write_text(json.dumps({k:v for k,v in values.items() if v!=0},indent=2),encoding='utf8')
(folder/'manifest.json').write_text(json.dumps({'status':'DIAGNOSTIC_ONLY_NOT_PRODUCTION_ACCEPTED',
 'basis':'original-engine full-model pair identical with/without 43 records at Update 0,1,60; all57 source vars captured',
 'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'derived_sha256':hashlib.sha256((folder/'model.json').read_bytes()).hexdigest(),
 'edits':edits,'omitted_parameter_value':0,'original_model_modified':False},indent=2),encoding='utf8')
print(json.dumps({'optional_records_changed':len(edits),'purpose':'diagnostic only','source_unchanged':True}))
