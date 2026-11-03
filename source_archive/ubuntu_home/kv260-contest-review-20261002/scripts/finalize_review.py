#!/usr/bin/env python3
"""Save the bounded rule conclusions and seal this read-only review."""
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DFX = Path('/home/ghmd/kv260-dfx-manager-repair-20261002')
ZOCL = Path('/home/ghmd/kv260-overlay-repair-20261002')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    initial = json.loads((ROOT / 'input_manifest.json').read_text())
    assert sha(initial['original_zip']) == initial['zip_sha256']
    report = (ROOT / 'CONTEST_REVIEW.md').read_text()
    assert '§' not in report
    for link in re.findall(r'\]\(([^)]+)\)', report):
        if link.startswith(('https://', 'http://')):
            continue
        assert Path(link).is_file(), 'Missing evidence link: ' + link
    licenses = ROOT / 'license_evidence'
    licenses.mkdir(exist_ok=False)
    license_rows = []
    for source, name in (
        (DFX / 'sources/dfx-mgr/LICENSE', 'dfx_mgr_license.txt'),
        (ZOCL / 'sources/XRT_patched/src/runtime_src/core/edge/drm/zocl/LICENSE',
         'zocl_license.txt')
    ):
        shutil.copy2(source, licenses / name)
        assert sha(source) == sha(licenses / name)
        license_rows.append({'original': str(source), 'copy': str(licenses / name),
                             'sha256': sha(source)})
    dfx_base = DFX / 'sources/dfx-mgr'
    dfx_patch = DFX / 'sources/dfx-mgr-patched'
    zocl_base = ZOCL / 'sources/XRT_baseline/src/runtime_src/core/edge/drm/zocl'
    zocl_patch = ZOCL / 'sources/XRT_patched/src/runtime_src/core/edge/drm/zocl'
    declarations = []
    for base, patched, filename in (
        (dfx_base, dfx_patch, 'src/daemon_helper.c'),
        (zocl_base, zocl_patch, 'cu.c'),
        (zocl_base, zocl_patch, 'include/zocl_drv.h'),
        (zocl_base, zocl_patch, 'zocl_drv.c')
    ):
        original = (base / filename).read_text()
        changed = (patched / filename).read_text()
        old_tag = re.search(r'SPDX-License-Identifier:\s*([^*\n]+)', original)[1].strip()
        new_tag = re.search(r'SPDX-License-Identifier:\s*([^*\n]+)', changed)[1].strip()
        assert old_tag == new_tag
        assert original.splitlines()[:20] == changed.splitlines()[:20]
        declarations.append({
            'original': str(base / filename), 'patched': str(patched / filename),
            'spdx': new_tag, 'first_twenty_lines_unchanged': True,
            'original_sha256': sha(base / filename),
            'patched_sha256': sha(patched / filename)
        })
    pages = (ROOT / 'official_amd_2026.txt').read_text().split('\f')
    excerpt = ''.join('=== PDF PAGE %d ===\n%s\n' % (page, pages[page - 1])
                      for page in (22, 23, 24, 25, 28))
    (ROOT / 'rules_excerpt.txt').write_text(excerpt)
    summary = {
        'reviewed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'track': '3.3 autonomous topic, beginner group',
        'main_conclusion': 'No conflicting clause for the two open-source runtime repairs found in the supplied 2026 AMD guide',
        'basis': 'Supplied guide, not a ruling from the organizer or confirmation of the latest detailed rules',
        'rule_pdf_sha256': sha(ROOT / 'inputs/official_amd_2026.pdf'),
        'rule_text_sha256': sha(ROOT / 'official_amd_2026.txt'),
        'main_pdf_pages': [22, 23, 24, 25],
        'final_detailed_rules_clause_pdf_page': 28,
        'original_zip_unchanged': True,
        'new_source_code_changes': False, 'new_board_operations': False,
        'source_license_headers_preserved': declarations,
        'license_evidence': license_rows,
        'verified_online_source': {
            'url': 'https://www.amd.com/en/products/system-on-modules/kria/k26/kv260-vision-starter-kit.html',
            'fact': 'Device Support: Zynq UltraScale+ MPSoC',
            'role': 'Primary AMD device-family confirmation'
        },
        'online_rule_lookup': {
            'official_urls_attempted': [
                'https://www.fpgachina.cn/',
                'http://www.fpgachina.cn/',
                'https://www.fpgachina.cn/home',
                'https://fpga2026.fpgachina.cn/'
            ],
            'observed_result': 'Browser returned Internal Error for these pages; search did not provide a readable current 2026 AMD detailed scoring rule',
            'latest_detailed_rules_verified': False,
            'absence_of_updates_not_asserted': True
        },
        'conditional_items': [
            'Explain Vivado/Vitis 2022.2 and preserve a reproducible fixed toolchain and build',
            'Disclose upstream components, licenses, exact patches and original contribution',
            'Submit visible model collaboration records and reusable skill package',
            'Export a complete project with English paths, current status and accurate reports',
            'Complete the intended application and remaining board validation',
            'Confirm final detailed scoring and submission rules'
        ],
        'pynq_mandatory_in_supplied_guide': False,
        'self_designed_dpu_mandatory_in_supplied_guide': False,
        'whole_entry_compliance_verified': False,
        'report': str(ROOT / 'CONTEST_REVIEW.md')
    }
    (ROOT / 'review_summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    local_date = datetime.datetime.now().astimezone().date().isoformat()
    daily = Path('/home/ghmd/AMD_Smart/logs/daily') / (local_date + '-CONTEST-REVIEW.md')
    with daily.open('x') as stream:
        stream.write('# ' + local_date + '：自主选题初级组规则核对\n\n'
                     '读取用户项目.zip，435 成员中选择官方 AMD 2026 指南及四份项目材料；'
                     '原 ZIP 哈希首尾一致，没有执行归档内代码。PDF 共 28 页，重点核对 PDF 页 22–25 的第 3.3 节及页 28 最终细则条款。\n\n'
                     '在所给指南范围内，DFX manager 和 ZOCL 开源运行时修复未发现冲突；'
                     'PS/RTL/HLS 等实现方式开放，PYNQ 为推荐，其他工具版本允许附说明与复现条件。'
                     '现有四个修改文件的 SPDX 与前二十行声明保留，DFX 为 MIT，ZOCL 三文件为 GPL-2.0 OR Apache-2.0。\n\n'
                     '尚需工具版本与完整复现说明、上游和补丁声明、真实可见大模型协作记录、skill/、'
                     '完整英文路径工程导出及完整应用实测。当前测试 bundle 和原 ZIP 不能直接宣称已是完整参赛提交物。'
                     '未核验报名证件或最终评分细则；官网访问未取得可读最新细则，不能宣称没有更新。'
                     '器件类别另由 AMD KV260 官方页核实为 Zynq UltraScale+ MPSoC。\n\n'
                     '本次没有继续改源码、切换板端或公开仓库；原封存材料保留。\n\n'
                     '报告：[CONTEST_REVIEW.md](' + str(ROOT / 'CONTEST_REVIEW.md') + ')。\n')
    files = sorted(p for p in ROOT.rglob('*') if p.is_file())
    files.append(daily)
    index = ROOT / 'REVIEW.sha256'
    index.write_text(''.join(sha(p) + '  ' + os.path.relpath(p, ROOT) + '\n'
                            for p in files))
    result = subprocess.run(['sha256sum', '-c', '--quiet', index.name], cwd=ROOT,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    verification = {
        'passed': result.returncode == 0, 'entries': len(files),
        'index_sha256': sha(index), 'exit_code': result.returncode,
        'stdout': result.stdout, 'stderr': result.stderr,
        'original_zip_unchanged': sha(initial['original_zip']) == initial['zip_sha256']
    }
    (ROOT / 'REVIEW_VERIFY.json').write_text(
        json.dumps(verification, ensure_ascii=False, indent=2) + '\n')
    assert verification['passed'] and verification['original_zip_unchanged']
    print(json.dumps({'review_complete': True, 'entries_verified': len(files),
                      'original_zip_unchanged': True, 'license_headers_preserved': 4,
                      'whole_entry_compliance_verified': False,
                      'report': str(ROOT / 'CONTEST_REVIEW.md')}))


if __name__ == '__main__':
    main()
