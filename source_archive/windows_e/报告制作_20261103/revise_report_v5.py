from pathlib import Path
from datetime import datetime, timezone, timedelta
import shutil, json, hashlib, re, sys

sys.stdout.reconfigure(encoding='utf-8')
B = Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5')
OLD = B / 'v4_face_mosaic'
R = B / 'v5_contribution_bjt_simsun'
if R.exists():
    raise RuntimeError('Revision directory already exists; preserve it and inspect before re-running')
R.mkdir()
for name in ['data', 'evidence', 'figures', 'report', 'sources', 'tools']:
    shutil.copytree(OLD / name, R / name, ignore=shutil.ignore_patterns('__pycache__'))
(R / 'qa').mkdir()
shutil.copy2(OLD / 'readme.md', R / 'readme.md')
p = R / 'report/technical_report.md'
t = p.read_text(encoding='utf-8')
changes = []
def replace(old, new, label):
    global t
    if t.count(old) != 1:
        raise ValueError((label, t.count(old)))
    t = t.replace(old, new)
    changes.append(label)

replace('AMD 自主选题  技术报告 V2  2026年11月3日',
        'AMD 自主选题  技术报告 V5  2026年11月3日 北京时间', 'revision')
replace('人脸检测和特征提取采用 OpenCV Zoo 的 YuNet 与 SFace 作为基础。YuNet 提供人脸框及关键点，SFace 将对齐人脸转为可匹配的特征。项目增加目标工具链适配、INT8 量化、输出顺序检查和模板版本隔离。算法名称及公开模型属于既有成果，团队贡献集中在适配、调度、接口与验证。[R3]',
'''人脸检测和特征提取以 OpenCV Zoo 的 YuNet 与 SFace 公开模型为基础，团队针对 KV260 B4096 的算子与接口约束，完成了部署计算图的重构和等价改写。YuNet 按固定版本提取卷积、激活与池化子图，将形状整理和 Softmax 留在 PS，并将输入缩放的逆变换折入首层权重；SFace 则对 27 处 PReLU、全连接头和输出归一化层作等价表示转换，使计算主体能够进入目标 DPU 编译链。[R3][E15][E29]

在计算图改造之外，团队建立了公开数据校准、INT8 量化、目标编译、端口顺序核对和实板整数向量比对流程，并将特征模型与模板库按版本配套。这样，公开模型的网络能力转化为可在本项目单 DPU 与四核 ARM 环境中运行、可检查数值及任务质量的板端模块。固定输入实测中，YuNet 和 SFace 的迁移路径分别获得约 2.02 倍与 38.41 倍加速；该结果对应硬件与精度共同变化的路径对照，测试范围见第 5 章。[E04–E07][E19]''', 'model_contribution')
replace('''| 既有方法或平台 | 本项目复用部分 | 项目需要补足的问题 |
| --- | --- | --- |
| YOLOX 与 ByteTrack | 目标检测和轨迹关联 | 唯一相机源 时间关联 业务目标有效性 |
| YuNet 与 SFace | 人脸框 关键点 身份特征 | DPU 适配 量化一致性 拒识与模板版本 |
| AMD Vitis AI | 量化 编译 DPU 运行基础 | 三模型共享及 PS 预后处理组织 |
| AXI4-Lite 与 PYNQ | 寄存器访问和元数据接口 | 业务接受语义 有限执行许可 可复用测试 |''',
'''| 既有方法或平台 | 本项目采用基础 | 团队完成的改造与集成 |
| --- | --- | --- |
| YOLOX 与 ByteTrack | 目标检测与轨迹关联 | 统一相机源和帧标识 接入有效目标状态与跟随入口 |
| YuNet | 公开人脸检测网络与权重 | 重构卷积子图 输入缩放折叠 PS 解码与 DPU 分工 |
| SFace | 公开人脸特征网络与权重 | 27 处激活及全连接头等价改写 INT8 校准 模板版本配套 |
| AMD Vitis AI | 量化 编译及 DPU 运行工具 | 目标指纹和端口核对 三模型共享 逐整数实板验证 |
| AXI4-Lite 与 PYNQ | 寄存器访问及元数据接口 | 自研租约和序号事务 配套驱动 合同测试生成 |''', 'related_work_table')
replace('表 1-2 需求与评价指标', '表 1-2 需求 设计优势与评价依据', 'advantages_caption')
replace('''| 需求 | 实现机制 | 评价口径与已有结果 |
| --- | --- | --- |
| 持续观察用户 | 唯一相机源与检测轨迹 | 本次主检测约 9.89 Hz 观测年龄另测 |
| 多模型共存 | PS 准入与单 DPU 所有权 | 本次三模型均有完成计数 主超周期增量为 0 |
| 约束单轴执行 | 上下文 序号 租约 限速 | 四套 RTL 仿真 电气与机械另验 |
| 交互结果有效 | 请求代次 取消 播放确认 | 历史完整播放回执 软件事件不等于声学首声 |
| 工程可复现 | 固定输入 工件配套 分阶段回执 | 本次新目录 RTL 通过 完整部署范围见第 8 章 |''',
'''| 需求 | 团队设计 | 对应优势 | 评价依据 |
| --- | --- | --- | --- |
| 持续观察用户 | 唯一相机源 帧标识与轨迹 | 检测 身份与跟随可追溯到同源输入 | 主检测约 9.89 Hz 图龄另测 |
| 小模型高效部署 | 计算图改写 INT8 校准与 DPU 移植 | 保留公开模型能力 降低指定路径耗时 | YuNet 2.02 倍 SFace 38.41 倍 路径对照 |
| 多模型共存 | PS 准入及单 DPU 所有权 | 按需执行身份任务 为主视觉维持优先级 | 三模型计数推进 主超周期增量 0 |
| 语言模型与 FPGA 协同 | 主机语义推理 板端感知与执行 | 大模型服务与设备状态通过明确接口衔接 | 当前视觉 历史交互与 RTL 分别验证 |
| 约束单轴执行 | 上下文 连续序号 租约与限速 | 上层停顿后 PL 独立收回许可 | 四套 RTL 通过 电气与机械另验 |
| 交互结果有效 | 请求代次 取消及播放确认 | 迟到回答不重启旧会话 历史对应实际交付 | 历史完整播放回执 声学首声另测 |
| 工程可复现 | 固定向量 配套工件与阶段回执 | 定位兼容 数值和业务问题 支持模块替换 | 新目录 RTL 通过 完整部署见第 8 章 |''', 'advantages_table')
replace('第三项贡献是将回答交付与状态管理连接起来。有效回答进入播放和字幕，完整播放确认再参与历史提交；记忆摘要在校验和存储后才允许回收原文。开发中反复出现的接口与测试问题进一步提炼为 PYNQ Skill，使用两个独立任务和超时反例验证方法的复用性。',
'''第三项贡献是建立大语言模型与 FPGA 感知及执行系统的联合协同框架。团队将 Windows 上的 27B 大语言模型和语音合成服务，与 KV260 的 PS 业务管理、PL DPU 视觉推理和自研运动监督逻辑接入同一交互系统。板端负责真实输入、当前目标和会话状态，主机承担语义回答及语音生成，回答返回后再由板端校验并交付。该分工将大模型的语义能力与 FPGA 的视觉计算、定时输出能力衔接，使终端能在维持用户感知的同时组织语音交互。[E15][S02]

协同的关键在于把不同计算过程的有效条件写入接口。语言生成和网络返回的耗时会变化，PS 通过请求代次、取消和结果接受管理回答生命周期；运动请求经过目标与帧龄检查，再由 PL 独立验证序号、范围和租约。这样，语义交互、持续感知与受限动作能够在统一状态下配合，主机生成等待也不会成为 PL 输出许可的时间基准。当前跟随依据视觉目标形成，语言模型返回文本与音频，动作仍通过既定监督接口执行。[E20][E21]

有效回答进入播放、字幕与角色显示，完整播放确认后才提交已交付历史，摘要校验并落库后才回收原文。团队由此将主机推理结果落实到设备可见、可听和可追溯的交互过程。接口和测试中的反复问题进一步整理为 PYNQ Skill，以两个独立任务和超时反例验证方法复用，形成后续扩展模型与硬件模块的工程基础。''', 'llm_fpga_contribution')
replace('### 3.6 板端与 Windows 的协议生命周期',
        '### 3.6 大语言模型与 FPGA 的协同接口', 'collaboration_heading')
