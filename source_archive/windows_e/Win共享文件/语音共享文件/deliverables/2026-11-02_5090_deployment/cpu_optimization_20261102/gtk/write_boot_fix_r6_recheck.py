"""Static-only R6 review over root's frozen byte cut and author evidence."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OPT = HERE.parent
R6 = OPT / 'boot_review_inputs/observed_revision6'
R5 = OPT / 'boot_review_inputs/observed_revision5'
AUTHOR = OPT.parent / 'boot_recovery_parallel_20261102/validation'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': sha(raw), 'bytes': len(raw)}


expected = {
    'boot_recovery.py': 'f1abe1a9ee15192fce5f1d436b782f8eab0841762c61d2205fdc26ef36d35a8f',
    'original_history_gate.py': '9802e2454d9622c32b4d4ab18affb39606dfa57246ca2d3ddd569188239f46d3',
    'manage_installation.py': 'c11c46d2b9af4ce11300514b8ff31baccfaa4bed542616924fe3e99fffb9e241',
    'capture_contract.py': 'bce6d4d1b2f7547827f9f886014297d1483c1eb8a8b99ef6cf04421cd1b5562c',
    'recovery_rules.py': '55bfc4db498be172beb040605dcae351c6f972e0df1371cecb48b7d1034ed268',
}
for name, value in expected.items():
    assert pin(R6 / 'candidate' / name)['sha256'] == value
adapter = OPT / 'camera/validate_fresh_final_history_readonly.py'
assert pin(adapter)['sha256'] == '5ca99d4231c686de0f89dac5792299bec13af517a5c6e2b8f73c4cc66b9285c9'


def top_function(path, name):
    return next(node for node in ast.parse(path.read_bytes()).body if isinstance(node, ast.FunctionDef) and node.name == name)


def recovery_method(root, name):
    klass = next(node for node in ast.parse((root / 'candidate/boot_recovery.py').read_bytes()).body
                 if isinstance(node, ast.ClassDef) and node.name == 'Recovery')
    return next(node for node in klass.body if isinstance(node, ast.FunctionDef) and node.name == name)


execute = top_function(R6 / 'candidate/original_history_gate.py', 'execute_request')
same_boot = next(node for node in execute.body if isinstance(node, ast.If))
calls = [node.func.attr for statement in same_boot.body for node in ast.walk(statement)
         if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
         and isinstance(node.func.value, ast.Name) and node.func.value.id == 'adapter']
assert calls == ['validate_inputs', 'original_modules', 'validate_current', 'validate_chain']
assert ast.dump(recovery_method(R5, 'accepted_live_history')) == ast.dump(recovery_method(R6, 'accepted_live_history'))
assert ast.dump(recovery_method(R5, 'quiet')) == ast.dump(recovery_method(R6, 'quiet'))
signatures = {}
for name in ('validate_inputs', 'validate_current', 'validate_chain'):
    node = top_function(adapter, name)
    signatures[name] = [arg.arg for arg in node.args.args]
assert signatures == {'validate_inputs': ['expected', 'snapshot'],
                      'validate_current': ['expected', 'intent', 'result', 'snapshot', 'protection', 'boot_module'],
                      'validate_chain': ['document', 'history_expected', 'snapshot', 'protection', 'boot_module']}

# Freeze the author's existing result and log, without importing or executing tests.
author_raw = (AUTHOR / 'LOCAL_VALIDATION.json').read_bytes()
author = json.loads(author_raw)
assert author['tests_run'] == 50 and author['failed'] == author['errors'] == 0
for name, value in expected.items():
    assert author['source_sha256']['candidate/' + name] == value
author_log = (AUTHOR / 'repair_final_revision3.log').read_bytes()
assert b'Ran 50 tests' in author_log and b'OK' in author_log
evidence_directory = HERE / 'R6_AUTHOR_EVIDENCE'
evidence_directory.mkdir(exist_ok=False)
for name, raw in (('LOCAL_VALIDATION.json.bin', author_raw), ('repair_final_revision3.log.bin', author_log)):
    with (evidence_directory / name).open('xb') as handle:
        handle.write(raw)

report = {
    'schema': 'aura-boot-fix-r6-same-boot-and-commit-gap-recheck-1',
    'verdict': 'PASS_STATIC_FOR_THE_TWO_REQUESTED_R6_FIXES',
    'scope': 'Only the R5 same-boot inactive-guard timing incompatibility and the active-written/committed-missing rollback gap. Read-only source/AST inspection and author50 evidence attribution. No test, prior counterexample, original validator, Native or device call was executed by this recheck.',
    'snapshot': pin(R6 / 'SNAPSHOT.json'),
    'reviewed_inputs': [pin(R6 / 'candidate' / name) for name in expected] + [pin(adapter)],
    'same_boot_fix': {
        'status': 'PRESTART_INACTIVE_GUARD_CONFLICT_RESOLVED_STATICALLY',
        'locations': {'original_history_gate.py': [54, 55, 56, 57, 58, 59, 61, 62, 63, 64, 65, 66, 67, 68, 69, 75, 76, 77, 78, 79, 80],
                      'boot_recovery.py': [350, 359, 360, 388, 399, 400, 401, 402, 403, 611, 616],
                      'camera/validate_fresh_final_history_readonly.py': [235, 244, 246, 249, 257, 259, 270, 274, 283, 287, 291, 303, 350, 354, 356, 361, 364, 366, 368, 370, 371, 375]},
        'exact_adapter_calls_in_same_boot_branch': calls,
        'original_API_signatures': signatures,
        'finding': 'R6 no longer invokes adapter.main or adapter.guard from same_boot_resume. It first reads the genuine prior complete result by exact pin, binds original schema/status, final pin, source owner, expected input SHA and original reader/history/current-bound flags, and requires the four chain fields to match the full normal-stop expected. It then calls unchanged validate_inputs with the full expected object, original_modules, validate_current with the actual returned stop intent/result, and validate_chain. Original archives must equal the freshly revalidated ordered records; consumed-marker absence and snapshot byte stability remain checked. This avoids asking the old inactive-only service guard to succeed during ExecStartPre.',
        'preserved_checks': [
            'validate_inputs still verifies exact startup/config/manifest pins, current boot and source owner, genuine single normal-stop intent/result and independent pre-stop history source bindings including the5ca alias gates.',
            'validate_current still calls original load_business_checkpoint and _sealed_source, checks current owner/source unit/manifest/monotonic domain, unconsumed final and all original primary/SFace/optional/Native/recovery lower bounds.',
            'validate_chain and the entire original5ca adapter bytes are unchanged; there is no new traversal, seed, restore or forged receipt.',
            'camera_check still runs quiet before the history helper. quiet is AST-identical to R5 and admits only its ordered helper state with no prior/live service or hardware owners. This recheck does not close the separately tracked B01 review.'
        ],
        'provenance_boundary': 'The prior complete_result_pin must really come from unchanged original main while both services were normally inactive. The new wrapper validates a pinned receipt and rechecks semantics; it does not authenticate a receipt against a malicious root or turn a fabricated flag into stop proof.',
    },
    'commit_gap_fix': {
        'status': 'KNOWN_AFTER_LEDGER_COVERS_THE_STATED_INTERRUPTION_POINT_STATICALLY',
        'locations': {'boot_recovery.py': [722, 723, 724, 728, 729, 730, 733, 734, 736, 738, 739, 740, 741, 743, 745, 746, 751, 752, 754, 755, 756, 757, 759],
                      'manage_installation.py': [234, 235, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 249, 250, 251, 252, 256]},
        'finding': 'Before the first UI/startup publication R6 computes exact active_after_raw, O_EXCL/fsync-creates active-source.after.json and seals its SHA in intent. The final active ledger CAS and committed marker use those same bytes. rollback hashes sealed-after against intent, permits missing committed, requires a present committed to equal sealed-after, and accepts the live ledger only when it is exact prior or exact sealed-after. It can therefore restore the known published-after state even when committed was never reached, without trusting current ledger contents as a new after source.',
        'newer_ledger_rejection': 'A regular newer ledger whose bytes are neither sealed before nor sealed after fails NEWER_ACTIVE_LEDGER_CONFLICT before the first UI/startup reversal. A tampered after file fails its intent SHA. A conflicting committed file also fails before source reversal. Final ledger reversal uses sealed-after as its expected CAS bytes, not a freshly blessed live read.',
        'prior_limitation_disposition': 'The old active-written/committed-missing manual HOLD limit is resolved for new R6 transactions with complete sealed before/after artifacts and normal-stop/no-owner rollback preconditions. Transactions lacking those new artifacts still require explicit manual reconciliation; no backfill or Native receipt creation is authorized.',
        'atomicity_boundary': 'This remains the existing multi-file, known-byte transaction under an exclusive writer freeze. It does not claim a kernel-wide atomic transaction across UI/startup/ledger.'
    },
    'author_evidence_only': {
        'record': pin(evidence_directory / 'LOCAL_VALIDATION.json.bin'),
        'log': pin(evidence_directory / 'repair_final_revision3.log.bin'),
        'tests_run': 50, 'failed': 0, 'errors': 0,
        'source_SHAs_match_frozen_R6': True,
        'independently_rerun_here': False,
        'original_Native_validators_executed_per_author': author['original_Native_validators_executed'],
        'limitations': author['limitations'],
    },
    'marker_modes': 'accepted_live_history is AST-identical to R5; the previously checked original same-boot raw-SHA marker and new-kernel JSON marker distinction is retained. No marker-mode test was repeated.',
    'remaining_open_gates': [
        'B01 remains open for root AST comparison; this narrow result does not approve it or the whole B04/package.',
        'Fresh dpu-auto-config merged unit/helper source and ordering or actual absence remains required.',
        'Camera candidate publication, genuine new proof and stable GUI/identity/GTK closure must precede final fresh boot-contract capture; legitimate later source drift must HOLD, not silently repin.',
        'Real target systemd, Native, actual source/owner/receipt and READY evidence remains uncollected by this review. The device window was revoked per main coordination; no device action occurred here.'
    ],
    'new_tests_or_counterexamples_run': 0,
    'full65_or_author50_rerun': False,
    'author_candidate_global_or_production_files_modified': False,
    'board_SSH_HTTP_model_real_store_or_media_access': False,
    'cross_window_or_cross_conversation_messages_sent': False,
    'B01_approved': False, 'whole_B04_or_package_approved': False,
    'deployment_or_device_execution_authorized': False,
}
output = HERE / 'BOOT_FIX_R6_SAME_BOOT_AND_COMMIT_GAP_RECHECK.json'
with output.open('x', encoding='utf-8') as handle:
    json.dump(report, handle, indent=2)
    handle.write('\n')
print(json.dumps({'verdict': report['verdict'], 'report': pin(output), 'new_tests_run': 0,
                  'same_boot_adapter_calls': calls, 'author50_source_pins_match': True}))
