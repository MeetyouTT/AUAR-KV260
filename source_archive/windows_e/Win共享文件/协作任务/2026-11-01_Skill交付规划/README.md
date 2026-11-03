# AURA 比赛 Skill 交付规划

> 当前模式：用户最新要求先整理文档，暂停实现与测试。请先读[三个Skill完整内容文档](skill_complete_documentation.md)，包含[A](skill_a_content.md)、[B含声纹](skill_b_content.md)、[C近期LLM/语音优化](skill_c_content.md)及[桌面5090迁移状态](migration_5090_status.md)。以下先前规划保留追溯；已有技术草稿不是正式交付，未验收项保持待验。

> C方向已按用户要求更新：[Windows语音/LLM优化成果审查与新C范围](c_llm_voice_review.md)。C改为llm-voice-runtime-optimization（本地大模型语音交互优化与记忆一致性验证），原异步验证作为子模块；73份新增来源另存清单。只更新规划，没有独立包完成或性能重测声明；DPU声纹暂缓定稿保持。

> 待执行任务入口：[A/B/C三包一天初版清单](one_day_tasks.md)，列负责人、产物、完成标准和后续实板/声纹/整机任务。全部初始TODO，仅安排限定范围离线初版，未启动实施或解除DPU声纹暂缓定稿。

> 创新性比较建议：[保留三人三包结构，以DPU多模型协同为B主线](innovation_comparison.md)，把现有验证工作流融入A/B/C，版本检查作为公共工具或附录。本条为建议，不冻结组合；声纹和DPU封装继续待定。

> 最新需求补充：用户要求DPU包加入声纹识别，并暂缓定稿。[声纹范围记录](dpu_speaker_scope.md)说明现有ECAPA CPU/ARM ONNX基础、DPU待适配事项与边界。下文四包是11月1日本轮建议，不是最早原计划的包数；DPU范围和最终组合尚未冻结，未执行封装或移植。

## 原规划与本次建议的区别

[20天三人计划V2第13节](../../方案/amd_kv260_20day_3person_execution_plan_v2.md)（文件标注2026-09-15）原先建议三个主题：A的kv260_motion_ip_bringup（运动IP调通/仿真/板端验证）、B的kv260_vision_model_validation（同源CPU/DPU、预后处理、模型哈希/坏样例及身份结果归属）、C的avatar_voice_integration（音频、对话状态、取消与UI/播放同步）。DPU相关工作已经包含在原B主题。

[2026-10-07技能包方案](../../方案/aura_skill_package_plan_and_delivery_20261007.md)把这三个来源主题收敛为command-guard-validation、perception-freshness-benchmark、async-result-validation，并把kv260-artifact-check及avatar-playback-validation列为条件性参考案例。10月9日框架和10月24日接续沿用这三个验证包。

本页11月1日建议新增release-evidence-audit作为辅助包，是本轮新增规划；独立DPU移植包及其新增声纹范围也需另外确认。历史主题、后来的工作流收敛和本轮建议须分别引用，不将原B的DPU内容说成此前没有规划。

日期：2026-11-01（America/Los_Angeles）；来源盘点UTC 2026-11-02T01:37:10.834491+00:00。
状态：PLANNED。本文完成交付规划，不表示已经实现、封装或验收四个独立技能包。

## 建议交付组合

建议规划4个正式包：保留现有3个专业包，增加1个工程版本与证据检查包。前三个体现执行监督、感知时效和异步交互经验，第四个解决交付版本不一致的实际问题。

官方第3.3.5.2关注陌生使用者能否复用，以及适用范围、用法、失效条件、验证效果、失败/观察来源。没有规定必须交4个、每包多少测试或必须采用Codex插件形式。以下数量、阶段和独立执行要求是本项目建议。

