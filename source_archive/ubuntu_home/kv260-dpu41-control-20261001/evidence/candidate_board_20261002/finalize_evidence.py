#!/usr/bin/env python3
"""Check saved evidence, retain old indexes, and index the final local reports."""
import datetime
import hashlib
import json
from pathlib import Path
import re

evidence = Path(__file__).resolve().parent
project = evidence.parent.parent
summary_path = evidence / 'candidate_board_summary.json'
validation_path = evidence / 'final_evidence_validation.json'
candidate_index = project / 'evidence/candidate_board_20261002.sha256'
baseline_index = project / 'evidence/test_card_board_20261001.sha256'
saved_index = evidence / 'before_summary/test_card_board_20261001.sha256'
if validation_path.exists() or candidate_index.exists():
    raise SystemExit('Refusing to overwrite final evidence or index')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def entries(index, base):
    result = []
    for line in index.read_text().splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
        if not match:
            raise RuntimeError('Invalid index entry: ' + str(index))
        expected, name = match.groups()
        result.append((expected, name, base / name))
    return result


def verify_index(index, base):
    rows = entries(index, base)
    for expected, name, path in rows:
        if digest(path) != expected:
            raise RuntimeError('Hash mismatch: ' + name)
    return len(rows)


if baseline_index.read_bytes() != saved_index.read_bytes():
    raise RuntimeError('Baseline index changed since the pre-edit snapshot')
snapshots = json.loads((evidence / 'before_summary/snapshot_manifest.json').read_text())
for snapshot in snapshots:
    if digest(project / snapshot['snapshot']) != snapshot['sha256']:
        raise RuntimeError('Pre-edit snapshot changed: ' + snapshot['snapshot'])
allowed_updates = {'DEPLOYMENT_REVIEW.md', 'TEST_CARD_PLAN.md',
                   'TEST_CARD_BASELINE_REPORT.md', 'BASELINE_INFERENCE_REPORT.md'}
refreshed = []
updates = []
for expected, name, path in entries(saved_index, project):
    actual = digest(path)
    if actual != expected:
        if name not in allowed_updates:
            raise RuntimeError('Original evidence changed: ' + name)
        updates.append({'file': name, 'old_sha256': expected, 'new_sha256': actual})
    refreshed.append(actual + '  ' + name + '\n')
if {r['file'] for r in updates} != allowed_updates:
    raise RuntimeError('Unexpected set of report updates')

checked_indexes = {
    'build_artifacts': verify_index(project / 'evidence/ARTIFACTS.sha256', project),
    'runtime_bundle': verify_index(project / 'test_bundle/SHA256SUMS', project / 'test_bundle'),
    'flash_evidence': verify_index(project / 'evidence/test_card_flash_files.sha256', project),
}
command_count = 0
for results in sorted(evidence.glob('*.results.jsonl')):
    phase = results.name[:-len('.results.jsonl')]
    recorded = [json.loads(line) for line in results.read_text().splitlines()]
    recorded = [r for r in recorded if r.get('type') == 'command']
    commands = json.loads((evidence / (phase + '.commands.json')).read_text())
    if [r['id'] for r in recorded] != [c['id'] for c in commands]:
        raise RuntimeError('Command list mismatch: ' + phase)
    for r in recorded:
        output = evidence / (phase + '.' + r['id'] + '.output')
        if not r['complete'] or r['exit_code'] != 0 or digest(output) != r['integrity_sha256']:
            raise RuntimeError('Incomplete/failed/changed command: ' + phase + '/' + r['id'])
        command_count += 1
if command_count != 30:
    raise RuntimeError('Unexpected command count')

archive = json.loads((evidence / 'runtime_archive.json').read_text())
transfer = json.loads((evidence / '03-runtime-transfer.result.json').read_text())
archive_path = Path(archive['archive'])
if (digest(archive_path) != archive['sha256'] or not transfer['complete']
        or transfer['expected_sha256'] != archive['sha256']
        or transfer['bytes'] != archive_path.stat().st_size or transfer['frames_acknowledged'] != 1070):
    raise RuntimeError('Runtime archive or transfer mismatch')
sources = json.loads((evidence / 'kernel_source_review.json').read_text())
for source in sources['files']:
    if digest(evidence / source['file']) != source['sha256']:
        raise RuntimeError('Downloaded kernel source changed')

summary = json.loads(summary_path.read_text())
for key in ('candidate_load_and_runtime_pass', 'candidate_top5_matches_official',
            'restored_top5_matches_official', 'restore_verified',
            'default_vart_configuration_restored', 'original_hardware_revision_restored',
            'original_file_hashes_match'):
    if summary[key] is not True:
        raise RuntimeError('Summary check did not pass: ' + key)
if (summary['final_active_application'] != 'kv260-benchmark-b4096'
        or summary['overlay_refcount_issue_resolved'] is not False
        or len(summary['observed_refcount_error_events']) != 2):
    raise RuntimeError('Final state or unresolved issue mismatch')

documents = [project / name for name in (
    'CANDIDATE_BOARD_TEST_REPORT.md', 'DEPLOYMENT_REVIEW.md', 'TEST_CARD_PLAN.md',
    'TEST_CARD_BASELINE_REPORT.md', 'BASELINE_INFERENCE_REPORT.md')]
links_checked = 0
for doc in documents:
    for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', doc.read_text()):
        if re.match(r'^(?:[a-zA-Z]+:|#)', target):
            continue
        name = re.sub(r':\d+$', '', target.split('#', 1)[0].strip('<>'))
        destination = doc.parent / name
        if not destination.exists() and destination.resolve() != candidate_index:
            raise RuntimeError('Missing report link: ' + doc.name + ' -> ' + target)
        links_checked += 1

baseline_index.write_text(''.join(refreshed))
checked_indexes['official_baseline_current_index'] = verify_index(baseline_index, project)
index_paths = {p for p in evidence.rglob('*') if p.is_file()}
index_paths.update(documents)
index_paths.update((validation_path, archive_path, baseline_index,
                    project / 'evidence/test_card_board_20261001/baseline_inference_summary.json',
                    project / 'evidence/test_card_board_20261001/transfer_image.py',
                    Path('/home/ghmd/AMD_Smart/logs/fpga/2026-09-30-kv260-readonly/collect_serial.py')))
report = {
    'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'result': 'PASS', 'verified_original_command_outputs': command_count,
    'checked_indexes': checked_indexes, 'updated_report_entries': updates,
    'old_index_and_reports_preserved': 'evidence/candidate_board_20261002/before_summary/',
    'checked_local_report_links': links_checked,
    'archive_transfer_verified': True, 'official_kernel_source_hashes_verified': True,
    'candidate_index_entries': len(index_paths),
    'final_active_application': summary['final_active_application'],
    'unresolved_overlay_refcount_issue': True,
    'scope': 'Local evidence and file checks only; no additional board command or application switch.',
}
with validation_path.open('x') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
    f.write('\n')
with candidate_index.open('x') as f:
    for path in sorted(index_paths, key=str):
        try:
            name = str(path.relative_to(project))
        except ValueError:
            name = str(path)
        f.write(digest(path) + '  ' + name + '\n')
report['candidate_index_verified_entries'] = verify_index(candidate_index, project)
print(json.dumps(report, ensure_ascii=False, indent=2))
