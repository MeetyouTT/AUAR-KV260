"""Freeze deliverable metadata locally; no services/models/devices accessed."""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from build_candidate import AURA, SOURCES


if __name__=='__main__':
    log=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_first_wait.py')
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    (ROOT/'OFFLINE_TESTS.log').write_text(log.getvalue(),encoding='utf-8')
    if not result.wasSuccessful():
        print(json.dumps({'status':'OFFLINE_TEST_FAILURE','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors)}))
        raise SystemExit(1)
    deps={target:hashlib.sha256((AURA/target).read_bytes()).hexdigest() for target in (
        'tools/dialogue_host_ollama.py','tools/native_grammar.py','common/gpu_coordination.py',
        'config/gpu_runtime.local.json','config/character_profile.local.json','common/reply_quality.py')}
    (ROOT/'BENCH_DEPENDENCY_PINS.json').write_text(json.dumps(deps,indent=2)+'\n',encoding='utf-8')
    targets={
        'tools/model_inference_host.py':'after/tools/model_inference_host.py',
        'common/model_inference_wire.py':'after/common/model_inference_wire.py',
        'common/inference_output_contract.py':'candidate/inference_output_contract.py',
        'board/runtime/compact_request_adapter.py':'candidate/compact_request_adapter.py',
        'benchmark':'root_abba_benchmark.py','benchmark_dependencies':'BENCH_DEPENDENCY_PINS.json',
        'review_patch':'output_contract_review.patch','tests':'tests/test_first_wait.py',
        'builder':'build_candidate.py'}
    artifacts={target:{'file':name,'sha256':hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),
                       'bytes':(ROOT/name).stat().st_size} for target,name in targets.items()}
    value={'status':'FROZEN_CORE_AND_FOUR_CALL_ABBA_READY_ROOT_EXECUTION_ONLY',
        'frozen_utc':datetime.now(timezone.utc).isoformat(),'artifacts':artifacts,
        'before':{key:sha for key,sha in SOURCES.items() if key!='board/runtime/board_memory_policy.py'},
        'exact_before_files':'reference/',
        'offline_tests':{'passed':result.testsRun,'failures':0,'errors':0,'evidence':'OFFLINE_TESTS.log',
                         'model_requests':0,'device_operations':0,'production_database_accesses':0},
        'first_pilot':{'order':'ABBA','complete_model_generations':4,'extra_warmups':0,
            'family':'canonical_schema','A':'generic json','B':'strict canonical schema',
            'identical_prompt_seed_budget':True,'seed':8701,'num_predict':120,'num_ctx':2048,
            'raw_reply_prompt_or_pcm_saved_by_script':False,'tts_requests':0},
        'root_command':'python -B root_abba_benchmark.py --execute --root-permit <fresh-root-proof.json> --family canonical_schema --cycles 1 --seed 8701',
        'root_proof':'Root alone reads closed board UI/writer, model host idle, sole existing runner, logging policy and unchanged residency; example booleans are NOT evidence',
        'prefix_order_warning':{'status':'SEPARATE_HISTORICAL_REFERENCE_ONLY_DO_NOT_INSTALL_FULL_FILE',
            'old_before':'9af4a5bfc4a039db55d8e46e08ce994e04091a0653919886fb04c23f39f94d54',
            'root_reported_v13_current':'48c7499fe5371c822738f2f42029a6b82fe2aa71c503fc0accd9fa15549188a5',
            'requires_fresh_replay_on_v13_or_v14_and_memory_owner_review':True},
        'no_actual_speedup_claim':True,'no_production_publication':True,
        'frozen_files_will_not_be_edited_in_this_revision':True}
    (ROOT/'FREEZE_HANDOFF.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    status=json.loads((ROOT/'STATUS.json').read_text(encoding='utf-8'))
    status.update(status=value['status'],updated_utc=value['frozen_utc'],handoff='FREEZE_HANDOFF.json',
        offline_tests=value['offline_tests'],benchmark='root_abba_benchmark.py',
        next='Root executes exactly four public canonical-schema ABBA calls after its fresh exclusive-window readback; subsequent changes use a separate revision')
    (ROOT/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':value['status'],'tests':result.testsRun,
        'benchmark_sha256':artifacts['benchmark']['sha256'],'core_host_sha256':artifacts['tools/model_inference_host.py']['sha256'],
        'core_wire_sha256':artifacts['common/model_inference_wire.py']['sha256']}))
