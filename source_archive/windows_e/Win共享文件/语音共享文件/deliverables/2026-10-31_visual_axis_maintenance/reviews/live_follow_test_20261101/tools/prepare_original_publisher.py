"""Freeze a four-configuration update, retaining all 376 other v24 components and original motor sources."""
import ast
import base64
import copy
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
BUSINESS=HERE.parents[3]
V24=BUSINESS/'deliverables/2026-10-30_board_owner/integration/dialogue_repair/release_v24_memory_followup_candidate/memory_followup_evidence'
sha=lambda b:hashlib.sha256(b).hexdigest()
encoded=lambda v:(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

def main():
    out=HERE/'package/original_restore'
    base_raw=(V24/'spec.json').read_bytes();base=json.loads(base_raw)
    assert sha(base_raw)=='9015c45aa735035e2185b998ae68f97ddeb7bcbf5252301143a235dce2f3ffe1'
    current=(HERE/'audit_sources/current_v24_publisher.py.txt').read_text(encoding='utf-8')
    assert sha(current.encode())=='636c556a8a62322c4c9c341809bed27b9787a48ef0da2601fd45dc81da920c25'
    tree=ast.parse(current)
    literals={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body
        if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('EXPECTED_GUI','EXPECTED_STARTUP')}
    old_gui=literals['EXPECTED_GUI'];old_start=literals['EXPECTED_STARTUP']
    assert sha(encoded(old_gui))==base['configuration_sha256']
    assert sha(encoded(old_start))==base['startup_sha256']
    binding=json.loads((out/'binding.json').read_bytes())
    stage='/home/root/aura-board-business-20261030/control-production-v1/axis-original-binding-'+binding['camera_binding_proof_sha256'][:16]
    new_gui=copy.deepcopy(old_gui);new_gui['board_business']['face_readback']=binding['face_readback']
    config_changes={'config/'+n:(out/n).read_bytes() for n in ('pan_manual.local.json','pan_face.local.json','pan_direction.current.json')}
    config_changes['config/board_avatar_gtk.json']=encoded(new_gui)
    pins=dict(base['component_sha256']);pins.update({r:sha(b) for r,b in config_changes.items()})
    assert len(pins)==380 and {r for r,h in pins.items() if h!=base['component_sha256'][r]}==set(config_changes)
    assert all(not r.endswith(('.py','.so')) for r in config_changes)
    new_start=copy.deepcopy(old_start);new_start['component_sha256']=pins
    manifest_raw=(out/'production_source_manifest.json').read_bytes()
    assert sha(manifest_raw)==base['source_manifest_sha256']
    manifest=json.loads(manifest_raw)
    manifest.update(component_pins=pins,configuration_sha256=sha(encoded(new_gui)),configuration_path=stage+'/prepared-gui.json')
    new_bytes={r:blob for r,blob in config_changes.items()}
    new_bytes['startup/config.json']=encoded(new_start)
    for rel,blob in new_bytes.items():
        key=rel if rel.startswith('startup/') else 'runtime/aura/'+rel
        assert key in manifest['files']
        manifest['files'][key]=dict(sha256=sha(blob),bytes=len(blob))
    manifest['axis_original_binding']=dict(previous_startup_sha256=base['startup_sha256'],
        previous_manifest_sha256=base['source_manifest_sha256'],camera_owner=binding['camera_owner'],
        camera_readback=binding['face_readback'],camera_proof_sha256=binding['camera_binding_proof_sha256'],
        original_controller_root='/home/root/aura-pan-wide-20261028/control-10282601',
        original_controller_manifest_sha256='5c8206ee626c91c9f311ee870245813e169ac14e554e2579554c74489066f562',
        python_or_native_sources_changed=False)
    new_manifest=encoded(manifest)
    spec=copy.deepcopy(base)
    spec.update(camera_owner=binding['camera_owner'],face_readback=binding['face_readback'],
        configuration_sha256=sha(encoded(new_gui)),component_sha256=pins,
        startup_sha256=sha(encoded(new_start)),source_manifest_sha256=sha(new_manifest),
        minor_prepared_configuration_path=stage+'/prepared-gui.json',
        minor_previous_configuration_sha256=base['configuration_sha256'],minor_previous_startup_sha256=base['startup_sha256'],
        minor_previous_manifest_sha256=base['source_manifest_sha256'],minor_revision='axis-original-binding-20261101',minor_state='APPLIED')
    for rel,blob in config_changes.items():spec['release_sources'][rel]=sha(blob)
    spec['axis_original_rebind']=dict(stage=stage,camera_proof_sha256=binding['camera_binding_proof_sha256'],
        changed_components=sorted(config_changes),parent_v24_spec_sha256=sha(base_raw),
        original_controller_manifest_sha256=manifest['axis_original_binding']['original_controller_manifest_sha256'],
        candidate_r2_selected=False,original_sources_retained=True)
    targets={}
    for rel,blob in config_changes.items():
        targets[Path(rel).name]=dict(path=base['target']+'/runtime/aura/'+rel,
            old_sha256=base['component_sha256'][rel],new_sha256=sha(blob),new_base64=base64.b64encode(blob).decode())
    targets['startup-config.json']=dict(path=base['target']+'/startup/config.json',old_sha256=base['startup_sha256'],
        new_sha256=spec['startup_sha256'],new_base64=base64.b64encode(encoded(new_start)).decode())
    targets['production-source-manifest.json']=dict(path=base['target']+'/production_source_manifest.json',old_sha256=base['source_manifest_sha256'],
        new_sha256=spec['source_manifest_sha256'],new_base64=base64.b64encode(new_manifest).decode())
    transaction=dict(schema='aura-original-axis-config-transaction-1',parent_v24_spec_sha256=sha(base_raw),
        new_spec_sha256=sha(encoded(spec)),targets={n:{k:v for k,v in row.items() if k!='new_base64'} for n,row in targets.items()})
    plan=dict(stage=stage,face_readback=binding['face_readback'],camera_proof_sha256=binding['camera_binding_proof_sha256'],
        changed_components=sorted(config_changes),targets=targets,transaction=transaction,transaction_sha256=sha(encoded(transaction)),
        parent_transactions={'camera_rebind':'ecdc034bd06cdd15bffe004a3ac1be3a6bc350dc3c879d91d3a19403f5c0f74a',
            'summary_revision':'8376770e832d82add3ae207da3228c46c34ada89b95830cdd7536f8291224ec2',
            'summary_followup':sha(base_raw)})
    # Reuse exact normal-close/start/guard/owner/source checks. The original
    # dispatcher is replaced by a dedicated transaction that verifies all three
    # historical transactions against their original, unchanged specs.
    definitions=[]
    for n in tree.body:
        if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef,ast.Assign)):
            if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('READBACK_HELPER','SAMEBOOT_HELPER','RESTORED_HELPER'):continue
            definitions.append(ast.get_source_segment(current,n))
        elif isinstance(n,ast.Assert) and not any(isinstance(x,ast.Name) and x.id=='ACTION' for x in ast.walk(n)):
            definitions.append(ast.get_source_segment(current,n))
        elif isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and ast.get_source_segment(current,n).startswith('sys.path.insert'):
            definitions.append(ast.get_source_segment(current,n))
    definition_source='\n\n'.join(definitions)+'\n'
    # The freshly consumed checkpoint verifier runs in its own namespace so its
    # session journal helpers cannot shadow the production publisher's helpers.
    binding_source=(HERE/'remote/prepare_camera_readback.py').read_text(encoding='utf-8')
    body=binding_source[binding_source.index("original=Path("):binding_source.index("private=ROOT/'camera-binding'")]
    verify="def verify_binding():\n    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT\n    wide_active();verify_wide_files()\n    j=state()\n"+'\n'.join('    '+x for x in body.splitlines())+'\n'
    verify+="    proof_path=ROOT/'camera-binding/proof.json'\n    proof=document(proof_path)\n    assert digest(proof_path)=="+repr(binding['camera_binding_proof_sha256'])+"\n"
    verify+="    assert proof['candidate']==j['camera_readback']\n    assert digest(proof['candidate']['path'])==proof['candidate']['sha256']\n    assert document(proof['candidate']['path'])==candidate\n"
    verify+="    assert proof['service_epoch']==h['service_epoch'] and proof['camera_epoch']==h['camera_epoch']\n    return candidate,proof\n"
    binding_runtime=(HERE/'remote/_session_common.py').read_text(encoding='utf-8')+'\n'+(HERE/'remote/_camera_binding_rules.py').read_text(encoding='utf-8')+'\n'+verify
    ast.parse(binding_runtime,feature_version=(3,9));ast.parse(definition_source,feature_version=(3,9))
    for name,value in [('base_spec.json',base),('new_spec.json',spec),('old_gui.json',old_gui),('new_gui.json',new_gui),
                       ('plan.json',plan)]: (out/name).write_bytes(encoded(value))
    (out/'publisher_definitions.py').write_text(definition_source,encoding='utf-8',newline='\n')
    (out/'camera_binding_runtime.py').write_text(binding_runtime,encoding='utf-8',newline='\n')
    (out/'new_startup.json').write_bytes(encoded(new_start));(out/'new_manifest.json').write_bytes(new_manifest)
    files={name:sha((out/name).read_bytes()) for name in ('base_spec.json','new_spec.json','old_gui.json','new_gui.json','plan.json','publisher_definitions.py','camera_binding_runtime.py')}
    overlay=HERE/'tools/original_publisher_overlay.py';ast.parse(overlay.read_text(encoding='utf-8'),feature_version=(3,9))
    files['../../tools/original_publisher_overlay.py']=sha(overlay.read_bytes())
    (out/'publisher_bundle_manifest.json').write_bytes(encoded(dict(files=files,changed_components=sorted(config_changes),
        remaining_components_unchanged=376,python_or_native_changed=False,original_controller_files=25,
        original_controller_unchanged=True,new_startup_sha256=spec['startup_sha256'],new_manifest_sha256=spec['source_manifest_sha256'],
        new_configuration_sha256=spec['configuration_sha256'],new_spec_sha256=sha(encoded(spec)))))
    print(json.dumps(dict(status='ORIGINAL_CONFIGURATION_TRANSACTION_PREPARED',changed_components=sorted(config_changes),
        unchanged_components=376,python_or_native_sources_changed=False,startup_sha256=spec['startup_sha256'],
        manifest_sha256=spec['source_manifest_sha256'],new_spec_sha256=sha(encoded(spec)))))

if __name__=='__main__':main()
