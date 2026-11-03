"""Build a prospective one-source publisher and exact-byte rollback locally; never deploy."""
from pathlib import Path
import ast
import base64
import copy
import difflib
import hashlib
import json
import zipfile

HERE=Path(__file__).resolve().parents[1]
PROJECT=HERE.parents[3]
OLD=HERE.parent/'live_follow_test_20261101/package/original_direction_fix'
PUBLIC=PROJECT/'deliverables/2026-10-30_board_owner/integration/dialogue_repair/joint_balance_20261101'
OUT=HERE/'package/single_projection'
SOURCE='tools/production_memory_presentation.py'
ROOT='/home/root/aura-board-business-20261030/production-5259eab11e42af13'
STAGE='/home/root/aura-board-business-20261030/control-production-v1/single-metadata-projection-984d3ca24067bf51'

def encoded(v):return (json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(p):return json.loads(p.read_bytes())
def put(name,raw):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(raw)
def structured(name,v):put(name,encoded(v))

def main():
    assert not OUT.exists()
    original=read(OLD/'publisher_bundle_manifest.json')
    for name,pin in original['files'].items():assert sha((OLD/name).read_bytes())==pin
    base_raw=(OLD/'new_spec.json').read_bytes();base=json.loads(base_raw)
    assert sha(base_raw)=='8ef2aa320d9ca2cf5a05e6b8b74458dfa7cf8c56be4efbebca69eed1102e2428'
    assert base_raw==(PROJECT/'deliverables/2026-10-30_board_owner/integration/production_business_acceptance/spec.json').read_bytes()
    assert encoded(base)==base_raw
    startup_raw=(OLD/'new_startup.json').read_bytes();old_startup=json.loads(startup_raw)
    manifest_raw=(OLD/'new_manifest.json').read_bytes();old_manifest=json.loads(manifest_raw)
    assert sha(startup_raw)==base['startup_sha256']=='226b5a20f0089f5c534b1d540dd3605d805c17f7f1bd371a6ab5b3a4b287ad15'
    assert sha(manifest_raw)==base['source_manifest_sha256']=='8ff79452570385921e06c098b5d42c2ea1ef5dfb84d81dfa7f53a9295373d0e8'
    arm_path=HERE/'evidence/public_single_projection_arm_1793532734568477500.json';arm=read(arm_path)
    assert sha(arm_path.read_bytes())=='ea2256f1bbf0e074fadbfe2e48ca0c1411ddac51d40d89e8557b031a8ed61027'
    assert arm['result']['status']=='PASSED'
    benchmark=arm['result']['tests_and_benchmark'][1]['result']
    assert all(row['equal_output'] and row['observed_cpu_change_percent'] < -30 for row in benchmark['cases'].values())
    zip_path=PUBLIC/'single_projection_public_validation.zip';zraw=zip_path.read_bytes()
    assert sha(zraw)=='61b816240e692844b8df71137feea6260e7b22153c0e5be9edcce28c6575f9ea'
    with zipfile.ZipFile(zip_path) as z:
        old_source=z.read('baseline/'+SOURCE);new_source=z.read('presentation_candidate/'+SOURCE)
    assert sha(old_source)==base['component_sha256'][SOURCE]=='414ed67c68ad5f6ad3e0f89608e4f7ccef71d7b8765dfffc4f071eb806cc081a'
    assert sha(new_source)=='984d3ca24067bf5129e9ce3b0054f32cced717b6b8824eab347476bef2f9e502'
    ast.parse(new_source.decode())
    startup=copy.deepcopy(old_startup);startup['component_sha256'][SOURCE]=sha(new_source);sraw=encoded(startup)
    manifest=copy.deepcopy(old_manifest);manifest['component_pins'][SOURCE]=sha(new_source)
    manifest['files']['runtime/aura/'+SOURCE]=dict(bytes=len(new_source),sha256=sha(new_source))
    manifest['files']['startup/config.json']=dict(bytes=len(sraw),sha256=sha(sraw))
    revision=dict(stage=STAGE,source=SOURCE,before_sha256=sha(old_source),after_sha256=sha(new_source),
                  parent_startup_sha256=sha(startup_raw),parent_manifest_sha256=sha(manifest_raw),
                  parent_spec_sha256=sha(base_raw),public_arm_evidence_sha256=sha(arm_path.read_bytes()),
                  public_package_sha256=sha(zraw),unchanged_components=379)
    manifest['single_metadata_projection']=revision;mraw=encoded(manifest)
    spec=copy.deepcopy(base);spec['component_sha256'][SOURCE]=sha(new_source)
    spec['release_sources'][SOURCE]=sha(new_source)
    spec.update(startup_sha256=sha(sraw),source_manifest_sha256=sha(mraw),single_metadata_projection=dict(revision,state='APPLIED'))
    nraw=encoded(spec)
    assert [k for k in spec['component_sha256'] if spec['component_sha256'][k]!=base['component_sha256'][k]]==[SOURCE]
    assert len(spec['component_sha256'])==len(base['component_sha256'])==380
    for relative in ('config/board_avatar_gtk.json','config/pan_manual.local.json','config/pan_face.local.json','config/pan_direction.current.json'):
        assert base['component_sha256'][relative]==spec['component_sha256'][relative]
    assert spec['configuration_sha256']==base['configuration_sha256']
    assert spec['camera_owner']==base['camera_owner'] and spec['face_readback']==base['face_readback']
    parents={}
    old_plan=read(OLD/'plan.json')
    for key,pin in old_plan['parent_transactions'].items():
        parents[key]=dict(stage=base[key]['stage'],field=pin.get('field','applied_spec_sha256') if isinstance(pin,dict) else 'applied_spec_sha256',
                          spec_sha256=pin['sha'] if isinstance(pin,dict) else pin)
    parents['axis_direction_rebind']=dict(stage=base['axis_direction_rebind']['stage'],field='new_spec_sha256',spec_sha256=sha(base_raw))
    baseline=read(HERE/'evidence/baseline_1793532356967963000.json')['result']
    definitions=(OLD/'publisher_definitions.py').read_bytes();binding=(OLD/'camera_binding_runtime.py').read_bytes()
    assert sha(definitions)=='1a898a854c3c1c6175e3a7585716bfcf6ed08b2e4ff50afa4fb7759f4b6cb27f'
    assert sha(binding)=='7e6a08fd97aec82cc0326c6d31d9a745b75bfa218a506ba5e8d3b3be29616878'
    for name,raw in [('base_spec.json',base_raw),('candidate_spec.json',nraw),('base_startup.json',startup_raw),('candidate_startup.json',sraw),
                     ('base_manifest.json',manifest_raw),('candidate_manifest.json',mraw),('gui.json',(OLD/'new_gui.json').read_bytes()),
                     ('payload/production_memory_presentation.py',new_source),('rollback/production_memory_presentation.py',old_source),
                     ('publisher_definitions.py',definitions),('camera_binding_runtime.py',binding),
                     ('single_projection_overlay.py',(HERE/'tools/single_projection_overlay.py').read_bytes())]:put(name,raw)
    data=[('production_memory_presentation.py',ROOT+'/runtime/aura/'+SOURCE,old_source,new_source),
          ('production-source-manifest.json',ROOT+'/production_source_manifest.json',manifest_raw,mraw),
          ('startup-config.json',ROOT+'/startup/config.json',startup_raw,sraw)]
    plans={}
    for direction in ('forward','rollback'):
        rollback=direction=='rollback';stage=STAGE+('-rollback' if rollback else '')
        before_spec=spec if rollback else base;after_spec=base if rollback else spec
        target={name:dict(path=path,old_sha256=sha(new if rollback else old),new_sha256=sha(old if rollback else new),
                          new_base64=base64.b64encode(old if rollback else new).decode()) for name,path,old,new in data}
        tx=dict(schema='aura-single-metadata-projection-transaction-1',direction=direction,stage=stage,
                parent_spec_sha256=sha(encoded(before_spec)),applied_spec_sha256=sha(encoded(after_spec)),
                targets={k:{x:y for x,y in v.items() if x!='new_base64'} for k,v in target.items()})
        plan=dict(stage=stage,marker='single_metadata_projection'+('_rollback' if rollback else ''),
                  direction=direction,changed_source=SOURCE,targets=target,transaction=tx,transaction_sha256=sha(encoded(tx)),
                  expected_before_owners=baseline['after']['owners'],face_readback=base['face_readback'],
                  parent_transactions=copy.deepcopy(parents),allow_known_mixed_on_first_apply=rollback)
        if rollback:
            plan['parent_transactions']['single_metadata_projection']=dict(stage=STAGE,field='applied_spec_sha256',
                 spec_sha256=sha(nraw),allowed_states=['INTENT','APPLIED'])
        plans[direction]=plan;structured(direction+'_plan.json',plan)
    diff=''.join(difflib.unified_diff(old_source.decode().splitlines(True),new_source.decode().splitlines(True),
                                    fromfile='before/'+SOURCE,tofile='after/'+SOURCE))
    put('source.patch',diff.encode())
    report=dict(schema='aura-single-projection-prospective-publisher-1',status='PREPARED_FOR_LOCAL_REVIEW_NOT_APPLIED',
                old_startup_sha256=base['startup_sha256'],new_startup_sha256=spec['startup_sha256'],
                old_manifest_sha256=base['source_manifest_sha256'],new_manifest_sha256=spec['source_manifest_sha256'],
                old_spec_sha256=sha(base_raw),new_spec_sha256=sha(nraw),configuration_sha256=base['configuration_sha256'],
                changed_components=[SOURCE],unchanged_components=379,gui_and_four_current_pan_configurations_retained=True,
                camera_owner=base['camera_owner'],forward_stage=STAGE,rollback_stage=STAGE+'-rollback',
                arm_evidence=str(arm_path),arm_evidence_sha256=sha(arm_path.read_bytes()),
                baseline_sampling_script_sha256=sha((HERE/'remote/baseline.py').read_bytes()),
                candidate_source_sha256=sha(new_source),rollback_exact_source_sha256=sha(old_source),
                production_modified=False,device_commands_executed_by_builder=False,
                rollback_supports_known_partial_forward=True,normal_wm_delete_only=True,
                internal_review_required_by_main_chat=True)
    structured('PREPARATION.json',report)
    files={str(p.relative_to(OUT)).replace('\\','/'):sha(p.read_bytes()) for p in OUT.rglob('*') if p.is_file()}
    files['../../tools/publish_single_projection.py']=sha((HERE/'tools/publish_single_projection.py').read_bytes())
    structured('BUNDLE_MANIFEST.json',dict(schema='aura-single-projection-publisher-bundle-1',status='PREPARED_NOT_APPLIED',files=files,
                                          source=SOURCE,source_sha256=sha(new_source),new_spec_sha256=sha(nraw),
                                          new_startup_sha256=sha(sraw),new_manifest_sha256=sha(mraw)))
    print(json.dumps(dict(status=report['status'],bundle=str(OUT),bundle_manifest_sha256=sha((OUT/'BUNDLE_MANIFEST.json').read_bytes()),**{k:report[k] for k in ('new_spec_sha256','new_startup_sha256','new_manifest_sha256')})))


if __name__=='__main__':main()
