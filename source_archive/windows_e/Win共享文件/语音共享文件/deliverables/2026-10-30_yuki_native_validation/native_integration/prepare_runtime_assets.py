"""Build the explicit, reversible source-engine compatibility profile for Yuki.

Raw source and all optional records are retained next to the derived runtime
JSON. Acceptance is gated separately by native picture/timing evidence.
"""
from pathlib import Path
import hashlib,json,shutil
BASE=Path(__file__).parent.parent;phase=BASE/'native_integration';dest=phase/'runtime_assets'
source=BASE/'inputs/ems/yuk_0.ems.json'
comparison=json.loads((phase/'reference-pair-comparison.json').read_text(encoding='utf8'))
required=['original_vs_rebuilt_combo','original_engine_combo_vs_removed','combo_vs_removed_tick1','combo_vs_removed_tick60']+[
 'source_manual_extremes_combo_vs_removed_pose'+str(pose) for pose in (0,1)]
assert all(comparison[key]['different_pixels']==0 for key in required)
document=json.loads(source.read_text(encoding='utf-8-sig'));edits=[]
def walk(value,path=''):
    if isinstance(value,dict):
        if value.get('meshCombinator'):
            edits.append({'path':path+'/meshCombinator','control_count':len(value['meshCombinator']['combinatorList'])})
            value['meshCombinator']=None
        for key,child in value.items():walk(child,path+'/'+key)
    elif isinstance(value,list):
        for i,child in enumerate(value):walk(child,path+'/'+str(i))
walk(document)
assert len(edits)==43 and sum(x['control_count'] for x in edits)==122
dest.mkdir(exist_ok=True)
shutil.copyfile(source,dest/'model.source.ems.json')
(dest/'model.runtime.json').write_text(json.dumps(document,ensure_ascii=True),encoding='utf8')
shutil.copyfile(BASE/'inputs/ems/yuk_0.ems.resx.json',dest/'yuk_0.ems.resx.json')
(dest/'yuk_0.ems').mkdir(exist_ok=True)
shutil.copyfile(BASE/'inputs/ems/yuk_0.ems/tex-texture.png',dest/'yuk_0.ems/tex-texture.png')
manifest={'schema':'aura.yuki.source_profile.v1','profile_id':'fuyukiss-yuki-freemote39-frame-mesh',
 'status':'SOURCE_BEHAVIOR_PROVEN_FINAL_GPU_GATES_PENDING',
 'model':'Yuki yuk_0 only; source EMS3.03 and pinned FreeMote WebGL driver',
 'source_psb_sha256':'d752ef761e53922ffcc9895023f3782a20161792e8f28b51099721534544aad7',
 'evidence':'reference-pair-comparison.json: original/rebuild exact; records on/off exact at0/1/60ticks and both poses with actual extreme inputs',
 'runtime_semantics':'use source frame mesh.bp tracks, retain extra combinator source tables without applying a second deformation',
 'source_retained':True,'generic_combinator_evaluator_retained':True,'general_model_compatibility_claim':False,
 'edits':edits,'physics_disabled':False,'mask_guards_relaxed':False,'production_deployed':False,
 'files':{p.relative_to(dest).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.rglob('*') if p.is_file() and p.name!='source_profile.json'}}
(dest/'source_profile.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print(json.dumps({'profile':manifest['profile_id'],'changed_records':43,'retained_controls':122,'production_deployed':False}))
