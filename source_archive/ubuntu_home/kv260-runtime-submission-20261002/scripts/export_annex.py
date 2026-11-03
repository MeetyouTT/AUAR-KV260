#!/usr/bin/env python3
"""Export verified local inputs to a new annex. Never access the target board."""
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
DFX = Path('/home/ghmd/kv260-dfx-manager-repair-20261002')
ZOCL = Path('/home/ghmd/kv260-overlay-repair-20261002')
PREP = Path('/home/ghmd/kv260-runtime-enable-20261002')
CONTEST = Path('/home/ghmd/kv260-contest-review-20261002')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    payload = ROOT / 'payload'
    payload.mkdir(exist_ok=False)
    evidence = ROOT / 'evidence'
    evidence.mkdir(exist_ok=False)
    record = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'board_access': False, 'inputs': [], 'preserved_indexes': [], 'passed': False}
    try:
        for owner, index in [(DFX, 'EVIDENCE.sha256'), (ZOCL, 'EVIDENCE.sha256'),
                             (ZOCL, 'BOARD_EVIDENCE.sha256'), (PREP, 'PREPARATION.sha256'),
                             (CONTEST, 'REVIEW.sha256')]:
            path = owner / index
            result = subprocess.run(['sha256sum', '-c', '--quiet', str(path)], cwd=str(owner),
                                    text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            item = {'index': str(path), 'sha256': sha(path), 'exit_code': result.returncode,
                    'entries': len(path.read_text().splitlines()), 'stderr': result.stderr}
            record['preserved_indexes'].append(item)
            if result.returncode:
                raise RuntimeError('Preserved evidence check failed: ' + str(path))

        def copy(source, relative):
            dest = payload / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(source), str(dest))
            original = sha(source)
            if original != sha(dest):
                raise RuntimeError('Copy mismatch: ' + str(source))
            record['inputs'].append({'source': str(source), 'export': relative,
                                     'sha256': original, 'bytes': dest.stat().st_size})

        for name, directory in [('dfx_mgr_baseline', DFX/'sources/dfx-mgr'),
                                ('dfx_mgr_patched', DFX/'sources/dfx-mgr-patched'),
                                ('libdfx', DFX/'sources/libdfx')]:
            for path in sorted(directory.rglob('*')):
                if path.is_file():
                    if path.is_symlink():
                        raise RuntimeError('Unexpected source symlink: ' + str(path))
                    copy(path, 'sources/' + name + '/' + str(path.relative_to(directory)))

        copy(DFX/'artifacts/watch-dedup.patch', 'patches/dfx_watch_dedup.patch')
        copy(ZOCL/'evidence/source_review/candidate-patch.log', 'patches/zocl_ref_balance.patch')
        xrt = ZOCL / 'sources/XRT_patched'
        commit = '43926231f7183688add2dccfd391b36a1f000bea'
        actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=str(xrt), text=True).strip()
        if actual != commit:
            raise RuntimeError('XRT commit changed')
        changed = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=str(xrt), text=True).splitlines()
        expected = ['src/runtime_src/core/edge/drm/zocl/cu.c',
                    'src/runtime_src/core/edge/drm/zocl/include/zocl_drv.h',
                    'src/runtime_src/core/edge/drm/zocl/zocl_drv.c']
        if changed != expected:
            raise RuntimeError('Unexpected XRT source changes: ' + repr(changed))
        actual_patch = subprocess.check_output(['git', 'diff', '--binary', 'HEAD'], cwd=str(xrt))
        if actual_patch != (payload/'patches/zocl_ref_balance.patch').read_bytes():
            raise RuntimeError('ZOCL patch no longer matches working source')
        archive = payload/'sources/xrt_baseline.tar.gz'
        temp = evidence/'xrt_baseline.tar'
        subprocess.run(['git', 'archive', '--format=tar', '--output='+str(temp), commit],
                       cwd=str(xrt), check=True)
        with temp.open('rb') as source, archive.open('xb') as dest:
            with gzip.GzipFile(filename='', fileobj=dest, mode='wb', mtime=0) as packed:
                shutil.copyfileobj(source, packed)
        # Retain the uncompressed archive only in host evidence, outside the distributable payload.
        tree_manifest = {}
        with tarfile.open(archive, 'r:gz') as bundle:
            for member in bundle.getmembers():
                if member.isfile():
                    data = bundle.extractfile(member).read()
                    tree_manifest[member.name] = {'sha256': hashlib.sha256(data).hexdigest(), 'mode': member.mode}
                elif not member.isdir():
                    raise RuntimeError('Unsupported archive member: ' + member.name)
        for path in expected:
            copy(xrt/path, 'sources/zocl_patched_files/'+path)
        write(payload/'sources/xrt_tree.json', tree_manifest)
        copy(ZOCL/'evidence/image_files/kernel.config', 'config/kernel.config')

        for source, target in [(DFX/'sources/dfx-mgr/LICENSE', 'licenses/dfx_mgr_license.txt'),
                               (DFX/'sources/libdfx/LICENSE.md', 'licenses/libdfx_license.txt'),
                               (xrt/'LICENSE', 'licenses/xrt_license.txt'),
                               (xrt/'src/runtime_src/core/edge/drm/zocl/LICENSE', 'licenses/zocl_license.txt')]:
            copy(source, target)

        summary = json.loads((DFX/'evidence/validation_summary.json').read_text())
        copy(DFX/summary['candidate']['path'], 'tested_inputs/dfx-mgrd')
        copy(ZOCL/'artifacts/patched/zocl.ko', 'tested_inputs/zocl.ko')
        for name in ['BASELINE_INPUTS.json','RUNTIME_REQUIREMENTS.json','PROVENANCE.json']:
            copy(PREP/'bundle/kv260-runtime-reviewed'/name, 'config/'+name.lower())
        for owner, source, target in [
            (DFX,'evidence/validation_summary.json','historical/dfx_validation_summary.json'),
            (DFX,'evidence/host_validation_summary.json','historical/host_validation_summary.json'),
            (DFX,'evidence/board_command_ledger.json','historical/board_command_ledger.json'),
            (DFX,'DFX_MANAGER_REPAIR_REPORT.md','historical/dfx_manager_repair_report.md'),
            (ZOCL,'BOARD_REPAIR_REPORT.md','historical/zocl_board_repair_report.md'),
            (ZOCL,'OVERLAY_REPAIR_REPORT.md','historical/overlay_repair_report.md'),
            (CONTEST,'CONTEST_REVIEW.md','historical/contest_review.md')]:
            copy(owner/source, 'evidence/'+target)
        ledger = json.loads((DFX/'evidence/board_command_ledger.json').read_text())
        for command in ledger['commands']:
            copy(DFX/command['output'], 'evidence/board_outputs/'+Path(command['output']).name)
        for result in json.loads((DFX/'evidence/host_validation_summary.json').read_text())['results']:
            copy(DFX/result['log'], 'evidence/host_outputs/'+Path(result['log']).name)
        for path in sorted((ZOCL/'evidence/build').glob('*/status.json')):
            copy(path, 'evidence/kernel_build/'+path.parent.name+'/status.json')
        original_source_map = json.loads((DFX/'evidence/source_final_review.json').read_text())
        copy(DFX/'evidence/source_final_review.json', 'evidence/historical/dfx_source_review.json')

        lock = {'format_version': 1, 'scope': 'Runtime source and evidence annex; not the complete AURA entry',
                'dfx_mgr_commit': 'bc06691eb35d7f0acb7c2508b6d050d77b0264a0',
                'libdfx_header_commit': 'f2b7bbca9d6936141024becfb92266600eeefc2b',
                'xrt_commit': commit, 'xrt_url': 'https://github.com/Xilinx/XRT.git',
                'kernel_commit': '19984dd147fa7fbb7cb14b17400263ad0925c189',
                'kernel_url': 'https://github.com/Xilinx/linux-xlnx.git',
                'kernel_release': '5.15.36-xilinx-v2022.2',
                'kernel_config_sha256': sha(payload/'config/kernel.config'),
                'xrt_archive_sha256': sha(archive),
                'dfx_patch_sha256': sha(payload/'patches/dfx_watch_dedup.patch'),
                'zocl_patch_sha256': sha(payload/'patches/zocl_ref_balance.patch'),
                'link_libdfx_sha256': '1acb6c9ac1f27e0ea769dc231f32db5565f6ca02a53be00e969fc48c038d290f',
                'board_tested_binaries': {
                    name: {'bytes': (payload/'tested_inputs'/name).stat().st_size,
                           'sha256': sha(payload/'tested_inputs'/name), 'new_build_this_turn': False}
                    for name in ['dfx-mgrd', 'zocl.ko']},
                'zocl_changed_files': expected,
                'tested_card_cid': '0353445345333247805558c00401a100',
                'candidate_zocl_srcversion': '9BDC942A6014BCCBD1DCB78',
                'stock_zocl_srcversion': '0991D1B457855C8987936E6',
                'permanently_installed': False, 'sustained_test_completed': False}
        write(payload/'config/source_lock.json', lock)
        record['source_counts'] = {'dfx_baseline': len(list((payload/'sources/dfx_mgr_baseline').rglob('*'))),
                                   'xrt_tracked_files': len(tree_manifest)}
        record['passed'] = True
    finally:
        write(evidence/'export_state.json', record)
    print(json.dumps({'passed': record['passed'], 'copied_files': len(record['inputs']),
                      'xrt_files': len(tree_manifest), 'payload': str(payload)}))


if __name__ == '__main__':
    main()
