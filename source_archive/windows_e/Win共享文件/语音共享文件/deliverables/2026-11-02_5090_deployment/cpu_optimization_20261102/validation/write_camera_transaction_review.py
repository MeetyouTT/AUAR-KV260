"""Record final local transaction review; no board calls or production writes."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
template=ROOT/'camera/six_file_transaction_template.py'
builder=ROOT/'camera/prepare_transaction_payload.py'
old_template=ROOT/'transaction_root_hardening/six_file_transaction_template.py.before.bin'
raw=template.read_bytes();old=old_template.read_bytes();payload=builder.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='32329668ea3dfb63744e58a7866025cb7ba1f0986f72d30948b8c93ceb401a6a'
assert hashlib.sha256(old).hexdigest()=='070f71357e9f703022b6d4eb4e03a50add91ca9fa8061827869a0ac3b0d1c2cb'
assert hashlib.sha256(payload).hexdigest()=='c8092a3777b583082beda9bfd5abae1f8e635d1f81983687b0407cd8a6976ff1'
old_line="            if Path(row['stage']).exists():pinned({'path':row['stage'],'sha256':row['after_sha256']})"
new_line="            if stage.exists() or stage.is_symlink():pinned({'path':row['stage'],'sha256':row['after_sha256']})"
a=old.decode().replace('\r\n','\n');b=raw.decode().replace('\r\n','\n')
assert a.count(old_line)==1 and a.replace(old_line,new_line)==b
fix=json.loads((HERE/'TRANSACTION_DANGLING_STAGE_FIXED.json').read_text(encoding='utf-8'))
assert fix['template_sha256']==hashlib.sha256(raw).hexdigest()
assert fix['results']=={'recover_plan_rejected_before_commit':True,'commit_recover_rejected_before_commit':True}
result={
    'status':'PASS_STATIC_AFTER_ROOT_STAGE_FIX_LINUX_DRY_RUN_AND_ORIGINAL_READER_PENDING',
    'template_sha256':hashlib.sha256(raw).hexdigest(),
    'prior_template_sha256':hashlib.sha256(old).hexdigest(),
    'payload_builder_sha256':hashlib.sha256(payload).hexdigest(),
    'root_fix_only_expected_one_branch':True,
    'resolved_finding':{
        'id':'RECOVER_DANGLING_STAGE_DRY_RUN_FALSE_POSITIVE',
        'old_behavior':'exists()==False could skip a dangling symlink during recover_plan; O_EXCL still refused unknown name during apply, possibly after known earlier items committed',
        'new_behavior':'exists() OR is_symlink() requires pinned regular after-bytes during preflight; dangling link fails before replacement',
        'evidence':'TRANSACTION_DANGLING_STAGE_FIXED.json',
        'actual_linux_execution_claimed':False},
    'code_blockers_remaining':[],
    'checks':{
        'six_fixed_targets_and_known_original_reference':True,
        'all_original_and_after_bytes_durable_before_any_target_replacement':True,
        'same_directory_atomic_per_file_rename_with_sha_inode_vector_checks':True,
        'whole_six_atomic_commit_claimed':False,
        'original_222_source_member_set_and_other_221_unchanged':True,
        'operator_7_members_only_app_pin_changes':True,
        'native_6_c_unit_and_library_pinned_unchanged':True,
        'explicit_known_before_or_after_recovery_only':True,
        'rollback_requires_prior_durable_plan_and_newest_unconsumed_final':True,
        'default_dry_run_has_no_target_stage_or_backup_writes':True,
        'template_starts_services_or_replays_motion':False},
    'reader_receipt_contract':{
        'kind':'trusted root attestation wrapping a pinned real original-reader result',
        'not_an_independent_semantic_reader':True,
        'must_map_actual_pin_owner_full_history_success_not_fill_example_literals':True,
        'plan_identity_binds_every_contract_field_except_root_receipt_pin':True,
        'fresh_board_monotonic_attestation_maximum_ms':60000},
    'new_boot_archive_only':{
        'template_scope':'same-kernel fresh final exported by the actually normally stopped current owner',
        'first_cross_kernel_archive_only_bootstrap_supported_by_this_template':False,
        'original_boot_loader_remains_authority':True,
        'previous_kernel_history_source_boot_must_equal_current_boot':False,
        'old_archive_counters_or_monotonic_times_must_be_imported_into_current_domain':False,
        'must_not_rewrite_archive_or_fabricate_same_boot_seed_to_satisfy_template':True},
    'required_external_preconditions':[
        'Explicit handoff and actual freeze of all other writers; advisory flock alone is not a freeze',
        'Fresh boot and stopped camera/GUI PID-birth-command evidence and no native owner',
        'Normal-stop current owner, original reader and complete actual history validation for that exact fresh final',
        'Fresh root normalization receipt and matching plan identity; no copied old success receipt',
        'Fresh original six hashes must match reviewed references; otherwise rebase/review rather than relax pins',
        'Root Linux default dry-run before apply and explicit recovery only for its durable known plan',
        'After successful six-file commit, original restore/audit/marker/counter checks, actual new owner and selected binding closure before GUI restart',
        'A consumed predecessor is never rolled back; stop the new owner and use its newest valid final'],
    'tests_reused_without_rerun':{'payload_builder':4,'transaction_core':10},
    'new_test_scope':'One dangling-stage core model, then the actual root fix; no live_guard/target Linux executor',
    'board_or_network_or_native_context_or_models_accessed':False,
    'production_or_candidate_or_template_modified_by_reviewer':False,
    'validation_protocol_updated_for_current_projection_and_fresh_identity_parameters':True}
(HERE/'CAMERA_TRANSACTION_INDEPENDENT_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':result['status'],'template_sha256':result['template_sha256'],
    'code_blockers_remaining':result['code_blockers_remaining'],'root_fix_only_expected_one_branch':True}))
