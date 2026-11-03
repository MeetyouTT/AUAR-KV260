#!/usr/bin/env python3
"""Audit current source roles and render the reviewed delivery directory design.

This does not import application modules, relocate source, or access devices.
"""
import ast
import csv
from datetime import datetime, timezone
import hashlib
import html
import io
import json
from pathlib import Path
import re
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'report/architecture'
STAGE = ROOT / 'submission/aura_junior'
MARKER = '<!-- aura-architecture-generated -->'
DETAIL = '<!-- aura-structure-details -->'


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.suffix in ('.md', '.html'):
        if MARKER not in path.read_text(encoding='utf-8'):
            raise ValueError('Refusing to replace unmarked document: ' + str(path))
    path.write_text(text, encoding='utf-8')


def dump(path, value):
    write(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def csv_text(rows, fields):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ' ; '.join(v) if isinstance(v, list) else v for k, v in row.items()})
    return stream.getvalue()


def path_for(name):
    p = Path(name)
    return p if p.is_absolute() else ROOT / p


def role_for(name):
    exact = {
        'host/model_service/client.py': ('src/ps/runtime/model_client', 'PS 异步客户端，名称位于 host 但由 AuraRuntime 创建'),
        'host/model_service/protocol.py': ('src/shared/contracts/interaction', 'PS/主机共用媒体类型与交付规则'),
        'host/model_service/schema.py': ('src/shared/contracts/interaction', '媒体协议兼容导出'),
        'board/runtime/audio/selected_voice.py': ('src/host/tts', 'Windows 选定 Qwen 声线合成实现'),
        'board/runtime/audio/asr.py': ('src/host/asr', '旧 ASR 实现来源，最终主机适配待接'),
        'board/runtime/audio/tts.py': ('src/ps/audio', '混合旧合成后端与播放类；仅作主要归属，需拆分适配'),
        'board/runtime/character.py': ('src/shared/utilities', '角色设定数据/逻辑；UI 与模型消费位置须按最终调用冻结'),
        'board/motion/guard.py': ('src/ps/motion/simulation_guard', '运行时直接依赖的软件模拟后端'),
        'board/motion/vsrv_driver.py': ('src/ps/motion/hw_access', '旧相对租约 ABI 的注入式驱动参考'),
        'common/contracts.py': ('src/shared/contracts', '帧、轨迹、证据与软件运动命令类型'),
        'tools/aura_project.py': ('src/ps/runtime', '当前组合/诊断/模拟入口；真实运行能力分别核验'),
        'tools/aura_host.py': ('sim/software', '三阶段媒体 fixture 联调入口，不是真实模型服务'),
        'tools/dialogue_host_ollama.py': ('src/host/vlm', '既有文字服务/候选模型适配'),
        'tools/selected_voice_service.py': ('src/host/tts', 'PC 选定声线服务，仍有演示/UI 依赖'),
    }
    if name in exact:
        return exact[name]
    prefixes = [
        ('board/runtime/dialogue_client/', 'src/ps/runtime/model_client', '旧文字客户端与适配'),
        ('board/runtime/audio/', 'src/ps/audio', '旧音频/可选门控参考；逐个冻结实际板端功能'),
        ('board/runtime/', 'src/ps/runtime', '板端运行时/状态/校验或模拟辅助'),
        ('board/interaction/', 'src/ui', 'UI/播放器源码；PC 基线与最终板端验收分开'),
        ('board/vision/', 'src/ps/vision', '采集/检测/跟踪软件'),
        ('board/identity/', 'src/ps/identity', '身份特征适配与存储'),
        ('board/fusion/', 'src/ps/fusion', '目标/时效/调度/说话人复核'),
        ('board/motion/', 'src/ps/motion', '运动服务及后端'),
        ('common/', 'src/shared/utilities', '公共配置/时钟与初始化'),
        ('host/', 'src/host/service', '主机流水线/候选后端及初始化'),
        ('tests/', 'sim/software', '软件验证源；是否已运行见原测试记录'),
    ]
    for prefix, area, note in prefixes:
        if name.startswith(prefix):
            return area, note
    base = Path(name).name
    if name.startswith('tools/') and base.startswith(('verify_', 'check_', 'run_tests')):
        return 'sim/software', '历史专项验证工具；最终版本选择与执行待核对'
    if name.startswith('tools/') and base.startswith(('demo_', 'realtime_', 'facial_', 'mouth_', 'show_demo', 'selected_voice_demo')):
        return 'src/ui', 'PC 演示/音画交互基线；不能整目录判为 KV260 已部署'
    if name.startswith(('scripts/', 'tools/')):
        return 'build/scripts/application', '开发/资源生成/打包工具；正式交付入口需逐个选择'
    raise ValueError('Unclassified Python source: ' + name)


