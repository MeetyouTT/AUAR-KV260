"""Offline container/structure audit; never execute any renderer or board tool."""
from pathlib import Path
import collections
import hashlib
import json
import math
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from inspect_psb import Reader

BASE=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
real_path=Path('D:/share、/项目开发/美冬本地女友项目/assets/fuyukiss/webgl/yuk_0.ems.psb')
real_json=BASE/'inputs/ems/yuk_0.ems.json'
real_resx=BASE/'inputs/ems/yuk_0.ems.resx.json'
v1=BASE/'native_integration/mesh_fixtures/absolute_with_bp/model.psb'
params_path=BASE/'native_integration/controlled-normal-parameters.json'
real=json.loads(real_json.read_text(encoding='utf8'))
resx=json.loads(real_resx.read_text(encoding='utf8'))
params=json.loads(params_path.read_text(encoding='utf8'))

def owners(doc):
    result=[]
    def visit(x,path):
        if isinstance(x,dict):
            if 'meshCombinator' in x:result.append((path,x))
            for k,v in x.items():visit(v,path+'/'+k)
        elif isinstance(x,list):
            for i,v in enumerate(x):visit(v,path+'/'+str(i))
    visit(doc,'')
    return result

def lookup(doc,path):
    for key in path.split('/')[1:]:doc=doc[int(key)] if isinstance(doc,list) else doc[key]
    return doc

reader=Reader(real_path)
original=reader.inspect()
offsets,_=reader.table(reader.u32(44));lengths,_=reader.table(reader.u32(48));start=reader.u32(52)
payloads=[reader.data[start+o:start+o+n] for o,n in zip(offsets,lengths)]
checks=[]
neutral_count=0
for path,node in owners(real):
    native=node['meshCombinator']['combinatorList']
    psb=lookup(original['root'],path)['meshCombinator']['combinatorList']
    is_neutral=True
    for i,(a,b) in enumerate(zip(native,psb)):
        resource=int(a['rawMeshList'].split('@')[1])
        flat=resx['ExtraFlattenArrays']['@'+str(resource)]
        packed=struct.pack('<'+'f'*len(flat),*flat)
        variable=a['variable']
        value=params.get(variable['key'],0)
        t=max(0,min(1,(value-variable['rangeBegin'])/(variable['rangeEnd']-variable['rangeBegin'])))
        q=t*(variable['meshCount']-1)
        is_neutral &= a['neutralIndex']>=0 and math.floor(q)==a['neutralIndex'] and q-math.floor(q)<2**-23
        fields_equal=all(a[k]==b[k] for k in a if k!='rawMeshList')
        raw_equal=packed==payloads[resource]
        floats=struct.unpack('<'+'f'*(len(payloads[resource])//4),payloads[resource])
        checks.append(dict(path=path+'/meshCombinator/combinatorList/'+str(i),
            variable=variable['key'],parameter=value,normalized_mesh_position=q,
            raw_resource=resource,psb_resource_node=b['rawMeshList'],
            fields_equal=fields_equal,float32_le_payload_equal=raw_equal,
            byte_length=len(payloads[resource]),expected_bytes=variable['meshCount']*128,
            finite=all(math.isfinite(v) for v in floats)))
    neutral_count+=bool(is_neutral)

failed=Reader(v1).inspect()
v1_json=json.loads((v1.parent/'model.json').read_text(encoding='utf8'))
real_owners=owners(real)
report={
    'scope':'offline only; no original-engine/board operation; production files unchanged',
    'status':'original-engine fixture load hang unresolved; real-model pixel parity failed',
    'sources':{'actual_psb':str(real_path),'json':str(real_json),'resx':str(real_resx),
               'failed_fixture':str(v1),'controlled_parameters':str(params_path)},
    'sha256':{'actual_psb':hashlib.sha256(reader.data).hexdigest(),
              'failed_fixture':hashlib.sha256(v1.read_bytes()).hexdigest()},
    'proven_container_facts':{
        'v1_resource_tags':failed['resource_tags'],
        'rawMeshList_tag':'0x22: extra PSB resource reference; not a string literal',
        'v1_raw_resource_bytes':384,'v1_expected_raw_resource_bytes':384,
        'v1_texture_bytes':16384,'v1_expected_texture_bytes':64*64*4,
        'roundtrip':'PsbDecompile -raw preserved all combinator/variable fields and rawMeshList marker; only small numeric bp float rounding differed',
        'real_owner_count':len(real_owners),'real_control_count':len(checks),
        'real_psb_and_native_json_control_fields_equal':all(x['fields_equal'] for x in checks),
        'real_psb_and_native_resx_float32_le_bytes_equal':all(x['float32_le_payload_equal'] for x in checks),
        'real_resources_match_exact_count_and_finite':all(x['byte_length']==x['expected_bytes'] and x['finite'] for x in checks),
        'all_neutral_owner_count_at_controlled_parameters':neutral_count},
    'structural_differences':[
        {'field':'combinator owner topology','real':'43/43 src=blank deformation parents; textured children below',
         'failed':'direct texture sprite owns combinator','judgment':'unverified topology; main suspect, not proven root cause'},
        {'field':'owner frame mesh.bp','real':'null in every combinator owner',
         'failed':'nonnull conflicting +0.5 absolute X grid','judgment':'bp precedence deliberately adversarial before a valid base was established'},
        {'field':'terminal frame/priority','working_and_real':'terminal frame time61 type0 and priority tail item retained',
         'failed':'removed terminal frame and priority tail; lastTime changed61->3600',
         'judgment':'another independent unverified change that might affect loader scan termination'},
        {'field':'variable range','real':'mostly [-30,30]', 'failed':'[-1,1]',
         'judgment':'structurally valid finite range, lower confidence suspect'}],
    'side_path_fixtures':str(BASE/'native_integration/mesh_fixtures_v2'),
    'side_path_changes':'restore existing working sentinel structure; blank parent plus null bp first; use body_LR/body_UD ranges[-30,30]; bp conflict and direct sprite tested only after base',
    'pixel_difference':{'reference':str(BASE/'reference_controlled/normal-reference.png'),
        'native':str(BASE/'evidence/native_integration/results/controlled-normal-native.png'),
        'known_observation':'native head top about3px higher, eyes/nose about5px higher, extended hand about7px right; received and visually checked',
        'inference':'This is not explained by resource truncation/tag loss or different imported raw grid bytes. Interpolation/variable semantics, neutral boundary revocation and existing ancestor mesh propagation remain unproved.',
        'acceptance':'CPU numeric PASS is not a source-engine geometry/pixel PASS'},
    'controls':checks,
    'source_modified':False,'browser_used':False,'board_connected':False
}
(OUT/'analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report['proven_container_facts'].items() if k!='v1_resource_tags'},ensure_ascii=True,indent=2))
