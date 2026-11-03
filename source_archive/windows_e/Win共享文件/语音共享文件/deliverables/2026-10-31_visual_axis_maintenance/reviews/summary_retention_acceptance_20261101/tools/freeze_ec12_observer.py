"""Freeze software-only continuation materials; never starts a device or service."""
from pathlib import Path
import ast,hashlib,json

HERE=Path(__file__).resolve().parents[1]
JOINT=HERE.parent/'joint_performance_20261101'

def pin(path):
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def main():
    adapter=HERE/'tools/start_pause_resume_one_turn.py'
    proof_path=HERE/'evidence/ec12_observer_combined_public_tests.json'
    proof=json.loads(proof_path.read_bytes())
    assert proof['passed'] and proof['tests']==6 and proof['device_or_private_data_accessed'] is False
    assert proof['adapter_sha256']==pin(adapter)['sha256']
    original=JOINT/'remote/live_observer_caption_accepted.py'
    assert pin(original)['sha256']=='8ebb76746cb87bd3608671848cc8087d724e24d4282f2933a3c15b4879bd4819'
    for path in (adapter,HERE/'remote/selection_scope_metadata.py',original):
        ast.parse(path.read_text('utf-8'),feature_version=(3,9))
    folder=HERE/'observer_ec12';folder.mkdir(exist_ok=True)
    preparation=dict(schema='aura-ec12-ordinary-listening-observer-frozen-1',status='SOFTWARE_ONLY_READY_ACTUAL_UI_PENDING_MCP01',
        adapter=pin(adapter),observer=pin(original),public_tests=pin(proof_path),
        actual_new_ready_required=True,context_evidence_not_accepted=True,
        expected_startup_sha256='ec12fccfdd3e8446e9c761e161167e00187e6fcf90372aa7e52c9865cc23c56f',
        observer_bytes_unchanged=True,observer_namespace_isolated=True,
        metadata_added='selection file hash and hashed conversation scope before enable, at READY and after pause',
        raw_conversation_identifiers_exported=False,selection_file_modified=False,
        original_ui_toggle_and_graceful_no_cancel_cleanup_retained=True,
        only_complete_if_full_accepted_ack_and_scope_preserved=True,
        actual_live_test_or_device_access=False,hardware_blocker='MCP01 not enumerated; do not retry until physical connection restored and user resumes hardware work')
    prep=folder/'PREPARATION.json';prep.write_text(json.dumps(preparation,indent=2)+'\n',encoding='utf-8')
    paths=[adapter,HERE/'remote/selection_scope_metadata.py',HERE/'tools/test_ec12_observer_combined.py',
           Path(__file__),proof_path,original,JOINT/'remote/common.py',
           HERE/'package/pause_resume/camera_binding_runtime.py',HERE/'package/pause_resume/candidate_spec.json',
           HERE/'package/pause_resume/BUNDLE_MANIFEST.json',prep]
    manifest=dict(schema='aura-ec12-observer-exact-local-material-1',status='FROZEN_NOT_RUN',files=[pin(path) for path in paths])
    target=folder/'FROZEN_MANIFEST.json';target.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='EC12_OBSERVER_SOFTWARE_FROZEN',manifest=pin(target),preparation=pin(prep),adapter=pin(adapter))))

if __name__=='__main__':main()
