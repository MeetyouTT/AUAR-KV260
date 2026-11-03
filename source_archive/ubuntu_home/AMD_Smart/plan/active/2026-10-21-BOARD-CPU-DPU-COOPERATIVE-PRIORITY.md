# 板端CPU/DPU协同的新实施优先级

<!-- hdmi-training-native-observation-20261024 -->
**范围补全更新：** 用户要求同时交代论文、DPU/全模型统一调度和Skill。[核查及实施顺序](/home/ghmd/Win共享文件/协作任务/2026-10-18_双机联调/2026-10-24_论文_统一调度_Skill_状态与实施顺序.md)明确：三模型PS原生共享调度已有，跨机资源编排/PL通用仲裁/源绝对期限与G0—G5真实实验未完成，三Skill尚为说明框架。后续补统一任务/测量合同、可运行时效评测Skill、真实软件编排与公平论文对照，再做PL联合验收；转轴继续离线构建、现场验证单列，不把运行故障清单当全部剩余工作。HDMI按用户暂停，YuNet按自动恢复阶段标准，旧证据保持。
**最新单终端：花屏现场已测一次软件候选，待用户实屏结论。** [源码与实际证据](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-24_hdmi_link_training/README.md)。真实冷启c5f247b9…/1309/1310/X1077业务自动恢复、旧checkpoint精确归档；用户确认仍花屏后，单次train/VBLANK/卸载及业务存活通过，无新超限，实屏结果仍PENDING，未接启动或重复触发。下一步先收用户反馈：若恢复再安排多轮冷启；若未恢复则留证后物理重插对照，不以驱动返回当显示成功。两小时完整7200.054秒YOLO9.9527/YuNet27116完成/0新fault/gap，SF新0且有干预，非三模型满载/严格收益。诊断已清理，旧4fault4rec及交接空档保留、长尾未根治；pan FAULT、严格收益及实际回退仍待。
<!-- /hdmi-training-native-observation-20261024 -->

<!-- native-acceptance-coldboot-20261024 -->
**最新验收顺序更新：** [现场与真实冷启证据](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-24_native_acceptance/README.md)。本人正脸/单一陌生人/双脸拒绑定已通过；真实断电业务自动恢复，但实体显示需HDMI拔插，整机冷启仍不通过。上一原生期YuNet4超限4恢复、SF0已归档，需补fault逐事件留证/归因，不能继续称根治。当前boot b7871498…、1294/1295/X1076，用户正在换屏幕USB供电对照、板端暂停。接续先完成不牺牲触摸的显示供电/握手单变量检查，再原生尾延迟证据与严格CPU/DPU收益；旧记录的0超限/未验身份/未物理冷启均是对应历史时点。
<!-- /native-acceptance-coldboot-20261024 -->

<!-- native-critical-live-20261024 -->
**原生三模型主线已进入实际运行：** [r4源码/实流/失败与回退](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-24_native_critical_live/README.md)。boot a69299ef…、camera2174/GUI2206；同输入真实模型对照过，180.841秒YOLO9.9369/SFace新46，0新primary/optional超限gap。旧5/3fault和4/2恢复归档，primary累计2保留；所有模型仍原INT8域/阈值/库/30ms5ms。接续优先真人身份/多人准确率、正常业务积累长尾、严格同输入CPU/DPU收益及实体冷启/实回退；不再机械重复候选编译或无脸长测。资源63–64%CPU/5%DPU是点测，不能当创新收益或资源率提升。单终端保持，旧“未启用/只有YOLO”是历史。
<!-- /native-critical-live-20261024 -->

<!-- native-critical-single-r2-20261024 -->
**最新单终端接续已形成r2候选：** [代码/预备配置/验证](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-24_native_critical_candidate/README.md)。222源/5 C++、62业务迁移/237旧回归（2跳过）/12真CDLL-fake及原生20/8/5＋SAN过；目标链接/常量ABI与当前boot拒legacy验证过。只有YOLO当前DPU，YuNet5fault4rec CPU、SFace3fault2rec停用，原计数/PID/库保持。首次新kernel迁移/归档与boot唯一marker已补，未实际重启/启模型。后续须在明确维护窗口做真实INT8等价→三模型业务/资源短测→稳定后延长/精度/冷启；同boot不可用清计数解锁替代修复，当前候选未生产启用。
<!-- /native-critical-single-r2-20261024 -->

