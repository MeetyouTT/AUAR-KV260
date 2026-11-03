#!/usr/bin/env python3
"""Prepare verified runtime inputs on the host; no board commands or installation."""
import datetime
import hashlib
import json
import os
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DFX = Path('/home/ghmd/kv260-dfx-manager-repair-20261002')
ZOCL = Path('/home/ghmd/kv260-overlay-repair-20261002')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    manager = DFX / 'release/kv260-dfx-watch-reviewed/dfx-mgrd'
    module = ZOCL / 'artifacts/patched/zocl.ko'
    assert sha(manager) == 'db9c25f09f1178177884b1114c57f32c076f1e7f9cdd0d12b7a896039038a46c'
    assert sha(module) == '5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412'
    prior = json.loads((DFX / 'evidence/validation_summary.json').read_text())
    assert prior['board_verified'] and prior['original_baseline_restored']
    bundle = ROOT / 'bundle/kv260-runtime-reviewed'
    bundle.mkdir(parents=True, exist_ok=False)
    inputs = {}
    for source, name in (
        (manager, 'dfx-mgrd'), (module, 'zocl.ko'),
        (DFX / 'artifacts/watch-dedup.patch', 'watch-dedup.patch'),
        (DFX / 'release/kv260-dfx-watch-reviewed/RUNTIME_REQUIREMENTS.json',
         'RUNTIME_REQUIREMENTS.json'),
        (ROOT / 'NEXT_STEPS.md', 'NEXT_STEPS.md')
    ):
        shutil.copy2(source, bundle / name)
        assert sha(source) == sha(bundle / name)
        inputs[name] = {'source': str(source), 'bytes': source.stat().st_size,
                        'sha256': sha(source)}
    (bundle / 'BASELINE_INPUTS.json').write_text(
        json.dumps(prior['final']['original_files'], indent=2) + '\n')
    (bundle / 'PROVENANCE.json').write_text(json.dumps({
        'scope': 'Host preparation only; reuses the exact previously board-tested binaries',
        'new_binary_compilation': False, 'new_board_activation': False,
        'candidate_inputs': inputs,
        'previous_combined_board_validation': str(DFX / 'evidence/validation_summary.json'),
        'previous_combined_summary_sha256': sha(DFX / 'evidence/validation_summary.json'),
        'previous_source_index_sha256': sha(DFX / 'EVIDENCE.sha256'),
        'tested_kernel': '5.15.36-xilinx-v2022.2',
        'patched_zocl_srcversion': '9BDC942A6014BCCBD1DCB78',
        'module_parameters': {'enable_xgq_ert': '1'},
        'startup_socket_protocol': 'SOCK_SEQPACKET',
        'ready_for_runtime_use_after_fresh_board_preflight': True,
        'automatic_installer_included': False
    }, ensure_ascii=False, indent=2) + '\n')
    members = sorted(bundle.iterdir())
    (bundle / 'SHA256SUMS').write_text(
        ''.join(sha(p) + '  ' + p.name + '\n' for p in members))
    archive = ROOT / 'bundle/kv260-runtime-reviewed.tar.gz'
    with tarfile.open(archive, 'w:gz') as packed:
        packed.add(bundle, arcname=bundle.name)
    with tarfile.open(archive, 'r:gz') as packed:
        for member in packed.getmembers():
            assert not member.name.startswith('/') and '..' not in Path(member.name).parts
            if member.isfile():
                expected = bundle / Path(member.name).name
                assert hashlib.sha256(packed.extractfile(member).read()).hexdigest() == sha(expected)
    checks = {str(p.relative_to(bundle)): {'sha256': sha(p), 'bytes': p.stat().st_size}
              for p in sorted(bundle.iterdir())}
    created = datetime.datetime.now(datetime.timezone.utc).isoformat()
    record = {
        'created_utc': created, 'host_preparation_passed': True,
        'board_activation_performed': False,
        'usb_serial_directory_present': Path('/dev/serial/by-id').is_dir(),
        'archive': str(archive), 'archive_bytes': archive.stat().st_size,
        'archive_sha256': sha(archive), 'members': checks,
        'archive_member_readback_hashes_passed': True,
        'inputs': inputs, 'next_steps': str(ROOT / 'NEXT_STEPS.md')
    }
    (ROOT / 'PREPARATION_STATUS.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    daily = Path('/home/ghmd/AMD_Smart/logs/daily/2026-10-02-RUNTIME-PREP.md')
    with daily.open('x') as stream:
        stream.write('# 2026-10-02：运行时联合启用准备\n\n'
                     '已阅读最新 DFX/ZOCL/M3 封存结果，准备联合输入包。DFX manager 和修复 ZOCL '
                     '逐字节匹配已板测二进制；压缩包成员回读哈希通过。未重新编译、修改原产物或执行板端切换。\n\n'
                     '本次 Ubuntu 未发现 /dev/serial/by-id，未取得新的板端实时状态；旧恢复结果只作为历史证据。'
                     '接回备用卡和 USB 串口后，先重新预检与备份，再受控启用、扩大运行观察及确认恢复入口。'
                     '无需重新烧录 SD 卡。30 轮切换和 30 分钟采样属于计划，尚未执行。\n\n'
                     '原程序中两项软件缺陷、重复 /boot 配置、overlay 属性警告和既有 DRC/时序限制保持记录。'
                     '永久启用、重启验收、长期验证和 PWM 尚未完成。\n\n'
                     '方案：[NEXT_STEPS.md](' + str(ROOT / 'NEXT_STEPS.md') + ')。\n'
                     '联合包：' + str(archive) + '\n\n'
                     '准备时间：' + created + '。\n')
    files = sorted((p for p in ROOT.rglob('*') if p.is_file()),
                   key=lambda p: str(p.relative_to(ROOT)))
    files.append(daily)
    index = ROOT / 'PREPARATION.sha256'
    index.write_text(''.join(sha(p) + '  ' + os.path.relpath(p, ROOT) + '\n' for p in files))
    print(json.dumps({'prepared': True, 'board_activation_performed': False,
                      'archive': str(archive), 'bytes': archive.stat().st_size,
                      'sha256': sha(archive), 'usb_serial_directory_present':
                      record['usb_serial_directory_present']}))


if __name__ == '__main__':
    main()