| Skill | 解决的问题 | 已有基础 | 交付前要补的内容 |
| --- | --- | --- | --- |
| command-guard-validation | 验证数字输出命令的范围、序号、租约、停止和恢复是否符合合同 | wide RTL、4套仿真入口、控制器/假MMIO测试、有限板测历史 | 冻结当前ABI、独立参考/RTL入口、可替换配置、真实失败与分层证据 |
| perception-freshness-benchmark | 判断感知结果到使用时是否仍有效，量化共享推理的等待与覆盖 | 三模型Native调度、窗口统计、来源/期限设计和真实日志 | 标准事件合同、真实日志适配、独立分析器、黄金样例与未知值处理 |
| llm-voice-runtime-optimization | 优化固定LLM/TTS下的有效回复等待、资源共存与记忆/播放一致性 | Windows分流/输出/历史/显存/音频优化及后续板端业务接管，已有分版本实验 | 计时分析、路由/输出、公开SQLite记忆、异步交付四模块；冻结源与独立运行/真实模型验收 |
| release-evidence-audit | 检查源码、固件、模型配置及证据引用是否属于同一发布版本 | 本轮380组件定位、SHA/长度检查、过期LATEST案例、位流配对工具 | 独立只读检查器、统一清单、可移植路径和正反例报告 |

历史三个技能目录的interface.json仍为evidence_status=PLAN，每包为README+接口框架；旧async-result-validation目录保留追溯。新C本轮完成范围调整和来源审查，尚无独立实现/复用验收。既有业务测试和优化结果按对应版本引用，不计为新包已通过的次数。

## 1. 命令监督验证：command-guard-validation

主责A，B复核来源与时效；建议作为硬件主打Skill。

- 适用任务：上位软件提交命令，FPGA或数字外设负责允许、拒绝、租约到期、STOP与复位的系统。首版固定当前wide ABI，随后用第二份模拟合同展示参数适配。
- 输入：ABI/版本、字段和单位、范围/速率、会话/序号、租约、STOP/复位语义；公开事件向量。寄存器偏移、位宽和时钟从实际合同取得，不使用旧README猜测。
- 输出：逐例预期/实际、拒绝原因、状态转换、参考与RTL差异、波形索引、工具/源码SHA及覆盖层级。
- 首版交付：参数化合同示例、纯软件参考验证器、RTL运行包装、4套既有testbench适配、公开正常/反例、历史失败与修正说明。工具链路径由配置提供。
- 计划用例：合法更新、越界、重复/乱序序号、会话切换、租约到期、STOP、复位、半写提交，以及合同要求的脉冲结束边界。具体断言在冻结当前ABI后确定。
- 来源：/home/ghmd/aura-pan-wide-20261028/candidate/rtl/visual_servo.sv、candidate/tests/、run_rtl_tests.py、controller/、OFFLINE_COMPLETION.json。通用源树board/motion/guard.py为SimulationGuard，可作历史参考，不能直接代表当前硬件。
- 提炼工作：去掉run_rtl_tests.py中的本机Vivado绝对路径；把软件参考、RTL仿真、板端寄存器、外部PWM波形和机械现象分开输出。
- 完成条件：新目录可跑软件样例；配置工具后能重复RTL向量并获得预期报告；第二合同的模拟验证有记录；实际板测仅引用版本配套、来源完整的案例。
- 验证边界：当前PL能力按实际相对租约与监督合同说明，不宣称PL绝对源截止期、全模型硬件仲裁、机械零点或真实±90°已经完成。此次规划不启动MMIO、ARM或运动。

## 2. 感知时效与调度评测：perception-freshness-benchmark

主责B，A复核时钟与统计口径；建议作为方法与评测主打Skill。