def audit_sources():
    paths = sorted(p for folder in ('board', 'common', 'host', 'tools', 'scripts', 'tests')
                   for p in (ROOT / folder).rglob('*.py') if '__pycache__' not in p.parts)
    rows, trees, module_files = [], {}, {}
    for p in paths:
        name = p.relative_to(ROOT).as_posix()
        assert not p.is_symlink()
        raw = p.read_bytes()
        tree = ast.parse(raw.decode('utf-8-sig'), filename=name)
        trees[name] = tree
        module = '.'.join(Path(name).with_suffix('').parts)
        if module.endswith('.__init__'):
            module = module[:-9]
        module_files[module] = name
        area, note = role_for(name)
        rows.append({'current_path': name, 'target_responsibility_area': area,
                     'classification_note': note, 'bytes': len(raw),
                     'sha256': hashlib.sha256(raw).hexdigest(),
                     'relocation_state': 'SOURCE_NOT_MOVED', 'classification_is_not_runtime_acceptance': True})
    imports = []
    for name, tree in trees.items():
        package = list(Path(name).parent.parts)
        for node in ast.walk(tree):
            candidates = []
            if isinstance(node, ast.Import):
                candidates = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = '.'.join(package[:len(package) - node.level + 1]) if node.level else ''
                base = '.'.join(v for v in (base, node.module) if v)
                candidates = [base] + [base + '.' + a.name for a in node.names if a.name != '*']
            for candidate in sorted(set(candidates)):
                if candidate in module_files:
                    imports.append({'consumer': name, 'line': node.lineno, 'provider': module_files[candidate],
                                    'import_name': candidate, 'scope': 'STATIC_IMPORT_NOT_PROCESS_OR_CALL_GRAPH'})
    imports = [dict(items) for items in sorted({tuple(row.items()) for row in imports})]
    return rows, imports


def verify_basis(spec):
    ids = {b['id'] for b in spec['basis']}
    assert len(ids) == len(spec['basis'])
    references = []
    for b in spec['basis']:
        for name in b['paths']:
            p = path_for(name)
            assert p.exists(), name
            r = {'basis_id': b['id'], 'path': name, 'exists': True, 'kind': 'directory' if p.is_dir() else 'file'}
            if p.is_file():
                raw = p.read_bytes()
                r.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            references.append(r)
    for d in spec['directories']:
        assert re.fullmatch(r'[a-z0-9_/-]+', d['path']) and '..' not in Path(d['path']).parts
        assert set(d['basis']) <= ids
        assert all(path_for(p).exists() for p in d['sources'])
    for finding in spec['findings']:
        assert set(finding['basis']) <= ids
    needles = [
        ('F01', 'board/runtime/media_session.py', 'from host.model_service.protocol import'),
        ('F02', 'board/runtime/application.py', 'from host.model_service.client import AsyncModelClient'),
        ('F02', 'host/model_service/client.py', 'from board.runtime.dialogue_client.ws_client import WebSocketClient'),
        ('F03', 'board/runtime/audio/selected_voice.py', 'qwen_tts'),
        ('F03', 'board/runtime/audio/tts.py', 'class TtsPlayer'),
        ('F03', 'board/runtime/audio/tts.py', 'class SherpaTtsBackend'),
        ('F04', 'board/runtime/application.py', 'from board.motion.guard import SimulationGuard'),
        ('F05', 'hardware/platform/platform_manifest.json', '"absolute_source_deadline_supported": false'),
        ('F07', '/home/ghmd/kv260-visual-servo-20261007/scripts/implement_source_platform.py', 'ip_cache'),
        ('F07', '/home/ghmd/kv260-visual-servo-20261007/scripts/implement_source_platform.py', 'pin.xdc'),
        ('F08', 'board/interaction/avatar_assets.py', 'AVATAR_DIR = _ROOT / "assets" / "avatar"'),
        ('F09', 'common/config.py', 'PROJECT_ROOT = Path(__file__).resolve().parents[1]'),
        ('F09', 'board/interaction/avatar_assets.py', '_ROOT = Path(__file__).resolve().parents[2]'),
        ('F10', 'docs/LICENSE_MATRIX.md', 'LVGL'),
    ]
    anchors = []
    for finding, name, needle in needles:
        lines = path_for(name).read_text(encoding='utf-8-sig').splitlines()
        matches = [(i + 1, line.strip()) for i, line in enumerate(lines) if needle in line]
        assert matches, (name, needle)
        line, excerpt = matches[0]
        anchors.append({'finding': finding, 'path': name, 'line': line, 'excerpt': excerpt})
    manager = path_for('/home/ghmd/aura-submission-framework-20261009/references/manager_20261002.md').read_text()
    for c in spec['contracts']:
        assert re.search(r'^\| ' + c['id'] + r' \|', manager, re.M)
        assert c['original_name'] in manager
        assert all(path_for(n).exists() for n in c['existing'])
    assert [c['id'] for c in spec['contracts']] == ['I%02d' % n for n in range(1, 8)]
    return references, anchors


