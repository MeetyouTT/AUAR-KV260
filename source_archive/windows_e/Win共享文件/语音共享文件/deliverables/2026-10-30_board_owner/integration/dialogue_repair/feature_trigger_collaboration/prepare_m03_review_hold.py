"""Read-only source audit; append a review hold without modifying any candidate.
No counterexample is executed and no root/reviewer evidence is overwritten.
"""
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
D=H/'candidate_m03'


def frozen(path):
    return dict(path=str(path.relative_to(H)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)


def main():
    manifest=json.loads((D/'SOURCE_MANIFEST.json').read_bytes())
    bindings={}
    for relative,row in manifest['files'].items():
        raw=(D/'after'/relative).read_bytes()
        actual=hashlib.sha256(raw).hexdigest()
        bindings[relative]=dict(declared_sha256=row['sha256'],actual_sha256=actual,
            matches=actual==row['sha256'],lf_normalized_sha256=hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest())
    pins=json.loads((H/'board_integration_v17/source_mapping.json').read_bytes())['component_pins']
    for relative in ('tools/production_memory_presentation.py','common/timeline.py'):
        assert hashlib.sha256((H/'board_integration_v17/local_runtime_v17'/relative).read_bytes()).hexdigest()==pins[relative]
    references=[D/'SOURCE_MANIFEST.json',D/'HANDOFF.json',D/'after/board/runtime/history_delete.py',
        D/'after/board/runtime/board_business.py',D/'REGRESSION_02.xml',
        H/'board_integration_v17/local_runtime_v17/tools/production_memory_presentation.py',
        H/'board_integration_v17/local_runtime_v17/common/timeline.py',H/'tests/test_history_delete_m03.py']
    value=dict(schema='aura.m03.independent-review-hold.v1',
        status='HOLD_NOT_FOR_RELEASE_WAITING_INDEPENDENT_COUNTEREXAMPLES',
        instruction_source='Authorized main/root chat: independent win_inference review; v18 excludes M03/D01',
        candidate_sources_and_evidence_unchanged=True,checked_references=[frozen(p) for p in references],
        source_manifest_bindings=bindings,
        additional_manifest_defect='M03 board_business.py was written with Windows CRLF while its manifest digest was computed from LF text. Actual e09d... differs from declared6df6..., with LF normalization equal. Keep original artifact, correct byte sealing only in a separately named revision.',
        findings=[
            dict(id='calendar_end_is_inclusive',level='source_verified_runtime_counterexample_pending',
                source='candidate_m03/after/board/runtime/history_delete.py:59',
                description='Selection uses recorded_utc<=end. common.timeline.query yields the next local midnight for a completed calendar day; exact next-day midnight is therefore eligible.',
                intended_review_boundary='A single calendar day needs a precise half-open end in its requested timezone, including DST. Do not change general history semantics incidentally.'),
            dict(id='today_end_frozen_at_preview',level='source_verified_runtime_counterexample_pending',
                source='candidate_m03/after/board/runtime/history_delete.py:156',
                description='query(date,now=event_time) truncates today end to preview time and pending stores this same end. A later valid source after that end may be outside confirmation reselect.',
                existing_test_gap='The new_source test appends while its fake monotonic clock remains unchanged, so it covers an equal-timestamp addition only.',
                intended_review_boundary='Determine exact counterexample and required preview semantics. A new source in the requested day must not be silently treated as covered/deleted; any correction must still require a new explicit preview if membership changes.'),
            dict(id='presentation_postcommit_hook_bypassed',level='source_verified_runtime_counterexample_pending',
                source='board_integration_v17/local_runtime_v17/tools/production_memory_presentation.py:301',
                description='Production bind_presentation wraps instance correct/forget/clear/commit_compaction. M03 _confirm calls private _invalidate/_save_operation directly, so those wrappers are not invoked.',
                existing_test_gap='Synthetic Harness does not bind the production presentation lifecycle; body/fact invalidation and simulated complete ACK alone do not prove display projection or queued audio invalidation.',
                intended_review_boundary='Require explicit postcommit/presentation proof, stale display and source/audio/late-ACK cases. Notify only after transaction/scope locks have exited; preserve current confirmation ownership and original lock order.')],
        next_action='Wait for independent reviewer counterexamples and root direction, then create a separate minimal revision plus unchanged failing-case replay. Do not edit current candidate or negative evidence.',
        no_production_or_model_or_device_or_private_store_access=True,
        previous_tests='183 local passes remain scoped historical evidence and do not cover these three review concerns.')
    path=D/'REVIEW_HOLD.json'
    with path.open('x',encoding='utf-8') as out:
        json.dump(value,out,ensure_ascii=False,indent=2);out.write('\n')
    print(json.dumps(dict(status=value['status'],frozen_files=len(references),candidate_modified=False)))


if __name__=='__main__':main()
