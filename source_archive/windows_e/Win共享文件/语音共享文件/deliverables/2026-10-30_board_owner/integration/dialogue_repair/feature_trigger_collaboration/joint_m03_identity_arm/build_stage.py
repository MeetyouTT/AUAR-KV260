"""Prepare a public-only five-source ARM stage against the actual v19 spec."""
import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
H = D.parent
REPAIR = H.parent
SPEC = REPAIR/'release_v19_stability_candidate/applied_spec_1793500668831017100.json'
SPEC_SHA = '49ffbc82a4b9543d92234f055fce8af055de29764ca6f688ae0a36fe7a35a904'
STARTUP = 'de7772b898378d2263b0809d18c095a60585a672690371d2f072b2e04c2f574f'


def sha(raw):return hashlib.sha256(raw).hexdigest()
def dump(path,value):path.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def need(ok,code):
    if not ok:raise ValueError(code)
def replace(text,old,new):
    need(text.count(old)==1,'worker_edit_not_unique:'+old[:80])
    return text.replace(old,new)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mapping',type=Path,required=True)
    parser.add_argument('--composed-manifest',type=Path,default=H/'identity_cooperation_v90/COMBINED_M03_SOURCE_MANIFEST.json')
    parser.add_argument('--stage',type=Path,default=D/'stage_v19')
    args=parser.parse_args();stage=args.stage.resolve()
    need(not stage.exists(),'fresh_stage_required')
    spec_raw=SPEC.read_bytes();need(sha(spec_raw)==SPEC_SHA,'actual_spec_changed')
    spec=json.loads(spec_raw);mapping_raw=args.mapping.read_bytes();mapping=json.loads(mapping_raw)
    need(mapping['startup_sha256']==spec['startup_sha256']==STARTUP,'not_actual_v19')
    need(mapping['source_manifest_sha256']==spec['source_manifest_sha256'],'source_manifest_changed')
    need(mapping['boot_id']==spec['boot_id'] and len(mapping['component_pins'])==379,'boot_or_components_changed')
    need(mapping['component_pins']==spec['component_sha256'],'mapping_not_actual_spec_pins')
    combined=args.composed_manifest
    combined_manifest=json.loads(combined.read_bytes())
    need(len(combined_manifest['files'])==5,'five_sources_required')
    stage.mkdir(parents=True)
    files={}
    def copy(source,relative):
        raw=source.read_bytes();target=stage/relative
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        files[relative]=dict(source=str(source),sha256=sha(raw),bytes=len(raw))
        return raw
    source_files={}
    for relative,row in combined_manifest['files'].items():
        need(row['before_sha256']==mapping['component_pins'].get(relative),'five_source_before_changed:'+relative)
        raw=copy(Path(row['source']),'after/'+relative)
        need(sha(raw)==row['sha256'],'frozen_composed_source_changed:'+relative)
        source_files[relative]=dict(before_sha256=row['before_sha256'],sha256=sha(raw),bytes=len(raw))
    copy(args.mapping,'source_mapping.v19.json');copy(SPEC,'applied_spec.v19.json')
    originals={
        'tree/a/b/c/d/review_m03_win_inference/test_delete_boundaries.py':H/'review_m03_win_inference/test_delete_boundaries.py',
        'test_independent_boundaries.py':H/'review_m03_r2_root_agent/test_independent_boundaries.py',
        'public_worker.py':H/'board_integration_v17/worker.py',
        'identity_tests.py':H/'identity_cooperation_v90/test_identity_cooperation.py',
        'identity_independent.py':REPAIR/'performance_review_newboot/identity_cooperation_review/test_independent_counterexamples.py',
        'speaker_fixtures.py':H.parents[4]/'aura/tests/framework/test_board_speaker_business.py',
        'face_fixtures.py':H.parents[4]/'aura/tests/framework/test_simple_enrollment.py',
        'identity_stdlib_cases.py':D/'identity_stdlib_cases.py'}
    for relative,source in originals.items():copy(source,relative)
    dump(stage/'SOURCE_MANIFEST.json',dict(schema='aura.joint-m03-identity.sources.v1',
        status='PUBLIC_ARM_TEST_OVERLAY_NOT_DEPLOYMENT',baseline_startup_sha256=STARTUP,
        baseline_source_manifest_sha256=mapping['source_manifest_sha256'],baseline_mapping_sha256=sha(mapping_raw),
        baseline_applied_spec_sha256=SPEC_SHA,files=source_files,
        identity_frozen_manifest_sha256='6db50db1d9c211dc9935465b8ef5038d852c552e2cc288b8352cbb9febe8b7c0',
        identity_root_review_sha256='9911b8cedb32a15881f75907fe457733c32e135629dc7cb7ab4342661b9bb73c',
        M03_frozen_manifest_sha256='cd462e0e26e5d41291afea66b8e598b7fcece0560ebe56257b2f79a132e7f820'))
    candidate_raw=(stage/'SOURCE_MANIFEST.json').read_bytes()
    files['SOURCE_MANIFEST.json']=dict(source=str(stage/'SOURCE_MANIFEST.json'),sha256=sha(candidate_raw),bytes=len(candidate_raw))

    old_path=H/'candidate_m03_v90_stage/arm_public_worker.py';old_raw=old_path.read_bytes()
    need(sha(old_raw)=='fdd4fcc2a91d60ccd23040931d2633c3a08775c3a77213a21e4ee6c7688e9e68','frozen_M03_worker_changed')
    worker=old_raw.decode('utf-8')
    worker=replace(worker,"STARTUP='90f6c6c40f6501362aa77483235a7260a212de6e3357615311bdaa5cc193ebbe'",'STARTUP='+repr(STARTUP))
    worker=replace(worker,"SOURCE_MANIFEST='6d03c1d7aa95a9c5615f540606699f67c4ee7a44be1e50dcb2983c6c555e3637'",'SOURCE_MANIFEST='+repr(mapping['source_manifest_sha256']))
    worker=replace(worker,"MAPPING='df6b26927ad60d6d3513429c697d70bd15c84cfdca6d16c5527e9992cb7b04e2'",'MAPPING='+repr(sha(mapping_raw)))
    worker=replace(worker,"FILES={'board/runtime/board_business.py','board/runtime/history_delete.py','tools/production_memory_presentation.py'}",
        'FILES=set('+repr(sorted(source_files))+')')
    constants='\nAPPLIED_SPEC='+repr(SPEC_SHA)+'\nRUN_STATE=None\n'
    for field,path in (('IDENTITY_TESTS','identity_tests.py'),('IDENTITY_INDEPENDENT','identity_independent.py'),
            ('SPEAKER_FIXTURES','speaker_fixtures.py'),('FACE_FIXTURES','face_fixtures.py'),('IDENTITY_ADAPTER','identity_stdlib_cases.py')):
        constants+=field+'='+repr(files[path]['sha256'])+'\n'
    worker=replace(worker,'def sha(raw):return hashlib.sha256(raw).hexdigest()',constants+'\ndef sha(raw):return hashlib.sha256(raw).hexdigest()')
    worker=replace(worker,"    base=args.runtime_root.resolve(strict=True);after=args.candidate_root.resolve(strict=True)",
        "    for path,digest in ((args.applied_spec,APPLIED_SPEC),(args.identity_tests,IDENTITY_TESTS),(args.identity_independent,IDENTITY_INDEPENDENT),(args.speaker_fixtures,SPEAKER_FIXTURES),(args.face_fixtures,FACE_FIXTURES),(args.identity_adapter,IDENTITY_ADAPTER)):\n"
        "        need(not path.is_symlink() and sha(path.read_bytes())==digest,'joint_public_artifact_changed')\n"
        "    applied=json.loads(args.applied_spec.read_bytes())\n"
        "    need(applied['startup_sha256']==STARTUP and applied['source_manifest_sha256']==SOURCE_MANIFEST and applied['component_sha256']==mapping['component_pins'],'actual_v19_spec_mismatch')\n"
        "    base=args.runtime_root.resolve(strict=True);after=args.candidate_root.resolve(strict=True)")
    worker=replace(worker,"'exact_three_file_overlay_required'","'exact_five_file_overlay_required'")
    worker=replace(worker,"'runtime-root','candidate-root','mapping','candidate-manifest','original-review','independent-tests','public-worker','output'",
        "'runtime-root','candidate-root','mapping','candidate-manifest','original-review','independent-tests','public-worker','output','applied-spec','identity-tests','identity-independent','speaker-fixtures','face-fixtures','identity-adapter'")
    worker=replace(worker,'def main():\n    p=', 'def main():\n    global RUN_STATE\n    p=')
    worker=replace(worker,"schema='aura.m03-newboot.public-arm-overlay.v1'","schema='aura.joint-m03-identity.public-arm-overlay.v1'")
    worker=replace(worker,'    save(args.output,result)\n    if args.check_only:return 0','    RUN_STATE=(args.output,result)\n    save(args.output,result)\n    if args.check_only:return 0')
    worker=replace(worker,"        'board.runtime.board_business','board.runtime.history_delete','tools.production_memory_presentation'):",
        "        'board.runtime.board_business','board.runtime.history_delete','tools.production_memory_presentation',\n        'board.runtime.board_speaker_business','tools.provisional_voice'):")
    worker=replace(worker,"        ('tools.production_memory_presentation','tools/production_memory_presentation.py')):",
        "        ('tools.production_memory_presentation','tools/production_memory_presentation.py'),\n        ('board.runtime.board_speaker_business','board/runtime/board_speaker_business.py'),\n        ('tools.provisional_voice','tools/provisional_voice.py')):")
    worker=replace(worker,"    old_temp=tempfile.tempdir;threads=set(threading.enumerate());log=io.StringIO()",
        "    adapter=load_module('joint_public_stdlib_adapter',args.identity_adapter)\n"
        "    identity_suite,adapter_proof=adapter.build_suite(args,public)\n"
        "    suite.addTests(identity_suite);result['identity_adapter']=adapter_proof\n"
        "    need(suite.countTestCases()==67,'joint_case_count_changed')\n"
        "    old_temp=tempfile.tempdir;threads=set(threading.enumerate());log=io.StringIO()")
    worker=replace(worker,"test_framework='stdlib unittest; original4 unchanged + original3 AST with assertRaises/patch adapter + paired smoke'",
        "test_framework='stdlib unittest; M03 original4+3 AST+paired; identity47+independent12 original test-body AST with explicit stdlib fixture adapters'")
    worker=replace(worker,"if __name__=='__main__':raise SystemExit(main())",
        "def entry():\n"
        "    try:return main()\n"
        "    except Exception as exc:\n"
        "        import traceback\n"
        "        if RUN_STATE is not None:\n"
        "            output,result=RUN_STATE;result.update(status='ERROR_BEFORE_TEST_COMPLETION',exception_class=type(exc).__name__)\n"
        "            save(output,result)\n"
        "        traceback.print_exc()\n"
        "        return 1\n\n"
        "if __name__=='__main__':raise SystemExit(entry())")
    ast.parse(worker)
    (stage/'arm_public_worker.py').write_bytes(worker.encode('utf-8'))
    files['arm_public_worker.py']=dict(source=str(stage/'arm_public_worker.py'),sha256=sha(worker.encode()),bytes=len(worker.encode()))
    (stage/'WORKER_REVIEW.diff').write_bytes(''.join(difflib.unified_diff(old_raw.decode().splitlines(keepends=True),worker.splitlines(keepends=True),fromfile='frozen-M03-worker',tofile='joint-67-worker')).encode())

    # Only public saved Python/config files; two v19 overrides replace v90's
    # old versions. No model, binary assets, private DB or environment is copied.
    public_configs={'config/character_profile.local.json','config/persona.xuefei.candidate.json','config/yuki_pair.formal.json','config/yuki_accepted_prompt.baseline.txt'}
    snapshot=stage/'public_runtime_v19';snapshot.mkdir()
    pins={rel:digest for rel,digest in mapping['component_pins'].items() if rel.endswith('.py') or rel in public_configs}
    need(len(pins)==343,'public_source_count_changed')
    for relative,digest in pins.items():
        source=H/'candidate_m03_v90_stage/public_runtime_v90'/relative
        if sha(source.read_bytes())!=digest:
            source=Path(spec['minor_overrides'][relative]['local_source'])
        raw=source.read_bytes();need(sha(raw)==digest,'public_snapshot_source_changed:'+relative)
        target=snapshot/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    dump(stage/'STAGING_MANIFEST.json',dict(schema='aura.joint-m03-identity.public-stage.v1',
        status='PREPARED_LOCAL_REPLAY_PENDING_NOT_DEPLOYED',files=files,source_files=5,
        composition_input_manifest_sha256=sha(combined.read_bytes()),
        case_count=67,actual_v19_applied_spec_sha256=SPEC_SHA,baseline_mapping_sha256=sha(mapping_raw),
        baseline_startup_sha256=STARTUP,baseline_source_manifest_sha256=mapping['source_manifest_sha256'],
        full_live_379_source_checks_required_before_application_imports=True,
        original_review_nested_relative='tree/a/b/c/d/review_m03_win_inference/test_delete_boundaries.py',
        UI_close_required=False,real_listening_or_hardware_control=False,
        root_must_preserve_saved_PAUSED=True,local_snapshot_not_for_board_upload=True))
    print(json.dumps(dict(stage=str(stage),files=len(files),worker_sha256=sha(worker.encode()),candidate_manifest_sha256=sha((stage/'SOURCE_MANIFEST.json').read_bytes()))))


if __name__=='__main__':main()
