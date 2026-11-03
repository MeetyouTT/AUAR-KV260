"""Side-path mesh fixtures; preserve v1 and production code unchanged.

Keeps the working synthetic fixture sentinel frames/priority/lastTime. Places
the combinator on a blank parent as in all 43 real Yuki combinator owners.
Still diagnostic inputs, not original-engine validated output.
"""
from pathlib import Path
import copy
import hashlib
import json
import struct
import subprocess
import sys

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE/'source/tools/reference_capture'))
sys.path.insert(0, str(BASE/'native_integration/mesh_fixtures_diagnosis'))
from synthetic_model import layer, model
from inspect_psb import Reader

OUT = BASE/'native_integration/mesh_fixtures_v2'
OUT.mkdir(exist_ok=True)
TOOL = Path('D:/share、/项目开发/美冬本地女友项目/assets/fuyukiss/_freemote/toolkit/PsBuild.exe')

def grid(dx=0, dy=0, absolute=True):
    return [v for y in range(4) for x in range(4)
            for v in ((x/3 if absolute else 0)+dx, (y/3 if absolute else 0)+dy)]

absolute = [grid(dx=-.25), grid(), grid(dx=.25)]
delta = [grid(dy=-.25, absolute=False), grid(absolute=False), grid(dy=.25, absolute=False)]
flat = lambda grids: [v for g in grids for v in g]

def control(variable, index):
    return dict(meshType=1, neutralIndex=1, rawMeshList=f'#resource@{index}',
                variable=dict(key=variable, meshCount=3, rangeBegin=-30, rangeEnd=30))

working = json.loads((BASE/'native_integration/mask_fixtures/sprite_self/model.json').read_text(encoding='utf8'))
base_rig = json.loads((BASE/'native_integration/mask_fixtures/motion-self-rig.json').read_text(encoding='utf8'))
texture = (BASE/'native_integration/mesh_fixtures/bp_only/texture.png').read_bytes()
manifest = {'scope': 'side-path diagnostic inputs; original-engine unverified',
            'v1_preserved': True, 'browser_executed': False, 'production_modified': False,
            'models': {}, 'cases': []}

def document(mode):
    has_combo = mode != 'baseline_texture'
    is_direct = mode == 'direct_null_bp'
    child = layer('controlled tile', dict(src='tex', icon='tile', coord=[0.,0.,0.],
                  mask=0x2000002, mesh=dict(bp=None, cc=None)), meshSyncChildMask=0)
    if mode == 'baseline_texture' or is_direct:
        child['frameList'][0]['content']['coord'] = [32.,32.,0.]
        layers = [child]
        owner = child
    else:
        owner = layer('controlled blank', dict(src='blank', icon='64:64:0:0',
                      coord=[32.,32.,0.], mask=0x2000002, mesh=dict(bp=None, cc=None)),
                      children=[child], meshSyncChildMask=8)
        layers = [owner]
    if mode == 'blank_conflicting_bp':
        owner['frameList'][0]['content']['mesh']['bp'] = grid(dx=.5)
    if has_combo:
        owner['meshCombinator'] = {'combinatorList': [control('body_LR',0)]}
        if mode == 'blank_absolute_delta':
            owner['meshCombinator']['combinatorList'].append(control('body_UD',1))
    doc = model(layers, ['body_LR','body_UD'])
    # Keep the exact already-loaded fixture metadata apart from variables.
    doc['metadata'] = copy.deepcopy(working['metadata'])
    doc['metadata']['variableList'] = [dict(label=v,frameList=[
        dict(frame=-30,label='negative'),dict(frame=0,label='neutral'),dict(frame=30,label='positive')])
        for v in ('body_LR','body_UD')]
    doc['source']['tex']['texture'].update(width=64,height=64,truncated_width=64,truncated_height=64)
    doc['source']['tex']['icon']['tile'].update(width=64,height=64,left=0.,top=0.,originX=0,originY=0)
    return doc