- 适用任务：摄像头/传感器任务共享不可抢占资源，结果存在有效期的检测、识别和控制系统。首版是离线分析器，业务调度器本身作为可选适配示例。
- 输入：JSONL/CSV事件、字段映射与时间单位、boot/生产者、frame/task/model/request标识、采集/排队/开始/结束/消费时刻及有效期。缺失的字段明确登记，不能默认为0。
- 输出：排队和执行耗时、P50/P95/P99、结果/消费时帧龄、有效完成率、拒绝/丢弃原因、身份等待与覆盖；CPU和DPU忙时仅在数据支持时报告。
- 首版交付：事件合同、两种字段适配、日志校验/关联、指标分析器、人工可算的小样、预期JSON/CSV报告和真实脱敏窗口示例。
- 计划用例：ns/ms/s转换、跨boot拼接、跨机器时间差误用、缺采集时刻、重复/倒序、旧代次、过期、零完成、任务被关闭、缺少消费端事件。
- 来源：原生调度历史source/native-v2-560d824588eb8f8a/.../native_schedule.py、2026-10-24_native_critical_live的固定窗口与验证摘要、既有project_log.py/experiments.json，以及2026-10-31资源观察。当前源树dpu_schedule.py是较早实现，提炼时须按选定版本核对Native与Python字段。
- 提炼工作：区分事件级日志和累计快照。只有快照时输出该窗口可计算的频率/增量，帧龄、P99等事件级指标标UNKNOWN；不从窗口平均值反推尾延迟。
- 完成条件：黄金小样的手算结果吻合；缺字段/错时钟反例被正确识别；至少一个真实窗口保留版本/条件/完整性记录；另一个字段布局由非作者按说明适配成功。
- 验证边界：没有独立真值就不输出位置误差；不同负载的历史窗口不作为公平加速比；G0—G5及其未实现PL部分继续按原计划状态记录。CSV/JSON适配成功也不等于另一套真实硬件已验收。

## 3. 本地大模型语音交互优化：llm-voice-runtime-optimization

主责C，B复核模型/数据与测量条件；用户要求用近期LLM/语音优化成果替换原C主题。完整审查见[c_llm_voice_review.md](c_llm_voice_review.md)，73份来源与指标边界见[c_windows_source_inventory.json](c_windows_source_inventory.json)。

- 目标：在固定27B/OmniVoice等选定版本与质量约束下，优化有效回复等待、资源共存和可追溯记忆，同时保持取消/完整播放的正确归属。
- 输入：公开问题/PCM夹具、模型/后端/提示与配置指纹、阶段事件、缓存和冷暖标记、资源快照、公开SQLite来源/回执及预期结果。
- 输出：可计算的ASR/正文/台词就绪/音频交付/播放指标、资源占用、正确性与记忆检查、优化采用/撤回依据、失败/未知项和来源。
- 模块1：计时、显存和优化决策。区分首PCM/入队/完整ACK/声学首声、冷暖/缓存/无效测量；保留DFlash等未采用案例。
- 模块2：聊天/思考/事实/历史分流、结构化输出与防复述。用公开正常/否定/边界输入测试规则、字段及回退，不将路由通过等同模型答案正确。
- 模块3：有界上下文、会话/权限、事实更正/遗忘、摘要/来源撤销及完整播放后提交。采用公开SQLite夹具，区分存储通过与真实同会话召回。
- 模块4：保留async-result-validation的协议回放、段序/PCM/ACK、取消迟到和背压故障注入。GPU/TTS真实适配属于单列环境验证。
- 实际基础：短字段/正文优先、历史表示、思考路由、r9历史分流/空闲显存、GPU协调、语音IPC、逐句TTS、五分钟记忆和Windows纯推理/板端主控已有不同阶段材料。
- 首版交付：独立离线分析与公开规则/SQLite/协议样例、预期报告、真实失败和采用/撤回案例、环境/源清单；真实模型/GPU与声学复测分层安排。
- 完成条件：新目录按README运行，公开预期匹配，错误样例正确拒绝/报缺，完整数据解释冷暖/缓存；至少一次非作者执行。实际模型和声音只按对应新证据升级状态。
- 验证边界：现有材料支持运行时/交互系统优化，不支持自主训练新LLM或任意对话固定提速。旧Windows权威库是历史，最新业务/记忆归板端，Windows仅推理。当前声纹DPU和ec12整机READY仍未闭环。

