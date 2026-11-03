from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,re,shutil,hashlib,sys
sys.stdout.reconfigure(encoding='utf-8')
B=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5')
R=B/'v6_verified_revision'
F=B/'self_audit_latest_package/frozen_sources'
S=Path(r'E:\Win共享文件\语音共享文件\deliverables\2026-11-03_scheme_a_source_release_9a4f')
assert json.loads((B/'self_audit_latest_package/verification_basis.json').read_text(encoding='utf-8'))['recomputed_checksums']==1686
P=R/'report/technical_report.md';t=P.read_text(encoding='utf-8')
assert '技术报告 V5' in t
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def rep(a,b):
 global t
 assert t.count(a)==1,(a[:70],t.count(a))
 t=t.replace(a,b)
def add_after(a,b):rep(a,a+'\n\n'+b)
today=datetime.now(timezone(timedelta(hours=8))).strftime('%Y年%m月%d日')
rep('AMD 自主选题  技术报告 V5  2026年11月3日 北京时间','AMD 自主选题  技术报告 V6  '+today+' 北京时间')
rep('历史固定输入实验中，YuNet 的 ARM FP32 与 DPU INT8 路径中位耗时分别为 124.02 ms 和 61.41 ms，SFace 分别为 520.86 ms 和 13.56 ms；对照同时改变硬件与精度。公开独立 1000 对人脸测试中，两种精度路径的准确率均为 98.8%。宽版联合平台使用 66,960 个 LUT、710 个 DSP，已约束路径 WNS 为 0.001 ns。本次在当前板卡上进行 59.988 s 自然业务观察，CPU 平均占用 79.43%，主检测与 YuNet 完成频率分别约为 9.89 Hz 和 9.85 Hz，主任务超周期计数无新增；另完成 30 次 ICMP 往返采样与四套 Ubuntu XSim 测试。',
'''历史固定输入路径对照中，YuNet 由 ARM FP32 的 124.02 ms 降至 DPU INT8 的 61.41 ms，约加速 2.02 倍；SFace 由 520.86 ms 降至 13.56 ms，约加速 38.41 倍，样本分别为 40 次与 8 次。公开独立 1000 对人脸测试中，FP32 与 INT8 模拟总体准确率均为 98.8%，错误类型在正文分列。约 1 分钟板端自然负载观察中，主检测约 9.89 Hz，YuNet 591 次、SFace 8 次原生完成，二者失败计数均无新增。历史两轮真人交互均保存完整播放回执。上述数据各自保留模型版本、输入及计时范围。

最新已交付源码 RAR 共 1687 个文件，1686 条文件校验通过；该包从源码完成综合、实现及解包复跑，使用 66,887 个 LUT、123,100 个 FF 和 710 个 DSP，WNS 为 0.002 ns、WHS 为 0.010 ns，路由错误及 DRC Error 为 0。本报告将历史实板测量、报告采样、独立 RTL 重跑及源码重建结果分别关联到工件指纹；新固件、原生库及新编译模型的实板验收另列。''')
rep('历史固定输入数据证明两条人脸模型迁移路径的耗时变化，本次观察证明当前负载下三模型计数持续推进','历史固定输入数据支持两条人脸模型迁移路径的耗时结论，约 1 分钟观察记录了当前负载下三模型计数持续推进')
add_after('| SFace | 112×112 对齐人脸 | 12b2ff5c7de15713 | 输入输出转换 归一化 匹配 |',
'''表 4-1 对应历史部署工件。最新源码包重新编译出的 YuNet 为 1219f82492943772…，SFace 为 d37b5a806bbec566…；其编译、量化与主机评估已完成，回执标记为 COMPILED_CANDIDATE_NOT_PRODUCTION_ACCEPTED。第 5 章的历史板端速度和逐整数一致结果仍归属于表 4-1 的旧图，两个新图需独立完成同输入板测后再更新成绩。[E32]''')
rep('表 5-1 历史固定输入路径对照 单位为 ms','表 5-1 历史固定输入路径对照 单位为 ms 小样本不报告尾部分位数')
rep('| SFace 8 次对齐输入 | 520.86 | 627.78 | 13.56 | 26.60 |','| SFace 8 次对齐输入 | 520.86 | 不报告 n=8 | 13.56 | 不报告 n=8 |')
rep('对应中位耗时比约为 2.02 倍和 38.41 倍。该结果反映执行硬件与数值精度组合变化，不把收益全部归因于量化，也不外推为整机问答加速。SFace 样本仅 8 次，P95 对单个样本敏感，不能用于估计稳定尾延迟。',
'''对应路径中位耗时比分别约为 2.02 倍和 38.41 倍，体现执行硬件与数值精度共同变化后的路径收益。YuNet 包含预后处理，SFace 输入已对齐并包含转换，两者与整机问答分别计量。SFace 的 8 次样本用于展示固定输入路径的中位数，表和图不再报告其 P95；原始描述性统计仍保留在历史 JSON 中。[E04][E05]''')
rep('图 5-1 固定输入路径耗时对照 硬件与精度同时变化 样本分别为 40 次和 8 次','图 5-1 固定输入路径耗时对照 YuNet n=40 SFace n=8 数据见 data/history_latency_summary.csv')
rep('图 5-2 SFace 每 100 对独立分组准确率 1000 对为主机公开测试 INT8 为量化模拟','图 5-2 SFace 独立测试共1000对 每组100对 主机INT8模拟 数据见 evidence/history/v06_sface_quality.json')
rep('图 5-3 SFace 低误接收区间 ROC 工作点由独立训练配对确定 500 个负对的非零 FAR 分辨率为 0.2%','图 5-3 SFace ROC 正负各500对 非零FAR分辨率0.2% 统计点见 figures/history_sface_roc.svg')
add_after('可选模型原生完成计数与主视觉完成计数分别计算，不能把 API 频率字段简单相加当成 DPU 满载吞吐。[L02]',
'''本窗口采集计数增加 1354，主检测计数增加 593，差为 761；这是两个处理层计数的差额，逐帧跳过和背压的归因未在本次快照中采集。22.57 Hz 是该窗口实际采集频率，主检测按约 100 ms 的业务节拍处理。前段固定输入切换实验中的 10/5/2 Hz 是历史测试配置，可选身份任务在当前业务中按目标和预算准入，其频率不按该历史比例判定。''')
rep('### 5.5 语音响应与回答交付优化','### 5.5 语音阶段拆解与回答交付')
add_after('两组回复措辞和长度发生变化，该数据用于定位阶段开销，不作为严格同文本收益。[E08]',
'''这组 n=4 的结果作为阶段拆解示例，说明输出字段顺序会影响有效台词何时可消费。正式优化收益应采用同模型、同输入和配对文本检验，当前材料未给出这种因果对照。''')
add_after('它们分别属于合成短测与软件事件计时，未测扬声器真实首声。',
'''这里均为两点示例，未计算对话分位数。两轮的 LLM RPC 分别约 1.940 s 和 1.833 s，TTS RPC 约 0.766 s 和 0.838 s；RPC 指应用请求往返，包含传输及服务等待。RTF 为合成耗时与音频时长之比。完整播放回执表示软件已报告完整播放，声学首声由独立物理测量确认。''')
rep('P50 为 1.010 ms、P95 为 1.7365 ms、P99 为 1.821 ms，最大为 1.850 ms，平均约 1.056 ms','中位数为 1.010 ms、样本 P95 约 1.737 ms，最大为 1.850 ms，平均约 1.056 ms')
rep('30 个样本的 P99 只是本样本插值统计，不支持稀有网络尾部事件判断。','本节不再用 30 个样本报告 P99，稀有网络尾部事件需更长窗口记录。')
add_after('| WNS 及 WHS | 0.001 及 0.000 ns | 0.001 及 0.000 ns | 已约束路径 |',
'''表 5-4 最新源码包重建与历史宽版对照

| 指标 | 历史宽版 E02 E25 | 源码重建 E31 | 含义 |
| --- | --- | --- | --- |
| LUT 与 FF | 66,960 与 124,192 | 66,887 与 123,100 | 各自完整联合平台 |
| BRAM Tile URAM DSP | 93.5 56 710 | 93.5 56 710 | 资源类别计数 |
| 已用 CLB 站点 | 13,968 / 14,640 95.41% | 14,440 / 14,640 98.63% | 站点占用与 LUT 利用率分别解释 |
| WNS TNS | 0.001 / 0.000 ns | 0.002 / 0.000 ns | setup 违规端点均为 0 |
| WHS THS | 0.000 / 0.000 ns | 0.010 / 0.000 ns | hold 违规端点均为 0 |
| 路由完全布通 | 200,473 条 | 199,333 条 | 路由错误均为 0 |
| 物理板测 | 见各历史记录 | 本轮未执行 | 新实现与现役板端分开 |

新结果来自整包 SHA 为 022422d9… 的源码重建回执。新 BIT 与 XSA 的配置载荷逐字节一致，设备树与实际归档底图合并、XCLBIN 八段回读均通过。已接受 WNS 0.002 ns、WHS 0.010 ns 的合格基线；后续可选时序优化未形成另一份合格结果，报告不计入额外优化收益。原生报告关键行、完整指纹和 DRC 分类列于附录 G。[E30][E31]''')
rep('表 5-4 功能与异常验证范围',
'''表 5-5 已有任务计数与判定口径

| 对象与窗口 | 参考或期望 | PASS / FAIL | 分母及适用范围 |
| --- | --- | --- | --- |
| 当前 YuNet 原生任务 | 本窗失败增量为 0 | 591 完成 / 0 失败 | 本窗 calls 增量 591 |
| 当前 SFace 原生任务 | 本窗失败增量为 0 | 8 完成 / 0 失败 | 本窗 calls 增量 8 |
| 历史完整播放交付 | 每个选中轮次有完整回执 | 2 / 0 | 已完成的两轮观察 不是全场景成功率 |
| 本次独立 RTL 重跑 | 四台均有通过标记 | 4 / 0 | 4台各执行3阶段 共12个退出码为0 |
| Skill 单元测试 | 正例与反例均符合合同 | 15 / 0 | 保存的15项单元测试 |
| Skill 模拟向量 | 输出与独立参考一致 | 73 / 0 | 加法36个 CRC37个 |

该表提供有依据的任务计数。整机从感知到机械和真实出声的任务分母尚未采集，未由上述软件计数合成整机成功率。

表 5-6 功能与异常验证范围''')
rep('源码包已将 380 项主业务、224 项独立相机、25 项运动控制和多组锁外依赖分别登记。39 处相机与主业务同名异版按命名空间保留；默认设置可由原读写器生成。正式外置文件与配置全部一致时可以精确恢复旧清单，现场参数改变则必须生成新的有效发布指纹。',
'''本版对应已交付 RAR 的 SHA256 为 022422d9d1efa6106c2b247ac901dddd2f439a1a5e8eb19a22539010c3a944f4，共 1687 个文件、44,475,833 字节；checksums.sha256 有 1686 条记录并排除自身。该同 SHA 的冻结解包树已重新计算全部文件指纹，匹配通过。[E30]

380 项主业务、224 项独立相机和 25 项运动控制是部署源清单的登记数，各集合可能重叠，不是 RAR 文件数。板端采样的 380 个启动组件又属于当时运行配置，需与其 69080f98… 启动指纹配对；源码重建的离线部署则恢复 9a4f06da… 基准。39 处同名异版按命名空间保留，现场参数改变后应生成新的发布指纹。''')
rep('以下是本次实际重跑 RTL 的命令形式。进入方案 A 工程根，将输出设为全新目录；本次实际输出为 /home/ghmd/auar-techdoc-01a1a1a5/verification，已验证四套 bench 通过。示例使用另一全新目录名，避免覆盖回执。',
'''以下命令在解包后的唯一工程根执行。将 VIV、VIT 指向合法安装的 2022.2 工具，OUT 指向源码树之外的全新输出目录。工具版本锁在 build/env.json，路径由复现者填写；本报告不要求保留作者的用户名或旧目录。四套 RTL 的 12 阶段记录和源码重建结果分别保存在 L03 与 E30/E31。''')
rep('export VIV=/home/ghmd/Xilinx_2022.2/Vivado/2022.2\nexport VIT=/home/ghmd/Xilinx_2022.2/Vitis/2022.2\nexport OUT=/home/ghmd/auar_reproduce_new',
'''export VIV="$DEPS/Xilinx/2022.2/Vivado/2022.2"
export VIT="$DEPS/Xilinx/2022.2/Vitis/2022.2"
export OUT="$AUAR_NEW_OUTPUT"''')
rep('本次报告工作没有重新执行综合实现，已有 prepare 与其他构建记录保留在独立证据中。',
'''报告采集任务与工程包构建分别执行。最新源码包已完成综合、实现、BIT/XSA 导出及解包后的软件、Skill、RTL、建工程等复跑；新工件的目标板与物理验收状态见 E30/E31。''')
rep('现有整数一致及 1000 对质量结果只属于各自保存工件，本次没有重新量化或推理公开测试集。',
'''工程包已重新运行两模型的量化、评估和目标编译，生成的候选 SHA 见 E32。历史逐整数一致及 1000 对质量数据继续与旧工件绑定，新编译输出的质量与板端执行按其自己的记录评价。报告另附历史 YuNet 全零合成输入及四个期望 INT8 输出，共 16,085 字节，无人脸像素；完整四组的输入输出字节数及 SHA 见 public_vectors/historical_vector_manifest.json。[E36]''')
add_after('INPUTS 由读者设置为有权读取的原件目录，AUDIO_ZIP 指向独立音频附件，不能省略后声称相同安装。',
'''15 项板端音频依赖包含 ASR、前端降噪/VAD、说话人模型和 ARM64 Python 轮子，未压缩合计 211,612,620 字节，逐件路径、大小与 SHA 在 src/models/inputs/board_audio_dependencies.json。授权持有者需另备 auar_board_audio_dependencies.zip；省略 --audio 时回执明确记录 0 项。公开分发和取得路线仍须依据各上游与团队授权，源码包本身不包含这些权重。

八个原生库已从源码交叉编译，其中三个与历史部署输入的 SHA 相同，五个不同；新 SO、两个新 xmodel 及新固件都需先形成候选清单，再完成目标板验证和正式绑定。install.sh 的 plan/index/board/windows 子命令已与 stage.py 参数核对，它执行包外目录的离线落盘，后续 systemd 安装与上电检查另按 deploy.json 执行。[E33][E34]''')
rep('本次在独立 Ubuntu 输出目录实际执行四套 RTL 测试，并读取当前 KV260 状态；Windows 汇总数据后，将 CSV 送到 Ubuntu 的已有 Vitis AI CPU 容器，用 Matplotlib 3.4.3 生成三组新曲线，再取回配图。容器只用于绘图，不运行模型推理。[L03][L04]',
'''证据分为四层。历史固定输入与任务质量保留原工件；报告采样保存约 1 分钟板端状态、30 次 ICMP 和真实页面；独立 Ubuntu 目录保留四套 RTL 重跑；工程包证据则关联最新 RAR 的源码综合、实现、量化编译和解包复跑。前三层的范围延续原报告，第四层补足本次源码交付的结果。[E30–E34][L01–L04]

原始 CSV 在 Ubuntu 既有 Vitis AI CPU 容器中由 Matplotlib 3.4.3 生成三组曲线；本次排版统一其宋体字体并核对曲线几何不变。绘图容器未在该任务中执行模型推理。''')
add_after('所有新增结果都应能回到具体版本、输入和原始证据。',
'''资源扩展还受布局和时序限制。历史宽版已用 CLB 站点 95.41%，最新源码重建为 98.63%，URAM 均为 87.50%；站点被占用不等于其中所有 LUT/FF 都已用满，但分布拥挤会增加新增逻辑的布局与时序压力。后续先按实际布局、布线和时序重新评估 DPU/IP 组合，再决定裁减逻辑或调整器件，当前 WNS 0.002 ns 仅说明指定约束通过。''')
rep('export DTC17=/home/ghmd/kv260-dpu41-control-20261001/dependencies/dtc-1.7.2','export DTC17="$DEPS/dtc-1.7.2"')
rep('--base-dtb /home/ghmd/aura-system-pan-20261028/fresh-base.dtb','--base-dtb "$BASE_DTB"')
rep('--rootfs /home/ghmd/kv260-sd-backup-20261003/offline-inspection/root.original.ext4','--rootfs "$ROOTFS_EXT4"')
add_after('原生交叉构建需要固定 EXT4 内的开发头文件与库，包内入口为 build/prepare_cross_sdk.py。缺依赖时先核对目标 sysroot 和链接路径，不复用未知旧对象来宣称源码已构建。',
'''DEPS 是使用者选择的依赖根目录，AUAR_NEW_OUTPUT 是其新输出目录，INPUTS 是授权原件索引根。DTC 1.7.2 的源归档来自 kernel.org，固定 SHA 见 build/env.json；Bootgen、xclbinutil 和 DTC 1.6.1 来自匹配的 Vitis 2022.2 安装。BASE_DTB 与 ROOTFS_EXT4 取自匹配目标系统的授权归档，底图 SHA 为 22516e08…，镜像与分区信息见 board/system/image_manifest.json。脱敏底图用于元数据合并测试，真实上板须使用对应目标底图。''')
add_after('报告包的 evidence/history 保留历史证据，evidence/live_board_samples.json 保留本次过滤采样，live_summary.json 保存计算值，evidence/ubuntu_rtl 保留本次 RTL 回执。data/live_resources.csv 与 live_rtt.csv 可直接重绘新曲线。完整路径与 SHA256 见 sources/source_manifest.json 及最终 package_manifest.json。',
'''证据编号沿用原资料库，非连续编号不表示正文缺页；仅正文采用的材料进入下表。数值展示按来源精度区分：资源为原生整数或半 BRAM，模型路径为 0.01 ms，业务频率为 0.01 Hz，占用为 0.01%；单调窗口在方法段保留原计算值，图表适度取整。原始 JSON/CSV 保留全部精度，分位数采用 (n-1)p 线性插值。

submit/wait 指原生任务提交与等待区段，bit-exact 指比较范围内的整数逐项相同；WNS/TNS 为建立时序最差余量/总负余量，WHS/THS 为保持时序最差余量/总负余量。READY、IDLE_READY、SPEAKING 等保留各模块原始大写状态名，其模块归属分别说明。''')
add_after('| S03 | sources/release_* 及 evidence/release_* | 方案 A 入口 依赖与已有构建记录 |',
'''| E30 | evidence/source_archive/final_archive_verification.json | 1687文件的最终RAR及解包复跑 |
| E31 | evidence/rebuild_022422d9/hardware_results.json | 新综合实现 资源 时钟 时序与固件 |
| E32 | evidence/rebuild_022422d9/model_build.json | 新YuNet/SFace量化与编译候选 |
| E33 | evidence/rebuild_022422d9/native_build.json | 8个新SO及历史SHA对照 |
| E34 | sources/reproduction 与附录 H | 外置输入 部署参数及来源 |
| E35 | evidence/ai_dialogue_three_rounds.json | 三轮真实DPU审查与纠错记录 |
| E36 | evidence/public_vectors | 无人脸全零向量 期望输出及四组SHA |''')
rep('以下两段为现有可见摘录原文，属于工作范围调整记录，不代表 FPGA 或 DPU 案例的完整逐轮对话。[E16]',
'''除原工作范围调整摘录外，本版从已有会话回收了 DPU 调度审查的三轮完整可见往返，按时间顺序保存于 evidence/ai_dialogue_three_rounds.json。原用户提示与可见回答保留原文，选定的工具核验输出单独登记，不含内部推理；下列为阅读摘录，完整提示、回答和轮次 ID 见附件。[E35]

第一轮用户原话：那已经自动恢复意味着这个是不是正常现象，属于工程误差

第一轮 AI 回答原文摘录：可以按“工程上可能接受的偶发时延抖动”评估。自动恢复说明容错有效；是否正常，要看它有没有影响业务。

第二轮人工提供独立审查与新故障材料后，AI 对照源码核验，并将早期判断收窄。AI 原文摘录：更重要的是，新回传证据出现了第三次82.93ms超限，并越过guard。这次没有自动恢复，YuNet已锁定在CPU保护模式。因此，我之前“可能是可接受的小抖动”的评价只适用于前两次，不能覆盖当前故障。

第二轮工具回执记录 5 份源码 SHA、3 条故障时间线和 4 类本地反例检查，production_changes 为 0。该轮纠正了返回侧采样顺序、输出数组分配区间及 deadline 与周期休眠的关系，保留了不确定的长尾根因。

第三轮用户给出修订版后，AI 原文摘录：修订版的事实分析基本可用，但补丁示例仍不能直接上板。其核验指出 release_mono 仍早于实际释放，线程退出后的 finally 标志也可能误报存活；本地核验输出为 local_checks_passed=true、python_AST_passed=true、production_changes=0。

这组三轮记录体现原判断、新证据、修订和再次核验的过程，结论是拒绝未被验证的补丁直接进入运行系统。其余 FPGA、模型迁移和语音案例仍按工程复盘与原问答的实际覆盖范围分别标注。

以下两段为早期工作范围调整记录。[E16]''')
add_after('[R6] 全国大学生嵌入式芯片与系统设计竞赛 2026 FPGA 赛道选题指南 AMD 第 3.3.5.3 节 设计报告七项要求 本地参考原件 SHA256 c6ad82acd4f7bdcd13bd412e232ed85d05f2a87dd5e2cdd04f9d219f88b569fc',
'''发布仓库地址 https://gitee.com/Vickyiii/fpgachina26-amd/blob/master/tracks/open-topic/GUIDE.md  本次在线读取未成功，条款以已保存同版原件核对。

[R7] AMD Vitis AI 3.0 Model Development and Quantization  https://xilinx.github.io/Vitis-AI/3.0/html/docs/workflow-model-development.html

[R8] AMD DPUCZDX8G for Zynq UltraScale Plus MPSoCs Product Guide PG338 4.1  https://docs.amd.com/r/en-US/pg338-dpu

[R9] AMD Kria KV260 Vision AI Starter Kit User Guide UG1089  https://docs.amd.com/r/en-US/ug1089-kv260-starter-kit

[R10] k2 fsa OmniVoice 项目与源码  https://github.com/k2-fsa/OmniVoice

[R11] Device Tree Compiler 1.7.2 源归档  https://www.kernel.org/pub/software/utils/dtc/dtc-1.7.2.tar.xz''')
rep('项目形成了多模型部署、PS 与 PL 执行监督、语音交付及离线 PYNQ Skill 的可追溯实现。报告分别说明历史对照、当前运行观察、软件模拟与 RTL 仿真的条件，不将其合并为完整物理闭环验收。机械标定、声学端到端延迟和统一版本的全功能持续运行仍需独立测量。',
'''KV260 上的单 DPU 组织 YOLOX-Nano、YuNet 和 SFace，与主机 27B 语言模型、板端音频和受监督执行形成协同结构。主检测约 9.89 Hz 来自已注明版本的 1 分钟窗口；语音交付有两轮历史完整回执，最新源码包具备独立构建与解包复验记录。整机同版长稳、机械响应和声学首声另行测量。''')

