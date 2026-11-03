from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'first_wait_candidate'


if __name__=='__main__':
    frozen=json.loads((BASE/'FREEZE_HANDOFF.json').read_text(encoding='utf-8'))
    for entry in frozen['artifacts'].values():
        if hashlib.sha256((BASE/entry['file']).read_bytes()).hexdigest()!=entry['sha256']:
            raise ValueError('frozen_v1_artifact_changed')
    log=io.StringIO()
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(
        unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_direct.py'))
    (ROOT/'OFFLINE_TESTS.log').write_text(log.getvalue(),encoding='utf-8')
    if not result.wasSuccessful():
        print(json.dumps({'status':'FAIL','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors)}))
        raise SystemExit(1)
    files=('root_direct_name_abba.py','name_semantics.py','direct_logic.py','direct_name_runner_review.patch',
           'build_direct_runner.py','tests/test_direct.py','交接说明.txt')
    value={'status':'FROZEN_DIRECT_NAME_ABBA_READY_ROOT_EXECUTION_ONLY',
        'frozen_utc':datetime.now(timezone.utc).isoformat(),
        'files':{name:{'sha256':hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),'bytes':(ROOT/name).stat().st_size} for name in files},
        'immutable_v1_all_manifest_artifacts_match':True,
        'base_runner_sha256':'e5d1f4fe85e2f40ee52cdf52c66e86c0b7e12c0deff47f94525d5a1382d28a36',
        'offline_tests':{'passed':result.testsRun,'failures':0,'errors':0,'model_requests':0,'production_database_accesses':0,'device_operations':0},
        'study':{'question_code':'SELF_NAME_DIRECT','generations':4,'order':'ABBA','seed':8701,'num_predict':120,
                 'num_ctx':2048,'warmups':0,'A':'canonical generic json','B':'compact ABC strict schema',
                 'same_question_seed_budget_sampling':True,'prompt_field_contract_names_differ':True,
                 'frozen_safety_guard_ast_unchanged':True,'full_reply_validation_before_delivery':True},
        'command':'python -B root_direct_name_abba.py --execute --root-permit <fresh-root-readback-permit.json> --seed 8701',
        'results_directory':'benchmark_runs/',
        'raw_reply_prompt_hash_or_pcm_saved':False,
        'root_reads_permit_and_unique_idle_model_state':True,
        'actual_model_or_performance_test_performed_here':False,
        'performance_gain_claimed':False,
        'do_not_apply_review_patch_to_frozen_v1':True,
        'no_further_edits_to_this_revision_after_handoff':True}
    (ROOT/'FREEZE_DIRECT.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    status=json.loads((ROOT/'STATUS.json').read_text(encoding='utf-8'))
    status.update(status=value['status'],updated_utc=value['frozen_utc'],handoff='FREEZE_DIRECT.json',
                  offline_tests=value['offline_tests'],next='Root executes the single direct name ABBA if appropriate; no matrix or production publication here')
    (ROOT/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':value['status'],'tests':result.testsRun,
        'runner_sha256':value['files']['root_direct_name_abba.py']['sha256'],
        'name_semantics_sha256':value['files']['name_semantics.py']['sha256'],
        'frozen_v1_untouched':True}))