for mode in ('baseline_texture','blank_absolute','blank_absolute_delta','blank_conflicting_bp','direct_null_bp'):
    folder = OUT/mode
    folder.mkdir(exist_ok=True)
    doc = document(mode)
    arrays = {} if mode == 'baseline_texture' else {'@0':flat(absolute)}
    if mode == 'blank_absolute_delta': arrays['@1'] = flat(delta)
    resx = dict(PsbVersion=4,PsbType='Motion',Platform='ems',CryptKey=None,ExternalTextures=False,
                Context={},Resources={'0':'texture.png'},ExtraResources={},ExtraFlattenArrays=arrays)
    (folder/'model.json').write_text(json.dumps(doc,indent=2),encoding='utf8')
    (folder/'model.resx.json').write_text(json.dumps(resx,indent=2),encoding='utf8')
    (folder/'texture.png').write_bytes(texture)
    command = [str(TOOL),'-v','4','-p','ems','-ns','-o',str(folder/'model.psb'),str(folder/'model.json')]
    result = subprocess.run(command,cwd=folder,capture_output=True,text=True,errors='replace',timeout=60)
    (folder/'compile.log').write_text(result.stdout+result.stderr,encoding='utf8')
    if result.returncode: raise RuntimeError('PsBuild failed: '+mode)
    inspected = Reader(folder/'model.psb').inspect()
    raw = Reader(folder/'model.psb')
    offsets,_ = raw.table(raw.u32(44)); lengths,_ = raw.table(raw.u32(48)); chunk=raw.u32(52)
    payloads = [raw.data[chunk+o:chunk+o+n] for o,n in zip(offsets,lengths)]
    for a in arrays.values():
        assert struct.pack('<'+'f'*len(a),*a) in payloads
    resource_tags = inspected['resource_tags']
    assert all(t['tag']=='0x22' for p,t in resource_tags.items() if p.endswith('/rawMeshList'))
    assert all(t['tag']=='0x19' for p,t in resource_tags.items() if p.endswith('/pixel'))
    (folder/'container-tags.json').write_text(json.dumps(resource_tags,indent=2),encoding='utf8')
    manifest['models'][mode] = {'model':f'/mesh-fixtures-v2/{mode}/model.psb',
        'bytes':len(raw.data),'sha256':hashlib.sha256(raw.data).hexdigest(),
        'extra_lengths':lengths,'resource_tags':resource_tags,
        'motion_lastTime':61,'terminal_frames_retained':True}

cases = [('baseline_texture','baseline',0,0),
         ('blank_absolute','blank-neutral',0,0),
         ('blank_absolute','blank-half',15,0),
         ('blank_absolute','blank-left-end',-30,0),
         ('blank_absolute','blank-right-end',30,0),
         ('blank_absolute_delta','sum-neutral',0,0),
         ('blank_absolute_delta','sum-delta-only',0,30),
         ('blank_absolute_delta','sum-half',15,15),
         ('blank_absolute_delta','sum-ends',30,30),
         ('blank_conflicting_bp','bp-neutral',0,0),
         ('blank_conflicting_bp','bp-half',15,0),
         ('direct_null_bp','direct-neutral',0,0),
         ('direct_null_bp','direct-half',15,0)]
for mode,name,p,q in cases:
    x = 32 if mode=='baseline_texture' else 32+16*max(-1,min(1,p/30))
    y = 32+(16*max(-1,min(1,q/30)) if mode=='blank_absolute_delta' else 0)
    rig=copy.deepcopy(base_rig)
    rig.update(model=f'/mesh-fixtures-v2/{mode}/model.psb',idleTimeline='',poseTimelines={'0':''},
        poses=[0],defaultPose=0,expressions={'normal':{'body_LR':p,'body_UD':q}},
        character=name,modelId=name)
    (OUT/(name+'-rig.json')).write_text(json.dumps(rig),encoding='utf8')
    manifest['cases'].append(dict(name=name,mode=mode,variables={'body_LR':p,'body_UD':q},
        rig=f'/mesh-fixtures-v2/{name}-rig.json',expected_candidate_bounds=[x,y,x+64,y+64]))
manifest['test_order']=['baseline','blank-neutral','blank-half','sum-delta-only','sum-half',
                        'bp-neutral','bp-half','direct-neutral','direct-half']
manifest['hashes']={p.relative_to(OUT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in OUT.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'models':len(manifest['models']),'cases':len(cases),'path':str(OUT)},ensure_ascii=True))