replace('请求返回时，板端检查任务是否取消、代次是否变化以及回答是否可用，再向播放和字幕交付。网络响应完成、PCM 入队、软件 SPEAKING 和扬声器首声分别是不同事件。只读健康接口与模型推理请求也分开：本次采集没有增加 LLM/TTS 生成任务。',
'''该接口把大模型能力连接到 FPGA 终端的实际交互流程。PS 维护输入、会话和请求标识，PL DPU 持续承担视觉计算，主机围绕板端组织的请求生成回答。模型端和硬件端通过数据格式及生命周期衔接，各自可以在保持接口的条件下升级；视觉推理、语言生成和运动监督的故障也能按边界定位。运动许可仍由 PS 与 PL 的专用事务链维护，语言模型输出不直接绕过监督逻辑写 PWM。

请求返回时，板端检查任务是否取消、代次是否变化以及回答是否可用，再向播放和字幕交付。网络响应完成、PCM 入队、软件 SPEAKING 和扬声器首声分别是不同事件。只读健康接口与模型推理请求也分开：本次采集没有增加 LLM/TTS 生成任务。''', 'collaboration_interface')
replace('模型迁移依次处理算子兼容、数值等价、代表性校准、INT8 量化、目标编译和板端向量比对。算子改写应先与原 FP32 输出核对，不能只以编译成功判断正确。编译后还要确认一个 DPU 子图的输入输出形状、目标 fingerprint、端口顺序和缩放因子。',
'''模型迁移依次处理算子兼容、数值等价、代表性校准、INT8 量化、目标编译和板端向量比对。团队为 YuNet 和 SFace 编写了目标平台适配代码，将公开权重转换为适合 B4096 执行的计算图，并保留模型外 PS 处理。编译后检查 DPU 子图的输入输出形状、目标 fingerprint、端口顺序和缩放因子，使模型工件与运行接口配套。[E15][E19][E29]

YuNet 的重构脚本按原始 ONNX 的 SHA256 固定版本，复建 43 个卷积、18 个 ReLU 和 5 个池化节点，保留四路网络输出。由于板端采用 BGR/256 输入，脚本把对应逆缩放折入首层卷积权重；输出的形状整理与 Softmax 由 CPU 完成。该处理明确了 DPU 计算主体与 PS 后处理的边界，避免将不匹配的输出布局直接接入人脸解码。[E29]

SFace 的改写针对目标工具链的表示约束。27 处 PReLU 按原斜率改写为残差、ReLU 与逐通道卷积的组合；全连接头改写为分组空间卷积和通道求和，保留原权重与偏置，移除中间 Flatten，并把输出 BatchNorm1d 转换为空间形式。脚本包含激活与全连接头的浮点等价检查，随后再做公开数据校准、INT8 量化、编译及板端向量核对。这里的成果是面向 FPGA 部署的模型计算图改造与验证，基础网络及预训练权重仍来自公开模型。[E15][E29]''', 'model_implementation')
replace('本次主机记录时间为洛杉矶 2026年11月3日 05:52:23 至 05:53:24，对应 UTC 13:52:23 至 13:53:24。板卡系统日期偏离实际时间，观察时长使用板端单调时钟，跨设备定位使用主机时间与 boot ID，不用两端墙钟相减计算单向延迟。61 个状态样本形成 60 个 CPU 差分区间，实际首末间隔为 59.988313 s。',
'''本报告日期和时刻统一采用北京时间（UTC+8）。本次资源采样的主机记录时间为 2026年11月3日 21:52:23 至 21:53:24。板卡系统日期偏离实际时间，观察时长使用板端单调时钟，跨设备定位使用主机时间与 boot ID，不用两端墙钟相减计算单向延迟。61 个状态样本形成 60 个 CPU 差分区间，实际首末间隔为 59.988313 s。原始证据中的时间戳保持采集格式，正文展示已换算为北京时间；耗时、周期、租约和相对观察时间继续使用原单位。''', 'beijing_measurement_time')
replace('图 1-1 板端视觉页面 人脸已作马赛克处理 2026年11月3日采集',
        '图 1-1 板端视觉页面 人脸已作马赛克处理 北京时间2026年11月3日22:47:40采集', 'beijing_screenshot_time')
