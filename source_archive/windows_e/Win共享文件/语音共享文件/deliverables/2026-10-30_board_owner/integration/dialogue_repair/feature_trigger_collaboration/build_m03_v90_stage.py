"""Metadata-only rebind of the frozen 8-case public worker to sealed v90.
All three candidate product files are copied byte-for-byte. Old packages stay.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
OLD=H/'candidate_m03_newboot'
D=H/'candidate_m03_v90_stage'
REPAIR=H.parent
MAP=REPAIR/'release_v18_minor_ui_candidate/minor_evidence/source_mapping.json'


def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(path,raw):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
def dump(tree):return ast.dump(tree,include_attributes=False)


def main():
    prior_raw=(OLD/'SOURCE_MANIFEST.json').read_bytes()
    assert sha(prior_raw)=='29107d8ebf03c541cb4ad771eeb26526a96a8c74aad0c09950344a6fd7e97a7a'
    original=json.loads(prior_raw)
    old_worker=(OLD/'arm_public_worker.py').read_bytes()
    assert sha(old_worker)=='16b67f5c93fa4c86f62f64667c58bae395bc353cd5d0f8e7b4f0bf00a3b3eb77'
    map_raw=MAP.read_bytes();mapping=json.loads(map_raw)
    assert mapping['startup_sha256']=='90f6c6c40f6501362aa77483235a7260a212de6e3357615311bdaa5cc193ebbe'
    assert mapping['source_manifest_sha256']=='6d03c1d7aa95a9c5615f540606699f67c4ee7a44be1e50dcb2983c6c555e3637'
    assert mapping['boot_id']==original['baseline_boot_id'] and len(mapping['component_pins'])==379
    candidate=copy.deepcopy(original)
    candidate['baseline_startup_sha256']=mapping['startup_sha256']
    candidate['baseline_source_manifest_sha256']=mapping['source_manifest_sha256']
    candidate['baseline_mapping_sha256']=sha(map_raw)
    product_proof={}
    for relative,row in original['files'].items():
        raw=(OLD/'after'/relative).read_bytes()
        assert sha(raw)==row['sha256']
        assert mapping['component_pins'].get(relative)==row['before_sha256']
        write(D/'after'/relative,raw)
        if row['before_sha256'] is not None:write(D/'before'/relative,(OLD/'before'/relative).read_bytes())
        candidate['files'][relative]['source']=str(D/'after'/relative)
        product_proof[relative]=dict(sha256=sha(raw),same_as_frozen_newboot_and_reviewed_r2_logic=True)
    # JSON-equivalence proof: only three baseline fields and source path
    # metadata change. No product/source hash or test reference is rewritten.
    restored=copy.deepcopy(candidate)
    for key in ('baseline_startup_sha256','baseline_source_manifest_sha256','baseline_mapping_sha256'):
        restored[key]=original[key]
    for relative,row in original['files'].items():restored['files'][relative]['source']=row['source']
    assert restored==original
    new_worker=old_worker
    replacements={
        'STARTUP':(original['baseline_startup_sha256'],mapping['startup_sha256']),
        'SOURCE_MANIFEST':(original['baseline_source_manifest_sha256'],mapping['source_manifest_sha256']),
        'MAPPING':(original['baseline_mapping_sha256'],sha(map_raw)),
    }
    for name,(before,after) in replacements.items():
        anchor=(name+'='+repr(before)).encode()
        assert new_worker.count(anchor)==1
        new_worker=new_worker.replace(anchor,(name+'='+repr(after)).encode(),1)
    old_tree=ast.parse(old_worker.decode());new_tree=ast.parse(new_worker.decode());tree=copy.deepcopy(new_tree)
    for node in tree.body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in replacements:
            key=node.targets[0].id
            assert isinstance(node.value,ast.Constant) and node.value.value==replacements[key][1]
            node.value.value=replacements[key][0]
    assert dump(tree)==dump(old_tree)
    restored_worker=new_worker
    for name,(before,after) in replacements.items():restored_worker=restored_worker.replace((name+'='+repr(after)).encode(),(name+'='+repr(before)).encode(),1)
    assert restored_worker==old_worker
    write(D/'arm_public_worker.py',new_worker)
    write(D/'source_mapping.v90.json',map_raw)
    write(D/'SOURCE_MANIFEST.json',(json.dumps(candidate,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    write(D/'THREE_WAY_MERGE_PROOF.json',(OLD/'THREE_WAY_MERGE_PROOF.json').read_bytes())
    proof=dict(schema='aura.m03-v90.metadata-only-rebind.v1',status='STAGING_ONLY_NOT_EXECUTED_ON_BOARD',
        old_worker_sha256=sha(old_worker),new_worker_sha256=sha(new_worker),
        only_worker_constants_changed=list(replacements),worker_AST_and_bytes_restored_after_reverting_constants=True,
        old_candidate_manifest_sha256=sha(prior_raw),new_candidate_manifest_sha256=sha((D/'SOURCE_MANIFEST.json').read_bytes()),
        candidate_JSON_restored_after_reverting_baseline_and_path_metadata=True,product_sources=product_proof,
        root_UI_close_required=False,hardware_stop_or_pause_or_mic_off_gate_added=False,
        why_UI_may_stay_visible='No real UI/device/model/private DB access. Synthetic Store factory skips production locks; in-process fake GUI is separate from live UI. Slot is only a root coordination label.',
        original_r2_or_newboot_or_production_modified=False)
    write(D/'REBIND_PROOF.json',(json.dumps(proof,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    # A small local source snapshot validates the new baseline binding only.
    changes=json.loads((REPAIR/'release_v18_minor_ui_candidate/HANDOFF.json').read_bytes())['exact_product_sources']
    direct={relative:Path(row['local_source']) for relative,row in changes.items()}
    configs={'config/character_profile.local.json','config/persona.xuefei.candidate.json',
             'config/yuki_pair.formal.json','config/yuki_accepted_prompt.baseline.txt'}
    wanted={p:s for p,s in mapping['component_pins'].items() if p.endswith('.py') or p in configs}
    for relative,digest in wanted.items():
        choices=([direct[relative]] if relative in direct else [])+[OLD/'public_runtime_newboot'/relative]
        for path in choices:
            if path.is_file() and not path.is_symlink() and sha(path.read_bytes())==digest:
                write(D/'public_runtime_v90'/relative,path.read_bytes());break
        else:raise ValueError('Missing exact public v90 source:'+relative)
    write(D/'PUBLIC_SNAPSHOT.json',(json.dumps(dict(public_files=len(wanted),copied_weights_environments_or_databases=False),indent=2)+'\n').encode())
    print(json.dumps(dict(status=proof['status'],candidate_manifest_sha256=proof['new_candidate_manifest_sha256'],
        worker_sha256=proof['new_worker_sha256'],public_files=len(wanted),product_bytes_changed=False)))


if __name__=='__main__':main()
