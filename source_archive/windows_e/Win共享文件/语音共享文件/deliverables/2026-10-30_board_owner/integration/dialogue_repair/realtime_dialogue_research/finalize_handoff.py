"""Finalize this research folder only; does not modify authoritative status."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


if __name__ == '__main__':
    documents = {}
    for path in ROOT.glob('*.json'):
        documents[path.name] = json.loads(path.read_text(encoding='utf-8-sig'))
    validation = documents['VALIDATION.json']
    if validation['status'] != 'PASS' or validation['tests'] != documents['HANDOFF.json']['integration']['tests']:
        raise ValueError('validation_not_current')
    if documents.get('PATCH_CHECK.json', {}).get('status') != 'PASS_PATCH_APPLIES_TO_ISOLATED_COPY_ONLY':
        raise ValueError('isolated_patch_check_not_passed')
    sources = documents['SOURCE_REVIEW.json']
    if not all(item['matches_375_pin_manifest'] for item in sources['files']):
        raise ValueError('reviewed_source_pin_mismatch')
    if not sources['windows_host']['matches_response_latency_installed_receipt']:
        raise ValueError('reviewed_host_pin_mismatch')
    for name, entry in documents['CANDIDATE_MANIFEST.json']['artifacts'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('candidate_artifact_changed')
    status = documents['STATUS.json']
    status.update(status='RESEARCH_REVIEW_PATCH_AND_SYNTHETIC_VALIDATION_READY_NOT_INSTALLED',
        updated_utc=datetime.now(timezone.utc).isoformat(),
        progress=[
            'Official-source research complete; versions, ARM/resource caveats and ranked implementation/rollback gates documented',
            'Seven selected public sources matched the root 375-pin baseline; Windows inference source matched installed receipt',
            'Review patch changes only model-generated reply grouping, preserving complete JSON validation, local paths, fresh packet checks and complete ACK',
            '44 offline tests passed, plus 1000 text partitions and 200 arrival traces inside property tests',
            'Environment speech addendum complete; metadata separates environment-only rounds from directed human tests; no behavior changed'
        ],
        offline_tests=dict(status='PASS', tests=validation['tests'], failures=0, evidence='VALIDATION.json'),
        report='实时对话成熟方案与落地评审_20261031.txt',
        environmental_false_activation_report='环境讲话误触与无唤醒词取舍_20261031.txt',
        handoff='HANDOFF.json', patch='integration_review.patch', metadata_request='METADATA_REQUEST.json',
        latest_root_scene_report='v11 surrounding speech/playback, user not actively testing; ENVIRONMENT_ONLY; normal full ACK/rearm not itself a fault',
        production_files_changed=False, services_or_devices_operated=False, private_database_accessed=False,
        model_requests_or_downloads_performed=False, physical_dialogue_acceptance=False,
        next='Root reviews fresh pins and patch after its frontend live window; optional passive metadata, same-text TTS trial and directed listening acceptance remain root-owned')
    (ROOT / 'STATUS.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    inventory = {path.name: dict(bytes=path.stat().st_size,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                 for path in ROOT.iterdir() if path.is_file() and path.name != 'DELIVERY_INVENTORY.json'}
    (ROOT / 'DELIVERY_INVENTORY.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': status['status'], 'tests': validation['tests'],
                      'top_level_files': len(inventory), 'matched_board_sources': len(sources['files']),
                      'root_metadata_reply_present': (ROOT / 'root_metadata_reply.json').exists(),
                      'production_or_device_changes': False}))