replace('AUAR 雪妃形成了以 KV260 为感知与业务中心、Windows 为 LLM/TTS 推理节点的桌面交互结构。工程完成单 DPU 三模型的适配与组织、自研 PL 执行事务和受限 PWM、板端语音与记忆状态管理，并将接口失败提炼为离线测试生成 Skill。',
'''AUAR 雪妃形成了大语言模型与 FPGA 联合协同的桌面交互结构，以 KV260 为感知、设备状态与执行中心，以 Windows 为 27B LLM/TTS 推理节点。团队完成 YuNet 卷积子图重构、SFace 激活及全连接头等价改写、INT8 校准和三模型共享运行，将公开模型能力接入目标 FPGA 平台；通过 PS 的会话和任务管理、自研 PL 执行事务及播放确认，将主机语义推理与终端实时感知、受限动作和交付历史衔接。相关接口问题进一步提炼为离线测试生成 Skill。''', 'conclusion')
replace('| E19–E25 | evidence/history/v19 至 v25 | 模型身份 RTL 地址 引脚 时钟与时序 |',
        '| E19–E25 | evidence/history/v19 至 v25 | 模型身份 RTL 地址 引脚 时钟与时序 |\n| E29 | sources/model_adaptation 与 model_adaptation_manifest.json | YuNet 重构 SFace 等价改写及源码 SHA |', 'model_evidence_index')
