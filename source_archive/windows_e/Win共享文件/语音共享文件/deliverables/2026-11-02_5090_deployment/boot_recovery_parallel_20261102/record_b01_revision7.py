"""Seal the already-executed eight B01 cases; never run old suites or devices."""
import ast
import copy
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
PRIOR = HERE / 'validation/r6_before_b01'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def recovery_class(tree):
    return next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Recovery')


def main():
    snapshot = json.loads((PRIOR / 'SNAPSHOT.json').read_bytes())
    review_path = PRIOR / 'BOOT_CANDIDATE_FIX_RECHECK_R6.json'
    assert sha(review_path.read_bytes()) == snapshot['frozen_review']['sha256']
    review = json.loads(review_path.read_bytes())
    old_raw, new_raw = (PRIOR / 'candidate/boot_recovery.py').read_bytes(), (HERE / 'candidate/boot_recovery.py').read_bytes()
    old_tree, new_tree = (ast.parse(raw, feature_version=(3, 9)) for raw in (old_raw, new_raw))
    old_methods = {node.name: node for node in recovery_class(old_tree).body if isinstance(node, ast.FunctionDef)}
    new_methods = {node.name: node for node in recovery_class(new_tree).body if isinstance(node, ast.FunctionDef)}
    assert old_methods.keys() == new_methods.keys()
    changed = [name for name in old_methods if ast.dump(old_methods[name]) != ast.dump(new_methods[name])]
    assert changed == ['quiet'], changed
    normalized = copy.deepcopy(old_tree)
    body = recovery_class(normalized).body
    body[body.index(next(node for node in body if isinstance(node, ast.FunctionDef) and node.name == 'quiet'))] = copy.deepcopy(new_methods['quiet'])
    assert ast.dump(normalized) == ast.dump(new_tree), 'Change outside Recovery.quiet'
    current_candidate = {p.relative_to(HERE).as_posix(): sha(p.read_bytes())
                         for p in sorted((HERE / 'candidate').rglob('*')) if p.is_file()}
    assert set(current_candidate) == set(snapshot['source_sha256'])
    changed_files = [path for path, pin in snapshot['source_sha256'].items() if current_candidate[path] != pin]
    assert changed_files == ['candidate/boot_recovery.py'], changed_files
    assert sha(old_raw) == review['boot_sha256']
    assert current_candidate['candidate/recovery_rules.py'] == review['rules_sha256']

    before_path, after_path = (HERE / ('validation/b01_r7_' + suffix + '.log') for suffix in ('before_fix', 'after_fix'))
    before, after = before_path.read_text(encoding='utf-8'), after_path.read_text(encoding='utf-8')
    assert 'Hold not raised' in before and 'FAILED (failures=1)' in before and 'errors=' not in before
    cases = [klass + '.' + name for name, klass in re.findall(r'^(test_\w+) \(([^)]+)\) \.\.\. ok$', after, re.MULTILINE)]
    assert len(cases) == 8 and len(set(cases)) == 8 and re.search(r'^Ran 8 tests in ', after, re.MULTILINE)
    assert after.rstrip().endswith('\nOK') and 'FAILED' not in after
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    prior_validation = PRIOR / 'validation/LOCAL_VALIDATION.json'
    prior_receipt = json.loads(prior_validation.read_bytes())
    assert prior_receipt['tests_run'] == 50
    previous = dict(path=prior_validation.relative_to(HERE).as_posix(), sha256=sha(prior_validation.read_bytes()),
                    tests_run=50, scope='Historical R6 only; not rerun or applied to R7 hashes')
    diff_path = HERE / 'review/B01_R7_SOURCE.diff'
    diff_path.write_text(''.join(difflib.unified_diff(old_raw.decode('utf-8').splitlines(keepends=True),
        new_raw.decode('utf-8').splitlines(keepends=True), fromfile='R6/candidate/boot_recovery.py',
        tofile='R7/candidate/boot_recovery.py')), encoding='utf-8')
    retained = {name: dict(status=value['status'], evidence='Unchanged source/AST relative to CPU frozen R6; no new execution claimed')
                for name, value in review['items'].items() if name != 'B01'}
    change_path = 'review/B01_R7_CHANGE_RECEIPT.json'
    change = dict(schema='aura-boot-b01-minimal-change-r7-1', updated_utc=timestamp,
                  status='B01_LOCAL_REPAIR_TARGETED_PASS_AWAITING_CPU_NEW_HASH_RECHECK',
                  scope='Only queued own platform-action classification, including original Python ID_STOP_ONLY',
                  cpu_r6_review=dict(original_path=snapshot['frozen_review']['path'], local_copy=review_path.relative_to(HERE).as_posix(),
                                     sha256=sha(review_path.read_bytes()), verdict=review['verdict']),
                  prior_boot_sha256=sha(old_raw), boot_sha256=sha(new_raw), rules_sha256=current_candidate['candidate/recovery_rules.py'],
                  changed_candidate_files=changed_files, changed_method='Recovery.quiet',
                  minimal_diff=dict(path=diff_path.relative_to(HERE).as_posix(), sha256=sha(diff_path.read_bytes())),
                  unchanged_candidate_sha256={path: pin for path, pin in current_candidate.items() if path not in changed_files},
                  unchanged_recovery_methods={name: sha(ast.dump(node).encode()) for name, node in new_methods.items() if name != 'quiet'},
                  outside_quiet_ast_equal=True, once_ast_equal=True, observe_job_ast_equal=True,
                  other_r6_findings_retained=retained,
                  commit_rollback_gap_fix='Outside quiet AST and manage_installation.py bytes unchanged; retain R6 review, no new L01 test claimed',
                  queue_policy='Every aura-boot-wide-* queued action blocks advancement, even with MainPID=0; original owned running prepare helper and unrelated jobs retain prior policy',
                  same_action_policy='Existing intent binds boot/contract/startup/daemon/argv/unit; observe_job uses allow_submit=False and pinned InvocationID; no resubmission',
                  before_fix=dict(log=before_path.relative_to(HERE).as_posix(), sha256=sha(before_path.read_bytes()),
                                  tests_run=1, expected_failures=1, errors=0, reason='Exact queued original Python IDSTOP was admitted instead of HOLD'),
                  after_fix=dict(receipt='validation/LOCAL_VALIDATION.json', log=after_path.relative_to(HERE).as_posix(),
                                 log_sha256=sha(after_path.read_bytes()), tests_run=8, failed=0, errors=0, selected_case_ids=cases),
                  previous_50_validation=previous, previous_50_suite_rerun=False, baseline_65_suite_rerun=False,
                  cpu_recheck_request=dict(boot_sha256=sha(new_raw), rules_sha256=current_candidate['candidate/recovery_rules.py'],
                                          target='B01 exact queued Python IDSTOP plus bound same-job observation; retain B02-B05/L01 R6 results',
                                          independent_approval_for_new_hash=False),
                  board_calls=0, original_Native_validators_executed=False, activation_supplied=False,
                  ready_to_execute=False, deployed=False, cold_boot_accepted=False)
    write_json(HERE / change_path, change)
    files = [p for p in (HERE / 'candidate').rglob('*') if p.is_file()]
    files += [HERE / rel for rel in ('tests/test_b01_r7_queued_idstop.py', 'tests/test_boot_recovery.py',
                                   'tests/test_review_job_queue.py', 'record_b01_revision7.py', 'build_review_package.py')]
    evidence = [before_path.relative_to(HERE).as_posix(), review_path.relative_to(HERE).as_posix(),
                'validation/r6_before_b01/SNAPSHOT.json', previous['path'],
                'validation/r6_before_b01/validation/repair_final_revision3.log',
                'validation/r6_before_b01/candidate/boot_recovery.py',
                'validation/r6_before_b01/candidate/recovery_rules.py']
    receipt = dict(schema='aura-boot-recovery-b01-targeted-r7-1', revision='R7_B01_ONLY', updated_utc=timestamp,
                   status='PASS_OFFLINE_TARGETED_REVISION', tests_run=8, failed=0, errors=0, skipped=0,
                   scope='Only R6 B01 queued own actions and bound IDSTOP observation using public/synthetic metadata',
                   execution='Python unittest ran only tests/test_b01_r7_queued_idstop.py (two classes, eight cases); this recorder does not rerun tests',
                   rerun_command='python -B -m unittest test_b01_r7_queued_idstop -v (working directory: tests)',
                   selected_case_ids=cases, log=after_path.relative_to(HERE).as_posix(), log_sha256=sha(after_path.read_bytes()),
                   source_sha256={p.relative_to(HERE).as_posix(): sha(p.read_bytes()) for p in sorted(files)},
                   change_receipt=change_path, supporting_evidence=evidence,
                   previous_50_validation=previous, previous_50_suite_rerun=False,
                   baseline_validation=prior_receipt['baseline_validation'], baseline_65_suite_rerun=False,
                   board_calls=0, hardware_or_model_loads=0, real_databases_opened=0,
                   original_Native_validators_executed=False,
                   limitations=['B02-B05 and L01 retain prior R6 static/source evidence, not new dynamic test counts',
                                'CPU independent recheck of R7 hashes remains pending',
                                'Fresh target systemd/loader/owner/history and cold-boot evidence remains required'],
                   deployed=False, ready_to_execute=False, cold_boot_accepted=False)
    write_json(HERE / 'validation/LOCAL_VALIDATION.json', receipt)
    print(json.dumps(dict(status=receipt['status'], tests_run=8, boot_sha256=sha(new_raw),
                          rules_sha256=current_candidate['candidate/recovery_rules.py'], changed_method='Recovery.quiet',
                          outside_quiet_ast_equal=True, old_50_or_65_suite_rerun=False)))


if __name__ == '__main__':
    main()
