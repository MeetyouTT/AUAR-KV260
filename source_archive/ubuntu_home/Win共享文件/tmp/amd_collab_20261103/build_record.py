from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from copy import deepcopy
import csv
import hashlib
import json
import re
import shutil
import sys
import zipfile

from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'E:\项目')
TMP = ROOT / 'tmp/amd_collab_20261103'
OUT = ROOT / 'output/amd_llm_collaboration_20261103'
REPORT = OUT / 'report'
EVID = OUT / 'evidence'
for d in (REPORT, EVID / 'sources'):
    d.mkdir(parents=True, exist_ok=True)

messages = json.loads((TMP / 'conversation_messages.json').read_text(encoding='utf-8'))
lookup = {m['message_id']: m for c in messages['cases'] for t in c['turns'] for m in t['messages']}
json_write = lambda p, v: p.write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
json_write(EVID / 'conversation_messages.json', messages)

source_specs = [
 ('S01', 'AMD 选题指南', "参赛资料/全国大学生嵌入式芯片与系统设计竞赛'2026FPGA赛道选题指南-AMD.pdf", False),
 ('S02', '原五案例工程记录', '协作任务/2026-11-02_AI辅助学习记录/ai_learning_record_review.md', True),
 ('S03', '原工程证据索引', '协作任务/2026-11-02_AI辅助学习记录/evidence_index.json', True),
 ('S04', '单一创新方向说明', 'output/aura_single_innovation_direction_20261007.md', True),
 ('S05', '下巴修复说明', '共享文件夹/deliverables/2026-10-08_chin_fix/README.md', True),
 ('S06', '151 帧像素对照', '共享文件夹/deliverables/2026-10-08_chin_fix/chin_verification.json', True),
 ('S07', '550 项回归回执', '共享文件夹/deliverables/2026-10-08_chin_fix/regression_verification.json', True),
 ('S08', '嘴部合成器', '共享文件夹/aura/tools/mouth_compositor.py', True),
 ('S09', '嘴部合成器测试', '共享文件夹/aura/tests/test_mouth_compositor.py', True),
 ('S10', 'Windows ASR 联调原记录', r'C:\Users\uuh56\.codex\visualizations\2026\10\17\01a149c0-ee96-7f02-9071-1c3bb096f193\verysync-diagnostics\检查结果.md', True),
 ('S11', 'DPU 移植与失败记录', '语音共享文件/deliverables/2026-10-21_dpu_vision_start/README.md', True),
 ('S12', 'SFace 实板及三模型固定输入', '语音共享文件/deliverables/2026-10-21_dpu_vision_start/evidence/board-three-fixed.json', True),
 ('S13', 'SFace 独立量化评估', '语音共享文件/deliverables/2026-10-21_dpu_vision_start/evidence/sface-evaluation-report.json', True),
 ('S14', '短字段优化与播放回执', '语音共享文件/deliverables/2026-10-18_compact_reply_fields/verification_summary.json', True),
 ('S15', '短字段配对模型测量', '语音共享文件/deliverables/2026-10-18_compact_reply_fields/paired_profile.json', True),
 ('S16', '显存协调交付说明', '语音共享文件/deliverables/2026-10-29_parallel_interaction/README.md', True),
 ('S17', '637 项合并回归原始结果', '语音共享文件/deliverables/2026-10-29_parallel_interaction/final_tests.xml', True),
 ('S18', '自然到期存储回执', '语音共享文件/deliverables/2026-10-30_board_owner/integration/dialogue_repair/joint_balance_20261101/continued_validation_20261101/RETENTION_RESULT.json', True),
 ('S19', 'PYNQ 提炼与真实失败', '协作任务/2026-11-02_pynq_skill/skill/pynq-contract-testgen/case_studies.md', True),
 ('S20', 'PYNQ 离线验证汇总', '协作任务/2026-11-02_pynq_skill/skill/pynq-contract-testgen/evidence/offline_validation.json', True),
 ('S21', '15 项单元测试原始日志', '协作任务/2026-11-02_pynq_skill/skill/pynq-contract-testgen/evidence/unit_tests.log', True),
 ('S22', '超时顺序修复模板', '协作任务/2026-11-02_pynq_skill/skill/pynq-contract-testgen/templates/driver.py.tmpl', True),
 ('S23', '迟到完成反例源码', '协作任务/2026-11-02_pynq_skill/skill/pynq-contract-testgen/tests/test_generator.py', True),
 ('S24', 'A B C 技能包说明', '协作任务/2026-11-01_Skill交付规划/skill_delivery_v1/readme.md', True),
 ('S25', 'PYNQ 离线包说明', '协作任务/2026-11-02_pynq_skill/readme.md', True),
]
source_index = []
for sid, title, rel, snapshot in source_specs:
    p = Path(rel) if Path(rel).is_absolute() else ROOT / rel
    if not p.is_file():
        raise FileNotFoundError(p)
    blob = p.read_bytes()
    entry = {'id': sid, 'title': title, 'original_path': str(p.resolve()),
             'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest(),
             'verification': 'file_read_and_sha256_calculated_for_this_record'}
    if snapshot:
        suffix = '.py.tmpl' if p.name.endswith('.py.tmpl') else p.suffix.lower()
        target = EVID / 'sources' / (sid.lower() + suffix)
        target.write_bytes(blob)
        entry['snapshot'] = target.relative_to(OUT).as_posix()
    source_index.append(entry)