def directory_tree(paths):
    tree = {}
    for path in paths:
        branch = tree
        for part in Path(path).parts:
            branch = branch.setdefault(part, {})
    lines = ['aura_junior/']
    def walk(branch, prefix=''):
        order = ['src', 'sim', 'build', 'board', 'data', 'skill', 'report']
        items = sorted(branch.items(), key=lambda item: (order.index(item[0]), item[0]) if not prefix and item[0] in order else (len(order), item[0]))
        for i, (key, children) in enumerate(items):
            last = i == len(branch) - 1
            lines.append(prefix + ('└── ' if last else '├── ') + key + '/')
            walk(children, prefix + ('    ' if last else '│   '))
    walk(tree)
    return '\n'.join(lines)


POLICY = """## 结构结论与适用范围

七类提交目录与 M1–M8 功能划分有明确依据。七目录按交付物用途组织；M1–M8 按产品功能组织；PS/PL/Windows/Ubuntu 标明运行或构建位置；A/B/C 标明责任。这四个维度不能互相替代。

以下是经过源码核对的目标目录与职责框架。现有主仓仍是唯一正在开发的源码。提交目录中的 README/interface 是说明，不能当作已迁移源码；目标目录名也不是当前 Python 包名。实际导出与迁移完成前，运行入口仍是主仓 tools/aura_project.py。

官方要求交付源码、验证、实现、板测、Skill、报告与复现；src/ps、src/host、src/shared 等细分是依据本项目职责作出的工程选择。官方没有规定必须有 64 个模块、三项 Skill、30 项测试或这些内部性能目标。

## 开发、接口与交付规则

1. 每个模块有唯一代码主责，接口另有主写/评审者。按原总包 I01–I07 登记接口；新增源期限是 I02 的版本演进，不能与旧相对租约混用。
2. 共用类型、版本、错误码和序列化应有唯一来源。当前媒体 protocol.py 虽位于 host，已被板端消费；目录重构前保留导入兼容。
3. UI/主机只经业务接口提交建议。相机、DPU、身份库、运动寄存器、音频与会话分别有唯一所有者；状态机不因拆目录再复制一套。
4. 当前应用存在组合入口、采集线程与异步工作线程。目录表示模块边界，并不要求每个目录启动独立进程；未来进程拆分按资源预算决定。
5. 固件、系统、模型、配置、应用、标定和实测须用同一 release 清单关联。旧证据可作参考，不自动覆盖新组合。
6. 数据按标定、独立测试、黄金参考、运行资源和实验分析分类；原始板测日志在 board/results 按 run_id 归档，其他地方引用或生成只读分析。
7. 真实身份数据库、在途媒体、缓存与日常日志放在部署环境配置的可写状态目录，不作为默认源码/测试样本打包。最终状态路径尚待目标镜像冻结。
8. 目录中的证据状态描述模块已有依据，不是每个新适配文件都已上板。BOARD 引用原有限板测；PC、软件测试与最终板验收保持各自范围。

## 源码迁移与发布的实际门槛

当前导入使用 common、board、host、tools 命名空间；common/config.py 和 avatar_assets.py 还依赖源码相对层级定位配置、模型和素材。先解决包入口和资源路径，再导出目标布局；不能只把文件按目录移动。

最终源码导出必须给出：唯一源文件→目标路径清单、SHA256、第三方来源/许可、明确选择的生产与参考入口、匹配的依赖锁。将导出包解到独立目录，在不依赖原工作区/相邻目录的条件下验证导入、配置和资源、模拟链；随后在目标平台验证真实模型、设备与构建。现在的结构校验尚未完成这些最终设备验收。

旧硬件构建脚本使用本机绝对路径、IP cache 与既有 routed DCP。src/platform 留输入，build/scripts 留可复建步骤，board/firmware 留匹配输出；正式“从零复现”需要参数化后实际执行。

Qt/Tk 是已有 PC 代码来源，RGB565 导出也是既有资源路径；板端最终渲染后端按原总包 §4.9 在实际镜像选定。旧许可矩阵中的 LVGL/旧版本陈述不构成当前冻结结论。

机构继续等待 3D 模型。源码/合同迁移、真实项目模型与媒体、PL 新期限、板端 UI、G0–G5 和完整复现均有独立验收入口。
"""


