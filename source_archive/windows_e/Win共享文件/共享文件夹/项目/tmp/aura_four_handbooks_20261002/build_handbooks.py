from pathlib import Path
import re
import os
import json
import hashlib
import zipfile

ROOT = Path(r'C:\Users\uuh56\Desktop\项目')
SOURCE_DIR = ROOT / '方案'
SOURCE = SOURCE_DIR / 'AURA_KV260_三人详细分工与同板运行实施书_2026-10-02.md'
MATERIAL = Path(__file__).parent
OUTPUT = SOURCE_DIR / 'AURA_三人执行总包_2026-10-02'
FILES = {
    '总': '00_总负责人_系统集成与交付总包.md',
    'A': '01_A负责人_FPGA平台硬件与板端底座执行手册.md',
    'B': '02_B负责人_视觉身份与板端运动服务执行手册.md',
    'C': '03_C负责人_视听交互主机模型与板端界面执行手册.md',
}
TITLES = {
    'A': 'A 负责人执行手册：FPGA、平台、硬件与共同板端底座',
    'B': 'B 负责人执行手册：板端视觉、身份与唯一运动服务',
    'C': 'C 负责人执行手册：视听交互、主机模型与板端界面',
    '总': '总负责人总包：完整系统、三人协作、同板集成与最终交付',
}
ROLE_GOALS = {
    'A': '交付可重建、可加载、可恢复的共同 KV260 平台，以及 DPU 与自研运动核同配置工作、受监督 PWM/停止/恢复和可供 B 调用的板端访问库。',
    'B': '在共同 KV260 上完成唯一采集、真实人体检测/跟踪、板端身份/数据库和唯一运动服务；向 C 提供真实本轮快照/连续脸/轨迹/身份，并核验其选人建议。',
    'C': '在共同 KV260 上完成 MCP01 录放音、请求/取消/断连、声画窗口、真实屏幕及日常启动入口；在 Windows 完成 ASR/VLM/TTS/Light-ASD，并把有归属/时效的结果接回板端。',
}
OPENING_INPUTS = {
    'A': [
        '现有官方/参考/候选报告、模型和输入来源；B/C提供真实依赖需求。',
        'A01平台事实、原卡/测试卡和恢复入口；B给同模型/同图/同程序对照包。',
        '可用候选/参考平台、最终linked design和实际控制接入；A02板端状态明确。',
        '现有运动框架/冲突表、实际时钟/地址取得计划；B/C共同评审业务状态。',
        'A04唯一寄存器与行为合同、复位/总线参数、合法和非法命令fixture。',
        '真实或仿真声明的ctrl_clk参数、舵机待标定范围；A05可提供原子更新。',
        'A04完整状态/优先级、A05提交接口、A06最终输出门控。',
        'A07许可/故障机制、速率/单步合同、A12实物标定取得计划。',
        'A03最小共存通过、A05—08仿真通过、真实IO/clock/reset与完整平台源。',
        'A04冻结ABI、A09访问描述/设备、真实系统权限；B给正式调用样例。',
        '同版硬件/设备描述及B/C具体依赖，当前OS/init/runtime与SDK事实。',
        '实物/载板/电源/机构、A09无动力输出、A07停止合同；B配合控制。',
        '联合完整硬件/库、电气标定；B/C提供最终实际并发负载。',
        '各人冻结包/配置和原始证据、最终恢复入口；所有未通过项列表。',
    ],
    'B': [
        '现有模型/代码/相机和分类样例；A交平台/候选身份，C交图像需求。',
        '实际相机与A支持的驱动/系统、可用格式/时间能力；尚不需要完整motion。',
        '可取得的模型/工具与真实校准图；A交真实arch，未取得时先浮点/量化。',
        'B03真实模型张量/输出定义、B02原图尺寸/颜色；固定图参考结果。',
        'B04原图人体框/分数/原采集时间、B02相机代次与真实连续图像。',
        'B02有所有权的原图、B05轨迹生命周期、人脸真实裁剪能力；C给窗口输入要求。',
        '板端CPU环境/真实人脸权重；A提供可用DPU/arch，CPU/DPU子任务分别推进。',
        'B07模型与对齐定义、B05人体归属、真实合格/不合格脸与不同身份样本。',
        '板端SQLite/持久存储、B07模型空间、C身份操作需求和授权规则。',
        'B08质量/特征、B09事务版本、B05当前唯一目标；C显式确认接口。',
        'B03/B07各真实job耗时和运行库行为、当前CU配置；A提供硬件自检。',
        'B05最新真实轨迹、A10库/ABI、A12标定/停止、C仅选人建议；先无动力。',
        '冻结模型/配置与独立测试标注、同板负载；A/C提供硬件/交互证据。',
        '真实ARM64程序/依赖、模型/配置/迁移/API和已通过/未通过测试清单。',
    ],
    'C': [
        'MCP01/屏幕实物、Windows配置、已有模型/UI代码；A/B给共同平台与接口需求。',
        '实际KV260系统/USB音频驱动、MCP01数据连接；A协助缺工具/驱动。',
        'C02真实输入/输出能力，模型实际格式与最长音频/窗口需求。',
        'B快照/目标合同、C03真实PCM格式、主机项目身份/网络；先可用fixture开发。',
        'C01实际主机能力/后端和可取得权重、固定音/图/中文文本。',
        'B本轮有效快照/目标、C04请求归属、C05真实VLM。',
        'C03实际播放后端、C04请求/段号、C05模型事件；需可注入迟到结果。',
        'A实际显示通路与目标渲染依赖、A/B/C状态/API；原型与实屏分开。',
        '固定作者源码/权重/依赖与真实离线短片；B连续脸/C音频用于项目适配。',
        'B原图时间语义/真实片段、C03真实样本锚点、可见可听事件。',
        'C09真实模型输入、C10有效对齐、B06连续脸/轨迹和B建议复核API。',
        'A真实init/平台探针、B启动/退出/功能探针、C各模块ready与统一release。',
        '冻结真值/模型/参数和最终同板A/B负载；实声/实屏测量方法。',
        '板端与Windows已冻结包/操作入口，A/B本人报告和真实测试/限制。',
    ],
}
COMMON_ANNOTATION = '''
日期：2026-10-02。执行手册版本：`AURA-EXEC-20261002-r2`。这是任务和接口文档版本，不是已经通过的硬件/软件 release。

三人共用范围：单水平轴、KV260 板端视觉/身份/运动/录放音/交互/UI，Windows 首版 ASR/VLM/TTS/Light-ASD，Ubuntu 构建。双 I2S、声学定位、audio_doa_ip 已取消；板端身份和 Light-ASD 保留。

**独立使用约定：**本文件包含执行所需的系统背景、共同接口、本人工作包、具体步骤、配置/诊断、部署、故障、测试和交付。来源链接用于追溯，执行时无需先阅读另一本手册。总负责人和其他成员交付的实际硬件/模型/库仍是工程依赖，不能用文档代替。

本次文档整理没有实际连接板卡或构建机。当前证据到“官方推理历史通过、独立 DPU 4.1 主机构建完成”，候选上板/联合运动/整机仍需验证。代码、配置样例和脚本入口是待实现约定；标 `null`、`待实测` 或参数变量的值必须取得后校验，不能直接用于运动使能。

四份手册里的共同合同必须保持一致。更改 ABI、消息、标定、模型空间或恢复语义时，总负责人组织同步四份执行文件及实际工程源；具体源码/工件仍以统一 release-id 和唯一合同源为准。
'''


