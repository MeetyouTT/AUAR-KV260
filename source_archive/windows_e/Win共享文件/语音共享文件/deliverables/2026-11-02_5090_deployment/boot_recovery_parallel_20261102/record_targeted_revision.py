"""Preserve the 65-case v1 evidence and record only actually run repair tests."""
import datetime
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def preserve_v1():
    directory = HERE / 'validation/baseline65_v1'
    directory.mkdir(exist_ok=True)
    original = HERE / 'validation/LOCAL_VALIDATION.json'
    saved = directory / 'LOCAL_VALIDATION.json'
    if not saved.exists():
        raw = original.read_bytes()
        value = json.loads(raw)
        if value.get('status') != 'PASS_OFFLINE_ONLY' or value.get('tests_run') != 65:
            raise RuntimeError('Original 65-case receipt is required before recording a revision')
        saved.write_bytes(raw)
        (directory / 'unittest_final.log').write_bytes((HERE / 'validation/unittest_final.log').read_bytes())
    return json.loads(saved.read_bytes()), saved


def parse_passed_log(path):
    text = path.read_text(encoding='utf-8-sig')
    count = re.search(r'^Ran ([0-9]+) tests? in ', text, re.MULTILINE)
    if not count or not re.search(r'^OK\s*$', text, re.MULTILINE) or 'FAILED (' in text:
        raise RuntimeError('Targeted log is missing an actual successful unittest summary')
    return int(count.group(1))


def main():
    baseline, baseline_path = preserve_v1()
    logs = sorted((HERE / 'validation').glob('repair_*.log'))
    interface_log = HERE / 'validation/cpu_interface_targeted_v2.log'
    if interface_log.exists():
        logs = [interface_log] + logs
    groups = [dict(log=p.relative_to(HERE).as_posix(), tests_run=parse_passed_log(p),
                   sha256=sha(p.read_bytes()), failed=0, errors=0) for p in logs]
    files = [p for p in (HERE / 'candidate').rglob('*') if p.is_file()]
    files += list((HERE / 'tests').glob('*.py'))
    receipt = dict(schema='aura-boot-recovery-offline-targeted-revision-2',
                   updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   status='PASS_OFFLINE_TARGETED_REVISION',
                   tests_run=sum(group['tests_run'] for group in groups), failed=0, errors=0, skipped=0,
                   baseline_validation=dict(path=baseline_path.relative_to(HERE).as_posix(), sha256=sha(baseline_path.read_bytes()),
                                            tests_run=baseline['tests_run'], scope='Original v1 candidate; not rerun for review waiting'),
                   baseline_65_suite_rerun=False, targeted_groups=groups,
                   counting_note='Targeted counts include related existing cases; do not add them to 65 as a new full-suite total.',
                   source_sha256={p.relative_to(HERE).as_posix(): sha(p.read_bytes()) for p in sorted(files)},
                   board_calls=0, hardware_or_model_loads=0, real_databases_opened=0,
                   audio_images_or_private_keys_opened=0, deployed=False, cold_boot_accepted=False,
                   limitations=['Public/synthetic local tests only; live metadata and target systemd validation remain pending',
                                'Independent review status is tracked separately; this receipt does not grant approval'])
    (HERE / 'validation/LOCAL_VALIDATION.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(dict(status=receipt['status'], targeted_tests_run=receipt['tests_run'], baseline_tests_retained=65,
                          baseline_65_suite_rerun=False, board_calls=0)))


if __name__ == '__main__':
    main()