# Source indices explicitly distinguish absent Ubuntu files from local evidence.
legacy = json.loads((ROOT / source_specs[2][2]).read_text(encoding='utf-8'))
legacy_references = [e for e in legacy['entries'] if e['case_id'] == 'AI01']
json_write(EVID / 'source_index.json', {'schema': 'amd-llm-collaboration-source-index-v1',
    'record_date': '2026-11-03', 'root': str(ROOT), 'entries': source_index,
    'historical_ubuntu_references': {'status': 'reported_in_S03_not_reread_on_this_windows_host',
                                    'entries': legacy_references}})

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.top_margin, sec.bottom_margin = Cm(1.8), Cm(1.7)
sec.left_margin, sec.right_margin = Cm(2.1), Cm(2.1)
sec.footer_distance = Cm(0.8)

def font_style(style, size, east='宋体', bold=False):
    st = doc.styles[style]
    st.font.name, st.font.size, st.font.bold = 'Calibri', Pt(size), bold
    st.font.italic = False
    st.font.color.rgb = RGBColor(0, 0, 0)
    st.element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'), east)
    st.paragraph_format.space_before = Pt(0)
    st.paragraph_format.space_after = Pt(6)
    st.paragraph_format.line_spacing = 1.18
    return st

font_style('Normal', 11)
font_style('Title', 23, '黑体', True)
font_style('Subtitle', 12, '黑体')
font_style('Heading 1', 16, '黑体', True)
font_style('Heading 2', 12.5, '黑体', True)
font_style('Heading 3', 11, '黑体', True)
font_style('Caption', 9.5)
font_style('Quote', 10.5)
for style in doc.styles:
    for border in list(style.element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
doc.styles['Quote'].paragraph_format.left_indent = Cm(.45)
doc.styles['Quote'].paragraph_format.right_indent = Cm(.15)
for key in ('Heading 1', 'Heading 2', 'Heading 3'):
    doc.styles[key].paragraph_format.keep_with_next = True
    doc.styles[key].paragraph_format.space_before = Pt(10 if key == 'Heading 1' else 6)
    doc.styles[key].paragraph_format.space_after = Pt(6)

footer = sec.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = footer.add_run()
run.font.size = Pt(9)
fld = OxmlElement('w:fldSimple'); fld.set(qn('w:instr'), 'PAGE')
run._r.addnext(fld)
doc.core_properties.title = 'AURA 大模型协作记录'
doc.core_properties.subject = 'AMD自主选题赛道大模型协作与自我纠错记录'
doc.core_properties.author = 'AURA 项目团队'
doc.core_properties.keywords = 'AURA,AMD,FPGA,大模型协作,自我纠错,Skill'
md = []
next_heading_new_page = False

def h(text, level=1):
    global next_heading_new_page
    par = doc.add_heading(text, level)
    if next_heading_new_page:
        par.paragraph_format.page_break_before = True
        next_heading_new_page = False
    md.append('#' * (level + 1) + ' ' + text + '\n')

def p(text, style=None):
    par = doc.add_paragraph(text, style)
    if not style:
        par.paragraph_format.first_line_indent = Cm(.7)
    md.append(text + '\n')
    return par

def quote(text):
    for line in text.strip().split('\n'):
        if line.strip():
            par = doc.add_paragraph(style='Quote')
            for n, segment in enumerate(re.split(r'\*\*(.*?)\*\*', line)):
                run = par.add_run(segment)
                if n % 2:
                    run.bold = True
    md.append('\n'.join('> ' + line for line in text.strip().split('\n')) + '\n')

def qmsg(mid, paragraphs=None):
    text = lookup[mid]['text'].strip()
    if paragraphs is not None:
        paras = text.split('\n\n')
        text = '\n\n'.join(paras[i] for i in paragraphs)
    quote(text)

def table(headers, rows, widths=None, size=10):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = 'Table Grid'
    t.autofit = False
    if widths:
        for c, w in zip(t.columns, widths): c.width = Cm(w)
    for i, s in enumerate(headers): t.rows[0].cells[i].text = s
    for row in rows:
        cells = t.add_row().cells
        for i, value in enumerate(row): cells[i].text = str(value)
    for ridx, row in enumerate(t.rows):
        trpr = row._tr.get_or_add_trPr()
        cant = OxmlElement('w:cantSplit'); trpr.append(cant)
        if ridx == 0:
            rep = OxmlElement('w:tblHeader'); trpr.append(rep)
        for i, cell in enumerate(row.cells):
            if widths: cell.width = Cm(widths[i])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tcpr = cell._tc.get_or_add_tcPr()
            margins = OxmlElement('w:tcMar')
            for side in ['top','left','bottom','right']:
                n = OxmlElement('w:' + side); n.set(qn('w:w'), '75'); n.set(qn('w:type'), 'dxa'); margins.append(n)
            tcpr.append(margins)
            if ridx == 0:
                sh = OxmlElement('w:shd'); sh.set(qn('w:fill'), 'F1F3F5'); tcpr.append(sh)
            for par in cell.paragraphs:
                par.paragraph_format.space_after = Pt(2)
                par.paragraph_format.space_before = Pt(1)
                par.paragraph_format.line_spacing = 1.07
                for run in par.runs:
                    run.font.size = Pt(size)
                    run.font.bold = ridx == 0
    md.append('| ' + ' | '.join(headers) + ' |\n| ' + ' | '.join('---' for _ in headers) + ' |\n' +
              '\n'.join('| ' + ' | '.join(str(c).replace('\n','<br>') for c in row) + ' |' for row in rows) + '\n')
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return t

def page():
    global next_heading_new_page
    next_heading_new_page = True
    md.append('<!-- pagebreak -->\n')

def label(text):
    par = doc.add_paragraph()
    r = par.add_run(text); r.bold = True
    par.paragraph_format.keep_with_next = True
    par.paragraph_format.space_after = Pt(3)
    md.append('**' + text + '**\n')

# Page 1
doc.add_paragraph('AURA 大模型协作记录', 'Title')
doc.add_paragraph('AMD 自主选题赛道参赛材料', 'Subtitle')
md.extend(['# AURA 大模型协作记录\n', 'AMD 自主选题赛道参赛材料\n'])
p('整理日期 2026年11月3日', 'Caption')
h('1 协作目标与记录范围')
p('AURA项目围绕KV260视觉感知、FPGA运动监督、板端交互与记忆，以及Windows本地语言模型和语音合成服务开展开发。团队借助大模型进行方案比较、代码和脚本草拟、故障定位、测试设计与交付整理，并通过文件、日志和实测结果决定是否采纳。')
p('本记录按AMD指南3.3节自主选题赛道组织，覆盖真实提示词、模型可见回答、自我纠错、人工判断以及技能包提炼。开发协作工具登记为Codex；原消息未显示精确模型版本。终端运行的27B与OmniVoice属于作品组件，分别登记，避免与开发助手混用。[S01、S14]')
table(['指南要求', '本记录对应内容'], [
 ('3.3.3.1 交互与纠错', '第2至4节收录原消息摘录；第5至7节关联实际失败、修改和验证'),
 ('3.3.5.3 协作与工作流', '记录人机职责、候选形成、工具验证、接受或回退及版本归档'),
 ('3.3.5.2 技能包提炼', '第8节说明适用场景、使用方法、验证效果与失效条件'),
], [5.1, 11.7])
h('人工与模型的职责', 2)
p('人工提出应用需求、冻结质量与接口约束、反馈现场问题，并决定取舍。模型给出候选实现、排查路径和测试建议。工具输出与保存证据用于检查功能、数值及交付状态；团队核对后接受、部分接受或否决。记录以团队开发为单位，个人贡献以最终署名和实际分工确认。')
table(['阶段', '必须留下的内容'], [
 ('任务输入', '目标、当前源码、接口、已有结果与禁止改变的条件'),
 ('候选与纠错', '提示词和回答、首次失败、补充反馈、修改文件及原因'),
 ('验证与归档', '输入、命令、原始输出、适用范围、版本或SHA256'),
 ('提炼复用', '形成模板、反例、检查脚本和边界说明'),
], [3.0, 13.8])
p('第2至4节是从原聊天读取的可见交互；第5至7节为有文件依据的工程复盘。两类材料分别标识。文中的通过项沿用各自历史版本与测试条件，整理工作不更新设备现场状态。', 'Caption')

# Page 2
page(); h('2 真实交互案例 创新方向收敛')
p('案例D01  2026年10月4日至7日  开发工具Codex', 'Caption')
h('工程问题', 2)
p('团队希望将论文方法落到E盘现有工程，并从多项增补中选定一个研究方向。协作需要区分原方案已要求的功能与真正新增的研究内容。[D01、S04]')
label('第一次输入 原话')
qmsg('01a10723-311e-7551-9b54-e595ded4b702')
label('AI第一次回答 摘录')
qmsg('msg_0535908431854d91016ac25912db5087d0a303b47d73a17ff8', [0])
label('后续输入 原话')
qmsg('01a115e8-504e-7c93-9c97-b2d450d4db5b')
label('AI自我修正 原话')
qmsg('msg_0535908431854d91016ac620c0114c87d0bc53e7ebebbd2427')
h('修改与人工判断', 2)
p('候选方向由共享DPU调度、人脸模型和运动监督的并列增补，收敛为“感知有效期如何共同约束推理安排和动作许可”。AI重读手册后发现最新帧、租约和旧目标复核已在原要求中，因此修正了创新归属。团队进一步要求只集中一个方向，避免把完成原任务重复计算为新增贡献。')
table(['需要改动的位置', '形成的候选设计'], [
 ('视觉与跟踪', '根据真实观测、运动和误差预算确定位置证据有效期'),
 ('共享DPU调度', '在身份任务启动前检查是否挤占下一次检测期限'),
 ('FPGA执行监督', '核对源证据截止时间，重复旧命令不延长有效期'),
], [4.0, 12.8])
h('结果与可复用经验', 2)
p('该轮形成aura_single_innovation_direction_20261007.md，并提出固定期限与可变期限、普通调度与期限调度、软件检查与PL检查三类对照。消息和文档证明方案已形成；该案例不据此登记可变期限算法的板级收益。[S04]')
p('提炼规则：让AI先核对已有要求，再说明候选新增量、比较基线与测量方法。引用论文和完成原功能分别登记，创新效果由后续实现和对照数据支持。')

# Page 3
page(); h('3 真实交互案例 口型下巴缺口修复')
p('案例D02  2026年10月6日至8日  开发工具Codex', 'Caption')
h('用户反馈与AI修正', 2)
label('用户反馈 原话')
qmsg('01a11a82-d956-7b82-bebd-7e65fd28592e')
label('AI定位与自我纠错 原话')
qmsg('msg_0de92a7f14154b07016ac74d173f5487d0b8c64c1a1a575fe2')
p('旧检查只确认人物外部透明轮廓不变，漏掉脸与颈部之间的RGB边界。修复新增mouth_compositor.py，将嘴部遮罩收至脸内并羽化，保护y≥158的下巴区域；口型评分区域由延伸至y=165改为止于y=155，避免将颈部颜色计为张嘴。[S05、S08、S09]')
table(['验证项目', '修复前', '修复后'], [
 ('五套151帧的下巴保护区改变像素', '累计15,252', '0'),
 ('各套最大单通道误差', '132至229', '0'),
 ('插值开合与播放增益组合', '作为补充回归项', '420种组合检查通过'),
 ('完整相关回归', '本轮修复前不作计数对比', '550项通过'),
], [8.4, 3.8, 4.6])
img = ROOT / '共享文件夹/deliverables/2026-10-08_chin_fix/chin_before_after.png'
shutil.copyfile(img, EVID / 'chin_before_after.png')
par = doc.add_paragraph(); par.alignment = WD_ALIGN_PARAGRAPH.CENTER
par.add_run().add_picture(str(img), width=Cm(16.4))
p('图1 五套口型局部对照 上排修复前 下排修复后 来源S05目录中的原图', 'Caption')
md.append('![五套口型前后对照](../evidence/chin_before_after.png)\n')
h('最终决定与适用边界', 2)
p('修复应用到当时临时剧本与实时演示，并打包移机补丁。实测范围为现有464×480且已对齐的五套姿势；新增取景需重新核对保护区域。550项为相关完整回归总数，420种组合另列，二者不相加。该修复验证边缘稳定性。[S06、S07]')
p('提炼规则：为AI修改增加直接针对用户可见缺陷的反例。透明通道、内部边界与动作保留应分别检查；测试通过的旧版本仍可能暴露遗漏的验收维度。')

# Page 4
page(); h('4 真实交互案例 Windows与板端ASR联调')
p('案例D03  2026年10月17日  开发工具Codex', 'Caption')
h('原始输入与边界', 2)
p('原任务要求实际检查并启动服务，保留UI、TTS、FPGA、运动与相机配置。以下是任务正文的连续摘录；完整输入保存在附件D03。')
quote('请检查并接通这台 Windows 电脑与 AURA/KV260 板卡的录音转文字服务，尽量直接完成检查和启动，不要只给操作建议。')
label('AI检查结果 原话')
qmsg('msg_0267ae615e7504cb016ad364c068c08199b4f8e3206ca0bc22')
label('用户补充 原话')
qmsg('01a149df-51ea-72d0-af5b-2564cc30517e')
label('AI修正排查路径 原话')
qmsg('msg_0267ae615e7504cb016ad36d5685f081998b9c707a0d0a34cf')
h('实际处理与验证', 2)
p('排查从“模型和服务是否正常”深入到“源文件是否已同步到本机”。旧子目录任务显示完成并不能说明Ubuntu项目的最新代码已到达；旧配置中的另一台电脑路径也不能直接使用。四个ASR文件到位后，用本机可用环境启动原服务，再核对监听、健康接口、真实样例和限定访问规则。[S10]')
table(['项目', '当次保存结果'], [
 ('环境', 'Python 3.12.10；sherpa-onnx 1.13.8；numpy 2.5.3'),
 ('服务', '0.0.0.0:8791监听；两个Windows本机health均ready=true'),
 ('实际HTTP样例', '使用test_wavs/0.wav及aura-asr-1协议成功转写；识别耗时219ms'),
 ('访问范围', '仅板卡192.168.50.2经有线网卡访问本机8791/TCP'),
 ('同步结果', '项目待同步文件、字节和错误数均为0；两端进度100%'),
], [4.0, 12.8])
h('最终决定与可复用经验', 2)
p('当次Windows侧模型与服务验证通过；由于板端登录条件未满足，未登记板端重新录音及实屏文字通过。219ms是该HTTP样例的识别耗时，不作为完整语音交互延迟。以上均为2026年10月17日记录。[S10]')
p('提炼规则：跨机故障按源码到位、路径与环境、模型、监听、本机HTTP、远端HTTP、实屏结果逐层排查。每一层保留独立回执，远端验证缺失时不扩展本机结论。')

# Page 5
page(); h('5 FPGA与DPU工程协作复盘')
p('本节依据已有工程文件与结果复盘，使用工程摘要表述，不补写未收回的历史提示词。', 'Caption')
h('5.1 FPGA运动监督与联合工件交付', 2)
p('任务是在DPU联合平台内扩展运动监督，同时保持RTL、寄存器、驱动与部署工件配套。已有协作记录关联visual_servo.sv、prepare.tcl、implement.tcl和export_resume.tcl。原项目模式XSA导出失败后，从同一已路由DCP恢复导出，核对嵌入位流与部署载荷。[S02、S03]')
p('原记录登记4套RTL测试、204项控制器回归和18项C模拟，以及WNS 0.001ns和路由错误0。这里保留其历史证据身份：本次Windows整理直接核对的是原工程索引，所列Ubuntu构建源和工件未在本机重新读取或构建。数字PWM范围与机械零点、实际行程分别验收。')
p('纠错方法：导出失败先定位到导出阶段，确认已完成的路由结果和配套文件，再决定是否重建。资源、时序、软件回归与实物动作保持各自的证据入口。')
h('5.2 YuNet与SFace的DPU适配', 2)
p('协作围绕等价网络改写、量化校准、目标编译、VART运行器和固定向量比对开展。真实失败是首次板测退出码-11：XIR输出集合顺序与VART端口顺序不同，缓冲区大小被放到错误端口。修正为以VART接口顺序分配输入和输出，并增加端口互换回归。[S11]')
table(['检查层级', '保存结果与判断'], [
 ('可执行与数值一致性', 'YuNet四组输入399,500个INT8值、SFace四组512个值与量化模拟逐值相同'),
 ('SFace任务质量', '独立1000对：FP32与INT8模拟准确率均98.8%；误接收0→1，误拒绝12→11'),
 ('固定输入延迟', 'SFace板载ARM FP32中位520.86ms，DPU路径13.56ms；各8次，含转换'),
 ('三模型切换', '预编码输入下YOLO/YuNet/SFace为40/20/8次，100ms周期超时0次'),
], [4.4, 12.4])
p('数据分别来自编译、量化模拟、固定输入实板与调度测试，不混作同一次整机现场结果。实时试运行出现预算失配和USB音频告警时保留回退记录；单凭编译成功和总体准确率相同，不能推断全部现场条件成立。[S11至S13]')
p('提炼规则：依次确认网络兼容、浮点等价、量化质量、目标接口、逐值执行与业务现场。端口顺序由实际运行接口确定；总体质量与具体错误类型同时报告。')

# Page 6
page(); h('6 语言模型输出与资源协调复盘')
h('6.1 结构化台词优先交付', 2)
p('团队要求保留原27B、业务字段和语音质量，缩短附属字段阻塞有效台词的等待。协作修改dialogue_stream.py及相关测试，采用正文优先、内部短字段解析和原字段映射，并通过profile_compact_fields.py保留模型阶段测量。[S02、S14、S15]')
table(['模型阶段中位数', '原格式', '短字段格式'], [
 ('首正文', '1754.07ms', '1344.27ms'),
 ('台词字段就绪', '2762.88ms', '2287.70ms'),
 ('完整结构结束', '4737.30ms', '3745.70ms'),
], [8.0, 4.4, 4.4])
p('旧、新格式各4次，回复措辞与长度发生变化。这组结果用于定位模型输出阶段；已有对应版本回执登记75项相关测试、完整记忆检查及一次新的连续播放听音接受。one_second_goal_achieved=false，acoustic_onset_measured=false，保留原状态。[S14]')
p('纠错要点：首正文、台词就绪、首PCM与扬声器首声是不同事件。优化文字交付后继续核对字段语义、取消和播放，不把局部阶段缩短直接写成整机固定提速。')
h('6.2 LLM与TTS显存共存', 2)
p('协作形成gpu_coordination.py、对应资源配置及OmniVoice生命周期接点，保留27B IQ4_XS、2048上下文、OmniVoice 16步与原音色等约束。方案通过实时资源观测、有限准入、租约、有界排队及取消控制处理共存压力。[S16]')
p('原环境曾出现显存余量不足；首次最终启动又遇到七位小数时间戳与Python 3.10不兼容。启动脚本修正为六位小数后，在实际环境核对READY；失败的旧final_ready.json保留，成功结果另存final_ready_fixed.json。[S16]')
table(['验证项目', '对应历史结果'], [
 ('最终adaptive三组非缓存语音', '采样最低空闲1656MiB；首PCM为5.063、4.438、5.235秒'),
 ('合并回归', '637通过，0失败，0跳过；包含其他既有业务'),
 ('采用范围', '只登记原平台配置与样例；新桌面5090预算及表现另验'),
], [7.0, 9.8])
p('提炼规则：将冷启动、暖合成、LLM解码和其他模型占用分别建模。回归总数不当作专项测试数，少量非缓存样例也不扩展为所有负载下的显存或延迟保证。[S16、S17]')

# Page 7
page(); h('7 记忆存储与超时反例纠错')
h('7.1 摘要提交后回收原文', 2)
p('协作目标是在来源和会话范围内保存用户信息，助手历史以完整播放确认为提交条件；摘要经过校验并提交后，原文才进入回收流程。原协作索引关联board_memory.py、board_memory_policy.py与公开worker测试。[S02、S03]')
p('自然到期记录显示：闭合年龄约115.80秒时用户和助手正文各1行，约333.44秒后各0行；两者关联同一有效摘要，任务已提交，未强改时钟、强制压缩或删除。原状态为STORAGE_PASS_RECALL_PENDING，actual_prompt_retrieval_observed=false。[S18]')
p('工程判断：存储和回收已有验证，实际问答是否正确召回另立验收项。优化摘要容量时同时保留来源、更正、遗忘和迟到回写约束，失败任务不因统计方便而被写成成功。')
h('7.2 PYNQ迟到完成反例', 2)
p('接口生成工具首轮15项单元测试中14项通过，test_late_completion_does_not_bypass_timeout失败。合同期限100ms，完成标志到200ms才被软件观察到；旧逻辑先接受完成，再判断超时，导致迟到结果被误收。[S19]')
table(['步骤', '失败与纠正轨迹'], [
 ('输入与期望', '模拟MMIO读取将时钟推进至0.2秒并返回done=1；应抛出TimeoutError'),
 ('旧逻辑错误', '先判断done，直接退出轮询，未触发应有的超时异常'),
 ('实际修改', '状态读回后计算remaining；先拒绝remaining<0，再判断完成'),
 ('回归验证', '保留迟到完成反例；15项单元测试最终通过'),
], [3.6, 13.2])
p('修复位置为templates/driver.py.tmpl，反例位于tests/test_generator.py。保存日志逐项包含迟到完成、永不完成、读清除、元数据冲突等测试；生成后加法36例、CRC37例共73例通过，新目录源码SHA一致。[S20至S23]')
h('从观察形成约束', 2)
p('另一项实际观察是工程HWH存在地址窗口，但aura_m3_regs_0的REGISTER元素数为0。因此工具区分元数据匹配、不完整与冲突，缺项时输出受限骨架，已知冲突不绕过。软件轮询的期限检查不能中断已阻塞的MMIO，也不证明硬件最坏执行时间；现有验证范围为离线生成和模拟。[S19、S20]')

# Page 8
page(); h('8 技能包提炼与复用方法')
p('技能包从已出现的失败和反复核对动作中形成。每项复用内容保留输入、操作、反例、预期输出和失效条件，使其他队伍能够判断是否适用于自己的工程。A/B/C目录的原说明明确标为暂停技术草稿，后续来源依赖检查修改后未完整复测，尚非正式交付；PYNQ离线初版单独登记。[S24、S25]')
table(['经验来源', '可复用内容', '效果与边界'], [
 ('过期命令与执行许可', 'command-guard-validation：合同、RTL反例与轨迹检查草稿', '暂停草稿；RTL包装未确认PASS，机械及整机另验'),
 ('DPU端口错配与质量混淆', 'dpu-model-validation-and-scheduling：元数据与调度检查草稿', '暂停草稿；模型工程既有验证不等同此包已验收'),
 ('台词交付与播放确认', 'llm-voice-runtime-optimization：阶段与轨迹检查草稿', '暂停草稿；新硬件不能直接沿用历史预算'),
 ('HWH缺项与迟到完成', 'pynq-contract-testgen：合同驱动生成、反例和双示例', '15项单测及73个模拟用例；真实PYNQ、跨板、非作者复用未验证'),
], [4.0, 6.6, 6.2], size=9.7)
h('现有包的复现入口', 2)
p('A/B/C包位置为协作任务/2026-11-01_Skill交付规划/skill_delivery_v1/skill/。PYNQ包位置为协作任务/2026-11-02_pynq_skill/skill/pynq-contract-testgen/。从后者目录执行python3 -B scripts/reproduce.py --out <新的输出目录>，检查单元测试、加法、CRC与合同报告；硬件路径另备真实位流、HWH和兼容PYNQ环境。此处给出已有入口，未在本轮重新运行。[S24、S25]')
h('后续协作可采用的提示词', 2)
p('以下为本次从案例提炼的新模板，供后续使用；它们不作为历史原话。', 'Caption')
quote('请读取所给接口合同、当前实现和失败日志。先列出本轮必须保持的接口、质量和版本条件，再给最小修改。每一项结论注明直接证据、假设和验证方法。不要把编译成功、软件模拟或固定输入结果扩展为整机通过。')
quote('请先构造能够复现该错误的反例，再修改实现。保留同一反例和正常案例的回归结果，报告修改文件、输入、原始输出及适用边界。对未验证的候选明确保留状态，不用新的概述覆盖旧失败。')
h('接受一次AI修改的依据', 2)
p('团队核对输入与版本一致、反例得到正确处理、正常路径仍成立，并确认质量与资源代价后再采纳。归档原消息、实际修改及结果，随后提炼Skill。新环境、硬件或模型改变时，从其相关验证层重新检查。')

# Page 9
page(); h('9 原始交互与工程证据索引')
p('D01至D03原消息见evidence/conversation_messages.json；便于阅读的逐条摘录见evidence/conversation_excerpts.md。消息保留角色、原文、消息ID、会话和时间；仅收录可见回答，不收录模型内部推理。')
table(['编号', '原会话名称', '定位'], [
 ('D01', '查找论文方法的 FPGA 实现', '01a106bd-1181-7eb1-818e-56e52c4a5eca'),
 ('D02', '审查共享文件中的玩偶项目', '01a10a55-dcf6-7b50-89f5-bf6dad625b03'),
 ('D03', '接通 Windows 与 KV260 ASR', '01a149c0-ee96-7f02-9071-1c3bb096f193'),
], [1.6, 7.0, 8.2], size=9.2)
p('S01至S25的原始绝对路径、逐文件SHA256和快照路径见evidence/source_index.json。S01指南引用PDF第23至25页，即印刷页20至22。下表给出正文检索入口；除指南外均随记录保存小型文本快照。')
table(['编号', '证据内容', '附件快照'], [
 ('S01', 'AMD要求与提交内容', '原PDF路径及SHA见索引'),
 ('S02 S03', '原五案例记录及原38条来源索引', 'sources/s02.md  s03.json'),
 ('S04', '创新方向候选与比较设计', 'sources/s04.md'),
 ('S05至S09', '下巴修复说明、像素结果、回归与源码', 'sources/s05.md  s06.json  s07.json\ns08.py  s09.py'),
 ('S10', 'Windows ASR真实样例与服务回执', 'sources/s10.md'),
 ('S11至S13', 'DPU失败、固定输入实板与量化质量', 'sources/s11.md  s12.json  s13.json'),
 ('S14 S15', '短字段模型阶段与播放结果', 'sources/s14.json  s15.json'),
 ('S16 S17', '显存共存说明与637项回归', 'sources/s16.md  s17.xml'),
 ('S18', '自然到期存储与召回状态', 'sources/s18.json'),
 ('S19至S23', 'PYNQ失败、测试、修复与反例', 'sources/s19.md  s20.json  s21.log\ns22.py.tmpl  s23.py'),
 ('S24 S25', '技能包入口及离线说明', 'sources/s24.md  s25.md'),
], [2.2, 7.4, 7.2], size=9.5)
h('记录使用与归档', 2)
p('将本记录与相应工程版本、源码和技能包一同归档。原消息可证明交互过程；源码和结果用于核对实现与效果。历史构建索引中仅存在于Ubuntu的条目，在source_index.json中单列来源状态。最终参赛仓库可将本报告放入report/，现有技能内容按各包实际状态放入skill/。')
p('开发协作工具精确模型版本与个人署名按实际账户记录填写；本记录不将运行端模型名称代填为开发助手型号。未记录的板级、声学和独立复用结果保持其原状态。', 'Caption')

docx_path = REPORT / 'amd_llm_collaboration_record.docx'
doc.save(docx_path)
(REPORT / 'amd_llm_collaboration_record.md').write_text('\n'.join(md), encoding='utf-8')

excerpts = ['# 大模型协作原消息摘录\n',
    '来源为本次通过Codex聊天读取工具取得的可见消息。按案例归档；保留原消息文本与消息ID。精确模型版本未由读取结果提供。\n',
    '消息时间统一按America/Los_Angeles转换；正文引用连续原文片段，工程分析不作为逐字引文。\n']
for c in messages['cases']:
    excerpts.extend(['## ' + c['case_id'] + ' ' + c['title'] + '\n',
                     '原会话：' + c['thread_title'] + '\n', '会话ID：' + c['thread_id'] + '\n'])
    for t in c['turns']:
        stamp = datetime.fromtimestamp(t['started_at_unix'], ZoneInfo('America/Los_Angeles')).isoformat()
        excerpts.append('### 轮次 ' + t['turn_id'] + '\n\n时间：' + stamp + '\n')
        for m in t['messages']:
            excerpts.extend(['#### ' + ('用户' if m['role'] == 'user' else 'AI ' + str(m['phase'])) + '\n',
                             '消息ID：' + m['message_id'] + '\n', m['text'] + '\n'])
(EVID / 'conversation_excerpts.md').write_text('\n'.join(excerpts), encoding='utf-8')

readme = '''# AURA 大模型协作记录

按2026年AMD选题指南自主选题赛道3.3节整理，日期2026-11-03。

- report/amd_llm_collaboration_record.docx：可编辑正文。
- report/amd_llm_collaboration_record.md：同内容文本稿。
- evidence/conversation_excerpts.md：三组可见历史消息的可读附件。
- evidence/conversation_messages.json：原消息ID、会话、时间、角色与可见文本。
- evidence/source_index.json：25项本地来源的路径、SHA256及快照对应关系。
- evidence/sources/：24项小型文本来源原字节快照。
- evidence/chin_before_after.png：已有工程中的修复对照原图。

本次先清点E:\\项目约137311个文件条目，再重点阅读赛题、方案、协作记录、源码及相关运行证据。清点包含临时目录、环境与历史副本，并不表示逐个通读全部二进制或缓存。未读取或复制LLM权重；未改动原文档、业务源码、设备和模型服务。

第2至4节为真实消息摘录，第5至7节为工程复盘。历史模型版本未由聊天读取结果提供；运行端27B不代替开发助手型号。精确人员署名和开发模型版本请按实际账户记录填写。Ubuntu历史构建文件只保留索引来源身份，本轮未重新构建或复测。

本包中生成的md提示词模板明确标注为新模板。PYNQ真实硬件、跨板与非作者复用未验证，不能将离线验证改写为这些结果。单元测试15项和模拟用例73项分别统计。

本包只提交记录及小型证据，不包含模型权重、虚拟环境或数据库。对外提交时保留report与evidence的相对目录，核对最终队伍信息与工程版本。
'''
(OUT / 'readme.md').write_text(readme, encoding='utf-8')

# Check quotations independently of their document formatting.
checks = {
 'source_count': len(source_index),
 'source_snapshots': sum('snapshot' in e for e in source_index),
 'real_dialogue_cases': len(messages['cases']),
 'dialogue_messages': sum(len(t['messages']) for c in messages['cases'] for t in c['turns']),
 'docx_paragraphs': len(doc.paragraphs),
 'tables': len(doc.tables),
 'planned_pages': 9,
 'quote_anchors_verified': True,
 'runtime_or_model_tests_run_this_task': False,
 'render_status': 'pending',
}
json_write(TMP / 'content_validation.json', checks)
print(json.dumps({'docx':str(docx_path), 'output':str(OUT), 'checks':checks}, ensure_ascii=False))
