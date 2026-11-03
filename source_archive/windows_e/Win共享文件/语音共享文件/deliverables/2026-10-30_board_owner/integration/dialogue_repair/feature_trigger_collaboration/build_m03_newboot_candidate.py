"""Local-only three-way M03 registration merge onto the saved 70a2 baseline.
Original r2, cold-start candidate, review files and production are never edited.
"""
import ast
import copy
import difflib
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
D=H/'candidate_m03_newboot'
R2=H/'candidate_m03_r2'
REPAIR=H.parent
PROJECT=H.parents[4]
MAPPING=REPAIR/'release_v18_newboot_candidate/newboot_evidence/source_mapping.json'


def sha(raw):return hashlib.sha256(raw).hexdigest()
def dump(node):return ast.dump(node,include_attributes=False)
def write(path,raw):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)


def main():
    map_raw=MAPPING.read_bytes();mapping=json.loads(map_raw)
    assert mapping['startup_sha256']=='70a2f7fa5440f2b65004d66d5c4984b664ccc2b60131a0abd9a8351591c8d4e6'
    assert mapping['source_manifest_sha256']=='e105159fea9a71a347b6564ef77d1db23f6596199ed27a5e8684d6b025b5bacb'
    assert mapping['boot_id']=='bebd3e7d-e984-4517-8cbb-211df7f1c6dc' and len(mapping['component_pins'])==379
    r2_raw=(R2/'SOURCE_MANIFEST.json').read_bytes();assert sha(r2_raw)=='b708c78fb75a2f621fdc99363d41342689951665bc8e0053486f44aba79b1bac'
    r2=json.loads(r2_raw)
    review=H/'review_m03_r2_root_agent/REVIEW.json'
    assert sha(review.read_bytes())=='3a3631c1946cdebd8d3284311ebe1f138acac8c400efd7a38bbac1dd4e3fed95'
    decision=json.loads(review.read_bytes())
    assert decision['regression']['passed']==38 and decision['regression']['failed']==0
    for relative,row in r2['files'].items():assert sha((R2/'after'/relative).read_bytes())==row['sha256']
    base=REPAIR/'cold_boot_recovery_candidate/after/board/runtime/board_business.py'
    before=base.read_bytes()
    assert sha(before)==mapping['component_pins']['board/runtime/board_business.py']=='482e250cf42cecd21358f4159a9550e4b384c3c223ee1f367e3c1d796423a198'
    ancestor=(R2/'before/board/runtime/board_business.py').read_bytes()
    newline=b'\r\n' if b'\r\n' in before else b'\n'
    anchor=b'        handlers = dict(extra_handlers or {})'+newline
    addition=newline.join([
        b'        from board.runtime.history_delete import LocalHistoryDelete',
        b"        handlers.setdefault('history_delete_preview', LocalHistoryDelete(self.store, self.timeline, clock=clock, zone=config.timezone))",
    ])+newline
    assert before.count(anchor)==1 and addition not in before
    after=before.replace(anchor,anchor+addition,1)
    assert after.replace(addition,b'',1)==before  # Exact cold factory byte retention.
    prior_ast=ast.parse(before.decode('utf-8'));merged_ast=ast.parse(after.decode('utf-8'))
    restored=copy.deepcopy(merged_ast)
    runtime=next(n for n in restored.body if isinstance(n,ast.ClassDef) and n.name=='BoardBusinessRuntime')
    init=next(n for n in runtime.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
    index=next(i for i,n in enumerate(init.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='handlers' for t in n.targets))
    assert isinstance(init.body[index+1],ast.ImportFrom) and init.body[index+1].module=='board.runtime.history_delete'
    registration=init.body[index+2]
    assert isinstance(registration,ast.Expr) and isinstance(registration.value,ast.Call)
    assert isinstance(registration.value.args[0],ast.Constant) and registration.value.args[0].value=='history_delete_preview'
    del init.body[index+1:index+3]
    assert dump(restored)==dump(prior_ast)
    factory_before=next(n for n in prior_ast.body if isinstance(n,ast.FunctionDef) and n.name=='create_board_business_runtime')
    factory_after=next(n for n in merged_ast.body if isinstance(n,ast.FunctionDef) and n.name=='create_board_business_runtime')
    assert dump(factory_before)==dump(factory_after)
    files={}
    for relative,old,new in [
        ('board/runtime/board_business.py',before,after),
        ('board/runtime/history_delete.py',None,(R2/'after/board/runtime/history_delete.py').read_bytes()),
        ('tools/production_memory_presentation.py',(R2/'before/tools/production_memory_presentation.py').read_bytes(),
            (R2/'after/tools/production_memory_presentation.py').read_bytes()),
    ]:
        assert mapping['component_pins'].get(relative)==(sha(old) if old is not None else None)
        ast.parse(new.decode('utf-8'),feature_version=(3,9))
        write(D/'after'/relative,new)
        if old is not None:write(D/'before'/relative,old)
        files[relative]=dict(before_sha256=sha(old) if old is not None else None,sha256=sha(new),bytes=len(new),source=str(D/'after'/relative))
        patch=''.join(difflib.unified_diff((old or b'').decode().replace('\r\n','\n').splitlines(True),
            new.decode().replace('\r\n','\n').splitlines(True),fromfile='before/'+relative,tofile='after/'+relative))
        write(D/(Path(relative).name+'.patch'),patch.encode('utf-8'))
    proof=dict(schema='aura.m03-newboot.three-way-proof.v1',
        common_ancestor_sha256=sha(ancestor),reviewed_r2_board_business_sha256=r2['files']['board/runtime/board_business.py']['sha256'],
        cold_boot_before_sha256=sha(before),merged_sha256=sha(after),
        only_added_import_and_one_registration=True,removing_exact_added_bytes_restores_cold_source=True,
        complete_AST_restored_after_removing_exact_two_added_statements=True,
        factory_AST_identical=True,factory_AST_sha256=sha(dump(factory_before).encode()),
        handler_and_presentation_exact_independently_reviewed_r2_bytes=True,
        original_cold_boot_source_modified=False,original_r2_modified=False)
    write(D/'THREE_WAY_MERGE_PROOF.json',(json.dumps(proof,ensure_ascii=False,indent=2)+'\n').encode())
    write(D/'source_mapping.newboot.json',map_raw)
    refs=[R2/'SOURCE_MANIFEST.json',R2/'HANDOFF.json',review,H/'review_m03_r2_root_agent/test_independent_boundaries.py',
        H/'review_m03_win_inference/test_delete_boundaries.py']
    reference_pins={}
    for path in refs:
        relative=path.relative_to(H);write(D/'frozen_references'/relative,path.read_bytes())
        reference_pins[relative.as_posix()]=sha(path.read_bytes())
    # Exact public Python/config snapshot, never model resources or environments.
    newboot_handoff=json.loads((REPAIR/'release_v18_newboot_candidate/HANDOFF.json').read_bytes())
    direct={p:Path(v['local_source']) for p,v in newboot_handoff['exact_source_overrides'].items()}
    roots=[R2/'public_v18_snapshot',H/'candidate_h01/after',H/'candidate_speaker_close/after',
           REPAIR/'memory_observation_candidate_r2/after',H/'board_integration_v17/local_runtime_v17',PROJECT/'aura']
    public_configs={'config/character_profile.local.json','config/persona.xuefei.candidate.json',
                   'config/yuki_pair.formal.json','config/yuki_accepted_prompt.baseline.txt'}
    wanted={p:s for p,s in mapping['component_pins'].items() if p.endswith('.py') or p in public_configs}
    copied={}
    for relative,digest in wanted.items():
        options=([direct[relative]] if relative in direct else [])+[root/relative for root in roots]
        for path in options:
            if path.is_file() and not path.is_symlink() and sha(path.read_bytes())==digest:
                write(D/'public_runtime_newboot'/relative,path.read_bytes());copied[relative]=str(path);break
        else:raise ValueError('Missing exact public newboot source: '+relative)
    value=dict(schema='aura.m03-newboot.candidate-source.v1',status='LOCAL_PREPARED_NOT_DEPLOYED',
        baseline_startup_sha256=mapping['startup_sha256'],baseline_source_manifest_sha256=mapping['source_manifest_sha256'],
        baseline_mapping_sha256=sha(map_raw),baseline_boot_id=mapping['boot_id'],component_count=379,
        baseline_configuration_sha256=mapping['configuration_sha256'],files=files,
        predecessor_r2_manifest_sha256=sha(r2_raw),independent_r2_review_sha256=sha(review.read_bytes()),
        frozen_reference_sha256=reference_pins,merge_proof_sha256=sha((D/'THREE_WAY_MERGE_PROOF.json').read_bytes()),
        production_source_or_private_store_model_or_hardware_accessed=False)
    write(D/'SOURCE_MANIFEST.json',(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
    write(D/'PUBLIC_SNAPSHOT.json',(json.dumps(dict(files=len(copied),source_paths=copied,
        weights_environments_or_private_databases_copied=False),ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps(dict(status=value['status'],public_files=len(copied),source_sha256={r:v['sha256'] for r,v in files.items()})))


if __name__=='__main__':main()