def split_sections(text):
    matches = list(re.finditer(r'(?m)^## (\d+)\. (.+)$', text))
    out = {}
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out[int(match.group(1))] = text[match.start():end].strip() + '\n'
    return out


def split_material(text):
    matches = list(re.finditer(r'(?m)^## ([^\n]+)$', text))
    out = {}
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out[match.group(1)] = text[match.end():end].strip()
    return out


def rebase_links(text):
    def replacement(match):
        label, target = match.groups()
        if re.match(r'^[a-zA-Z]+://', target) or target.startswith('#'):
            return match.group(0)
        target = target.strip('<>')
        name, separator, fragment = target.partition('#')
        dest = (SOURCE_DIR / name).resolve()
        rel = os.path.relpath(dest, OUTPUT).replace('\\', '/')
        return f'[{label}]({rel}{separator}{fragment})'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', replacement, text)


def chapter(section, n, title):
    section = re.sub(r'^## \d+\. .+', f'## {n}. {title}', section, count=1)
    section = re.sub(r'(?m)^### \d+\.(\d+)', lambda m: f'### {n}.{m.group(1)}', section)
    return section


def personal_tasks(section, owner, material):
    raw_cards = list(re.finditer(rf'(?m)^### ({owner}\d{{2}}) .+$', section))
    result = [f'## 7. {owner} 的 14 个工作包及逐项执行做法\n\n']
    for i, match in enumerate(raw_cards):
        end = raw_cards[i + 1].start() if i + 1 < len(raw_cards) else len(section)
        card = section[match.start():end].strip()
        code = match.group(1)
        if code not in material:
            raise RuntimeError(f'Missing detailed procedure {code}')
        opening = OPENING_INPUTS[owner][int(code[1:]) - 1]
        result.append(card + '\n\n**开工输入/前置条件：**' + opening + '\n\n#### 执行步骤、实现要点与现场判定\n\n' + material[code] + '\n\n')
    return ''.join(result)


