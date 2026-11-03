# 2026-10-11 算法、论文方法与 Skill 状态复核

用户追问此前全项目清单中的算法、论文实现和技能包。此次重点阅读论文方法对照、两份论文核查、10 月 6 日算法规划、10 月 7 日单一创新/技能方案，并核对当前源码、技能目录与新 YOLO 证据。没有连接板卡、执行模型或修改业务代码。

## 算法实现层级

- YOLOX-Nano：出现晚于前次复核的新结果，固定图板端推理 PASS，24次推理中去首样本后中位7.351ms、P95 10.359ms；参考图6个人框，空白图0、镜像图4。实际相机服务已换为 DPU YOLOX-Nano + IoU 基础关联，采集/检测计数增长。约9.4秒短测检测9.98Hz、预览12.66Hz。该窗口 people_count=0，不能据此声称真人检测准确率已验收；不等于 ByteTrack、身份或正式1000帧性能验收完成。
- CPU YuNet + IoU/速度预测：已有历史真实相机与台架基础。SFace/五点对齐/128维特征：已有板端图片参考链；实时身份业务及最终 DPU 身份模型未验收。
- ByteTrack：`board/vision/tracking.py` 已有作者API适配，保留低分检测并更新空帧；当前新增相机链仍是IoU，尚无正式ByteTrack板测。还需核对检测入口是否保留足够低分候选，适配代码存在不保证两阶段关联已被有效使用。
- 可变感知有效期：`board/fusion/freshness.py` 已实现误差增长模型的有效时长求解、上限和同源不延长；参数尚未真实标定，现有通过证据属于软件测试/模拟联调。
- 单CU准入：`board/fusion/scheduler.py` 已实现身份+检测+其他成本+余量与剩余期限比较、单任务排他及耗时记录；真实检测/身份双模型共享DPU与调度收益未验收。
- 运动控制：原工程 `face_servo_control.py` 有滤波状态、死区、比例速度或固定视角映射、范围/速率/单步限制；有历史有限命令板测。One Euro对照及机构正式标定未找到完成证据；不是完整PID调参验收。
- PL监督：既有VSRV相对租约、序号/会话/代次、原子提交和STOP有有限板测；新源绝对期限及PS/PL映射未实现为最终硬件。`board/motion/guard.py` 是软件合同模型。
- 说话人选择：`board/fusion/speaker.py` 已有窗口时间/轨迹代次/阈值/分差检查；Light-ASD实际模型、有界声画管线、长期漂移校准与真实多人上下文策略尚未完成。
- 异步结果/取消：已有会话、代次、期限、媒体段序和格式等软件实现/测试；缓存真实播放控制已板测，真实ASR/VLM/TTS端到端取消仍待接入。

## 论文方法落实状态

最新主创新是“感知有效期—共享推理准入—PL执行监督”，并非要求把所有调研论文各自完整复现。

| 方法/论文方向 | 当前已落实 | 未完成或边界 |
| --- | --- | --- |
| AoI/VoI、控制误差与信息时效 | 项目自己的候选有效期模型已有代码 | 标定、独立误差、真实收益；不是原论文算法完整复现 |
| 计算/通信协同调度 | 单CU预算准入已有软件实现 | 双模型板测、身份等待与基线对照；不是原MDP/MGF策略复现 |
| RTA / Neural Simplex | 独立VSRV监督有工程基础 | 新源期限规则、完整故障/恢复验证；未复现完整Neural Simplex系统 |
| FPGA Stream-Monitoring / RTLola / easy-rte | 资料和开源实现已做历史核查 | 当前是手写RTL，没有规格到RTL生成器复现 |
| ByteTrack | 作者API适配 | 正式板端跟踪及多人精度实验 |
| MobileFaceNets / ArcFace | 候选路线与外部工程核查 | 项目完整模型链及DPU验收；当前SFace不能算MobileFaceNet复现 |
| Light-ASD | 接口和项目输入规划 | 离线/实时模型推理与声画实验 |
| Streaming ASD | 有限上下文/窗口设计思路 | 实际流式管线与延迟实验，不声称严格因果模型复现 |
| LoCoNet | 多人竞争/时间保持的设计思路与基础结果门 | 完整上下文策略实测及网络复现未完成 |
| One Euro | 平滑候选与实施规划 | 与EMA同回放对照、实际参数和效果 |
| MagFace | 可选身份质量对照 | 尚无项目实际复现证据 |
| 资源感知剪枝、SATAY、TAPA、FILM-QNN、NAF、H2PIPE、hls4ml/fpgaConvNet | 已做资料/可用实现核查，供后续优化取舍 | 未形成AURA实现及结果，不是当前全部必做 |

`config/experiments.json` 仍标记 planned_not_board_verified。G0—G5真实同条件对照、消融和结论尚未完成。不能将论文作者成绩、模型下载或方案中的引用写成本项目复现成绩。

## 三个比赛 Skill

实际目录 `/home/ghmd/Win共享文件/共享文件夹/aura/submission/aura_junior/skill` 本轮列出7个文件：总README，三个包各自README和interface.json。各README明确是技能交付框架；没有独立脚本/样例/测试载荷。

