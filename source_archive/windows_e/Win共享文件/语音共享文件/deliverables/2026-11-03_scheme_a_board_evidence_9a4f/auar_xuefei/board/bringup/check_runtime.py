#!/usr/bin/env python3
"""Read and compare a deployed 9a4f runtime or an offline rootfs using the frozen release manifest."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import sys

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rootfs', type=Path, help='mounted/copy rootfs for an offline read-only check')
    p.add_argument('--out', type=Path, required=True, help='new JSON file outside the checked rootfs')
    args = p.parse_args()
    live = args.rootfs is None
    if live and platform.machine() not in ('aarch64', 'arm64'):
        p.error('live checks require the target AArch64 environment; use --rootfs for an offline check')
    base = Path('/') if live else args.rootfs.resolve(strict=True)
    if not live and base == Path(base.anchor):
        p.error('choose a separate offline rootfs directory')
    if not base.is_dir():
        p.error('--rootfs must be a directory')
    out = args.out.resolve()
    if out.exists() or out == ROOT or ROOT in out.parents or (not live and base in out.parents):
        p.error('select a new output outside the package and offline rootfs')
    release = json.loads((ROOT/'board/release_9a4f.json').read_text())
    deployment = json.loads((ROOT/'board/deploy.json').read_text())
    business = deployment['business_root']
    files = {}
    def target(absolute):
        q = PurePosixPath(absolute)
        if not q.is_absolute() or '..' in q.parts:
            raise ValueError('Invalid recorded target path')
        return base / str(q).lstrip('/')
    for rel, item in release['runtime_files'].items():
        files[business+'/'+rel] = item['sha256']
    startup = str(PurePosixPath(release['runtime']).parent/'startup/config.json')
    files[startup] = release['baseline_startup_sha256']
    for unit, dropins in deployment['systemd_order'].items():
        for name in ['/etc/systemd/system/'+unit] + dropins:
            files[name] = deployment['mapping'][name]['sha256']
    checks = []
    for name, expected in files.items():
        f = target(name)
        try:
            if not f.is_file():
                raise FileNotFoundError(str(f))
            actual = sha(f)
            error = ''
        except OSError as exc:
            actual, error = None, type(exc).__name__
        checks.append({'target': name, 'expected_sha256': expected, 'actual_sha256': actual,
                       'passed': actual == expected, 'error': error})
    report = {'status': 'PASS' if all(v['passed'] for v in checks) else 'FAIL',
              'scope': 'READ_ONLY_DEPLOYED_FILE_COMPARISON',
              'mode': 'target_board_files' if live else 'offline_rootfs',
              'host_arch': platform.machine(), 'kernel': os.uname().release,
              'frozen_startup_sha256': release['baseline_startup_sha256'], 'checks': checks,
              'writes_to_services': 0, 'motion_commands': 0, 'model_inferences': 0,
              'functional_board_test_performed': False}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(report['status'], len(checks), 'file comparisons', out)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())

