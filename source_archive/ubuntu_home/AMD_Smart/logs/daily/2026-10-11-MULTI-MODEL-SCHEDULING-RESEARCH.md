# AURA：板端多模型调度与加速可行性核查

日期：2026-10-11。任务：核对当前模型位置、已有调度实现，并检索相关论文。本文为源码、已有实测资料与文献核查；未修改运行代码、部署模型或开展新板测。

## 结论与事实来源

建议第一阶段实现“KV260 单 CU DPU 上的视觉多模型共享推理与期限调度”，Windows 保留用户报告已部署的千问 14B 和语音模型。板端 ARM 负责调度，PL 中的 DPU 负责兼容网络的计算。跨板卡与 Windows 的请求编排另行计时，不应将 Windows 推理称为板端 DPU 加速。

开工阅读 ZIP 的 `项目/README.md`、完整实施方案相关条目、PROJECT_BOOK_INDEX、最新 YOLO 日志和接入报告，并核对实际源码。ZIP §4.3 已列“共享 DPU 调度，保证人体检测不会被身份任务持续挤占”；10 月 7 日创新方案进一步提出按源感知有效期准入身份任务。因此该方向在项目目标中已经存在，但尚未完成真实多模型共享 DPU 验收。

- 最新 [YOLO 接入报告](/home/ghmd/aura-board-yolo-20261011/YOLO_INTEGRATION_REPORT.md)：YOLOX-Nano 已在 KV260 的 B4096 DPU 运行，1 CU、300MHz。真实相机检出人；最终 20 秒观察中检测调用中位数 10.66ms、P95 18.85ms。另一个短采样窗口实际检测约 9.98Hz。这些数值不是 DPU 纯核耗时、长期稳定性或多模型测试结果。
- [scheduler.py](/home/ghmd/Win共享文件/共享文件夹/aura/board/fusion/scheduler.py)：`SingleCuScheduler` 已有 detection/identity 两类成本记录、不可抢占进程内锁、期限准入及每 N 次检测执行身份的基线；无完整通用队列、跨进程统一所有权、任意模型注册或真实多模型板测。
- [application.py](/home/ghmd/Win共享文件/共享文件夹/aura/board/runtime/application.py)：身份后端为 disabled、synthetic 或 `CpuSFaceEmbedder`，不能据此声称第二个 DPU 模型已接入。
- [ui_camera_service.py](/home/ghmd/Win共享文件/共享文件夹/aura/board/vision/ui_camera_service.py) 实际创建 `DpuYoloX`，尚未调用上述统一调度器。[yolo_dpu.py](/home/ghmd/Win共享文件/共享文件夹/aura/board/vision/yolo_dpu.py) 生命周期持有 `/run/aura-person-dpu.lock`；后续须统一所有权，不宜通过简单删除锁或另开争抢进程实现共享。
- Windows 千问 14B 和语音模型来自本轮用户说明，未连接 Windows 核验版本、量化方式、显存、模型接口或耗时。未假定该 14B 模型具备视觉输入能力。

## 文献与适配边界

尝试直接访问 Google Scholar 的相关搜索页失败，工具报告不可访问。后续使用会议官网、作者/研究机构公开 PDF、arXiv、IEEE 出版记录和 AMD 官方文档。核对摘要、相关方法段落与平台说明；不是逐篇完整复现，也未验证作者代码可在本项目直接运行。