def complete_tasks(section, owner, material):
    matches = list(re.finditer(rf'(?m)^### ({owner}\d{{2}}) .+$', section))
    if len(matches) != 14:
        raise RuntimeError(f'Expected 14 master cards for {owner}')
    result = [section[:matches[0].start()]]
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section)
        card = section[match.start():end].strip()
        code = match.group(1)
        opening = OPENING_INPUTS[owner][int(code[1:]) - 1]
        result.append(card + '\n\n**开工输入/前置条件：**' + opening + '\n\n#### 执行步骤、实现要点与现场判定\n\n' + material[code] + '\n\n')
    return ''.join(result)


def master_operations(role_materials):
    result = []
    for number, owner in enumerate('ABC', 7):
        result.append(f'### 23.{number} {owner} 的操作附录、链路演练与签收细节\n\n')
        for key in ['操作附录', '链路演练', '开工与交付', '个人验收签收']:
            body = role_materials[owner][key]
            body = re.sub(r'(?m)^### \d+\.\d+ (.+)$', lambda m: f'##### {m.group(1)}', body)
            result.append(f'#### {owner}：{key}\n\n' + body + '\n\n')
    return ''.join(result)


def navigation(body, owner):
    chapters = re.findall(r'(?m)^## (\d+)\. (.+)$', body)
    cards = re.findall(r'(?m)^### ([ABC]\d{2}) (.+?)｜\d+ h$', body)
    lines = ['**章节快速入口**（每份的核心背景和合同均在本文件内）\n\n', '| 章节 | 章节 | 章节 |\n|---|---|---|\n']
    for start in range(0, len(chapters), 3):
        cells = [f'[{n}. {title}](#chapter-{int(n):02})' for n, title in chapters[start:start+3]]
        cells += [''] * (3 - len(cells))
        lines.append('| ' + ' | '.join(cells) + ' |\n')
    lines.append('\n**工作包快速入口**\n\n')
    if owner == '总':
        lines.append('| A：平台/硬件 | B：视觉/身份/运动服务 | C：视听/交互/UI |\n|---|---|---|\n')
        mapped = dict(cards)
        for number in range(1, 15):
            cells = []
            for o in 'ABC':
                code = f'{o}{number:02}'
                cells.append(f'[{code} {mapped[code]}](#task-{code.lower()})')
            lines.append('| ' + ' | '.join(cells) + ' |\n')
    else:
        lines.append('| 工作包 | 工作包 |\n|---|---|\n')
        for start in range(0, len(cards), 2):
            cells = [f'[{code} {title}](#task-{code.lower()})' for code, title in cards[start:start+2]]
            cells += [''] * (2 - len(cells))
            lines.append('| ' + ' | '.join(cells) + ' |\n')
    return ''.join(lines) + '\n'


def anchors(body):
    body = re.sub(r'(?m)^(## (\d+)\. .+)$', lambda m: f'<a id="chapter-{int(m.group(2)):02}"></a>\n\n{m.group(1)}', body)
    return re.sub(r'(?m)^(### ([ABC]\d{2}) .+)$', lambda m: f'<a id="task-{m.group(2).lower()}"></a>\n\n{m.group(1)}', body)


def own_schedule(section, owner):
    preamble = section.split('### 12.3')[0]
    idx = {'A': 2, 'B': 3, 'C': 4}[owner]
    rows = []
    for line in section.splitlines():
        if re.match(r'^\| R\d+ \|', line):
            cols = [x.strip() for x in line.split('|')]
            rows.append(f'| {cols[1]} | {cols[idx]} | {cols[5]} |')
    return preamble + f'''### 12.3 {owner} 的相对执行安排

R1 为本次接续的第一工作段；评审段 R7/R14/R21/R28 每人约 2 h，其他工作段约 6 h 容量参考。未过前置关卡不按编号强行推进；只记录实际通过成果。

| 工作段 | 本人执行 | 本段共同成果/退出条件 |
|---|---|---|
''' + '\n'.join(rows) + '\n\n达到工时预算但退出条件未成立时，记录阻塞并与总负责人重排；已通过工作从预算扣除，不重复安装或验证无变化部分。\n'