replace('| L01 | figures/board_x11_live.png 及 live_summary.json | 当前界面 版本 音频枚举 |',
        '| L01 | figures/board_x11_live.png screenshot_replacement.json 及 live_summary.json | 马赛克界面截图 版本 音频枚举 |', 'screenshot_evidence_index')
p.write_text(t, encoding='utf-8')

# Preserve the actual adaptation code behind the expanded contribution claims.
source_root = Path(r'E:\Win共享文件\语音共享文件\deliverables\2026-10-21_dpu_vision_start\source')
out_source = R / 'sources/model_adaptation'
out_source.mkdir()
records=[]
for name in ['reconstruct_yunet.py', 'rewrite_sface_v2.py']:
    src=source_root/name
    shutil.copy2(src, out_source/name)
    records.append({'path':'sources/model_adaptation/'+name,'source':str(src), 'sha256':hashlib.sha256(src.read_bytes()).hexdigest()})
(R/'sources/model_adaptation_manifest.json').write_text(json.dumps({'scope':'Historical deployment adaptation source; no new training or board run in this editorial revision','files':records},ensure_ascii=False,indent=2),encoding='utf-8')

# Use Song throughout editable text, including Latin characters, code and headers.
p=R/'tools/build_word.py';s=p.read_text(encoding='utf-8')
s=s.replace("'黑体'", "'宋体'").replace("'Consolas'", "'宋体'")
s=s.replace("f.set(qn('w:eastAsia'),name)", "\n for at in ['ascii','hAnsi','eastAsia','cs']:f.set(qn('w:'+at),name)")
s=s.replace("cp('技术报告 V2'", "cp('技术报告 V5'")
s=s.replace("cp('2026年11月3日',", "cp('2026年11月3日 北京时间',")
s=s.replace(" if nc==5:weights=[1.8,1,1,1,1]", " if nc==5:weights=[1.8,1,1,1,1]\n if nc==4 and rows[0][0]=='需求':weights=[1.05,1.5,1.85,1.6]")
s=s.replace("out=ROOT/'auar_xuefei_technical_report.docx';doc.save(out)", "from apply_simsun import apply_simsun\napply_simsun(doc)\nout=ROOT/'auar_xuefei_technical_report.docx';doc.save(out)")
s += "\n# Reapply after header creation to cover PAGE fields and all story parts.\ndoc=Document(out)\napply_simsun(doc)\ndoc.save(out)\n"
p.write_text(s,encoding='utf-8')
helper='''from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def apply_simsun(doc):
    def fonts(parent):
        f=parent.find(qn('w:rFonts'))
        if f is None:
            f=OxmlElement('w:rFonts');parent.insert(0,f)
        for key in list(f.attrib):
            if 'Theme' in key or key.endswith('hint'):
                del f.attrib[key]
        for attr in ['ascii','hAnsi','eastAsia','cs']:
            f.set(qn('w:'+attr),'宋体')
    for st in doc.styles:
        rp=st.element.find(qn('w:rPr'))
        if rp is None:rp=OxmlElement('w:rPr');st.element.append(rp)
        fonts(rp)
    defaults=doc.styles.element.find(qn('w:docDefaults'))
    if defaults is None:defaults=OxmlElement('w:docDefaults');doc.styles.element.insert(0,defaults)
    rd=defaults.find(qn('w:rPrDefault'))
    if rd is None:rd=OxmlElement('w:rPrDefault');defaults.append(rd)
    rp=rd.find(qn('w:rPr'))
    if rp is None:rp=OxmlElement('w:rPr');rd.append(rp)
    fonts(rp)
    roots=[doc.element]
    for sec in doc.sections:
        roots.extend([sec.header._element,sec.footer._element])
    for root in roots:
        for run in root.iter(qn('w:r')):
            rp=run.find(qn('w:rPr'))
            if rp is None:rp=OxmlElement('w:rPr');run.insert(0,rp)
            fonts(rp)
'''
(R/'tools/apply_simsun.py').write_text(helper,encoding='utf-8')
p=R/'tools/apply_header_logo.py';s=p.read_text(encoding='utf-8').replace("'Times New Roman'","'宋体'");p.write_text(s,encoding='utf-8')
for name in ['export_word.ps1','export_header_word.ps1']:
    p=R/'tools'/name;s=p.read_text(encoding='utf-8')
    needle='    $reportDocument.Repaginate()\n    foreach ($reportToc in $reportDocument.TablesOfContents) { $reportToc.UpdatePageNumbers() }'
    replacement='''    foreach ($reportStory in $reportDocument.StoryRanges) {
        $reportRange = $reportStory
        while ($null -ne $reportRange) {
            $reportRange.Font.Name = '宋体'
            $reportRange.Font.NameAscii = '宋体'
            $reportRange.Font.NameOther = '宋体'
            $reportRange.Font.NameFarEast = '宋体'
            $reportRange.Font.NameBi = '宋体'
            $reportRange = $reportRange.NextStoryRange
        }
    }
    $reportDocument.Repaginate()
    foreach ($reportToc in $reportDocument.TablesOfContents) { $reportToc.UpdatePageNumbers() }'''
    assert needle in s
    p.write_text(s.replace(needle,replacement),encoding='utf-8-sig')
