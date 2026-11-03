"""Independent small PSB scenes that discriminate self-referential alpha masks."""
from pathlib import Path
import copy, hashlib, json, sys

BASE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(BASE/'source/tools/reference_capture'))
from synthetic_model import layer,model,encode_psb,png_rgba

OUT=BASE/'native_integration/mask_fixtures'
OUT.mkdir(exist_ok=True)
def tile(label,icon,x,y,children=None):
    return layer(label,dict(src='tex',icon=icon,coord=[float(x),float(y),0.0],mask=0x2000002),
                 children,type=0,meshTransform=0,meshDivision=0,meshSyncChildMask=0)
def stencil(label,source,children):
    return layer(label,dict(src='blank',icon='32:32:0:0',mask=0),children,
                 type=12,meshTransform=0,meshDivision=0,meshSyncChildMask=0,stencilType=5,
                 stencilCompositeMaskLayerList=[source],inheritMask=37750780)
def profile(document):
    document['metadata']['charaProfile']={'height':128,'pixelMarker':dict(
      top=0.0,bottom=128.0,boundsTop=0.0,boundsBottom=128.0,boundsLeft=0.0,boundsRight=128.0,eye=40.0,mouth=80.0)}
    document['source']['tex']['texture'].update(width=192,height=64,truncated_width=192,truncated_height=64)
    document['source']['tex']['icon']={name:dict(attr=0,width=64,height=64,left=float(i*64),top=0.0,originX=0,originY=0,
      metadata={'zorder':i}) for i,name in enumerate(('red','green','blue'))}
    return document

cases={}
for mode in ('motion_self','sprite_self','ordinary_child','other_stencil'):
    clip=stencil('self clip','source root',[tile('masked green','green',48,16)])
    if mode=='motion_self':
        root=layer('source root',dict(src='test',icon='coverage',mask=524288,motion={'mask':0,'timeOffset':0}),[clip],
           type=3,meshTransform=0,meshDivision=0,meshSyncChildMask=0)
        doc=model([root]);doc['object']['test']['motion']['coverage']=model([tile('red coverage','red',16,16)])['object']['test']['motion']['root']
    else:
        children=[clip]
        if mode=='ordinary_child':
            extra=tile('extra blue coverage','blue',48,64)
            extra['frameList'][0]['content'].update(opa=0,mask=0x2000402)
            children.insert(0,extra)
        if mode=='other_stencil':
            # Blue is independently clipped by the red source. It must not enlarge red coverage.
            children.insert(0,stencil('other clip','source root',[tile('extra blue coverage','blue',48,64)]))
        root=tile('source root','red',16,16,children)
        # Child coordinates are parent-local, so keep source root at the origin with source icon origin.
        root['frameList'][0]['content']['coord']=[0.0,0.0,0.0]
        doc=model([root]);doc['source']['tex']['icon']['tile']['originX']=0
    cases[mode]=profile(doc)

colors=[(220,40,30,255),(25,210,60,255),(40,70,230,255)]
rgba=bytes(c for y in range(64) for x in range(192) for c in colors[x//64])
for name,doc in cases.items():
    folder=OUT/name;folder.mkdir(exist_ok=True)
    (folder/'texture.png').write_bytes(png_rgba(192,64,rgba))
    (folder/'model.json').write_text(json.dumps(doc,indent=2),encoding='utf8')
    (folder/'model.resx.json').write_text(json.dumps(dict(PsbVersion=4,PsbType='Motion',Platform='ems',
      CryptKey=None,ExternalTextures=False,Context={},Resources={'0':'texture.png'})),encoding='utf8')
    (folder/'model.psb').write_bytes(encode_psb(doc,[rgba]))
    rig=json.loads(Path('D:/share、/项目开发/美冬本地女友项目/web/tachie/yuki-rig.json').read_text(encoding='utf8'))
    rig.update(model='/fixtures/'+name+'/model.psb',idleTimeline='',poseTimelines={'0':''},poses=[0],defaultPose=0,
      expressions={'normal':{}},view={'pad':0.06,'bustFraction':1.0,'maxRenderSize':1536},character=name,modelId=name)
    (OUT/(name.replace('_','-')+'-rig.json')).write_text(json.dumps(rig),encoding='utf8')
manifest={p.relative_to(OUT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print(json.dumps({'fixtures':list(cases),'files':len(manifest),'path':str(OUT)}))
