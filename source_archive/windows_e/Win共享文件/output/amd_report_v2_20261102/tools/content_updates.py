"""Compose the AMD seven-part report from retained project prose and frozen evidence."""
from pathlib import Path
import json
import re


REQUIREMENTS = [
    ('R1','选题背景与创新点','第1章','既有工作、应用问题与本项目贡献分开说明'),
    ('R2','设计原理与功能框图','第2章','总体、视觉、语音记忆与运动接口图'),
    ('R3','软硬件划分与接口','第3章','PS/PL/Windows分工、寄存器与数据合同'),
    ('R4','优化与性能资源对照','第4章','原始数据、样本量、前后对照与统计边界'),
    ('R5','大模型协作记录','第5章','真实可见问答、工程复盘和工具纠错分层归档'),
    ('R6','技能包提炼过程','第6章','失败来源、离线效果、使用方法和失效条件'),
    ('R7','从零复现说明','第7章','附件可执行步骤、整机输入与尚待完成的验收'),
]


def change(text, old, new):
    if old not in text:
        raise ValueError('Retained source changed; cannot safely replace: '+old[:80])
    return text.replace(old,new,1)


def compose(out: Path, old: Path):
    source=(old/'amd_design_report.md').read_text(encoding='utf8')
    metrics=json.loads((out/'data/metrics.json').read_text(encoding='utf8'))
    snapshot=json.loads((out/'data/project_snapshot.json').read_text(encoding='utf8'))
    fresh=metrics['fresh_offline_skill']
    core=source[source.index('## 1 选题背景'):source.index('## 7 复现说明')]
    core=change(core,'![图1 系统总体功能框图；实线表示数据或控制关系，Ubuntu 属于开发链](figures/system_overview.png)',
                '![图1 系统总体功能框图 运行端与外设接口](figures/system_overview.png)')
    core=change(core,'| 语音、字幕与角色显示 | 旧版本完整播放与渲染记录 | 旧版本成果保留，新版就绪待复验 |',
                '| 语音、字幕与角色显示 | 两轮真人完整播放及后续UI就绪回执 | 两轮属于先前启动；新版联合演示另验 |')
    core=change(core,'| 单轴随动 | 历史用户反馈、命令回执；较新试验异常中止 | 未认定最终机械验收通过 |',
                '| 单轴随动 | 用户现场确认跟随正常、无卡顿 | 功能行为验收已通过；精确角度和载荷仍无量化结论 |')
    core=change(core,'| 三模型视觉与身份 | 固定向量、公开评测和历史真人定向检查 | 具体场景、版本分别报告 |',
                '| 三模型视觉与独立身份 | 固定向量、公开评测、人脸KNOWN及声纹本人确认 | 各自报告验证范围；不加入人脸与声纹关联 |')
    core=core.replace('[V10–V11、V15]','[V10、V29、V31]')
    marker='### 2.4 单轴执行监督原理'
    core=change(core,marker,
        '人脸与声纹按独立服务工作。保存进度已记录人脸KNOWN和声纹本人三次独立录音识别的现场确认；普通聊天首句自动识别接入仍在推进。人脸与声纹跨模态关联已取消，不列入本版交付和联合演示的前提。[V29]\n\n'+marker)
    core=change(core,'![图4 运动协议与输出许可；停止/租约失效可以独立终止输出](figures/motion_protocol.png)',
                '![图4 PS检查与PL命令许可 源帧时效和命令租约分别处理](figures/motion_protocol.png)')
    core=change(core,'运动信号在宽版 XDC 中约束为 E10、LVCMOS33，对应项目记录中的 J2.3 连接路径。',
                '运动信号在宽版 XDC 中约束为封装脚 E10、LVCMOS33；B03参考资料将E10映射为J2.3。封装脚、连接器针号和模块端子是三类编号，实物载板版本与针1方向需要另行确认。')
    core=change(core,'最终材料需要补正面与45°整机照片、开发板高清特写、线序/供电图及机械装配图。',
                '附件wiring已给出资料核对版电气接线图、整机外设连接图及W01-W11逐线表，保留供电方案值和现场待核项。实物照片、实际供电值、模块端子和机械装配图需随最终实物记录补齐。')
    core=change(core,'更晚的新boot初始化出现实体异常并中止，应保留该失败及恢复记录。[V03、V17]',
                '历史新boot初始化曾出现实体异常并中止，其失败记录保留。11月2日后续交接已记录用户对随动正常、无卡顿的现场确认；这一功能行为验收不等于机械零点、精确角度或载荷测量通过。[V03、V17、V29–V30]')
    core=change(core,'| LUT | 66,969（57.18%） | 66,960（57.17%） | 全平台，减少9 |',
                '| LUT | 66,969（57.18%） | 66,960（57.17%） | 全平台差9，不解释为独立IP收益 |')
    core=change(core,'新桌面RTX5090的迁移与性能没有本轮可核验回执，预算不能直接沿用。[V15]',
                '后续5090主机的原模型与LAN部署已有通过记录，保存健康状态正常；旧平台的预算和性能比仍只适用于原试验，不能移作新主机的优化收益。[V15、V29]')
    anchor='### 4.3 量化质量及参考结果'
    core=change(core,anchor,
                '![图6 固定输入路径中位耗时对照 两个子图使用独立纵轴](figures/model_latency.png)\n\n'+anchor)

    # Refresh the stale ec12 summary using a frozen point-in-time documentary snapshot.
    start=core.index('### 4.8 完成状态与最终验收缺口')
    end=core.index('## 5 大模型协作记录与自我纠错',start)
    states='''### 4.8 保存进度与验收范围

以下状态依据2026年11月2日的保存进度与各模块回执摘录。它们记录不同层级的验证，不拼接成一次同版本全功能验收。保存进度的总体结论为：'''+snapshot['overall']+'''。[V29-V30]

| 模块 | 保存记录中的结论 | 证据 |
| --- | --- | --- |
'''
    for row in snapshot['modules']:
        states+='| '+row['module']+' | '+row['status'].replace('|','/')+' | V29 |\n'
    states+='''
转轴随动的功能行为验收已经收口，保留现有实现和参数。后续开机恢复和其他模块维护不自动扩大这一验收结论。独立人脸和声纹能力分别表述，跨模态关联不作为待做功能。普通聊天首句自动声纹识别、同条件性能后测、现有记忆长时召回、冷启动和新版联合演示仍按各自回执验收。[V29-V30]

### 4.9 两轮完整播放的软件时延

已有两轮真人交互的完整播放回执；下表读取同一份原始JSON。起点为录音完成事件，终点为每0.25秒采样观察到的软件SPEAKING状态，不是最后一个发音音节到扬声器物理首声的声学测量。[V31]

| 阶段或事件 | 第1轮 | 第2轮 |
| --- | --- | --- |
'''
    for name,key in [('ASR','asr_ms'),('上下文准备','context_ms'),('LLM RPC','llm_rpc_ms'),('TTS RPC','tts_rpc_ms'),
                     ('worker起点至首音频入队','first_audio_queued_from_worker_ms'),('录音完成至观测SPEAKING','capture_complete_to_observed_speaking_ms')]:
        states+=f'| {name} | {metrics["voice_turns"][0][key]:.2f} ms | {metrics["voice_turns"][1][key]:.2f} ms |\n'
    states+='''
两轮完整播放确认均已提交，记录中的当前轮欠载包和背压等待为0。样本只有两个短轮次，不据此给出可靠P95/P99、固定响应保证或新版联合性能结论。RPC耗时包含传输与服务等待；累计guard处理与后续音频事件重叠，不能把全部阶段数值直接求和当作首声时间。[V31]

<!-- pagebreak -->

'''
    core=core[:start]+states+core[end:]
    # Distinguish preserved engineering reviews from direct excerpts.
    core=change(core,'历史逐轮原始问答、辅助模型版本及个人实际贡献尚未全部回收；下列为工程过程复盘，不冒充逐字历史对话。[V15–V16]',
                '五个历史工程案例保留为基于源码和日志的复盘；原始逐轮问答与准确模型构建版本按实际留存情况登记。第5.5节另列本对话真实可见提示、答复和工具纠错，附件使用不同记录类型标识，不将复盘改写成历史逐字问答。[V15-V16、V33]')
    at=core.index('## 6 技能包的提炼、验证与边界')
    ai='''### 5.5 可见问答与文档生成纠错实录

案例AI06来自本对话可见消息和实际工具反馈，日期为2026年11月2日，工具为Codex；具体模型构建版本未记录。附件ai_collaboration/wiring_case_verbatim.json保留摘录、修订及验证来源。[V33]

用户提示摘录：

> 这个怎么做，按照我这个盘里面的资料，你可以帮我做一下么

AI公开答复摘录：

> 我会按盘里的接线资料和 FPGA 引脚约束，先做一份可放进报告的接线图和逐线接线表。资料能确认的内容会直接标出，尚未核实的实物端子会标为“待核对”，重点处理旧图 H12 与宽版约束 E10 的差异。

证据核对后采用宽版XDC中的E10；B03的J2.3映射与实物端子待核状态分别标注。首次PDF绘制把颜色名称white交给HexColor，实际工具报错如下：

```text
ValueError: invalid literal for int() with base 10: 'white'
```

实际修正为允许颜色名称的转换函数：

```python
c.setFillColor(colors.toColor(fill))
```

随后的图片审阅还发现电源域标题压到导线、W10/W11标签过近以及端口文字碰线，分别移位修订。最终三页PDF逐页通过检查，两个SVG可解析，W01-W11与逐线表一致。此案例证明的是资料核对、图纸生成与工具反馈纠错，不扩大为FPGA算法设计的原始协作记录。[V33]

<!-- pagebreak -->

'''
    core=core[:at]+ai+core[at:]
    core=change(core,'### 6.2 从失败到规则',
                '![图7 接口合同到生成代码与参考比对的工作流](figures/skill_workflow.png)\n\n### 6.2 从失败到规则')
    target='| 真实PYNQ / 跨板 / 非作者复用 | 未验证 | 不计入现有通过项 |'
    replacement=(f'| 本次Windows Python {fresh["python"]}复跑 | 15项单元测试、加法36例、CRC37例通过 | 独立目录，原Skill源码未改 |\n'+target)
    core=change(core,target,replacement)
    core=change(core,'加法按uint32模2^32，CRC采用CRC-32/ISO-HDLC并明确四个小端字节的输入规则。',
                '本次复跑的是同一套已有用例，增加了Windows环境可执行性的证据，不增加用例覆盖。原始日志、新目录输出及软件环境保存在attachments/validation；board_verified与pynq_imported均为false。[V32]\n\n加法按uint32模2^32，CRC采用CRC-32/ISO-HDLC并明确四个小端字节的输入规则。')
    core=core.replace('<!-- pagebreak -->\n\n<!-- pagebreak -->','<!-- pagebreak -->')

    introduction='''# AUAR 雪妃

基于 KV260 的多模型交互与执行监督系统

AMD 自主选题设计报告 V2  2026年11月2日

## 摘要

AUAR·雪妃以AMD KV260组织视觉感知、独立身份服务、语音交互、记忆和单轴执行。PS承担采集、预后处理、业务与显示，PL集成单个B4096 DPU和自研运动监督逻辑，Windows主机提供27B语言模型与OmniVoice语音合成。设计重点是多模型共享、结果时效、命令许可和完整回答交付。

历史固定输入对照中，YuNet与SFace路径中位耗时分别由124.02ms、520.86ms降为61.41ms、13.56ms；宽版平台使用66,960个LUT、710个DSP。后续记录已确认转轴随动、人脸KNOWN和声纹本人识别的阶段成果；新版联合演示、冷启动及长时召回仍待对应验收。接口合同Skill在本次Windows独立目录通过15项单元测试和73个模拟用例。各结果按其版本、输入与验证层级分别报告。

关键词：KV260；软硬件协同；多模型；执行监督；语音交互；可复现验证

### 七项要求与章节位置

| AMD要求 | 章节 | 配套内容 |
| --- | --- | --- |
'''
    for _,title,chapter,detail in REQUIREMENTS:
        introduction+=f'| {title} | {chapter} | {detail} |\n'
    introduction+='\n<!-- pagebreak -->\n\n'

    reproduction='''## 7 从零复现说明与交付状态

### 7.1 包内组成与复现层级

附件为本报告的可核对材料和离线Skill，不将其称为完整整机源码发布。下表分别说明可执行的离线层级与整机层级；整机层级仍需最终工程输入、配套release与目标设备验收。

| 层级 | 输入与入口 | 完成判据 |
| --- | --- | --- |
| 文档与证据核对 | source_index.json及attachments/evidence | 每个归档证据文件SHA一致 |
| 离线Skill复现 | reproduction/reproduce_offline.py | 15项单元、加法36例和CRC37例通过；board_verified=false |
| FPGA完整构建 | 完整平台工程、参考DCP、IP仓库与2022.2工具链 | 新目录构建、导出和配套检查通过；本附件未完成该层级 |
| 模型重建与板端软件 | 固定模型来源、校准数据、arch及最终源码清单 | 量化/编译/参考比对与同版部署分别通过 |
| 最终整机复现 | 外设、板卡、主机和统一release | 现场按说明完成业务、恢复与持续运行验收 |

### 7.2 在空目录复现包内材料

1. 将附件ZIP解压到新的工作目录，进入包含README.txt、source_index.json、skill和reproduction的目录。
2. 准备Python 3.8或更高版本。离线入口只需标准库，不安装PYNQ、不调用模型服务，也不加载位流。
3. 在工作目录执行以下命令；结果目录必须尚不存在。Linux可将python改为python3。

```bash
python --version
python -B reproduction/reproduce_offline.py --out ../auar_verify_01
```

4. 检查新目录summary.json的status=PASS，以及examples中的adder=36例、crc32=37例。单元测试原始输出见unit_tests.log，示例输出见examples.log及examples子目录。
5. summary中的board_verified和full_system_reproduced应保持false。这两个字段区分离线包可执行性与实际板卡/整机验证，不用离线PASS替代板测。

### 7.3 换题目使用Skill

在skill/pynq-contract-testgen目录提供自己的contract.json、真实或明确标识的HWH、输入向量与独立参考结果。只修改这些输入，保持生成器核心不变。先核对寄存器名称、偏移、访问权限、启动与完成语义，再生成驱动和测试骨架。

```bash
python -B scripts/generate.py --help
python -B -m unittest discover -s tests -v
```

已有加法器和CRC两个实例改变了布局、完成位和读清除语义。真实PYNQ模式需要匹配的bit/HWH、相应环境和已核对的硬件；合成样例不能进入硬件模式。具体参数和失效条件见Skill自带readme.md与contract_format.md。[V12-V13、V32]

### 7.4 整机复现的必需输入

| 输入集合 | 应固定的内容 | 当前状态 |
| --- | --- | --- |
| 工具链 | Vivado/Vitis/PetaLinux 2022.2、Vitis AI 3.0及原IP版本 | 历史配套关系有记录；需在重建环境确认安装与许可 |
| 参考平台 | source_routed.dcp、完整BD/RTL/XDC、repos.txt与IP源码 | 历史DCP为125,094,047B；本附件不含该DCP及完整IP仓库 |
| 配套输出 | 同次BIT/XSA/DTBO/XCLBIN与设备树 | 阶段证据已归档；最终release仍须统一 |
| 视觉模型 | 固定来源、预处理、校准/测试划分、arch与xmodel SHA | 保留V19的模型身份；不能自动换用公开库最新默认文件 |
| 板端业务 | 实际应用380组件、独立相机/控制器、原生库、配置与服务 | 以最终配套清单收拢，不任选早期aura目录替代 |
| Windows模型服务 | 27B/OmniVoice版本、运行库、外部模型路径与LAN配置 | 已有部署验收；旧平台性能和预算不迁作新成绩 |
| 实物 | 载板版本、相机、MCP01、屏幕、供电与舵机线序 | 接线资料版已提供，实物核线和型号记录另补 |

历史构建脚本要求的参考DCP SHA256为ac5f85a14eee133b56e06a514f37e3e8db30b2ae4d16a5490b79b926a07bb77e。完整重建前须取得这一输入，或先验证一条不依赖它的源码重建路线。只拿到脚本和综合报告不等于构建输入齐全。[V14]

### 7.5 FPGA构建步骤

1. 在Ubuntu新工作区准备完整平台工程与已核对参考DCP，固定工具版本、IP仓库、RTL/BD/XDC和输入SHA。
2. 将原构建入口中的VIVADO、REFERENCE、平台输出和IP路径映射到该工作区，保存修改差异和新的输入清单。V14为历史入口证据，其绝对路径不能直接在其他机器上使用。
3. 先执行tb_wide、tb_servo、tb_pulse_guard和tb_nominal四套RTL验证，再按prepare、implement顺序完成平台构建。
4. 归档utilization、clocks、timing、check_timing、route、DRC，按需要检查CDC；记录警告、外部时序缺项与失败，不以单个WNS代替全部约束完整性。
5. 从同次路由结果导出配套工件，核对XSA嵌入载荷、位流、DTBO/XCLBIN、IP ID/ABI/build与模型目标。独立验证成功后再安排目标板部署。

### 7.6 模型和软件准备步骤

1. 按V19模型清单取得固定版本YOLOX-Nano、YuNet和SFace，保留来源、许可与SHA。公开仓库会更新，复现应选择经过本项目验证的工件，而不是仅按同名最新文件替换。[3-4、V19]
2. 固定B4096目标fingerprint 0x101000056010407及真实arch.json，使用项目保留的等价改写、量化与编译脚本；校准、选阈值、独立测试身份保持分离。
3. 依次验证浮点等价、INT8任务质量、编译接口和实板固定向量。VART端口顺序、输入形状、缩放因子与预后处理应配套。
4. 按最终应用、相机、控制器和原生库清单准备板端文件与服务。Windows准备相应LLM/TTS环境；大语言模型权重位于项目共享目录之外，使用明确的外部路径配置。
5. 在各自设备维护流程下验证服务就绪和LAN请求。新启动需要建立新的上下文与实际配套关系，不沿用旧进程和旧启动的绑定凭据。

### 7.7 最终运行和验收步骤

在统一release上记录启动、相机有效帧、独立人脸/声纹状态、录音、ASR、回答、完整播放、字幕和记忆落盘。随后在同一合法会话自然超过五分钟后追问，记录摘要状态与真实回答，单独验证长时召回。

转轴按用户已经验收的实现和参数保留，不把继续调参作为本报告的复现前提。若申报机械角度、精度或载荷指标，应另有相应测量。冷启动、长期运行、网络异常与取消恢复按最终版本分别记录；跨模态关联已取消，不新增为联合演示要求。[V29-V30]

### 7.8 当前证据与下一次补录

| 项目 | 当前可确认结果 | 仍需要的证据 |
| --- | --- | --- |
| 本包离线执行 | 本次Windows 15项单元与73例通过 | 陌生人员独立复用可另录 |
| AI协作 | 可见原话摘录、实际工具纠错与五项工程复盘 | 核心开发历史逐轮原问答、准确模型版本和个人分工继续归档 |
| Skill | 合同/HWH检查、生成与模拟路径可执行 | 若申报PYNQ通用加分，补真实PYNQ/跨板或独立复用证据 |
| 完整重建 | 参考脚本、接口及阶段工件证据已整理 | 参考DCP/IP等完整输入与新目录完整构建日志 |
| 整机最终结果 | 分模块阶段通过与两轮历史播放数据 | 新版联合演示、同条件后测、长时召回、冷启动与持续运行 |

本包的离线成功按其层级报告。完整整机从零复现尚未通过，因此不填写虚构的最终release、机械实测或全系统性能数据。七项要求的章节、附件与证据范围见requirements/coverage.json。

<!-- pagebreak -->

'''
    references=source[source.index('## 参考文献'):source.index('## 附录 证据索引与缺项')]
    references=references.replace('[8] 全国大学生嵌入式芯片与系统设计竞赛. 2026FPGA创新设计赛道作品上传要求[Z]. 用户提供PDF。',
        '[8] 往届验证报告[Z]. 用户提供，9个PDF页面。仅参考验证环境、流程、指标和结果的组织方式，不采用其光计算参数或得分公式。')
    references=references.replace('外部技术来源于本轮查阅的原始论文、项目仓库和官方文档；模型部署与测试结论以本项目对应版本工件为准。来源定位与SHA见source_index.json。',
        '公开算法和工具文献用于说明已有基础。项目部署、性能和完成情况由对应版本证据支持；来源路径、归档SHA及新旧证据范围见source_index.json。')
    appendix='''## 附录 证据与附件导航

| 编号或目录 | 内容 | 使用范围 |
| --- | --- | --- |
| V01-V03、V20-V25 | 资源、时序、RTL/Tcl、引脚与时钟 | 对应历史联合平台 |
| V04-V07、V19 | 模型身份、固定输入和质量JSON | 模型路径及量化模拟，分别标注层级 |
| V08-V10 | 短字段、资源短窗和自然回收 | 对应原版本，不拼成最新整机结果 |
| V11、V17 | 旧发布状态和旧项目审查 | 历史快照；当前结论采用V29-V30 |
| V12-V16、V26-V28 | Skill旧验证和工程协作复盘 | 保留原始范围与缺项 |
| V29-V31 | 新保存进度、转轴用户验收和两轮时延 | 文件中的原时点，不是本轮新设备查询 |
| V32 | 本次Windows离线Skill验证 | 15单元、加法36例、CRC37例；不含板测 |
| V33 | 本对话提示/答复与实际工具纠错 | 公开可见摘录，不冒充全部历史导出 |
| attachments/wiring | 接线PDF、PNG、SVG、逐线表与图题 | 资料核对版，外部接线尚待实物核对 |
| reproduction | 可执行离线入口与完整重建输入说明 | 离线可复现；整机前提和待验项明确 |

报告正文、对照图与数据表使用同一份data/metrics.json的数值，图表与正文按来源交叉核对。原始阶段证据、实际离线输出、代码和使用边界一起保留，方便复查。
'''
    text=introduction+core+reproduction+references+'\n'+appendix
    text=text.replace('–','-').replace('—','-').replace('审阅稿 V1','版本 V2')
    return text,REQUIREMENTS