def final_section(owner, original, extra):
    match = re.search(rf'(?ms)^### 18\.\d+ {owner} 必须交齐\n(.*?)(?=^### )', original)
    own = match.group(1).strip()
    shared = re.search(r'(?ms)^### 18\.4 共同完成条件\n(.*?)(?=^### )', original).group(1).strip()
    daily = re.search(r'(?ms)^### 18\.5 每日记录模板\n(.*)$', original).group(1).strip()
    return f'''## 18. 本人的最终验收、交付与每日记录

### 18.1 本人必须交齐

{own}

{extra}

### 18.2 共同完成条件

{shared}

### 18.3 每日记录模板

{daily}
'''


def sources_section(source):
    text = source.split('### 19.3')[0].strip()
    return text + '''

### 19.3 本套手册新增内容与采用边界

本次在原 42 项工作包基础上为 A/B/C 每项补入具体执行步骤、算法/状态逻辑、配置和诊断、端到端演练、交付签收；总包增加项目负责人的实际集成和发布做法。步骤示例是工程约定/待实现方法，不是本次已运行代码或板端实测。

四份文件可以独立分发；本章外部来源链接可能需要原项目目录，核心执行步骤和共同合同已写入各文件。官方软件文档用于技术核对，目标 PetaLinux/Vitis AI 固定版本的能力仍以实际运行验证为准。
'''