## 4. 工程版本与证据检查：release-evidence-audit

主责A/总负责人，B/C提供本模块清单；建议优先形成辅助交付，也用于最终工程收拢。

- 适用任务：FPGA固件、板端/主机程序、模型配置和证据分散，容易将旧源码、旧日志或其他boot混进最终发布物。
- 输入：发布根、文件清单、SHA256/长度、工件关系、模型/工具版本、证据索引；路径映射由用户配置，本地与远程资源明确分开。
- 输出：一致/缺失/失配/未检查清单、源与生成物配对状态、引用闭包、证据归属、冲突副本提示，以及“文件已应用”和“运行已READY”的区别。
- 首版交付：只读检查脚本、清单合同、两个互不依赖的微型示例工程、正反例、预期报告；明确不自动修改源码、修复索引、删除冲突或启动服务。
- 计划用例：全匹配、缺一个源文件、改一个字节、长度不符、LATEST指针过期、外部路径未映射、相同名字不同内容、旧boot回执、只有应用文件但没有READY回执。
- 来源：[全项目复核元数据](../2026-11-01_全项目文件复核/review_evidence.json)、CURRENT_PUBLICATION_STATE.json、applied_spec_pending_ready.json、LATEST_REVIEW.json；位流配对可复用bitstream_pairing.py，verify_transfer.py的绝对基线路径要先参数化。
- 真实提炼案例：380组件对应字节分散、通用语音树268一致/56不同/56缺少；36个引用中34一致/1失配/1远程未检查；LATEST声明1003字节与实际3510字节不符。这些是2026-11-01本次文件审计快照，不是未来运行状态。
- 完成条件：损坏/缺失/过期反例被准确报告，远程未访问显示UNKNOWN；在另一微型工程、新位置及两端路径样例下可重跑；完整报告可放入最终包。
- 验证边界：字节匹配不证明固件行为、服务健康或机械安全；boot/PID只按带采集时间的回执核对，不宣称离线文件反映当前现场。两个微型工程只验证工具复用，不宣称跨板实测。

## 统一包内容与提交形态

建议保持现有3个目录名，新增release-evidence-audit。放入比赛工程的skill/下：

    skill/
      readme.md
      delivery_matrix.csv
      command-guard-validation/
      perception-freshness-benchmark/
      llm-voice-runtime-optimization/
      release-evidence-audit/

每个包按实际需要包含：

    readme.md
    prompts/workflow.md
    scripts/
    adapters/
    config/example.json
    examples/
    tests/
    evidence/
    case_studies.md
    manifest.json

README负责何时使用、前置依赖、步骤/命令、输入输出、预期结果、失败排查和边界。prompts/workflow.md把“读合同—提出用例—执行工具—核对实际结果—修正—复测”整理成可复用模板。case_studies保存真实失败、修改点、复测及来源；真实历史大模型对话另按可取得的原件脱敏引用，不用新模板反向补造对话。

manifest固定来源SHA、依赖/工具版本、适配器、公开样例SHA和证据层级。正常例、故障注入和历史失败分别标注；新的合成反例不冒充历史现场故障。

建议输出机器可读JSON和便于报告引用的CSV/Markdown。判定至少区分PASS、FAIL、UNKNOWN、NOT_APPLICABLE；反例按预期被拒绝属于该用例通过，不能混淆为业务成功。缺依赖、缺时间/来源信息或未访问外部路径要明确显示。

当前规划不创建空实现脚本，也不把上述拟定结构写成已运行命令。真正实现后再冻结入口与依赖锁。

## 验收与分工

以下为建议验收门槛，不是官方硬性数量要求：

