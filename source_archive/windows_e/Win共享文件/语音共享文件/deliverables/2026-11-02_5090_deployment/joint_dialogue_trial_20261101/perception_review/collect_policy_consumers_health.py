"""Read only the existing DPU identity policy consumers and public health counts."""
import ast
import datetime
import hashlib
import http.client
import json
from pathlib import Path
import re

BOOT='903cfade-b93c-48fa-804e-379be1967313'
ROOT=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
STARTUP_SHA='3fd124287463650f48232cb387c78d01399bad7ddcda483db725163298de4591'
SELECTED_SHA='4d8f0c2bccea1c7a56761fbcb204f40ba3b3c2fc9efad76af778aff535d378ac'
def raw(path):
    p=Path(path);assert p.is_file() and not p.is_symlink() and p.suffix not in ('.db','.sqlite','.sqlite3')
    assert p.stat().st_size<64000000
    return p.read_bytes()
def sha(path):return hashlib.sha256(raw(path)).hexdigest()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert sha(ROOT/'startup/config.json')==STARTUP_SHA
startup=json.loads(raw(ROOT/'startup/config.json'));aura=Path(startup['runtime'])/'aura'
assert len(startup['component_sha256'])==380 and all(sha(aura/k)==v for k,v in startup['component_sha256'].items())
spec=json.loads(raw(aura/'config/board_avatar_gtk.json'))['board_business']['face_readback']
assert spec['sha256']==sha(spec['path'])==SELECTED_SHA
binding=json.loads(raw(spec['path']));assert len(binding['source_sha256'])==24
assert all(sha(k)==v for k,v in binding['source_sha256'].items())
run=json.loads(raw(binding['camera_config']));native=run['native_execution']
assert sha(native['source_manifest'])==native['source_manifest_sha256']=='5e08f7cf587d74334ef24104ea01f79701629b48f2004fb772ce3f8ea82afd0d'
pins=json.loads(raw(native['source_manifest']))['files'];base=Path(native['source_manifest']).parent/'aura'
sources={}
for name in ('board/identity/camera_faces.py','board/identity/model_store.py','board/identity/live.py'):
    source=raw(base/name);assert hashlib.sha256(source).hexdigest()==pins[name]
    text=source.decode();lines=text.splitlines();tree=ast.parse(text)
    indexes=set()
    if name.endswith('camera_faces.py'):
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='create_service')
        indexes.update(range(node.lineno,min(node.end_lineno,node.lineno+48)+1))
    elif name.endswith('model_store.py'):
        keywords=re.compile(r'^class |^def |def __init__|threshold|ambiguity_margin|IdentityStore|super\(\)|config\[')
        indexes.update(n for n,line in enumerate(lines,1) if keywords.search(line))
    else:
        klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='IdentityService')
        node=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='health')
        indexes.update(range(node.lineno,node.end_lineno+1))
    sources[name]={'path':str(base/name),'sha256':pins[name],
        'selected_public_source_lines':[{'line':n,'source':lines[n-1]} for n in sorted(indexes)]}
c=http.client.HTTPConnection('127.0.0.1',8790,timeout=3)
try:
    c.request('GET','/health');r=c.getresponse();body=r.read(2097153)
    assert r.status==200 and len(body)<=2097152
    h=json.loads(body)
finally:c.close()
ident=h['identity'];assert isinstance(ident,dict)
count_fields={};availability_fields={}
count_keys={'people_count','identity_count','identities_count','gallery_count','gallery_size','template_count','templates_count','row_count','entries_count','entries','count'}
availability_keys={'store_available','gallery_available','gallery_ready','database_available','store_ready'}
for prefix,item in [('',ident)]+[(k+'.',ident[k]) for k in ('gallery','store','model_store') if isinstance(ident.get(k),dict)]:
    for key,value in item.items():
        if key in count_keys and type(value) is int:count_fields[prefix+key]=value
        if key in availability_keys and type(value) is bool:availability_fields[prefix+key]=value
assert sha(ROOT/'startup/config.json')==STARTUP_SHA
print(json.dumps({'schema':'aura-policy-consumer-and-public-health-projection-1',
    'board_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot_id':BOOT,
    'source_read_path_evidence':sources,'model_chain_ready':ident.get('ready') is True and not ident.get('error'),
    'public_health_gallery_counts':count_fields,'public_health_gallery_availability':availability_fields,
    'gallery_count_publicly_available':bool(count_fields),'gallery_availability_publicly_available':bool(availability_fields),
    'empty_gallery_inferred_from_unknown':False,'database_opened':False,'board_mutations':False,
    'ids_names_templates_scores_images_dialogue_exported':False},sort_keys=True))
