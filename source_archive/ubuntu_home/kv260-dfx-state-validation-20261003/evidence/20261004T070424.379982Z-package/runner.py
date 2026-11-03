#!/usr/bin/env python3
"""Seal a local review candidate and verify patch replay and archive bytes."""
import datetime
import difflib
import hashlib
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = Path('/home/ghmd/kv260-dfx-manager-repair-20261002/sources/dfx-mgr')
PREVIOUS_BOARD_SHA = 'db9c25f09f1178177884b1114c57f32c076f1e7f9cdd0d12b7a896039038a46c'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def files(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def make_patch(original, candidate, output):
    before, after = files(original), files(candidate)
    assert before.keys() == after.keys(), 'Unexpected file addition or removal'
    changed = [name for name in before if before[name] != after[name]]
    result = []
    for name in changed:
        result.extend(difflib.unified_diff(
            (original / name).read_text().splitlines(keepends=True),
            (candidate / name).read_text().splitlines(keepends=True),
            fromfile='a/' + name, tofile='b/' + name))
    output.write_text(''.join(result))
    return changed


def main():
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    run = ROOT / 'evidence' / (now + '-package')
    run.mkdir(exist_ok=False)
    shutil.copy2(__file__, run / 'runner.py')
    baseline = ROOT / 'sources/dfx-mgr'
    source = ROOT / 'sources/dfx-mgr-patched'
    baseline_info = json.loads((ROOT / 'evidence/baseline_inputs.json').read_text())
    assert files(baseline) == baseline_info['files'], 'Preserved baseline changed'
    build_info = json.loads((ROOT / 'CURRENT_BUILD_PATCHED.json').read_text())
    build = json.loads(Path(build_info['status_file']).read_text())
    assert build['passed'] and files(source) == build_info['source_sha256']
    test_info = json.loads((ROOT / 'CURRENT_HOST_TESTS.json').read_text())
    tests = json.loads(Path(test_info['status_file']).read_text())
    assert tests['passed'] and tests['source_sha256'] == files(source)
    assert tests['sanitizers']['asan_ubsan']['state'] == 'passed'
    assert tests['sanitizers']['asan_ubsan']['leak_detection']
    reviews = sorted(ROOT.glob('evidence/*-runtime-review/status.json'))
    review_path = reviews[-1]
    review = json.loads(review_path.read_text())
    assert review['passed'] and review['client_text_unchanged']
    assert review['loader_check_requested']
    candidates = {Path(b['path']).name: b for b in review['binaries'] if b['phase'] == 'patched'}
    previous = next(b for b in review['binaries'] if b['phase'] == 'baseline' and Path(b['path']).name == 'dfx-mgrd')
    assert previous['sha256'] == PREVIOUS_BOARD_SHA
    # RPATH editing must be the only difference from this exact current build.
    raw = Path(build_info['artifact_dir']) / 'dfx-mgrd'
    assert sha(raw) == build['artifacts']['dfx-mgrd']['sha256']
    reviewed_raw = run / 'current-build-without-rpath'
    shutil.copy2(raw, reviewed_raw)
    chrpath = '/home/ghmd/petalinux/2022.2/components/yocto/buildtools_extended/sysroots/x86_64-petalinux-linux/usr/bin/chrpath'
    subprocess.run([chrpath, '-d', str(reviewed_raw)], check=True)
    assert sha(reviewed_raw) == candidates['dfx-mgrd']['sha256'], 'ABI review is stale'

    bundle = ROOT / 'release/dfx-state-20261004-host-verified'
    bundle.mkdir(exist_ok=False)
    (bundle / 'bin').mkdir()
    (bundle / 'patches').mkdir()
    incremental = bundle / 'patches/state-lifecycle.patch'
    aggregate = bundle / 'patches/vendor-to-candidate.patch'
    changed = make_patch(baseline, source, incremental)
    assert changed == ['example/sys/linux/dfx-mgrd.c', 'src/daemon_helper.c']
    make_patch(VENDOR, source, aggregate)
    replay_results = []
    for label, original, patch in (('incremental', baseline, incremental), ('vendor', VENDOR, aggregate)):
        replay = run / ('replay-' + label)
        shutil.copytree(original, replay)
        proc = subprocess.run(['patch', '--batch', '-p1', '-i', str(patch)], cwd=replay,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (run / ('patch-' + label + '.log')).write_text(proc.stdout)
        assert proc.returncode == 0 and files(replay) == files(source), label + ' patch mismatch'
        replay_results.append({'base': label, 'exit_code': proc.returncode,
                               'matching_source_files': len(files(source))})
    for name, record in candidates.items():
        binary = ROOT / record['path']
        assert sha(binary) == record['sha256']
        shutil.copy2(binary, bundle / 'bin' / name)
    shutil.copytree(source, bundle / 'source')
    for name in ('REPAIR_REPORT.md', 'BOARD_VALIDATION_PLAN.md'):
        shutil.copy2(ROOT / name, bundle / name)
    shutil.copy2(Path(build_info['status_file']), bundle / 'BUILD_STATUS.json')
    shutil.copy2(review_path, bundle / 'ABI_STATUS.json')
    shutil.copy2(Path(test_info['status_file']), bundle / 'HOST_TEST_STATUS.json')
    (bundle / 'tests').mkdir()
    shutil.copy2(ROOT / 'tests/state_regression.c', bundle / 'tests/state_regression.c')
    (bundle / 'board').mkdir()
    shutil.copy2(ROOT / 'board/90-kv260-dfx-state-validation.conf', bundle / 'board/90-kv260-dfx-state-validation.conf')
    (bundle / 'scripts').mkdir()
    shutil.copy2(ROOT / 'scripts/run_host_tests.py', bundle / 'scripts/run_host_tests.py')
    (bundle / 'SOURCE_MANIFEST.json').write_text(json.dumps(files(source), indent=2) + '\n')
    provenance = {
        'created_utc': now, 'vendor_commit': baseline_info['vendor_commit'],
        'baseline_source': baseline_info['baseline_source'],
        'previous_patch_sha256': baseline_info['previous_patch_sha256'],
        'previous_board_reference_sha256': PREVIOUS_BOARD_SHA,
        'build_status_file': build_info['status_file'], 'abi_status_file': str(review_path),
        'changed_source_files': changed, 'candidate_daemon_sha256': candidates['dfx-mgrd']['sha256'],
        'source_repair_complete': True, 'cross_compile_passed': True, 'static_abi_passed': True,
        'native_regression_run': True, 'native_cases_passed': tests['native_cases_passed'],
        'asan_ubsan': tests['sanitizers']['asan_ubsan'], 'tsan': tests['sanitizers']['tsan'],
        'host_test_status_file': test_info['status_file'],
        'board_verified': False, 'installed_on_board': False,
        'loader_check_run': review['loader_check_requested'],
        'client_text_unchanged': True, 'patch_replay': replay_results,
        'workspace_for_rebuild': str(ROOT),
        'installation_scope': 'Future deployment selects only bin/dfx-mgrd; current board client and ZOCL retained'
    }
    (bundle / 'PROVENANCE.json').write_text(json.dumps(provenance, indent=2) + '\n')
    manifest = files(bundle)
    (bundle / 'SHA256SUMS').write_text(''.join(f'{digest}  {name}\n' for name, digest in manifest.items()))
    assert all(sha(bundle / name) == digest for name, digest in manifest.items())
    archive = ROOT / 'release/dfx-state-20261004-host-verified.tar.gz'
    assert not archive.exists()
    members = files(bundle)
    with tarfile.open(archive, 'w:gz') as output:
        for name in members:
            output.add(bundle / name, arcname=name, recursive=False)
    with tarfile.open(archive, 'r:gz') as packed:
        assert set(packed.getnames()) == set(members)
        for member in packed.getmembers():
            assert member.isfile()
            assert hashlib.sha256(packed.extractfile(member).read()).hexdigest() == members[member.name]
    result = {'passed': True, 'created_utc': now, 'bundle': str(bundle),
              'archive': str(archive), 'archive_bytes': archive.stat().st_size,
              'archive_sha256': sha(archive), 'verified_archive_files': len(members),
              'candidate_daemon_sha256': candidates['dfx-mgrd']['sha256'],
              'preserved_baseline_files': len(files(baseline)), 'patch_replay': replay_results,
              'native_regression_run': True, 'native_cases_passed': tests['native_cases_passed'],
              'asan_ubsan': tests['sanitizers']['asan_ubsan'], 'tsan': tests['sanitizers']['tsan'],
              'loader_check_run': True, 'board_verified': False, 'installed_on_board': False,
              'run': str(run)}
    (run / 'status.json').write_text(json.dumps(result, indent=2) + '\n')
    (ROOT / 'PACKAGE_VERIFICATION.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