# Copy immutable current package evidence under a version-qualified namespace.
dest=R/'evidence/rebuild_022422d9';dest.mkdir(exist_ok=True)
for n in ['hardware_results.json','implementation_receipt.json','model_build.json','native_build.json','firmware_fresh.json','software_skill_deploy.json']:
 shutil.copy2(F/'report/evidence'/n,dest/n)
shutil.copy2(S/'最终工程包/archive_verification.json',R/'evidence/source_archive/final_archive_verification.json')
shutil.copy2(S/'timing_review_result.json',dest/'timing_review_result.json')
shutil.copy2(F/'report/validation_summary.md',dest/'validation_summary.md')
hist=R/'data/history_latency_summary.csv'
hist.write_text('model,n,arm_fp32_median_ms,dpu_int8_median_ms,arm_fp32_p95_ms,dpu_int8_p95_ms\nYuNet,40,124.02,61.41,147.60,64.75\nSFace,8,520.86,13.56,,\n',encoding='utf-8')
hw=json.loads((dest/'hardware_results.json').read_text(encoding='utf-8'))
drc=hw['drc_report_groups']
g='''

## 附录 G 最新源码重建的原生报告摘录

本附录对应 RAR SHA 022422d9d1efa6106c2b247ac901dddd2f439a1a5e8eb19a22539010c3a944f4。原生报告由该源构建产生，摘要及报告 SHA 取自 hardware_results.json；报告采样时的现役板端和本次新构建尚未声明同版。以下字段沿用工具命名，便于与原件核对。

表 G-1 原生时序与路由关键行

| 原生字段 | 数值 | 范围与判定 |
| --- | --- | --- |
| WNS TNS | 0.002 / 0.000 ns | Setup failing endpoints 0 / 392134 |
| WHS THS | 0.010 / 0.000 ns | Hold failing endpoints 0 / 392085 |
| WPWS TPWS | 0.071 / 0.000 ns | Pulse failing endpoints 0 / 137578 |
| Routable nets Fully routed nets | 199333 / 199333 | Routing errors 0 |
| DRC Error | 0 | Warning 仍保留 |
| Control DPU clock | 约100 / 300 / 600 MHz | HWH及原生时钟报告分别记录 |

表 G-2 DRC Warning 分类与审阅关注

| 类别 | 新构建数量 | 审阅关注 |
| --- | --- | --- |
| AVAL-318 | 59 | DSP动态级联端约束及目标器件使用条件 |
| DPIP-2 | 14 | DSP输入流水配置与关键路径余量 |
| DPOP-3 | 1 | DSP输出PREG流水配置 |
| DPOP-4 | 1 | DSP乘法MREG流水配置 |
| REQP-1731 | 512 | DSP操作模式及A端符号位限制 |
| RTSTAT-10 | 1 | 无可布线路径负载的网络 |

以上分组为原工具报告保留项，构建未将其改成 Error；本报告不将 Error 为 0 扩展为无告警。外部 I/O 的 no_input_delay、no_output_delay 与已约束内部路径分开审阅，新增外设或修改采样关系时须补齐相应约束。

表 G-3 原生报告指纹

| 报告 | SHA256 |
| --- | --- |
'''
for n,h in hw['report_hashes'].items():g+='| '+n+' | '+h+' |\n'
g+='''
新 BIT SHA 为 bfb57aea58fd0918d176cf2938465c5a79bb006aa38ead371fb2b36759582509，新 XSA SHA 为 26cf31e83102e5226844bb8512731f51b088a8bf21d4a21ad15c1e8d30e7ab04。firmware_fresh.json 记录两者配置载荷逐字节一致及 board_verified=false。物理优化的后续尝试没有形成另一份完成且合格的新结果，封版仍采用上述基线。

## 附录 H 外置输入 来源与提交对应

表 H-1 外置输入与取得依据

| 输入 | 当前提供内容 | 复现者取得方式与状态 |
| --- | --- | --- |
| Vivado Vitis 2022.2 | 版本锁 Tcl与脚本 | 按AMD授权安装匹配器件工具 |
| DTC 1.7.2 | 源URL SHA及构建记录 | kernel.org固定归档 按env锁校验 |
| 目标base DTB及rootfs | 目标SHA与镜像分区说明 | 从匹配目标系统的授权归档取得 |
| ASR前端声纹及ARM轮子 | 15件逐文件SHA 合计211612620字节 | 独立授权音频ZIP 源RAR未含权重 |
| 27B与OmniVoice权重 | 仓库revision与文件锁 | 放在工程共享目录之外 按授权取得 |
| 正式角色与纹理 | 当前固定RAR的输入说明及指纹 | 该SHA版本仍需原件 正在追加的新包另验 |
| 公开测试向量 | 无人脸YuNet全零输入与四路期望输出 | 报告附加证据包public_vectors目录 |

表 H-2 文档与源码的证据位置

| 内容 | PDF内位置 | 源码或附件位置 |
| --- | --- | --- |
| 资源时序与告警关键值 | 第5章 附录G | 源RAR report/evidence/hardware_results.json |
| 任务与参考对照 | 表5-5及表5-6 | 历史及报告采样原件在报告证据包 |
| 模型与原生库版本 | 第4章 第8章 | 源RAR report/evidence/model_build.json native_build.json |
| AI三轮原文 | 附录D阅读摘录 | 报告附加 evidence/ai_dialogue_three_rounds.json |
| 公共合成向量 | 第8章 附录C E36 | 报告附加 evidence/public_vectors |

当前固定 RAR 的关键构建摘要已直接纳入 PDF，便于只持有报告时审阅。报告专用 CSV、截图和本次新增原问答、合成向量原件随附加证据包提供；它们尚未宣称已写入 SHA 022422d9… 的历史封包。最终提交若合并到下一份源码 RAR，应重新生成文件清单和整包 SHA，并使报告附录同步引用该版本。

来源说明沿用工程包 third_party_notices.md 与各组件原许可：YuNet、SFace、ByteTrack、Droid 字体、角色运行时及其依赖分别保留原件。比赛 logo 来自用户提供 PSD，正式角色来自队伍现有素材；本次材料尚未给出二者对外分发的书面授权依据。报告使用宋体排版，字体文件未随证据包分发。整包公开仓库 URL、tag、commit 和统一公开许可尚未提供，未以归档 SHA 冒充 Git commit。

整板与舵机功耗、当前5090显存预算下的长稳、同版全流程成功率、声学首声及冷启动时间尚缺专门测量。已有 CPU/内存短窗、历史 GPU 资源案例和两轮软件播放记录各自保留范围，不填入缺失的物理指标。
'''
t+=g
assert '/home/ghmd/' not in t
P.write_text(t,encoding='utf-8')
# Update the portable builder version and cover date.
p=R/'tools/build_word.py';s=p.read_text(encoding='utf-8').replace("cp('技术报告 V5'","cp('技术报告 V6'").replace("cp('2026年11月3日 北京时间'","cp('"+today+" 北京时间'")
p.write_text(s,encoding='utf-8')
notes='''# V6 与最新固定工程包对照修订

本版以已交付 RAR SHA022422d9…为固定基线，1687文件、1686文件校验。按本次自查补充新源码综合实现、资源与时序、两个新xmodel、8个新SO和固件配对的范围。旧板端成绩保留原指纹，新构建未被写成已经板测。新增完整可见AI三轮原文与无真人像素的YuNet全零输入及期望输出。正文继续宋体和北京时间，页眉logo与马赛克截图保留。

报告专用新增证据尚未声称已合入上述固定RAR；下一次工程封包须更新清单、整包SHA及文档引用。角色素材另一个在制封包的最终状态未纳入本固定基线。

'''
p=R/'readme.md';p.write_text(notes+p.read_text(encoding='utf-8'),encoding='utf-8')
(R/'qa/v6_editorial_scope.json').write_text(json.dumps({'revision':'V6','archive_sha256':'022422d9d1efa6106c2b247ac901dddd2f439a1a5e8eb19a22539010c3a944f4','archive_files':1687,'old_results_version_preserved':True,'new_board_tests':False,'font':'宋体','timezone':'Asia/Shanghai','new_luts':66887,'new_ff':123100,'new_clb_sites':14440,'new_clb_percent':98.63,'new_wns_ns':0.002,'new_whs_ns':0.01,'ai_visible_rounds':3,'public_vector_pixels':'synthetic all-zero only'},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'markdown_chars':len(t),'figure_markers':t.count('!['),'tables':len(re.findall(r'^表 [0-9A-H]-',t,re.M)),'revision_date_beijing':today},ensure_ascii=False))