<!-- native-critical-progress-20261024 -->
**UTC2026-10-24新主线：一次原生调用内释放DPU执行权。** [实施状态](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-24_native_critical_candidate/README.md)。现役又第5次约36.5ms/guard越界，YuNet LATCHED退CPU，YOLO/SFace仍DPU，同PID/5fault4recovery/gap0保留；不重启解锁。桥接/缓冲/生命周期和源TTL候选已编译/软件验证，独立恢复policy13组/3840步对照过；用户允许四路，正在整合NativeLease v2/完整seed、SFace释放后TTL ACK与三模型业务。214当前源SHA闭包已齐，旧handoff不能直接承接mixed历史须补，不造零预算。顺序：同版实现/故障注入→维护窗口同输入真INT8输出等价→1–3分钟三模型业务与资源对照→稳定后延长、真人精度/冷启。候选未部署，原30ms/5ms/身份域和计数保留；不把pure fake/对象编译当DPU修复完成。
<!-- /native-critical-progress-20261024 -->

<!-- persistent-vision-recovery-final-20261023 -->
**2026-10-23恢复/准入持久版已启用：** [源码/实测/回退](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_vision_recovery_and_admission/README.md)。camera29563/GUI29588；SFace受限恢复/前两探测不发布、30ms预算＋5ms guard准入、worker前保护交接和新boot独立窗口已完成。4源/237软件0失败2跳过/68板隔离，60秒YOLO9.966/face3.897Hz通过；原unit/GUI/库/模型/阈值保持。真实两次YuNet硬超限均已自动恢复，CPU runnable排队与GIL重获睡眠会叠加，尚未完全根治。Nice未获稳定收益已回默认，所有探针/统计已清理。下一顺序：真人SFace恢复门复验→实际冷启→陌生人/多人精度和持续真实交互→匹配负载的CPU/调度收益；保持30ms/5ms/TTL，资源点测和SFace ready不代替满负载验收。
<!-- /persistent-vision-recovery-final-20261023 -->

<!-- native-wait-diagnosis-20261023 -->
**2026-10-23等待诊断接续与优先级更新：** [精确代码/证据/当前状态](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_native_wait_diagnosis/README.md)。实际VART已核实释放/重获GIL，不能再盲包一层release；外部30ms故障包围Q差0仍未区分GIL与原生。原生/外部schedstat成本门槛均未过已停；四点UProbe无DPU隔离500轮/2000事件、额外CPU20.27µs/清理过。60秒业务采样被SFace ready=false预检拒绝，生产probe未创建。同版本一次恢复后camera588727/GUI588755又YuNet21.04ms guard退CPU、SFace39.89ms硬超限停用，YOLO9.92Hz、gap0、USB新增0，旧故障保留、未再重启消计数。**下一先实现SFace独立受限恢复及probe许可/业务ready隔离，保留YuNet LATCHED；再native/GIL阶段短采样、单独准入余量。** 30ms/5ms/TTL、原库/阈值/GUI修复不变；当前无恢复新补丁或根因修复，冷启/精度/同输入收益未闭环。
<!-- /native-wait-diagnosis-20261023 -->

**2026-10-23 GUI按可见性处理已上线：** [实现/实测/回退](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_preview_visibility_live/README.md)。隐藏预览原仍12.5Hz处理，2源修复后main GUI组149.88→94.88%单核（降36.70%）；可见12.73/重映射12.68Hz、角色8Hz保持。15生命周期＋16协议＋5真实GTK及实流通过，175源仅2变，camera499773未重启、GUI535987；旧fault2/gap1保留未增，失败与实际回退有证。当前YuNet因37.069ms且guard越界仍CPU保护，YOLO/SFace DPU后端；本次不证明长尾根治、整板/模型加速或三模型持续满载。下一优先YuNet等待归因与guard问题，随后SFace恢复/独立多人精度/冷启长稳，不通过反复reset或放宽保护演示成功。

**2026-10-23 GUI CPU本轮结论：** [exact候选与同输入/恢复证据](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_gui_cpu_evaluation/README.md)。画质零差但待机进程CPU仅降5.46%，未过10%预声明门槛，正式GUI未改；下一项定位真实GUI进程/线程成本，不能重复把已完成分频/NEON当新收益。旧camera450495的3次YuNet超限/2恢复/LATCHED留证后，仅一次同版本重启恢复camera499773；GUI450525、unit29786434…保持。60.214秒9.964/3.737Hz、0新超限gap；SFace就绪但0新请求，非三模型满载。10秒整板CPU63.25%、GUI组38.40%、相机21.94%，非配对收益。保护/根因仍未闭环，继续低开销等待归因；本轮未部署CPU候选或放宽保护。