def md_table(headers, rows):
    def cell(v):
        return str(v).replace('|', '\\|').replace('\n', ' ')
    return ['| ' + ' | '.join(headers) + ' |', '|' + '|'.join('---' for _ in headers) + '|'] + [
        '| ' + ' | '.join(cell(v) for v in row) + ' |' for row in rows]


def markdown(spec, modules, rows, imports, anchors):
    lines = [MARKER, '# AURA 项目结构细化与依据复核', '', '版本：2026-10-09 / structure-2。', '', POLICY, '',
             '## 已发现并处理的结构问题', '']
    lines += md_table(['问题', '证据', '结构修正 / 尚待实现'], [(f['id'] + ' ' + f['title'], f['evidence'], f['decision'].rstrip('。；') + '；' + f['status']) for f in spec['findings']])
    lines += ['', '## 完整目标目录树', '', '每个叶位置仍明确标注来源与未完成内容；下列模块目录不等于已实现功能。', '', '```text',
              directory_tree({d['path'] for d in spec['directories']} | {m['planned_path'] for m in modules}), '```', '',
              '## 目录职责、责任与依据', '']
    lines += md_table(['目录', '负责人 / 位置', '放什么', '边界', '依据'], [(d['path'], d['owner'] + ' / ' + d['placement'], d['purpose'], d['boundary'], ', '.join(d['basis'])) for d in spec['directories']])
    lines += ['', '## 原 I01–I07 接口登记', '']
    lines += md_table(['编号', '原文件约定', '主写 / 评审', '当前状态'], [(c['id'] + ' ' + c['name'], c['original_name'], c['owner'], c['status']) for c in spec['contracts']])
    lines += ['', '## 共享资源与状态所有者', '']
    lines += md_table(['资源', '唯一所有者', '其他模块怎样使用', '必须保持的条件'], [(r['resource'], r['owner'], r['consumer_rule'], r['invariant']) for r in spec['resource_owners']])
    lines += ['', '## 现有源码与静态依赖核对', '',
              '已解析 %d 个 Python 文件并记录 %d 条本地静态导入。明细见 current_source_map.csv 与 static_imports.csv。解析和分类不表示所有历史工具都属于最终交付，也不表示运行通过。' % (len(rows), len(imports)), '',
              '这次重点核对的调用点：', '']
    lines += md_table(['问题', '实际文件 / 行', '原文片段'], [(a['finding'], a['path'] + ':' + str(a['line']), '`' + a['excerpt'] + '`') for a in anchors])
    lines += ['', '## 依据登记', '']
    lines += md_table(['编号 / 类型', '原文位置', '支持的判断', '文件'], [(b['id'] + ' / ' + b['kind'], b['section'], b['claim'], '; '.join(b['paths'])) for b in spec['basis']])
    lines += ['', '官方企业入口：https://gitee.com/Vickyiii/fpgachina26-amd 。本次能读取入口，分赛道正文仍无法抓取；详细要求引用用户 ZIP 原官方 PDF。未声称核实更晚上传字段或截止时间。', '',
              '本次只核对源码/资料并更新结构、图册与目录说明，没有重跑真实模型、硬件或此前 41 项软件测试。', '']
    return '\n'.join(lines)


