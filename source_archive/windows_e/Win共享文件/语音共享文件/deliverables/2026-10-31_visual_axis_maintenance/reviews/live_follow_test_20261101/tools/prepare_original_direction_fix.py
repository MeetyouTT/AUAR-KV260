"""Correct only the original follow polarity, bound to the user's reversed-direction feedback."""
import ast
import base64
import copy
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
encoded=lambda v:(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

def main():
    previous=HERE/'package/original_restore';out=HERE/'package/original_direction_fix';out.mkdir(exist_ok=True)
    read=lambda n:json.loads((previous/n).read_bytes())
    base=read('new_spec.json');gui=read('new_gui.json');startup=read('new_startup.json');manifest=read('new_manifest.json')
    assert sha(encoded(base))=='a5a575471e54c8dcbaadd541fd153ed72f73902892f9198f9993614ba6c17767'
    assert sha(encoded(startup))==base['startup_sha256']=='476fe10a4b0c62822841494a2997f22d74164572dfeeb4a6de036fdf5bc6db78'
    direction=read('pan_direction.current.json');assert direction['axis_camera_mirrored_control_polarity']==-1
    direction.update(axis_camera_mirrored_control_polarity=1,previous_control_polarity=-1,
        user_direction_correction='转轴转动方向反了',qualification_basis='invert previous following mapping on direct human feedback',
        corrected_mapping_live_acceptance='PENDING_USER')
    raw=encoded(direction);rel='config/pan_direction.current.json'
    stage='/home/root/aura-board-business-20261030/control-production-v1/axis-original-direction-'+sha(raw)[:16]
    new=copy.deepcopy(base);new['component_sha256'][rel]=sha(raw);new['release_sources'][rel]=sha(raw)
    new['minor_prepared_configuration_path']=stage+'/prepared-gui.json'
    new.update(minor_previous_startup_sha256=base['startup_sha256'],minor_previous_manifest_sha256=base['source_manifest_sha256'],
        minor_previous_configuration_sha256=base['configuration_sha256'],minor_revision='axis-original-direction-feedback-20261101')
    new['axis_direction_rebind']=dict(stage=stage,parent_spec_sha256=sha(encoded(base)),user_quote='转轴转动方向反了',
        previous_polarity=-1,new_polarity=1,changed_components=[rel],original_sources_retained=True)
    new_start=copy.deepcopy(startup);new_start['component_sha256']=new['component_sha256']
    new['startup_sha256']=sha(encoded(new_start))
    updated=copy.deepcopy(manifest);updated['component_pins']=new['component_sha256']
    updated['configuration_path']=stage+'/prepared-gui.json'
    updated['files']['runtime/aura/'+rel]=dict(sha256=sha(raw),bytes=len(raw))
    updated['files']['startup/config.json']=dict(sha256=new['startup_sha256'],bytes=len(encoded(new_start)))
    updated['axis_direction_binding']=dict(previous_startup_sha256=base['startup_sha256'],
        previous_manifest_sha256=base['source_manifest_sha256'],feedback='转轴转动方向反了',old_polarity=-1,new_polarity=1)
    manifest_raw=encoded(updated);new['source_manifest_sha256']=sha(manifest_raw)
    targets={}
    for name,path,old,blob in (
        ('pan_direction.current.json',base['target']+'/runtime/aura/'+rel,base['component_sha256'][rel],raw),
        ('startup-config.json',base['target']+'/startup/config.json',base['startup_sha256'],encoded(new_start)),
        ('production-source-manifest.json',base['target']+'/production_source_manifest.json',base['source_manifest_sha256'],manifest_raw)):
        targets[name]=dict(path=path,old_sha256=old,new_sha256=sha(blob),new_base64=base64.b64encode(blob).decode())
    tx=dict(schema='aura-original-axis-direction-transaction-1',parent_spec_sha256=sha(encoded(base)),new_spec_sha256=sha(encoded(new)),
        targets={n:{k:v for k,v in r.items() if k!='new_base64'} for n,r in targets.items()})
    plan=read('plan.json');plan.update(stage=stage,changed_components=[rel],targets=targets,transaction=tx,
        transaction_sha256=sha(encoded(tx)))
    plan['parent_transactions']['axis_original_rebind']=dict(field='new_spec_sha256',sha=sha(encoded(base)))
    definitions=(previous/'publisher_definitions.py').read_text(encoding='utf-8')
    nodes={n.targets[0].id:n for n in ast.parse(definitions).body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)}
    for key,value in (('EXPECTED_GUI',gui),('EXPECTED_STARTUP',startup)):
        old=ast.get_source_segment(definitions,nodes[key]);assert definitions.count(old)==1
        definitions=definitions.replace(old,key+'='+repr(value))
        nodes={n.targets[0].id:n for n in ast.parse(definitions).body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)}
    overlay=(HERE/'tools/original_publisher_overlay.py').read_text(encoding='utf-8')
    overlay=overlay.replace("'axis_original_rebind'","'axis_direction_rebind'")
    overlay=overlay.replace('axis_original_rebind=dict','axis_direction_rebind=dict')
    anchor="tx.get('applied_spec_sha256')==expected"
    assert overlay.count(anchor)==1
    overlay=overlay.replace(anchor,"tx.get(expected.get('field','applied_spec_sha256') if isinstance(expected,dict) else 'applied_spec_sha256')==(expected['sha'] if isinstance(expected,dict) else expected)")
    overlay+='''\n\ndef state():
    value=ready_state()
    need(value.get('phase')=='IDLE' and value.get('handsfree_dialogue',{}).get('conversation_entered') is False,
         'idle_paused_original_owner_required')
    return value
'''
    overlay_path=HERE/'tools/original_direction_overlay.py';overlay_path.write_text(overlay,encoding='utf-8',newline='\n')
    ast.parse(overlay,feature_version=(3,9));ast.parse(definitions,feature_version=(3,9))
    for name,value in (('base_spec.json',base),('new_spec.json',new),('old_gui.json',gui),('new_gui.json',gui),
        ('new_startup.json',new_start),('new_manifest.json',updated),('plan.json',plan),('binding.json',read('binding.json'))):
        (out/name).write_bytes(encoded(value))
    (out/'publisher_definitions.py').write_text(definitions,encoding='utf-8',newline='\n')
    (out/'camera_binding_runtime.py').write_bytes((previous/'camera_binding_runtime.py').read_bytes())
    (out/'pan_direction.current.json').write_bytes(raw)
    names=('base_spec.json','new_spec.json','old_gui.json','new_gui.json','plan.json','publisher_definitions.py','camera_binding_runtime.py')
    hashes={name:sha((out/name).read_bytes()) for name in names}
    overlay_rel='../../tools/original_direction_overlay.py';hashes[overlay_rel]=sha(overlay_path.read_bytes())
    (out/'publisher_bundle_manifest.json').write_bytes(encoded(dict(files=hashes,overlay_relative=overlay_rel,
        changed_components=[rel],remaining_components_unchanged=379,python_or_native_changed=False,
        new_startup_sha256=new['startup_sha256'],new_manifest_sha256=new['source_manifest_sha256'],new_spec_sha256=sha(encoded(new)))))
    print(json.dumps(dict(status='ORIGINAL_DIRECTION_CORRECTION_PREPARED',old_polarity=-1,new_polarity=1,
        changed_components=[rel],unchanged_components=379,startup_sha256=new['startup_sha256'],manifest_sha256=new['source_manifest_sha256'])))

if __name__=='__main__':main()
