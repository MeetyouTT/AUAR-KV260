"""Read-only AST/payload/layout review; never imports the board helper."""
import ast
import argparse
import base64
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path('/home/ghmd/aura-post-power-20261022')
HELPER = Path('/home/ghmd/aura-identity-dpu-check-20261018/board_postpower_combined_live_20261022.py')
BASE = Path('/home/ghmd/aura-identity-dpu-check-20261018/board_thread_switch_live_20261022.py')
CANDIDATE = Path('/home/ghmd/aura-yunet-retry-light-20261022')

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def finalizer(tree):
    main = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    guarded = next(n for n in main.body if isinstance(n,ast.Try) and n.finalbody)
    return ast.dump(ast.Module(body=guarded.finalbody,type_ignores=[]))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--helper',type=Path,default=HELPER)
    helper=parser.parse_args().helper
    raw = helper.read_text(); tree = ast.parse(raw)
    constants = {}
    for node in tree.body:
        if (isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name)
                and node.targets[0].id in ('RETRY_PAYLOAD','RETRY_HASHES','FAKE_TEST_WORKER','RETRY_WRAPPER','RETRY_WRAPPER_SHA')):
            constants[node.targets[0].id] = ast.literal_eval(node.value)
    payload = {}
    for name, encoded in constants['RETRY_PAYLOAD'].items():
        data = gzip.decompress(base64.b64decode(encoded))
        assert hashlib.sha256(data).hexdigest()==constants['RETRY_HASHES'][name]
        assert (CANDIDATE/name).read_bytes()==data
        ast.parse(data)
        payload[name] = {'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
    wrapper = base64.b64decode(constants['RETRY_WRAPPER'])
    assert hashlib.sha256(wrapper).hexdigest()==constants['RETRY_WRAPPER_SHA']
    assert finalizer(tree)==finalizer(ast.parse(BASE.read_text()))
    assert "checked_result['run']==82" in raw
    assert raw.index("checked_result['run']==82") < raw.index("service('stop','aura-camera-ui.service')")
    assert "slot_retry=True,freshness_metrics=True" in raw
    assert 'AURA_EXPERIMENT_GIL_MS=1' in raw
    assert "startup['actual_start_seconds']==.001 and startup['previous_seconds']==.005" in raw
    worker = constants['FAKE_TEST_WORKER']
    assert "pattern='test_*.py'" in worker
    cost = json.loads((ROOT/'light2-board-result.json').read_text())
    assert cost['passed'] and cost['assessment']['passed']
    assert all(cost['benchmark_report']['source_sha256'][name]==value
        for name,value in constants['RETRY_HASHES'].items() if name.startswith('candidate/aura/'))
    direct_path_tests = []
    for name in ('tests/test_light.py','tests/test_service.py'):
        text=gzip.decompress(base64.b64decode(constants['RETRY_PAYLOAD'][name])).decode()
        if "ROOT/'candidate/aura/" in text or "ROOT / 'candidate/aura/" in text:direct_path_tests.append(name)
    mirror = any(isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='fixture' for t in n.targets)
        and isinstance(n.value,ast.BinOp) and isinstance(n.value.op,ast.Div)
        and isinstance(n.value.left,ast.Name) and n.value.left.id=='folder'
        and isinstance(n.value.right,ast.Name) and n.value.right.id=='name' for n in ast.walk(tree))
    mirror = mirror and 'assert digest(fixture)==expected' in raw
    block = bool(direct_path_tests) and not mirror
    report = {'schema':'aura-combined-helper-structure-review-1','reviewed_utc':datetime.now(timezone.utc).isoformat(),
        'helper':str(helper),'helper_sha256':sha(helper),'builder_sha256':sha(ROOT/'build_combined_live.py'),
        'review_passed':not block,'allow_launch':not block,'read_only':True,'board_operations':0,
        'payload':payload,'restore_finalizer_ast_identical_to_a439':True,
        'fake82_gate_precedes_service_stop':True,'actual_cost_four_source_pins_match':True,
        'fake82_direct_path_fixture_mirrored':mirror,
        'native_failure_count_semantics':'Payload runtime equals independently reviewed e3b2: only pre_execute AdmissionCancelled has native_not_submitted; API/status failures do not increment withdrawn_after_slot. Helper requires absolute native_failed == withdrawn and diagnostic_errors == 0.',
        'blocking_findings':[{'id':'FAKE82_DIRECT_PATH_LAYOUT','files':direct_path_tests,
            'actual_source_root':'folder/aura','test_direct_source_root':'folder/candidate/aura',
            'baseline_root':'folder/baseline/aura (correct)',
            'impact':'Fake suite fails safely before production service mutation; bootstrap env cannot fix direct pathlib loads.'}] if block else [],
        'recommendations':[] if mirror else ['At runtime compare all four merged source SHA against measured cost report, not only observer module.',
            'For freshness acceptance reject invalid_source_ages/source_clock_pairs_rejected/counter_saturation; do not call missing gap samples proof of zero gap.'],
        'test_scope':'Static AST, payload SHA/bytes/syntax and local saved cost evidence only. No helper/build execution, fake82 rerun or board actions.'}
    target=ROOT/('review/combined-helper-v3-structure-review.json' if '_v3_' in helper.name else 'review/combined-helper-structure-review.json')
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'review_passed':not block,'allow_launch':not block,'helper_sha256':sha(helper),
        'payload_files':len(payload),'blocking_findings':len(report['blocking_findings']),'report':str(target),'report_sha256':sha(target)}))

if __name__=='__main__':main()