| 阶段 | 门槛 | 可宣称范围 |
| --- | --- | --- |
| PLAN | 需求/边界/来源与任务已明确 | 已规划 |
| OFFLINE_READY | 新目录能执行公开正反例，输出与预期吻合，脱离生产GUI/模型/私库 | 独立离线包可用 |
| RTL_VERIFIED | 当前合同与对应RTL向量重跑，有工具版本/波形和结果 | 指定RTL层通过 |
| BOARD_VERIFIED | 由原设备窗口按既有操作权取得同版本板端/外部测量记录 | 仅对应板端条件 |
| REUSE_VERIFIED | 非作者按README完成新目录执行或另一配置/协议/日志适配，保留问题与修正 | 明确写出已验证的复用范围 |

开发安排：A先提炼release-evidence-audit，再完成command-guard-validation的软件与RTL包装；B整理现有视觉DPU/时效材料，声纹范围继续待定；C完成llm-voice-runtime-optimization的限定离线初版，异步协议作为子模块。三人交换包复用，优先验证公开日志、规则、SQLite和合同；真实模型/GPU/音频另验。新C全部能力不直接沿用旧异步小包的一天估算。

实施顺序：

1. 冻结选定源码/合同和公开样例，沿[来源清单](source_inventory.json)逐项确认归属；旧框架字段不得直接覆盖当前ABI。
2. 第一批形成离线版本检查、时效分析和新C的计时/路由/公开记忆/异步回放；同步收集已有真实失败、采用/撤回依据与修正。
3. 补命令监督的软件/RTL入口和工具路径配置；对四包做新目录运行与交换复用。
4. 选择真正需要的板测/消费端验证，按既有设备交接另行安排；MCP01缺失或转轴异常不阻塞离线包装。无法完成的层级保留PENDING。
5. 汇总README、case_studies、输入输出、许可、源与证据SHA，在同一冻结版本上更新delivery_matrix。仅达到相应门槛的包进入最终验收清单。

## 备选包

| 候选 | 可提炼内容 | 本轮安排 |
| --- | --- | --- |
| memory-retention-verification | SQLite公开夹具、正文保留/摘要提交/撤销/权限域/自然到期检查；现有存储测试为基础 | 后续扩展。真实同会话召回尚待验收，首版只能限定为存储机制验证。 |
| dpu-model-porting-validation | YuNet/SFace现有移植经验；新增声纹模型的兼容、量化/编译、输出及共享运行验证 | 用户已补充声纹目标，范围待定、暂缓封装。现有ECAPA为CPU/ARM ONNX候选，DPU执行尚未验证；详见声纹范围记录。 |

现有aura/skills/aura-devices属于产品能力调用约定，可作为系统附录；其中旧唤醒词/观察策略等须与最新业务边界对齐后再用。它不计入本次四个工程复用包的验收数量。

当前没有足够证据将“全模型PL仲裁”“PL源绝对期限”“已解决全部机械异常”“通用PYNQ跨板复用”列为已验证技能。本轮沿现有Linux/VART平台规划，PYNQ通用技能另行论证。

## 本轮实际结果与依据

- 已读官方同版指南、ZIP入口/分工、有效方案与最新项目日志、共享入口、三份Skill框架、实际源码/脚本和验证摘要。
- 初次规划盘点44份来源，全部存在并保存SHA/长度；历史三包接口仍PLAN，见[原来源清单](source_inventory.json)。本次C调整另盘点73份来源，见[C来源清单](c_windows_source_inventory.json)；没有把不同版本业务回归相加为新C成绩。
- 新增本规划和[交付矩阵](delivery_matrix.csv)，更新共享入口与当日日志。未改业务/原Skill源码，无设备、推理、录音、播放、运动或新功能测试。
- 本轮线上仓库首页抓取超时，规则沿用此前已核对提交e47e4a8的本地同版指南。官方来源：[完整指南3.3.5.2](https://gitee.com/Vickyiii/fpgachina26-amd/blob/master/TRACK_GUIDE_2026.md)、[分赛道说明](https://gitee.com/Vickyiii/fpgachina26-amd/blob/master/tracks/open-topic/GUIDE.md)。