**2026-10-23最新正式部署：** [可靠性修复](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_vision_reliability_live/README.md)已接受，unit29786434…、camera450495/GUI450525，三视觉DPU后端就绪；9源210软件/26发布/71板隔离及60.519秒短实流通过。YOLO9.931/YuNet3.817Hz/231native、CPU56.92%，新增超限/gap/USB/诊断错误0；SFace启动5次、窗口新增0，未称精度或满负载验收。原模型/阈值/库、30ms/5ms和周期锚点保持，源/回退核验通过。旧版SFace36.743ms停用/ready误报及YuNet82ms故障均留档；状态/资源清理已修，长尾根因、SFace自动恢复、GUI CPU热点及同输入收益继续做。下方“分工后候选未部署/旧unit”为历史。

**用户最新分工：YuNet超限由另一AI审查；Ubuntu先修SFace状态并定位GUI CPU。** 当前unit未换，但YuNet第三次82.927ms/guard越界后LATCHED退CPU，现场已保留，不能沿用下方“2次恢复、三模型都在DPU”的运行状态。SFace状态/缓存与GUI语音消费4源候选92软件/16板隔离通过、尚未正式部署；下一步细分GUI controller.tick内部成本。[候选交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_sface_availability_candidate/README.md)、[第三次故障补充](/home/ghmd/Win共享文件/协作任务/2026-10-18_双机联调/YuNet审查交接_第三次超限与保护锁定_20261023.md)。未同时改YuNet/调度/保护门槛或重启生产。

**2026-10-23有效状态与后续入口：** 已恢复供电且YOLO/YuNet/SFace三模型正式DPU，SFace独立INT8库迁移与本人一分钟短验已完成；本页下方“断电暂停/正式SFace Windows/1ms未常驻”为各历史记录时点，不是当前部署。UTC08:14最新只读确认同版三服务正常，但YuNet又2次超过30ms、2次有界恢复，SFace未超限、gap0；转轴当前FAULT。当前工作顺序为SFace停用状态/恢复闭环→GUI CPU热点与API内外长尾对照→独立陌生人/多人和同输入收益→冻结整机验收。详情与未完成项见[当前问题审计](/home/ghmd/Win共享文件/协作任务/2026-10-18_双机联调/项目未闭环问题与下一步_20261023.md)，正式源码/回退见[三模型交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_sface_formal_dpu/README.md)。没有放宽30ms/5ms或以空推理增加占用。

## 历史进展与优先级调整记录

2026-10-22最新暂停：用户报告实验室断电，全部任务停止等待来电。核分配120秒通过但600秒约5分钟31.047ms失败，已恢复原双模型/Windows身份；默认关闭时效统计23项本机通过，板合成开销未做。恢复顺序为新boot/版本/服务/USB与原保护核验→时效观测合成开销→真实短诊断→有界退让→三模型与正式身份，详见[断电断点](/home/ghmd/Win共享文件/协作任务/2026-10-18_双机联调/断电暂停_20261022_CPU_DPU进度.md)。下方进行中/旧PID均为历史。

2026-10-22接续：用户允许三个终端；主任务独占实板做CPU核分配独立120秒，两个本地任务审查回退/时效。修正版r2的28项软件及独立版本核对通过、未证明板端收益；原5ms GIL/30ms/5ms保持，四角色推理[2,3]/准备[0,1]为实验策略，非独占核。原425227预检又31.971ms回CPU属候选启用前故障，保存后按原单元重启437343恢复DPU；当前实验进行中，结束补成功/失败和恢复。见[修正版候选](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_cpu_affinity_candidate_r2/README.md)、[日志](../../logs/daily/2026-10-22-CPU-AFFINITY-TRIAL.md)。

2026-10-22最新：1ms解释器间隔双模型120秒和600秒吞吐/占用保护已通过，长测603.23秒/1218累计成功，YOLO9.8868/YuNet2.0158Hz、最大27.2545ms、0真超限/新USB；CPU69.10%非收益对照。121个健康快照有3个人脸结果TTL过期，不能宣称业务时效全部通过或根因已修复。已恢复原相机425227/UI215734/Xserver1077，原源/配置/旧库/30ms/5ms保持，影子/埋点/统计timer关闭，1ms没有常驻。下一优先审查默认关闭CPU核分配候选并单独120秒实测，增加时效和CPU评估，不同时改GIL；然后重复5ms/1ms或回三模型10/30分钟及正式INT8身份。用户最新允许两个终端，第二任务只本地实现/测试，主任务独占板卡。见[本轮交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_gil_interval_trial/README.md)与[日志](../../logs/daily/2026-10-22-GIL-INTERVAL-TRIAL.md)。下方未实施GIL/旧PID/单终端为历史。

