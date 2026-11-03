#!/usr/bin/env python3
"""Reconstruct fixed patched sources in a fresh directory; no network or board access."""
import argparse
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
from common import PACKAGE, Run, clean_env, lock, require, sha


def extract_archive(archive, destination, allow_symlinks=False):
    destination.mkdir(parents=True, exist_ok=False)
    seen = set()
    with tarfile.open(archive, 'r:*') as source:
        for member in source.getmembers():
            relative = PurePosixPath(member.name)
            require(not relative.is_absolute() and '..' not in relative.parts,
                    'Unsafe archive path: ' + member.name)
            require(member.name not in seen, 'Duplicate archive path: ' + member.name)
            seen.add(member.name)
            target = destination.joinpath(*relative.parts)
            require(destination.resolve() in target.parent.resolve().parents or
                    target.parent.resolve() == destination.resolve(),
                    'Archive parent escapes destination: ' + member.name)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.extractfile(member) as data, target.open('xb') as output:
                    shutil.copyfileobj(data, output)
                target.chmod(member.mode & 0o777)
            elif member.issym() and allow_symlinks:
                link = PurePosixPath(member.linkname)
                require(not link.is_absolute(), 'Absolute archive symlink: ' + member.name)
                resolved = (target.parent / member.linkname).resolve()
                require(destination.resolve() in resolved.parents or resolved == destination.resolve(),
                        'Archive symlink escapes destination: ' + member.name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(member.linkname)
            else:
                raise RuntimeError('Unsupported archive member: ' + member.name)


def files(directory):
    return {str(p.relative_to(directory)): sha(p) for p in directory.rglob('*') if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    require(workspace != PACKAGE and PACKAGE not in workspace.parents,
            'Use a build workspace outside the submission package')
    require(not workspace.exists(), 'Workspace already exists; preserve it and use a fresh path')
    versions = lock()
    archive = PACKAGE / 'sources/xrt_baseline.tar.gz'
    require(sha(archive) == versions['xrt_archive_sha256'], 'XRT archive hash mismatch')
    for name, key in [('dfx_watch_dedup.patch', 'dfx_patch_sha256'),
                      ('zocl_ref_balance.patch', 'zocl_patch_sha256')]:
        require(sha(PACKAGE / 'patches' / name) == versions[key], 'Patch hash mismatch: ' + name)
    workspace.mkdir(parents=True, exist_ok=False)
    run = Run(workspace / 'logs/prepare_sources', 'Offline patch reconstruction in an independent workspace')
    try:
        source = workspace / 'sources'
        source.mkdir()
        shutil.copytree(PACKAGE / 'sources/dfx_mgr_baseline', source / 'dfx_mgr')
        shutil.copytree(PACKAGE / 'sources/libdfx', source / 'libdfx')
        extract_archive(archive, source / 'xrt')
        manifest = json.loads((PACKAGE / 'sources/xrt_tree.json').read_text())
        expected = {name: record['sha256'] for name, record in manifest.items()}
        require(files(source / 'xrt') == expected, 'XRT baseline tree hash mismatch')
        for component, patch in [('dfx_mgr', 'dfx_watch_dedup.patch'), ('xrt', 'zocl_ref_balance.patch')]:
            argv = ['patch', '--batch', '--forward', '--fuzz=0', '-p1', '-i', str(PACKAGE/'patches'/patch)]
            run.command('check-'+component, argv + ['--dry-run'], source/component, clean_env())
            run.command('apply-'+component, argv, source/component, clean_env())
        expected_dfx = files(PACKAGE / 'sources/dfx_mgr_patched')
        require(files(source / 'dfx_mgr') == expected_dfx, 'DFX reconstructed tree differs from tested source')
        for name in versions['zocl_changed_files']:
            expected[name] = sha(PACKAGE / 'sources/zocl_patched_files' / name)
        require(files(source / 'xrt') == expected, 'ZOCL reconstruction changed an unexpected file')
        run.state.update(dfx_files_verified=len(expected_dfx), xrt_files_verified=len(expected),
                         source_lock_sha256=sha(PACKAGE / 'config/source_lock.json'))
        run.finish(True)
    except Exception as error:
        run.finish(False, error)
        raise
    print(json.dumps({'passed': True, 'workspace': str(workspace), 'board_access': False}))


if __name__ == '__main__':
    main()