def webpage(spec, modules, rows, imports, anchors, source_prefix, diagrams_href):
    e = html.escape
    css = "body{margin:0;background:#f5f7fb;color:#17253c;font:15px/1.7 'Microsoft YaHei','Noto Sans CJK SC',sans-serif}header,main{max-width:1360px;margin:auto;padding:24px}h1{font-size:29px;margin:0}h2{font-size:22px}nav{display:flex;gap:15px;flex-wrap:wrap;margin:16px 0}a{color:#2454bc}section{background:white;border:1px solid #dce3ef;border-radius:10px;padding:22px;margin:20px 0}.note{background:#edf4ff;border-left:4px solid #3b70d0;padding:12px 18px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}details.folder{padding:16px;border:1px solid #dce3ef;border-radius:8px;break-inside:avoid}summary{cursor:pointer;font-weight:600}code{font-size:13px;overflow-wrap:anywhere}.meta{color:#59677b;font-size:13px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:10px;border-bottom:1px solid #dce3ef;vertical-align:top;text-align:left}th{background:#eff3f9}input,button{font:inherit;padding:7px 12px;border:1px solid #bfcde0;border-radius:5px;background:white}pre{overflow:auto;font-size:13px;line-height:1.6}article{margin:18px 0;padding:12px 16px;border-left:3px solid #d59b3d}.stats{font-size:18px;margin:12px 0}@media print{nav,input,button{display:none}.grid{display:block}details.folder{margin:10px 0}body{background:white}.scroll{overflow:visible}}"
    page = ['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">', MARKER,
            '<title>AURA 项目结构细分与依据</title><style>' + css + '</style><body><header><h1>AURA · 项目结构细分与依据</h1>',
            '<p>按正式交付用途、实际运行位置、业务所有权与可核验证据组织。</p>',
            '<div class="stats">7 类交付目录 · ' + str(len(spec['directories'])) + ' 项目录职责 · 64 个模块位置 · 原 I01–I07 · 10 项边界复核</div>',
            '<div class="note">结构已细化，现有源码保留在主仓。这里展示目标交付位置及当前来源；源码迁移、最终模型/硬件和整机复现尚待验收。子目录与三个 Skill 是本项目设计选择。</div>',
            '<nav><a href="#assessment">复核结论</a><a href="#folders">目录职责</a><a href="#tree">完整目录树</a><a href="#contracts">接口登记</a><a href="#owners">资源所有者</a><a href="#sources">现有源码</a><a href="#basis">依据</a><a href="structure_detail.md">完整说明</a><a href="' + diagrams_href + '">八张框图</a></nav></header><main>',
            '<section id="assessment"><h2>当前结构可保留的部分与需要修正的边界</h2><p>七类交付目录和 M1–M8 主线成立；原结构尚缺共用合同、部分源码角色、平台输入、资源和迁移规则。以下修正已有依据，代码重构及真实验收的未完成状态单列。</p>']
    for f in spec['findings']:
        page += ['<article><b>' + f['id'] + ' · ' + e(f['title']) + '</b><p>' + e(f['evidence']) + '</p><p>' + e(f['decision']) + '</p><p class="meta">依据：' + e(', '.join(f['basis'])) + ' · ' + e(f['status']) + '</p></article>']
    page += ['</section><section id="folders"><h2>目录职责：点击展开</h2><input id="folder-query" placeholder="搜索目录、负责人、职责或来源" oninput="filterFolders()"> <button onclick="expandFolders(true)">全部展开</button> <button onclick="expandFolders(false)">收起</button><p class="meta">每项写清放什么、边界、主责和依据。模块更细的目录仍保留状态与输入输出。</p><div class="grid">']
    for d in spec['directories']:
        matching = [m for m in modules if m['planned_path'] == d['path'] or m['planned_path'].startswith(d['path'] + '/')]
        page += ['<details class="folder" data-search="' + e(json.dumps(d, ensure_ascii=False), quote=True) + '"><summary><code>' + e(d['path']) + '/</code></summary><p><b>主责：</b>' + e(d['owner']) + '<br><b>位置：</b>' + e(d['placement']) + '</p><p><b>内容：</b>' + e(d['purpose']) + '</p><p><b>边界：</b>' + e(d['boundary']) + '</p><p class="meta">依据：' + e(', '.join(d['basis'])) + '</p>']
        if d['sources']:
            page.append('<p>当前来源：<br>' + '<br>'.join('<code>' + e(s) + '</code>' for s in d['sources']) + '</p>')
        if matching:
            page.append('<p class="meta">关联模块：' + e(', '.join(m['id'] for m in matching)) + '</p>')
        page.append('</details>')
    page += ['</div></section><section id="tree"><h2>完整目标目录树</h2><pre>' + e(directory_tree({d['path'] for d in spec['directories']} | {m['planned_path'] for m in modules})) + '</pre></section>',
             '<section id="contracts"><h2>恢复原总包 I01–I07 编号</h2><p>前一版九条数据流现在使用 D01–D09，避免与原接口编号冲突。合同框架不等于最终 ABI 或线协议已经冻结。</p><div class="scroll"><table><tr><th>编号 / 名称</th><th>原文件约定</th><th>主写 / 评审</th><th>当前状态</th></tr>']
    for c in spec['contracts']:
        page.append('<tr><td>' + c['id'] + ' ' + e(c['name']) + '</td><td><code>' + e(c['original_name']) + '</code></td><td>' + e(c['owner']) + '</td><td>' + e(c['status']) + '</td></tr>')
    page += ['</table></div></section><section id="owners"><h2>共享资源由谁管理</h2><div class="scroll"><table><tr><th>资源</th><th>唯一所有者</th><th>其他模块怎样使用</th><th>约束</th></tr>']
    for r in spec['resource_owners']:
        page.append('<tr>' + ''.join('<td>' + e(r[k]) + '</td>' for k in ('resource', 'owner', 'consumer_rule', 'invariant')) + '</tr>')
    page += ['</table></div></section><section id="sources"><h2>现有源码映射与导入依据</h2><p>AST 解析 ' + str(len(rows)) + ' 个文件，记录 ' + str(len(imports)) + ' 条本地静态导入。静态检查不证明可选依赖齐全、运行成功或已经完成源码迁移。</p><p><a href="current_source_map.csv">源码映射 CSV</a> · <a href="static_imports.csv">静态导入 CSV</a> · <a href="structure_review_validation.json">核验记录</a></p><details><summary>展开完整源码映射</summary><div class="scroll"><table><tr><th>现有源码</th><th>目标职责区域</th><th>实际含义与范围</th></tr>']
    for r in rows:
        page.append('<tr><td><a href="' + source_prefix + quote(r['current_path'], safe='/') + '"><code>' + e(r['current_path']) + '</code></a></td><td><code>' + e(r['target_responsibility_area']) + '</code></td><td>' + e(r['classification_note']) + '</td></tr>')
    page += ['</table></div></details><p>当前 Python 包名与资源路径依赖已有目录。正式重排前先改包/资源定位，再在隔离目录核验；src/ps 等目录不直接当作 Python import 路径。原始源文件是唯一维护点。</p></section>',
             '<section id="basis"><h2>官方要求、项目方案与代码事实的依据</h2><p><a href="https://gitee.com/Vickyiii/fpgachina26-amd">AMD 企业赛道入口</a>；详细条款依据用户 ZIP 中官方 PDF。分赛道在线全文本次仍未抓取成功，未推定更晚上传字段或时间。</p><div class="scroll"><table><tr><th>编号 / 类型</th><th>位置与支持内容</th><th>原文件</th></tr>']
    for b in spec['basis']:
        page.append('<tr><td>' + b['id'] + '<br>' + e(b['kind']) + '</td><td>' + e(b['section']) + '<br>' + e(b['claim']) + '</td><td>' + '<br>'.join('<code>' + e(p) + '</code>' for p in b['paths']) + '</td></tr>')
    page += ['</table></div></section><p>下一步按明确的模块与合同接入真实实现。物理机构继续等待 3D 模型；本轮没有访问板卡或真实模型。</p></main>',
             '<script>function filterFolders(){let q=document.getElementById("folder-query").value.toLowerCase();document.querySelectorAll(".folder").forEach(d=>d.hidden=!d.dataset.search.toLowerCase().includes(q))}function expandFolders(value){document.querySelectorAll(".folder").forEach(d=>d.open=value)}</script></body></html>']
    return ''.join(page)


