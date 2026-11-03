from pathlib import Path
import json,shutil
base=Path(__file__).parent.parent;phase=base/'native_integration';dest=phase/'native_references'
source=base/'reference_controlled/matched_viewport'
dest.mkdir(exist_ok=True)
manifest=json.loads((source/'capture-manifest.json').read_text(encoding='utf8'))
assert manifest['viewport']==[423,438] and manifest['canvas2dCopyOffset']==[0,0]
# Preserve the original web host's 1536-square crop as separate historical evidence.
# The production native renderer has a 423x438 viewport and no half-pixel Canvas2D copy.
old=phase/'native_references_webhost1536'
if not old.exists() and any(dest.iterdir()):shutil.copytree(dest,old)
for item in manifest['images']:
    tag=item['name']
    assert item['parameterCount']==57 and item['referenceViewport']=='423x438'
    shutil.copyfile(source/(tag+'.png'),dest/(tag+'.png'))
    params=json.loads((source/(tag+'-parameters.json')).read_text(encoding='utf8'))
    assert len(params)==57
    native_tag=tag.removeprefix('face-')
    (phase/'bp_diagnostic'/(native_tag+'-parameters.json')).write_text(json.dumps(params,indent=2),encoding='utf8')
for name in ('motion-self','sprite-self','ordinary-child','other-stencil'):
    shutil.copyfile(source/(name+'-reference-lossless.png'),dest/(name+'-reference-lossless.png'))
for name in ('capture-manifest.json','mask-capture-manifest.json'):
    shutil.copyfile(source/name,dest/name)
print('MATCHED_VIEWPORT_LOSSLESS_SOURCE_REFERENCES_PREPARED')