| 文献 | 核心内容 | AURA 适配判断 |
| --- | --- | --- |
| [Time-Predictable Acceleration of Deep Neural Networks on FPGA SoC Platforms，RTSS 2021](https://retis.sssup.it/~a.biondi/papers/RTSS21.pdf) | 对 Xilinx DPU 做执行画像和响应时间分析；DICTAT 用片上指令供给改善可预测性 | 优先阅读。先借鉴执行时间、访存竞争测量；DICTAT 本身需 FPGA 改造，未移植 |
| [Time-Predictable Acceleration of Deep Neural Networks on FPGA SoCs with Multi-Core DPUs，RTAS 2026](https://retis.santannapisa.it/~giorgio/paps/2026/Aromolo-RTAS26.pdf) | 多核 DPU、访存预算、优先级调度及网络分段；应用层控制在途请求以管理执行顺序 | 与需求直接相关，但论文平台配置不能当作 KV260 已有配置。分段需要重新导出/编译多个 xmodel，存在额外开销，不是任意暂停现有模型 |
| [Dynamic Sharing in Multi-accelerators of Neural Networks on an FPGA Edge Device，ASAP 2020](https://asap2020.cs.manchester.ac.uk/paper.php?id=79) | SharedDNN/PlanAhead 利用请求规律安排加速器分配与请求顺序 | 可借鉴周期检测与突发身份请求的分配方法；原工作为多加速器系统 |
| [PREMA: A Predictive Multi-task Scheduling Algorithm For Preemptible Neural Processing Units，2019 预印本](https://arxiv.org/abs/1909.04548) | 预测执行时间、优先级与可抢占 NPU 调度 | 可借鉴成本预测和优先级；现有 DPU 未验证中途抢占/恢复，不能声称完整复现 PREMA |
| [Serving Multi-DNN Workloads on FPGAs: A Coordinated Architecture, Scheduling, and Mapping Perspective，IEEE TC 2023](https://doi.org/10.1109/TC.2022.3214113) | H3M 联合搜索加速器架构、网络调度与多核映射，含 U200/U280 验证 | 适合作为多模型 FPGA 相关工作；当前固定 B4096 单 CU 不具备其空间多租户架构 |
| [Computation and Communication Co-scheduling for Multi-Task Remote Inference，2025](https://arxiv.org/abs/2501.04231) | 远程多任务推理的计算、通信与信息更新联合安排 | 与板卡—Windows 编排有关；已有项目成本准入启发式不等于原论文策略 |

原项目其他论文分工仍成立：ByteTrack 用于轨迹关联，MobileFaceNets/ArcFace 路线用于身份，Light-ASD 用于主动说话人，RTA/RTLola/AoI-VoI 支撑执行监督与信息时效。它们分别解决子问题，不是一个可直接安装的“多模型调度包”。原资料对照见 [PAPER_PROJECT_MAPPING.md](/home/ghmd/aura-shared-review-20261008/PAPER_PROJECT_MAPPING.md)；其中 10 月 8 日实时视觉状态须由 10 月 11 日 YOLO 记录更新。

## 第一阶段架构建议（未实现）

1. 模型组合先固定为 YOLOX-Nano + 一个 DPU 兼容的轻量身份特征模型。人脸检测/五点对齐可先保留 CPU 参考链，验证正确性后再决定是否增加第三个 DPU 模型。MobileFaceNet 是候选，不能预先承诺编译成功。跟踪和向量匹配主要留在 ARM；ByteTrack 不能计为第二个 DPU 网络。
2. 每个候选分别核验权重来源、目标架构指纹、量化精度、DPU/CPU 子图、预后处理、峰值内存与真实耗时。使用同一 DPU 支持的模型不需要每次切换 FPGA 位流，但仍有运行时切换、缓存、访存等成本需要测量。
3. 建立一个推理所有者，统一现有 YOLO 与新增模型；按内存允许常驻实例。应用层排队，每次只向现有单 CU 提交一个待执行作业，在下一任务开始前做决策；第一版以完整调用为不可抢占单元。AMD [VART 3.0 Runner 示例](https://docs.amd.com/r/3.0-English/ug1414-vitis-ai/vart-Runner-Example) 提供子图实例、异步执行和等待等基础接口，本身不提供 AURA 的源期限策略。
4. 检测仅保留最新待处理帧；身份按目标触发、缓存并有服务频率上限。作业包含模型、源帧/采集时间、轨迹代次、截止时间、成本估计和取消标记。发布结果前再次检查有效性。过期视频帧可替换，用户登记等有业务语义的请求须明确成功/拒绝，不能无声覆盖。
5. 身份准入保留下一轮检测和预后处理预算。先比较 FIFO、固定比例轮转、检测优先、期限准入；同时记录身份等待及拒绝，防止靠始终跳过身份获得低检测延迟。观测最大值/分位数加余量只是工程估计，不能当作已证明 WCET。
6. CPU 采集、预处理、跟踪及网络请求可与 DPU 运行重叠，但需测 CPU/DDR 竞争。多线程不等于两个模型在单 CU 同时独占计算。算法调度改善等待、帧龄与有效吞吐，不保证单次卷积更快。
7. Windows 服务按会话进行 ASR→千问→TTS 等依赖编排，计网络/排队/首响应/完成时间，支持取消和迟到结果失效；准确顺序依实际语音服务接口确定。该链应与视觉检测并行推进，不能阻塞相机服务。

KV260 官方 [规格](https://japan.xilinx.com/content/dam/xilinx/publications/product-briefs/xilinx-kv260-product-brief.pdf) 为 4GB DDR。以 140 亿参数稠密模型全部权重常驻、每权重 4bit 粗算，仅权重约 7GB，另有量化元数据、运行时和 KV cache。因此将现有 14B 整体迁入当前 KV260 内存/DPU 不是本阶段可行的直接部署路径；该估算不是对尚未知版本的实测。小型语音模型可另评估算子与资源，不预设其能在此 CNN DPU 运行。

## 验收与推进顺序（计划）

- M1：第二模型单独上板正确推理，取得精度、完整调用成本、内存数据。
- M2：两模型常驻同一个服务并交替运行，验证结果一致、所有权、资源清理、错误恢复和 UI 不阻塞。
- M3：相同输入、模型与请求到达序列下比较上述调度策略，覆盖单人/多人、身份请求突发、UI/音频并发、取消/目标更换及持续过载。
- M4：报告各任务 P50/P95/P99 等待与完成时间、视觉源帧龄、截止违约率、身份服务覆盖/等待、正确率、内存、CPU 与 DPU 活跃时间。有合适测量条件再报告功耗；不能仅凭主机函数耗时反推 DPU 利用率。
- M5：若基线显示长任务阻塞是瓶颈，再评估模型分段；若预后处理/拷贝占主导，再评估流水线和 PL 核；多 DPU、DICTAT/访存预算器等作为需要重新综合与时序验收的第二阶段。

可用的研究命题是“面向视觉交互的感知时效约束多模型共享 DPU 调度与执行监督”。多模型共享、优先级和期限调度均已有先例；贡献必须通过适配设计、强基线、消融与真实板测建立，不能称已有全球首创或预设提速比例。

## 本轮验证范围与遗留问题

完成：资料和源码只读核对、公开文献检索、形成此日志。未重跑已有测试、未访问板端/Windows、未下载或迁移模型、未改变当前运行服务。需要后续确认具体身份/语音模型及权重格式；本轮已发起板端模型范围澄清，暂按视觉优先、Windows 大模型保留的推荐方案分析。

## 后续追问：创新与改进的优先级

用户追问本项目可以有哪些创新与改进。本次继续核对原单一创新方案，并补查 [AoI/VoI 原论文](https://arxiv.org/abs/1903.05356) 与 [RTA 教程](https://arxiv.org/abs/2110.03506)。推荐围绕一个研究主线组织贡献，而不把多个成熟模块各自称作原创。

| 优先级 | 候选改动 | 贡献定位与验收 |
| --- | --- | --- |
| P0 | 第二个真实模型接入同一 DPU 所有者 | 必要工程基础；先证明两模型正确运行及资源可容纳，随后讨论调度收益 |
| P1 | 根据目标运动和位置不确定性调整检测需求、身份准入 | 主要研究候选。以独立位置误差、有效跟随覆盖和身份等待衡量；速度/误差参数需校准，跟踪预测不得给旧观测续期 |
| P1 | 源感知期限贯穿 PS 调度与 PL 输出许可 | FPGA 协同贡献候选。推进 PL 绝对源期限与同观测不可续期，在 PS 卡顿/重放/相机冻结时验证数字许可；机构停止另验 |
| P2 | 按图像质量与身份状态触发识别、缓存并明确失效 | 降低无效推理的工程优化，可作为主调度方法的消融。质量规则与误识/拒识需实测，低质量不能按高置信身份缓存 |
| P2 | 帧、目标、会话统一关联，淘汰迟到视觉/ASD/主机结果 | 跨模型一致性工程改进。验证换人/取消/断连时不串人、不播旧回答，不能仅凭加 ID 声称原创 |
| P2 | 常驻模型、预后处理流水和必要的数据复用 | 端到端性能优化。先画像再选加速点，分别报告核时间、排队、拷贝与整链延迟；此轮没有确定瓶颈或提速比例 |
| P3 | 模型分段、独立 PL 预处理核、多核 DPU/访存控制 | 进阶研究，依真实瓶颈和资源决定；需重新验证量化精度、开销、联合资源及时序 |

演示可用同一批输入切换已调好的固定策略和候选策略，展示慢移/快移/多人/拥塞及迟到结果；沿用既有 G0—G5 的消融定义。公平性同时约束检测质量与身份服务，避免以关闭次要任务或停止一切运动制造收益。调度估计并不提供硬实时数学保证。

可把调度日志采集、固定输入回放、故障注入、指标导出和报告生成整理为可执行 Skill 包，作为方法复用与比赛交付；只有 README/interface 文件不构成完整工具包。本次仅补充决策记录，未新增实现或运行测试。
