"""Independent small EMS/PSB inputs for original-engine combinator observations.

Only writes native_integration/mesh_fixtures. Does not operate any browser/board.
"""
from pathlib import Path
import copy
import hashlib
import json
import struct
import subprocess
import sys

BASE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(BASE/'source/tools/reference_capture'))
from synthetic_model import layer, model, png_rgba

OUT=BASE/'native_integration/mesh_fixtures'
OUT.mkdir(exist_ok=True)
TOOL=Path('D:/share、/项目开发/美冬本地女友项目/assets/fuyukiss/_freemote/toolkit/PsBuild.exe')

def grid(dx=0,dy=0,absolute=True):
    return [v for y in range(4) for x in range(4)
            for v in ((x/3 if absolute else 0)+dx,(y/3 if absolute else 0)+dy)]

absolute=[grid(dx=-.25),grid(),grid(dx=.25)]
delta=[grid(dy=-.25,absolute=False),grid(absolute=False),grid(dy=.25,absolute=False)]
flat=lambda grids:[v for g in grids for v in g]
def control(variable,index):
    return dict(meshType=1,neutralIndex=1,rawMeshList=f'#resource@{index}',
                variable=dict(key=variable,meshCount=3,rangeBegin=-1.0,rangeEnd=1.0))

def document(mode):
    # The conflicting bp translates X by 0.5*64=32 px. A combinator must own it.
    frame=dict(src='tex',icon='tile',coord=[64.0,64.0,0.0],mask=0x2000002,
               mesh=dict(bp=grid(dx=.5),cc=None))
    node=layer('controlled tile',frame,type=0,meshDivision=16,meshTransform=1,meshSyncChildMask=8)
    node['frameList']=[dict(content=frame,time=0,type=2)]
    if mode!='bp_only':
        node['meshCombinator']={'combinatorList':[control('p',0)]}
        if mode=='absolute_plus_delta':
            node['meshCombinator']['combinatorList'].append(control('q',1))
    doc=model([node],['p','q'])
    motion=doc['object']['test']['motion']['root']
    motion.update(lastTime=3600,priority=[dict(content=[0],time=0,type=1)])
    doc['source']['tex']['texture'].update(width=64,height=64,truncated_width=64,truncated_height=64)
    doc['source']['tex']['icon']['tile'].update(width=64,height=64,left=0.0,top=0.0,originX=0,originY=0)
    doc['metadata']['charaProfile']={'height':256,'pixelMarker':dict(
        top=0.0,bottom=256.0,boundsTop=0.0,boundsBottom=256.0,boundsLeft=0.0,
        boundsRight=256.0,eye=64.0,mouth=128.0)}
    doc['metadata']['variableList']=[dict(label=v,frameList=[
        dict(frame=-1,label='negative'),dict(frame=0,label='neutral'),dict(frame=1,label='positive')])
        for v in ('p','q')]
    return doc

def table_values(data,offset):
    cw=data[offset]-12
    assert 1<=cw<=4
    count=int.from_bytes(data[offset+1:offset+1+cw],'little')
    if count==0:
        return []
    width=data[offset+1+cw]-12
    assert 1<=width<=4
    start=offset+2+cw
    return [int.from_bytes(data[start+i*width:start+(i+1)*width],'little') for i in range(count)]

def verify_psb(path,expected):
    data=path.read_bytes()
    assert data[:4]==b'PSB\0' and int.from_bytes(data[4:6],'little')==4
    offsets=table_values(data,struct.unpack_from('<I',data,44)[0])
    lengths=table_values(data,struct.unpack_from('<I',data,48)[0])
    chunk=struct.unpack_from('<I',data,52)[0]
    actual=[data[chunk+o:chunk+o+n] for o,n in zip(offsets,lengths)]
    hashes={hashlib.sha256(v).hexdigest() for v in actual}
    for raw in expected:
        assert hashlib.sha256(raw).hexdigest() in hashes
    return dict(bytes=len(data),extra_resources=len(actual),extra_lengths=lengths,
                sha256=hashlib.sha256(data).hexdigest())

