"""Write the requested local field/API review, not B04/runtime approval."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OPT = HERE.parent
R5 = OPT / 'boot_review_inputs/observed_revision5'
R4 = OPT / 'boot_review_inputs/observed_revision4'


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


expected = {
    'boot_recovery.py': '36970f82a694da89c42189f315047b8e9a1f8f877b5ffdc15b71543c376c8c0b',
    'capture_contract.py': 'bce6d4d1b2f7547827f9f886014297d1483c1eb8a8b99ef6cf04421cd1b5562c',
    'original_history_gate.py': '735b0fb2f9bf696765c781f8f8573e8a368dacf916c58f5b0e556d1cde0e16d8',
    'recovery_rules.py': '55bfc4db498be172beb040605dcae351c6f972e0df1371cecb48b7d1034ed268',
    'manage_installation.py': '845b2bc8f2794eb80421e3b989f7afeddd899991cf83c3d009805ce3d8f4885c',
}
for name, value in expected.items():
    assert pin(R5 / 'candidate' / name)['sha256'] == value
adapter = OPT / 'camera/validate_fresh_final_history_readonly.py'
assert pin(adapter)['sha256'] == '5ca99d4231c686de0f89dac5792299bec13af517a5c6e2b8f73c4cc66b9285c9'
probe_path = HERE / 'BOOT_HISTORY_GATE_API_PROBES_R5.json'
probes = json.loads(probe_path.read_bytes())
assert probes['gate_sha256'] == expected['original_history_gate.py']
assert probes['original_guard_camera_start_pre_rejection'] == 'Original service not normally stopped'
assert len(probes['marker_cases']) == 2 and all(case['original_writer_payload_accepted'] for case in probes['marker_cases'])
adapter_tree = ast.parse(adapter.read_bytes())
exports = {node.name for node in adapter_tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
assert {'Snapshot', 'original_modules', 'optional_shape', 'validate_chain', 'main'} <= exports

report = {
    'schema': 'aura-boot-history-gate-compatibility-r5-1',
    'verdict': 'FIELD_API_MATCH_WITH_SAME_BOOT_PRESTART_GUARD_INCOMPATIBILITY',
    'scope': 'R5 field/API, provenance anchor and marker-mode compatibility review only. R4 is a historical draft. No original archive traversal was repeated; original full main/Native loader/ABI/runtime proof was not executed. This does not approve B04.',
    'primary_snapshot': pin(R5 / 'SNAPSHOT.json'),
    'reviewed_inputs': [pin(R5 / 'candidate' / name) for name in expected] + [pin(adapter)] + [
        pin(OPT / 'camera/baseline/251e9660633c__native_boot.py'),
        pin(OPT / 'camera/baseline/b8637c2aa387__native_protection.py'),
        pin(OPT / 'camera/baseline/4a729a29c6e4__native_startup.py'),
    ],
    'evidence': pin(probe_path),
    'probe_script': pin(HERE / 'check_history_gate_r5_compatibility.py'),
    'findings': [
        {'id': 'REAL_ADAPTER_API_AND_SAME_BOOT_OUTPUT_KEYS', 'status': 'MATCH',
         'locations': {'original_history_gate.py': [54, 57, 63, 66, 70, 74, 75, 76, 77, 79, 82, 94, 101],
                       'camera/validate_fresh_final_history_readonly.py': [88, 122, 306, 375, 428, 448, 449, 450, 452, 453, 455],
                       'native_boot.py': [140, 226]},
         'finding': 'Snapshot, original_modules(snapshot), optional_shape(auxiliary, protection), validate_chain(document, history, snapshot, protection, boot_module) and main() are real unchanged exports. Original native_boot exposes marker_paths(directory, boot). The same-boot caller checks the actual output schema/status, checkpoint_pin, source_owner, expected_sha256, original_load_business_checkpoint_called, complete_ordered_history_verified, all_required_current_boot_cumulative_lower_bounds_checked and archives; every key exists in the actual5ca success dictionary. Its --expected/--expected-sha256 argv matches original main. R5 projects the four chain fields before comparison, retaining the full original expected file for main to validate stop/bounds/provenance.',
         'probe_limit': 'The local success-output check evaluated the exact original success dictionary expression and used that projection as a fixture. It did not run original main or fabricate a deployable Native receipt.'},
        {'id': 'COLD_PREDECESSOR_PROVENANCE_AND_NO_CURRENT_DOMAIN_RESET', 'status': 'STATIC_API_MATCH',
         'locations': {'original_history_gate.py': [83, 85, 87, 88, 90, 91, 92, 93, 94, 95, 101],
                       'boot_recovery.py': [350, 354, 355, 356, 388, 389, 390, 392, 393],
                       'native_boot.py': [140, 226, 247, 257, 259]},
         'finding': 'Cold validation calls the archive-policy _sealed_source rather than the current-boot load_business_checkpoint reader. It binds seed boot/PID/birth, predecessor source manifest and original source C unit to the declared predecessor, requires source boot different from actual boot and refuses any current-kernel domain marker. The existing chain verifier begins at the pinned predecessor document actual history head. Archived domains retain their own manifests/counters; no current-domain seed, marker or restore is created here. Real predecessor/manifest/owner truth still depends on the fresh captured contract and original entry.'},
        {'id': 'RUNNING_CHAIN_HEAD_HAS_CALLER_ANCHOR_AND_COMPLETE_ORDER', 'status': 'CONDITIONAL_STATIC_COMPATIBILITY',
         'locations': {'capture_contract.py': [58, 66, 68, 71, 72, 73, 86, 87, 110, 167, 168],
                       'boot_recovery.py': [388, 400, 408, 413, 418, 423, 425, 426, 430, 437, 691, 739, 761, 762],
                       'recovery_rules.py': [173, 175, 176, 178, 180, 181, 182, 183, 185, 186, 189],
                       'original_history_gate.py': [97, 100, 101, 104],
                       'camera/validate_fresh_final_history_readonly.py': [375, 377, 378, 382, 393, 400, 403, 410, 411, 416, 423, 425]},
         'finding': 'running_archive_chain alone accepts a caller-provided head and is not an independent provenance authenticator. R5 integration supplies the missing anchor: capture binds the full original expected pin to its accepted main receipt and checks the running handoff head; prestart gate pins the exact predecessor final and complete prior history; accepted_live_history first verifies that gate, then next_history_expected either preserves same-boot head or prepends exactly one actual original commit edge while retaining every previous row and legacy pin. The real current-domain marker further binds new head path/SHA/source final; bind and READY compare accepted history to active ledger. The unchanged adapter then requires exact order/count, edge identity and terminal legacy with no early terminal/truncation success. The synthetic current-boot header is used only as validate_chain metadata and is never passed to a seed or restoration API.',
         'precondition': 'Do not reuse execute_request(running_archive_chain) as approval for an arbitrary standalone history request or bypass accepted_live_history/captured provenance. Completeness here is a static call-graph/contract conclusion, not a live traversal acceptance.'},
        {'id': 'ORIGINAL_MARKER_PAYLOAD_MODES', 'status': 'MATCH_IN_TWO_DIRECTED_PAYLOAD_CHECKS',
         'locations': {'boot_recovery.py': [426, 427, 428, 430, 431, 432, 433, 434, 435, 437],
                       'native_protection.py': [177, 179, 180, 182, 183],
                       'native_boot.py': [226, 349, 350, 351, 352, 353],
                       'native_startup.py': [117, 122, 126, 128, 129, 131, 135]},
         'finding': 'Same-boot consumption is raw checkpoint SHA plus newline in the .native-consumed-SHA file; new-kernel consumption is the original JSON record with schema/boot/source_checkpoint_sha256/archive_path/archive_sha256/captured_mono_ns. R5 reads the correct mode for each actual route. Both exact original writer payload expressions were evaluated with synthetic values and POSIX paths and accepted by the exact R5 accepted_live_history metadata method. The new-kernel case retained the entire old archive suffix and legacy pin. No writer, commit, consume or archive traversal was executed.'},
        {'id': 'SAME_BOOT_MAIN_AT_CAMERA_PRESTART', 'status': 'ROUTE_BLOCKER_FAILS_CLOSED',
         'locations': {'boot_recovery.py': [388, 394, 396, 397, 600, 605, 609],
                       'original_history_gate.py': [54, 66],
                       'camera/validate_fresh_final_history_readonly.py': [160, 162, 164, 165, 437, 438, 444]},
         'finding': 'same_boot_resume reruns exact original main from camera_check. At the camera ExecStartPre boundary the camera is activating/start-pre, which Recovery.quiet explicitly allows. The original adapter guard requires BOTH services inactive/dead, no job and normal success. It therefore rejects this real same-boot prestart state even with a genuine normal-stop expected pin. The exact original guard AST with a normal inactive GUI and camera start-pre fixture raised Original service not normally stopped before any owner scan. This is a lifecycle/precondition incompatibility, not a missing output field and not a false approval.',
         'minimal_recommendation': [
             'Keep the existing guard strict. Run unchanged full main while both original services are genuinely normally inactive, before issuing camera start, and retain its exact expected/result pins.',
             'At ExecStartPre verify that already genuine receipt against the exact still-unconsumed final/owner/history and unchanged fresh source closure plus no-owner prestart guards, without claiming that rerunning the full inactive-only main there can succeed. Alternatively explicitly keep same-boot restart outside this cold-only integration and HOLD it for the existing CPU/main stopped-stage flow.',
             'Do not synthesize a stop result, suppress the guard, or convert activating into inactive metadata. A revised integration still needs its own small stage/precondition check.'
         ]},
    ],
    'R4_historical_disposition': {
        'draft_pin': pin(R4 / 'candidate/original_history_gate.py'),
        'whole_expected_history_vs_four_field_manifest': 'R4 falsely rejects a genuine normal expected history containing observed_mono_ns/provenance_pin; locally reproduced at its binding comparison. R5 four-field projection resolves that field-shape issue.',
        'B04_approval_for_draft': False,
    },
    'external_release_order_constraint': {
        'status': 'REQUIRED_CORRECT_CLOSURE_BEHAVIOR_NOT_A_NEW_DEFECT',
        'locations': {'capture_contract.py': [43, 44, 108, 110, 113, 114, 115, 116, 118],
                      'manage_installation.py': [109, 111, 113, 135, 140], 'boot_recovery.py': [223, 228, 240]},
        'finding': 'Main coordination identifies the Native222 set including ui_camera_service.py plus GUI380 and selected-source closure as contract inputs. The7d4773 camera candidate has not yet been published. Activating a final boot contract before that later legitimate camera update would correctly cause source drift HOLD; hashes must not be silently repinned. Installer is add-only and refuses existing PACKAGE_ROOT/STATE_ROOT.',
        'preferred_order': ['Obtain the actual authorized camera maintenance window; do not publish while its current owner still uses it.',
                            'Publish the reviewed camera candidate and obtain new genuine final/history/bootstrap evidence.',
                            'Stabilize current GUI/identity/GTK sources and selected binding, then perform fresh final boot-contract capture and reviewed installation.'],
        'no_device_action_authorized_here': True,
    },
    'remaining_external_gates': ['Fresh dpu-auto-config merged unit/actual helper source/ordering evidence or actual absence remains mandatory.',
                                 'Fresh exclusive handoff, current source closure and real target systemd/Native/READY checks remain mandatory.'],
    'checks_executed': ['R5 same-boot fields against the exact original success-output dictionary expression.',
                        'Historical R4 extra-history-key rejection using the same non-Native output fixture.',
                        'One exact original guard AST prestart-state rejection.',
                        'Exact R5 accepted_live_history/next_history_expected with each original marker writer payload expression; upstream proof and running-chain calls explicitly stubbed.'],
    'checks_not_executed': ['No full65 or other whole suite rerun.', 'No original history traversal or main execution.',
                            'No original_modules, NativeContext, C library, consume, commit or restoration.',
                            'No SSH, board HTTP, model, real store/media or service action.'],
    'B04_approved': False, 'deployment_authorized': False, 'candidate_author_or_production_files_modified': False,
    'cross_window_or_cross_conversation_messages_sent': False,
}
output = HERE / 'BOOT_HISTORY_GATE_COMPATIBILITY_R5.json'
with output.open('x', encoding='utf-8') as handle:
    json.dump(report, handle, indent=2)
    handle.write('\n')
print(json.dumps({'verdict': report['verdict'], 'report': pin(output), 'evidence': pin(probe_path)}))