def build():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source_text = SOURCE.read_text(encoding='utf-8-sig')
    sections = split_sections(source_text)
    diagram_source = (SOURCE_DIR / 'AURA_KV260_共同板端部署与联调速查表_2026-10-02.md').read_text(encoding='utf-8-sig')
    diagram = re.search(r'(?s)```mermaid\n.*?\n```', diagram_source).group(0)
    manager_material = (MATERIAL / 'manager.md').read_text(encoding='utf-8')
    role_materials = {o: split_material((MATERIAL / f'{o}.md').read_text(encoding='utf-8')) for o in 'ABC'}
    report = {}
    for owner in 'ABC':
        materials = role_materials[owner]
        overview = f'''## 2. 本人闭环目标、边界与阅读路线

**本人最终结果：**{ROLE_GOALS[owner]}

建议执行顺序：第 1—6 章取得现状/同板接口；第 7 章按工作包操作；第 8 章填写配置和使用诊断；第 9 章逐段验证链路；第 10—11 章交接/过关；第 12—18 章排期、故障、测试和发布。

{materials['职责与边界']}

### 2.1 共同板端结构

{diagram}

图示表达职责和数据流，实际针脚、设备、动力停止和地址按工程取得。B 的正式运动服务唯一写入，A 最终监督，C 只建议对象。三人所有板端程序和电路同时进入同一发布版本。
'''
        own_task_source = sections[{'A': 7, 'B': 8, 'C': 9}[owner]]
        selected = [
            sections[1], overview, sections[3], sections[4], sections[5], sections[6],
            personal_tasks(own_task_source, owner, materials),
            '## 8. 本人实现配置、诊断及启动做法\n\n' + materials['操作附录'] + '\n',
            '## 9. 本人链路的端到端演练\n\n' + materials['链路演练'] + '\n',
            sections[10], sections[11], own_schedule(sections[12], owner), sections[13],
            sections[14], sections[15], sections[16],
            '## 17. 本人的第一批执行和阻塞处理\n\n' + materials['开工与交付'] + '\n',
            final_section(owner, sections[18], materials['个人验收签收']), sources_section(sections[19]),
        ]
        body = '\n\n'.join(selected)
        body = rebase_links(body)
        intro = f'# {TITLES[owner]}\n\n' + COMMON_ANNOTATION + '\n'
        intro += f'本手册交给 {owner} 独立执行；本人工作包 {owner}01—{owner}14。总负责人总包与其他两份文件用于跨人同步。\n\n'
        for key in ('总', *[x for x in 'ABC' if x != owner]):
            intro += f'- [{TITLES[key]}]({FILES[key]})\n'
        text = intro + '\n\n' + navigation(body, owner) + anchors(body).rstrip() + '\n'
        path = OUTPUT / FILES[owner]
        path.write_text(text, encoding='utf-8', newline='\n')
        report[owner] = {'file': str(path), 'characters': len(text), 'lines': len(text.splitlines())}
    master_sections = []
    for i in range(1, 19):
        if i in [7, 8, 9]:
            o = {7: 'A', 8: 'B', 9: 'C'}[i]
            master_sections.append(complete_tasks(sections[i], o, role_materials[o]))
        else:
            master_sections.append(sections[i])
    master_sections.append(sources_section(sections[19]))
    master_body = rebase_links('\n\n'.join(master_sections))
    master_intro = f'# {TITLES["总"]}\n\n' + COMMON_ANNOTATION + '\n'
    master_intro += '''总负责人由三人中一人兼任，建议由 A 担任，持有本文件并负责事实/接口/关卡/版本/集成/验收收敛。该角色不额外接管 B/C 代码。第 1—19 章保存完整项目及全部 42 项具体做法，新增第 20—23 章直接给出负责人怎样组织、集成、判断阻塞和交付；第 23.7—23.9 收录三人的配置/诊断、链路演练和签收细节。

分发：A 执行 01，B 执行 02，C 执行 03，总负责人执行 00。任何成员手册的必需接口和背景均已收录，可单独阅读。

'''
    for o in 'ABC':
        master_intro += f'- [{TITLES[o]}]({FILES[o]})\n'
    master_intro += '\n\n' + diagram + '\n\n'
    final_master_body = master_body + '\n\n' + manager_material.strip() + '\n\n' + master_operations(role_materials)
    master = master_intro + navigation(final_master_body, '总') + anchors(final_master_body)
    path = OUTPUT / FILES['总']
    path.write_text(master, encoding='utf-8', newline='\n')
    report['总'] = {'file': str(path), 'characters': len(master), 'lines': len(master.splitlines())}
    validate(report)
    zip_path = SOURCE_DIR / 'AURA_KV260_三份个人执行手册与总负责人总包_2026-10-02.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in FILES.values():
            archive.write(OUTPUT / name, arcname=name)
    with zipfile.ZipFile(zip_path) as archive:
        assert len(archive.namelist()) == 4
        assert archive.testzip() is None
        for name in FILES.values():
            assert archive.read(name) == (OUTPUT / name).read_bytes()
    report['archive'] = {'file': str(zip_path), 'bytes': zip_path.stat().st_size, 'documents': 4}
    (MATERIAL / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


def validate(report):
    from urllib.parse import unquote
    for owner, item in report.items():
        path = Path(item['file'])
        text = path.read_text(encoding='utf-8')
        assert '\ufffd' not in text
        assert len(re.findall(r'(?m)^```', text)) % 2 == 0
        chapters = list(map(int, re.findall(r'(?m)^## (\d+)\. ', text)))
        assert chapters == list(range(1, (24 if owner == '总' else 20))), (owner, chapters)
        cards = re.findall(r'(?m)^### ([ABC]\d{2}) .+｜(\d+) h$', text)
        owners = 'ABC' if owner == '总' else owner
        assert len(cards) == (42 if owner == '总' else 14)
        for o in owners:
            these = [(code, int(h)) for code, h in cards if code.startswith(o)]
            assert [code for code, h in these] == [f'{o}{n:02}' for n in range(1, 15)]
            assert sum(h for code, h in these) == 152
        assert text.count('#### 执行步骤、实现要点与现场判定') == (42 if owner == '总' else 14)
        assert text.count('**开工输入/前置条件：**') == (42 if owner == '总' else 14)
        assert len(re.findall(r'(?m)^\| R\d+ \|', text)) == 30
        anchor_ids = re.findall(r'<a id="([^"]+)"></a>', text)
        assert len(anchor_ids) == len(set(anchor_ids))
        for prefix, maxn in [('P', 28), ('I', 7), ('H', 9), ('J', 16), ('T', 30), ('U', 7)]:
            assert all(re.search(rf'\b{prefix}{n:02}\b', text) for n in range(1, maxn + 1))
        for block in re.findall(r'(?s)```json\n(.*?)\n```', text):
            json.loads(block)
        for label, target in re.findall(r'\[([^\]]+)\]\(([^)]+)\)', text):
            if target.startswith('#'):
                assert target[1:] in anchor_ids, (owner, label, target)
                continue
            if re.match(r'^[a-zA-Z]+://', target):
                continue
            name = unquote(target.strip('<>')).split('#')[0]
            assert (path.parent / name).resolve().exists(), (owner, label, name)
        item['bytes'] = path.stat().st_size
        item['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        item['verified_tasks'] = len(cards)
        item['verified_chapters'] = len(chapters)


if __name__ == '__main__':
    build()