| 包 | 可提炼的现成基础 | 剩余交付 |
| --- | --- | --- |
| command-guard-validation | VSRV、软件guard、协议/期限用例和板测日志 | 参数化ABI/时钟、独立执行入口、正常与故障波形、真实修复案例、非作者迁移 |
| perception-freshness-benchmark | 源时间日志、有效期/调度代码、六组配置 | 日志适配与分析脚本、黄金小样/独立真值、真实校准/测试、字段错误用例、另一场景复用 |
| async-result-validation | 会话/取消/段序/PCM测试，已有缓存播放控制 | 抽出最小依赖包、另一协议适配、迟到/重复/换目标注入、真实消费与停声证据、非作者复用 |

此前README“最终MCP01未验收”需细分：缓存MCP01播放控制已有后续板测，真实模型媒体全链仍未验收。不能据此把Skill本身标为完成。比赛技能包不要求先安装成Codex Skill；没有SKILL.md不是判定缺交付的唯一依据，关键是可复用工件和执行证据。

## 本轮验证及更新边界

读取 `20261011T114921.591458Z-probe/result.json` 的 commands 中 probe条目，以及 `20261011T115732.399537Z-deploy/result.json` 中 status/camera-test/profile条目，逐份核对对应.output的长度/SHA，4/4通过，退出码均0。初次尝试从解析后的业务JSON读取传输SHA字段，该字段并不存在；随后改用result.json中实际commands记录完成核验，并非发现证据损坏。

新YOLO结果更新此前进度日志和70项清单中“探针未完成”的读取时状态：R06已有固定图证据、R09已有相机接入证据，但模型重建、正式精度/长测、ByteTrack及统一业务集成仍有剩余项。历史日志保留当时事实，以本补记为新证据入口。

本轮没有重跑118项软件测试、模型或板测，也没有重新查阅外部论文原文；论文状态判断来自项目已有研究记录与本地实际实现，不主张新的文献综述结论。只新增此日志。

来源：[论文对照](/home/ghmd/aura-shared-review-20261008/PAPER_PROJECT_MAPPING.md)、[算法规划](/home/ghmd/Win共享文件/output/视觉与舵机算法详细实施规划_2026-10-06.md)、[技能入口](/home/ghmd/Win共享文件/共享文件夹/aura/submission/aura_junior/skill/README.md)、[固定图结果](/home/ghmd/aura-board-yolo-20261011/evidence/20261011T114921.591458Z-probe/probe.json)、[相机接入结果](/home/ghmd/aura-board-yolo-20261011/evidence/20261011T115732.399537Z-deploy/camera-test.json)。

## 后续追问：论文实现是否可行

用户问“论文的实现可以么”。此次补做作者资料与实际接入边界核对，尚未选定要完整复现的具体论文，没有据此修改运行代码或加载硬件。已询问是项目主线、应用算法还是指定论文原方法；读取时尚未收到选择。

- ByteTrack：作者README明确可接其他检测器输出。作者源码使用高分/低分两阶段关联，低分候选下界为0.1。当前项目YOLO输出默认0.3门限且最多16框，所以接入前需要单独设计跟踪候选输出；不能直接复用UI过滤结果并声称保留了全部作者低分关联语义。依赖还包括NumPy、匹配组件及作者代码的Torch导入，需在板端核验。具备实施基础，不等于已通过板测。
- Light-ASD：作者仓库提供权重、评测和视频demo，可先用预训练权重做真实片段推理，不必为了开始验证就重训。按项目既有分工优先放Windows主机；本轮未核验该主机算力或运行时性能，实时预算仍须实测。
- 项目主线：已有有效期/准入软件和VSRV基础，下一步是实测校准、源绝对期限RTL/仿真及联合实现，再做G0—G5。最新源平台WNS仅+0.001ns并保留外部约束缺口，新增逻辑能否与DPU满足时序只能由重新实现决定。
- AoI/VoI原文研究的是蜂窝网络控制调度；AURA的图像误差期限模型是工程适配，不能将项目公式当作该论文原算法复现。
- RTLola编译器与定制加速器路线应单独固定论文/代码/目标平台，先复现独立基准再决定整机集成；本轮未承诺所有候选都能在现有联合位流中直接加入。

建议把交付等级分为：作者方法/固定输入基线、项目数据评测、系统接入与真实对照。采用不同模型/平台时写清变化，只有对应实验通过才升级状态。当前优先级建议为ByteTrack应用接入与项目期限监督主线；Light-ASD可在主机线并行，但这不是用户已选择的执行指令。

本轮在线重新查看：[ByteTrack作者说明](https://github.com/FoundationVision/ByteTrack)、[作者跟踪源码](https://raw.githubusercontent.com/FoundationVision/ByteTrack/main/yolox/tracker/byte_tracker.py)、[Light-ASD作者仓库](https://github.com/Junhua-Liao/Light-ASD)、[AoI/VoI摘要](https://arxiv.org/abs/1903.05356)。RTLola仓库页面可访问，但猜测的master/README.md原始链接失败，未据该失败认定仓库不可用。本地初次猜测yolox_bridge.cpp位置失败，已用rg定位到board/vision/native/；不影响只读评估。没有新增软件、模型或板端测试。
