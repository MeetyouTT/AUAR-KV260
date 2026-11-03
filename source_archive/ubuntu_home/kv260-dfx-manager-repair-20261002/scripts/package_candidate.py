#!/usr/bin/env python3
"""Package the board-tested binary and its provenance, without installation."""
import datetime
import hashlib
import json
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    summary = json.loads((ROOT / 'evidence/validation_summary.json').read_text())
    assert summary['board_verified'] and summary['original_baseline_restored']
    release = ROOT / 'release'
    release.mkdir(exist_ok=False)
    bundle = release / 'kv260-dfx-watch-reviewed'
    bundle.mkdir()
    for source, name in (
        (ROOT / summary['candidate']['path'], 'dfx-mgrd'),
        (ROOT / 'artifacts/watch-dedup.patch', 'watch-dedup.patch')
    ):
        shutil.copy2(source, bundle / name)
        assert sha(source) == sha(bundle / name)
    (bundle / 'SOURCE_VERSION.json').write_text(json.dumps({
        'dfx_mgr_commit': 'bc06691eb35d7f0acb7c2508b6d050d77b0264a0',
        'libdfx_header_commit': 'f2b7bbca9d6936141024becfb92266600eeefc2b',
        'changed_source': ['src/daemon_helper.c'],
        'candidate_sha256': summary['candidate']['sha256'],
        'candidate_bytes': summary['candidate']['bytes'],
        'finite_board_validation_passed': True,
        'original_baseline_restored': True,
        'permanently_installed': False,
        'tested_archive': {
            'path': 'bundle-v2/kv260-dfx-watch-candidate.tar.gz',
            'sha256': '1718a46975f046ea018cf0b25b8373051dde9e0f5347185956775e77f87b39f2'
        },
        'host_report': str(ROOT / 'DFX_MANAGER_REPAIR_REPORT.md')
    }, ensure_ascii=False, indent=2) + '\n')
    runtime = json.loads((ROOT / 'evidence/20261003T040248.123957Z-runtime-review/status.json').read_text())
    (bundle / 'RUNTIME_REQUIREMENTS.json').write_text(json.dumps({
        'machine': 'AArch64',
        'tested_os': 'PetaLinux 2022.2_release_S10071807',
        'tested_kernel': '5.15.36-xilinx-v2022.2',
        'interpreter': '/lib/ld-linux-aarch64.so.1',
        'needed': summary['candidate']['needed'],
        'tested_libraries': [
            {k: row[k] for k in ('image_path', 'bytes', 'sha256')}
            for row in runtime['image_libraries']
        ],
        'startup_socket': '/tmp/dfx-mgrd.socket',
        'startup_socket_type': 'SOCK_SEQPACKET',
        'driver_for_repeated_overlay_removal_test': {
            'srcversion': '9BDC942A6014BCCBD1DCB78',
            'enable_xgq_ert': '1',
            'note': 'Previously verified repaired ZOCL; not rebuilt or included in this package'
        },
        'original_driver_restored_after_test': '0991D1B457855C8987936E6',
        'validation_scope': '1000 list queries; 50 directory create/delete cycles; 3 official app reload cycles; official/M3 identical-image inference'
    }, ensure_ascii=False, indent=2) + '\n')
    (bundle / 'README.md').write_text("""# KV260 DFX manager 修复候选

这里的 dfx-mgrd 与实际板测的二进制逐字节一致；补丁和运行库要求随包保存。它修复重复目录扫描耗尽内部 watch 表的问题。

本包没有安装脚本、驱动或 FPGA 固件。原板卡现已恢复原管理器、原 ZOCL 和官方应用；不会因为保留本包而自动启用修复。

再次启用前应核对备用卡、内核、运行库哈希、活动应用和 DRM 占用，重新保存当时基线；采用新的受控计划临时启动本候选。就绪检查必须使用 SOCK_SEQPACKET。

反复卸载 overlay 的已通过板测使用了此前修复 ZOCL，不能据此认为原 ZOCL 的退出引用错误也已消失。候选日志应独立保存，结束时通过原程序的 SIGINT 处理刷新完整日志，再核对错误数量和哈希，恢复原服务、原驱动、官方应用和 VART 配置。

bundle-v2 是历史测试输入，其中原就绪函数错误使用了 SOCK_STREAM；实际续跑的独立脚本覆盖为 SOCK_SEQPACKET 后通过。不要重放该历史包的旧启动探针或已执行过的控制器。

本轮有限验证通过；长期运行、并发加载、内存增长、断电恢复和永久安装尚未验收。PWM 未加入。
""")
    members = sorted(p for p in bundle.iterdir() if p.is_file())
    (bundle / 'SHA256SUMS').write_text(''.join(
        sha(p) + '  ' + p.name + '\n' for p in members))
    archive = release / 'kv260-dfx-watch-reviewed.tar.gz'
    with tarfile.open(archive, 'w:gz') as packed:
        packed.add(bundle, arcname=bundle.name, recursive=True)
    expected = {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)}
                for p in bundle.iterdir() if p.is_file()}
    with tarfile.open(archive, 'r:gz') as packed:
        rows = [m for m in packed.getmembers() if m.isfile()]
        assert len(rows) == len(expected)
        assert all(not m.name.startswith('/') and '..' not in Path(m.name).parts for m in packed.getmembers())
        for member in rows:
            data = packed.extractfile(member).read()
            assert hashlib.sha256(data).hexdigest() == expected[Path(member.name).name]['sha256']
    (release / 'manifest.json').write_text(json.dumps({
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'archive': str(archive.relative_to(ROOT)),
        'bytes': archive.stat().st_size, 'sha256': sha(archive),
        'members': expected,
        'binary_matches_board_tested_candidate': True,
        'archive_readback_hashes_passed': True,
        'packaging_only_not_redeployed': True
    }, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'archive': str(archive), 'sha256': sha(archive),
                      'binary_matches_board_tested_candidate': True}))


if __name__ == '__main__':
    main()
