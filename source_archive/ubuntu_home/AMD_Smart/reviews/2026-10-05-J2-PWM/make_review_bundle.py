"""Create an offline review snapshot; no UART, MMIO or board commands."""
from pathlib import Path
import hashlib
import json
import zipfile

HOME_ROOT = Path('/home/ghmd')
OUT = Path(__file__).resolve().parent
PROJECTS = [
    'kv260-j2-pwm-20261004',
    'kv260-j2-pwm-5s-20261005',
    'kv260-j2-pwm-continuous-20261005',
    'kv260-j2-square10-20261005',
    'kv260-j2-static-high-20261005',
]
items = {}

def add_file(path, name):
    if not path.is_file():
        raise FileNotFoundError(path)
    data = path.read_bytes()
    if len(data) > 2_000_000:
        raise ValueError(f'Oversized review member: {path}')
    if name in items:
        raise ValueError(f'Duplicate archive member: {name}')
    items[name] = (data, str(path))

add_file(OUT / '审查提示词.md', '审查提示词.md')
for project in PROJECTS:
    root = HOME_ROOT / project
    for directory in ('rtl', 'constraints', 'tests', 'board', 'scripts'):
        for path in sorted((root / directory).glob('*')):
            if path.suffix in ('.sv', '.v', '.in', '.xdc', '.py', '.tcl', '.c', '.h'):
                add_file(path, project + '/' + str(path.relative_to(root)))
    for path in sorted(root.glob('*.md')):
        add_file(path, project + '/' + path.name)
    for path in sorted(root.glob('*.json')):
        add_file(path, project + '/' + path.name)
    evidence = root / 'evidence'
    for name in ('source_identity.json', 'accessor_identity.json',
                 'accessor_review.json', 'mmio32.disassembly.txt',
                 'mmio32.elf.txt', 'static-levels-0p622-0p282-report.json',
                 'static-high-0p622v-report.json',
                 'two-row-voltage-after-reset-user-report.json'):
        path = evidence / name
        if path.exists():
            add_file(path, project + '/evidence/' + name)

selected = {
    PROJECTS[0]: ['20261005T052100.955710Z-uart-start',
                 '20261005T073342.186703Z-uart-load-idle',
                 '20261005T073601.448435Z-uart-scratch',
                 '20261005T073647.959523Z-uart-stop',
                 '20261005T074247.954619Z-uart-start'],
    PROJECTS[2]: ['20261005T085342.389377Z-uart-load-idle',
                 '20261005T085614.667848Z-uart-start'],
    PROJECTS[3]: ['20261005T092543.173663Z-build',
                 '20261005T133411.177990Z-uart-start',
                 '20261005T162239.028756Z-readonly-audit',
                 '20261005T175313.506128Z-uart-state'],
    PROJECTS[4]: ['20261005T162937.188603Z-sim',
                 '20261005T163122.523214Z-build',
                 '20261005T164503.104215Z-uart-load-idle',
                 '20261005T165914.652882Z-uart-start',
                 '20261005T171350.177174Z-uart-inspect',
                 '20261005T171505.513083Z-uart-stop',
                 '20261005T172151.276844Z-uart-inspect',
                 '20261005T174417.885624Z-uart-inspect'],
}
allowed_evidence = {'status.json', 'result.output', 'REJECTED_probe.py',
                    'build_result.json', 'io.rpt', 'timing.rpt', 'output_timing.rpt',
                    'tb_burst-run.log', 'tb_axi-run.log'}
for project, directories in selected.items():
    for directory in directories:
        folder = HOME_ROOT / project / 'evidence' / directory
        if not (folder / 'status.json').is_file():
            raise FileNotFoundError(folder / 'status.json')
        for path in sorted(folder.iterdir()):
            if path.is_file() and path.name in allowed_evidence:
                add_file(path, project + '/evidence/' + directory + '/' + path.name)

raw = HOME_ROOT / PROJECTS[0] / 'evidence/20261005T052100.955710Z-uart-start/uart.raw'
lines = raw.read_text(errors='replace').splitlines()
hit = next(i for i, line in enumerate(lines) if 'SError' in line)
excerpt = '\n'.join(lines[max(0, hit - 1):hit + 85]) + '\n'
assert 'Kernel panic' in excerpt
items['first_START_panic_uart_excerpt.txt'] = (excerpt.encode(), str(raw) + ' [excerpt]')

for name in ('2026-10-04-J2-PWM-OFFLINE.md', '2026-10-05-J2-PWM-RECOVERY.md',
             '2026-10-05-J2-PWM-CONTINUOUS.md', '2026-10-05-J2-SQUARE10.md',
             '2026-10-05-J2-STATIC-HIGH.md'):
    add_file(HOME_ROOT / 'AMD_Smart/logs/daily' / name, 'daily_logs/' + name)
ref = HOME_ROOT / 'kv260-reference-2022.2-20260930/src/kv260/platforms/vivado/kv260_ispMipiRx_vcu_DP'
add_file(ref / 'xdc/pin.xdc', 'default_reference/pin.xdc')
synth = ref / 'project/kv260_ispMipiRx_vcu_DP.gen/sources_1/bd/kv260_ispMipiRx_vcu_DP/synth/kv260_ispMipiRx_vcu_DP.v'
vlines = synth.read_text().splitlines()
snippets = []
for lo, hi in ((150, 170), (415, 430), (678, 690), (1205, 1216)):
    snippets.append('\n'.join(f'{i + 1}: {vlines[i]}' for i in range(lo - 1, hi)))
items['default_reference/synth_clock_connections_excerpt.txt'] = (
    ('\n\n'.join(snippets) + '\n').encode(), str(synth) + ' [numbered excerpts]')
add_file(HOME_ROOT / 'kv260-m3-axilite-20261002/rtl/aura_m3_regs.v',
         'dependency_reference/aura_m3_regs.v')

manifest = {name: {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                   'source': source} for name, (data, source) in sorted(items.items())}
(OUT / 'bundle_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
readme = '''这是只读审查资料快照，不是可直接部署的固件包。
先阅读 审查提示词.md。最近一次已核验状态是用户 RESET 后默认应用运行，候选 inactive。
各目录的历史日志和旧报告可能含过去的“当前运行”描述，不能覆盖最新 UART 状态。
源码/状态/报告为原件快照；first_START_panic_uart_excerpt.txt 是原始串口错误片段，默认 HDL 文件也是带行号摘录。
未加入大型 Vivado 工程、BIT/BIN/XSA 或全部原始 UART，原件在 manifest 的本机路径。
无需执行任何附带脚本即可审查；本机绝对依赖路径不保证在其他环境存在。
bundle_manifest.json 列出每份快照的 SHA256、大小和原件路径。
'''
archive = OUT / 'KV260_PWM_AI审查源码证据包.zip'
if archive.exists():
    raise FileExistsError(archive)
with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as z:
    for name, (data, _) in sorted(items.items()):
        z.writestr(name, data)
    z.writestr('bundle_manifest.json', (OUT / 'bundle_manifest.json').read_bytes())
    z.writestr('阅读说明.txt', readme)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name, meta in manifest.items():
        assert hashlib.sha256(z.read(name)).hexdigest() == meta['sha256']
print(json.dumps({'archive': str(archive), 'files': len(manifest),
                  'archive_bytes': archive.stat().st_size,
                  'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                  'zip_crc_and_member_hashes_verified': True}, ensure_ascii=False))