p=R/'tools/build_diagrams.py';s=p.read_text(encoding='utf-8').replace('msyh.ttc','simsun.ttc').replace('msyhbd.ttc','simsun.ttc');p.write_text(s,encoding='utf-8')

now=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
note='''# 贡献说明 北京时间与宋体修订

本版加强 YuNet/SFace 的实际计算图改造、模型部署及质量验证说明，扩展需求和设计优势表，重点补充大语言模型与 FPGA 的协同框架及接口。相关新增表述可追溯至历史适配源码与测试记录，没有新增模型训练或性能实验。

报告可编辑文字全部使用宋体，覆盖封面、标题、正文、目录、表格、图注、代码、页眉和页码；新制机制图及曲线文字也统一宋体。真实软件截图及原始比赛 logo 保留其原始界面和标识字体。

报告显示的日期和时刻统一为北京时间 UTC+8。资源采样窗口为2026年11月3日21:52:23至21:53:24；新视觉截图为同日22:47:40。耗时、周期和相对时间不做时区换算。原始证据保留原始时间戳，换算关系另存 evidence/timezone_display.json。

延续左上比赛 logo、右上页码及细线页眉，延续真实视觉页的人脸粗马赛克；未打码的脸部原图不进入本包。

'''
p=R/'readme.md';s=p.read_text(encoding='utf-8');s=s.replace('本次仅修改页眉与页码位置。','该次修订仅修改页眉与页码位置。').replace('日志同时保留主机UTC、单调时长和bootID。','原始日志保留主机时间戳、单调时长和bootID，正文的日期与时刻统一显示北京时间。');p.write_text(note+s,encoding='utf-8')
(R/'evidence/timezone_display.json').write_text(json.dumps({'display_timezone':'Asia/Shanghai','display_utc_offset':'+08:00','resource_observation':{'start_beijing':'2026-11-03T21:52:23+08:00','end_beijing':'2026-11-03T21:53:24+08:00','source_start_utc':'2026-11-03T13:52:23+00:00','source_end_utc':'2026-11-03T13:53:24+00:00'},'screenshot_capture':{'beijing':'2026-11-03T22:47:40.254808+08:00','source_utc':'2026-11-03T14:47:40.254808+00:00'},'raw_evidence':'Unmodified original timestamps retained for audit','durations':'Not shifted; durations, leases and relative plot axes retain their units'},ensure_ascii=False,indent=2),encoding='utf-8')
(R/'qa/editorial_changes.json').write_text(json.dumps({'revision':R.name,'edited_at_beijing':now,'changes':changes,'new_model_or_physical_tests':False,'font':'宋体','figure_screenshot_sha256':hashlib.sha256((R/'figures/board_x11_live.png').read_bytes()).hexdigest(),'raw_unredacted_face_in_package':False},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'directory':str(R),'editorial_changes':changes,'markdown_chars':len(t)},ensure_ascii=False,indent=2))