def main():
    spec = json.loads((OUT / 'structure_spec.json').read_text(encoding='utf-8'))
    data = json.loads((OUT / 'architecture.json').read_text(encoding='utf-8'))
    modules = data['modules']
    assert spec['physical_actuation_enabled'] is False
    assert {d['path'] for d in spec['directories'] if '/' not in d['path']} == set(spec['top_level_recommendation'])
    assert len({d['path'] for d in spec['directories']}) == len(spec['directories'])
    refs, anchors = verify_basis(spec)
    rows, imports = audit_sources()
    areas = {d['path'] for d in spec['directories']}
    assert all(r['target_responsibility_area'] in areas for r in rows)
    ids = {m['id'] for m in modules}
    assert all(set(c['module_ids']) <= ids for c in spec['contracts'])
    assert all(set(r['module_ids']) <= ids for r in spec['resource_owners'])
    for correction in spec['plan_path_corrections']:
        assert next(m for m in modules if m['id'] == correction['module'])['planned_path'] == correction['after']
    for d in spec['directories']:
        path = STAGE / d['path'] / 'README.md'
        if path.exists():
            original = path.read_text(encoding='utf-8')
            assert MARKER in original, str(path)
            original = original.split(DETAIL)[0].rstrip() + '\n\n'
        else:
            original = MARKER + '\n# ' + d['path'] + '\n\n'
        addition = DETAIL + '\n## 复核后的目录职责\n\n主责：' + d['owner'] + '；运行/使用位置：' + d['placement'] + '。\n\n内容：' + d['purpose'] + '。\n\n边界：' + d['boundary'] + '。\n\n依据：' + '、'.join(d['basis']) + '，见 report/structure_detail.md 的依据登记。\n\n'
        addition += '现有来源：\n\n' + ('\n'.join('- `' + name + '`' for name in d['sources']) or '- 按关联模块清单回收，具体工件尚待冻结。') + '\n\n目标目录已建立；本轮没有将实际源文件迁移到此处。\n'
        write(path, original + addition)
    text = markdown(spec, modules, rows, imports, anchors)
    for folder in (OUT, STAGE / 'report'):
        write(folder / 'structure_detail.md', text)
        write(folder / 'directory_catalog.csv', csv_text(spec['directories'], list(spec['directories'][0])))
        write(folder / 'current_source_map.csv', csv_text(rows, list(rows[0])))
        write(folder / 'static_imports.csv', csv_text(imports, list(imports[0])))
        write(folder / 'resource_owners.csv', csv_text(spec['resource_owners'], list(spec['resource_owners'][0])))
        dump(folder / 'contract_registry.json', {'schema_version': 'aura-contract-registry-1', 'basis': '2026-10-02 manager section 6.1', 'entries': spec['contracts'], 'description_is_not_frozen_abi_or_wire_schema': True})
        dump(folder / 'structure_basis.json', {'basis': spec['basis'], 'references': refs, 'code_anchors': anchors})
    write(OUT / 'structure_detail.html', webpage(spec, modules, rows, imports, anchors, '../../', 'index.html'))
    write(STAGE / 'report/structure_detail.html', webpage(spec, modules, rows, imports, anchors, '../../../', '../../../report/architecture/index.html'))
    current_hashes = {p['current_path']: hashlib.sha256((ROOT / p['current_path']).read_bytes()).hexdigest() for p in rows}
    assert all(current_hashes[p['current_path']] == p['sha256'] for p in rows), 'Source changed during audit'
    result = {'schema_version': 'aura-structure-review-validation-1', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'passed': True, 'directory_responsibilities': len(spec['directories']), 'modules': len(modules),
              'contract_ids_match_original': [c['id'] for c in spec['contracts']], 'resource_owners': len(spec['resource_owners']),
              'review_findings': len(spec['findings']), 'basis_entries': len(spec['basis']), 'basis_references': len(refs),
              'basis_file_hashes': sum('sha256' in r for r in refs), 'checked_code_anchors': len(anchors),
              'python_files_parsed_and_classified': len(rows), 'source_hashes_stable_during_audit': True,
              'local_static_imports': len(imports), 'active_source_relocated': False,
              'runtime_tests_rerun': False, 'hardware_or_model_execution': False,
              'scope': 'STRUCTURE_DESIGN_SOURCE_ROLES_AND_STATIC_DEPENDENCIES_NOT_FINAL_RELEASE_ACCEPTANCE'}
    dump(OUT / 'structure_review_validation.json', result)
    dump(STAGE / 'report/structure_review_validation.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