# Opaque asymmetric grid gives clear positions and vertex correspondence.
rgba=bytes(c for y in range(64) for x in range(64) for c in
    ((235,40,35,255) if x<4 or y<4 else
     ((25,205,80,255) if ((x//8+y//8)&1)==0 else (35,65,225,255))))
png=png_rgba(64,64,rgba)
manifest={'scope':'independent original-engine inputs; expectations are native candidate hypotheses',
          'browser_executed':False,'board_compiled':False,'models':{},'cases':[]}
base_rig=json.loads((BASE/'native_integration/mask_fixtures/motion-self-rig.json').read_text(encoding='utf8'))
for mode in ('absolute_with_bp','absolute_plus_delta','bp_only'):
    folder=OUT/mode;folder.mkdir(exist_ok=True)
    doc=document(mode)
    arrays={} if mode=='bp_only' else {'@0':flat(absolute)}
    if mode=='absolute_plus_delta':arrays['@1']=flat(delta)
    resx=dict(PsbVersion=4,PsbType='Motion',Platform='ems',CryptKey=None,ExternalTextures=False,
              Context={},Resources={'0':'texture.png'},ExtraResources={},ExtraFlattenArrays=arrays)
    (folder/'texture.png').write_bytes(png)
    (folder/'model.json').write_text(json.dumps(doc,indent=2),encoding='utf8')
    (folder/'model.resx.json').write_text(json.dumps(resx,indent=2),encoding='utf8')
    command=[str(TOOL),'-v','4','-p','ems','-ns','-o',str(folder/'model.psb'),str(folder/'model.json')]
    result=subprocess.run(command,cwd=folder,capture_output=True,text=True,errors='replace',timeout=60)
    (folder/'compile.log').write_text(result.stdout+result.stderr,encoding='utf8')
    if result.returncode:raise RuntimeError('PsBuild failed: '+mode)
    expected=[struct.pack('<'+'f'*len(values),*values) for values in arrays.values()]
    checked=verify_psb(folder/'model.psb',expected)
    manifest['models'][mode]=dict(directory=str(folder),model=f'/mesh-fixtures/{mode}/model.psb',
                                  source_variables=['p','q'],psb=checked)

cases=[
    ('bp_only','bp-control',0,0),
    ('absolute_with_bp','abs-neutral-bp-priority',0,0),
    ('absolute_with_bp','abs-fraction',.5,0),
    ('absolute_with_bp','abs-left-end',-1,0),
    ('absolute_with_bp','abs-right-end',1,0),
    ('absolute_with_bp','abs-left-clamp',-2,0),
    ('absolute_with_bp','abs-right-clamp',2,0),
    ('absolute_with_bp','abs-left-fraction',-.5,0),
    ('absolute_plus_delta','sum-neutral',0,0),
    ('absolute_plus_delta','sum-delta-only',0,1),
    ('absolute_plus_delta','sum-fraction',.5,.5),
    ('absolute_plus_delta','sum-two-endpoints',1,1),
    ('absolute_plus_delta','sum-negative-clamp',-2,-2)]
for mode,name,p,q in cases:
    # Candidate analytic expected values; no engine output is inferred here.
    x=96 if mode=='bp_only' else 64+16*max(-1,min(1,p))
    y=64+(16*max(-1,min(1,q)) if mode=='absolute_plus_delta' else 0)
    rig=copy.deepcopy(base_rig)
    rig.update(model=f'/mesh-fixtures/{mode}/model.psb',idleTimeline='',poseTimelines={'0':''},
        poses=[0],defaultPose=0,expressions={'normal':{'p':p,'q':q}},
        view={'pad':0.06,'bustFraction':1.0,'maxRenderSize':1536},character=name,modelId=name)
    (OUT/(name+'-rig.json')).write_text(json.dumps(rig),encoding='utf8')
    manifest['cases'].append(dict(name=name,mode=mode,variables={'p':p,'q':q},
        rig=f'/mesh-fixtures/{name}-rig.json',expected_model_bounds=[x,y,x+64,y+64],
        expected_model_corners=[[x,y],[x+64,y],[x,y+64],[x+64,y+64]],
        expected_scope='unprojected model XY; screenshot coordinates depend on common view'))
manifest['recommended_first_cases']=['bp-control','abs-neutral-bp-priority','abs-fraction',
                                    'sum-delta-only','sum-fraction','sum-two-endpoints']
manifest['hashes']={p.relative_to(OUT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in OUT.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'models':3,'cases':len(cases),'path':str(OUT)},ensure_ascii=True))