2026-10-22等待观测更新：轻量上下文计数67＋66软件/21板端合成与0.264ms平均额外开销通过；全排队模式开销未过。关闭SFace DPU影子的120秒诊断未满，最后健康65秒后YuNet31.153ms触发保护，自愿/非自愿各+1、execute29.959ms/线程CPU1.107ms、观测读取墙钟0.520ms亦计入，不能认定唯一根因。自动恢复400028/215734/1077、原双模型DPU/Windows旧库/影子与统计timer关闭、无新USB。下一优先改为两个独立、可回退的120秒调度实验：进程GIL切换间隔与推理/准备核分配（均待实现），不同时改、不放宽30ms/5ms，之后再三模型长稳/正式身份。见[交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_thread_wait_diagnostics/README.md)、[任务](/home/ghmd/Win共享文件/协作任务/2026-10-18_双机联调/下一步_执行等待单变量对照_20261022.md)。

2026-10-22重试实板更新：B60.73秒完成59次/0.972Hz、YOLO9.814/YuNet2.223Hz，阶段目标通过；原A人脸覆盖10/13，严格A/B无效。用户授权10分钟后约45秒YuNet33ms触发原30ms保护、自动恢复，长稳未过。execute墙钟32.65ms/调用线程CPU0.984ms、wait0.079ms、无新USB，根因尚不能区分native/OS/GIL/硬件等待。优先改为有开销核查的调用线程排队观测（尚未实施），随后再重跑10/30分钟，保持原硬预算及正式INT8现场验证前置。恢复378714/215734/1077、双模型DPU、SFace仍Windows/旧库、影子/producer/埋点/相关timer及XRT关闭，单终端保持。见[代码、短测与失败/恢复](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_sface_retry_board/README.md)及[日志](../../logs/daily/2026-10-22-SFACE-RETRY-BOARD.md)。

2026-10-22后续实测更新：音频原子owner/IPC候选33项本机及本板fakesink隔离检查通过，尚未生产GTK/MCP01验收。13源合并真人60.69秒接线通过，YOLO9.854/YuNet2.109Hz、SFace仅4次；109裁剪供给与53/57准入拒绝说明下一优先为时隙有效利用，不能以供给数冒充DPU完成数。新三源有界退让重试67＋45回归通过、默认关闭未上板；下一步在30ms/5ms/原YOLO优先不变下做人脸短对照，再长测和正式INT8登记/阈值。已恢复相机316838/UI215734/Xserver1077、原Windows身份和双模型DPU，影子/producer/埋点/统计关闭；音频真正恢复、USB根因、整板同输入收益和Windows接收仍未验收。详见[本轮交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_sface_live_retry/README.md)及[音频交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_audio_maintenance_ipc/README.md)。用户单终端限制继续，未新启agent。

2026-10-22单终端执行更新：音频维护引擎20项/真实Gst fakesink通过，上层barrier/IPC/AEC仍待接线；SFace独立供给与计时/单copy合成13源码，56＋45回归/板端导入与原配置通过，新合并路径未常驻。单copy真实UVC60.18秒观察通过，YOLO9.936Hz/采集12.479Hz/0新增USB告警，已恢复原源与单元，原身份库保持，当前264975/215734/1077。按用户最新只使用主任务串行操作；下一优先为实际owner维护事务接线、隔离合并路径验证及正式现场阈值，30ms/guard不变。不能将引擎虚拟出口、模块导入或短测当长期三模型/整板CPU收益。详见[新交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_single_terminal_integration/README.md)。

2026-10-22接续：新增有界诊断已在120秒双模型路径取得295次成功wait/分段数据，0fault/新USB告警，自动回退；之后600秒被基线新USB告警拒启。恢复顺序改为空闲音频关闭→重启原相机→原音频重建，独立验收当前215707/215734/1077、YOLO＋YuNet DPU/影子关闭；原恢复脚本跨PID计数验收错误留档，未将其写成脚本通过。后续先观察顺序对复发的影响、获得故障时trace，再按测量做同条件CPU单copy对照、SFace供给解耦/有界准入、现场正式身份。CPU候选只删一处.copy、8项回归通过未板测；不假定JPEG无用、不缩预算、不将wall时间当CPU用量。详见[接续交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_dpu_audio_diagnosis/README.md)。

2026-10-22执行后更新：T1标定软件候选46回归、T2计时15检查、合并56回归通过；T3长测在最后健康55.03秒后触发SFace保护并回退，MCP01播放告警复发，正常重开原应用后清除、同原配置重启相机恢复YuNet DPU。下一优先级改为有界故障时计时与音频复发/可选任务尾延迟定位，保持30ms保护，再验新测量/标定接线及重跑长测；不能直接放行正式SFace。当前双模型DPU/影子关闭/Windows原身份库保持，源码与数值证据见[第一批交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_cpu_dpu_implementation/README.md)。这次实际失败没有否定较早YuNet30分钟或SFace20秒短测，但证明还不能宣称三模型长期稳定。

2026-10-22最新执行入口：[下一阶段统筹计划](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-22_cpu_dpu_roadmap/README.md)，版本`AURA-CPU-DPU-ROADMAP-20261022-r1`。以YuNet30分钟保留、SFace真人影子通过为起点，第一批并行准备SFace标定/接入、性能测量、Windows接口核对；接续三模型影子持续观察→现场独立INT8身份闭环→定向CPU流水线→同输入调度/容量对照→展示发布。标定工具不依赖Windows在线；新的PL扩展须先取得匹配资源/时序报告。本次为计划，未改生产或解除暂停的全局CPU优化；下文原阶段顺序保留追溯，按上述最新任务表执行。

用户2026-10-21明确：最终成果展示重点为板卡使用、利用率、提升效果与创新，希望尽可能利用DPU和CPU。

当前实施主线调整为板端真实视觉/身份计算与CPU/DPU协同：现有YOLOX→SFace正式DPU身份链→YuNet适配→三模型统一调度/共享帧流水线→在准确率/时效约束下提高有效负载。主方案见[共享实施方案](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_model_inventory/板端CPU_DPU协同与竞赛展示实施方案.md)，基线与实验矩阵放同目录。

与10-12旧全模型PL调度计划的关系：保留旧合同、CPU/PL参考及多端生命周期的研究成果，但近期优先获得板端SFace/YuNet真实业务和可比性能；模型任务PL准入/计时仲裁作为软件调度稳定且资源/时序核实后的扩展，不把软件基线当硬件完成。

展示同时报告板端承担的模型计算、有效吞吐、延迟/帧龄/准确率、CPU核秒、DPU任务忙时和同源FPGA资源；CPU占用降低和承接更多有效业务都可以是收益。忙时、静态资源率和业务提升分别报告，不承诺任意目标利用率或加速比。

现有语音配置暂留Windows；保留转轴保护及此前暂停的CPU优化边界。新修改先回收实际版本、隔离验证、同版集成与实板复核。

后续实施更新（UTC2026-10-22 05:41后）：YuNet与新校准SFace已完成目标编译、固定输入实板验证，三模型固定10/5/2Hz切换0周期超时；SFace独立公开1000对准确率FP32/INT8均98.8%。YuNet实时短测后延长观察出现USB音频告警与日志负载，已恢复原配置；slot04映射MCP01，回退CPU后仍持续，根因未确定。当前正式位置仍为YOLO=DPU、YuNet=ARM、SFace=WindowsCPU，未改身份库/语音/显示/运动。完整模型、源码、回归、失败与回退证据见[实施交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_vision_start/README.md)。下一顺序：USB音频异常与稳定基线→三模型实时长稳与调度尾延迟→SFace版本隔离登记库/现场阈值→有效提频/多目标。

最新实测更新（UTC2026-10-22 07:02后，替代上述当前位置）：原应用正常重建播放流后MCP01本次告警消失，YuNet DPU30分钟实时检查通过并保留；现在YOLO+YuNet=DPU、SFace=WindowsCPU/原库。YOLO9.95/YuNet2.37Hz、整段CPU53.93%、0 USB告警/0 YuNet真正超限，有1次YOLO周期超时，不能称全链零超时。SFace版本隔离候选21项回归/最新板上纯配置检查通过，另有影子计算候选，均未切生产身份。接续优先为保持原FP32判定的SFace影子三模型实板验证，再独立INT8登记/阈值和有效提频；本次恢复不代表USB根因已修复。详见[实时交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_dpu_live_baseline/README.md)。

接续实测（UTC2026-10-22 07:25后）：用户确认有人后，SFace真人三模型影子20秒检查通过：10次完成/通过目标时效复核、平均14.48ms，YOLO10.04/YuNet2.15Hz，0计算失败/USB告警，身份决策与模板写入均0。已按预案恢复YOLO＋YuNet基线，影子关闭、原库/Windows身份配置保持；目前没有SFace正式身份/阈值或三模型长期验收。最终21项直接候选、16项影子回归和3项部署准备检查见交付。接续优先改为独立INT8登记及同人/异人/多人歧义现场验收，再延长三模型观察、同输入调度对照和有效提频；不能把影子调用当作识别准确率或DPU忙时提升。Windows8792可达性及同步回执仍未确认。
