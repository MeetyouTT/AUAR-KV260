# AURA 全项目文件复核

记录日期：2026-11-01（America/Los_Angeles）。目录和清单采集时间为 `2026-11-02T00:20:35.472584+00:00`。本报告依据本机已同步文件；设备的实际状态须由新的板端读回确认。

项目已有联合 FPGA、三模型视觉、板端业务与记忆、Windows 推理及界面实现。当前工作重点是恢复运行、补齐本轮验收和收拢最终发布版本。通用开发树、交付中的补丁与板端应用清单分开保存，不能任选一个 `aura` 目录作为最终包。

## 文件地图

| 位置 | 当前用途与使用边界 |
| --- | --- |
| [语音业务源码](../../语音共享文件/aura/) | 包含 board、common、host、tools、config、tests、assets；是持续开发目录，部分已应用修订另存于交付目录。 |
| [板端业务交付](../../语音共享文件/deliverables/2026-10-30_board_owner/) | 板端业务接管、ASR/前端、记忆、人格/动画及历次集成修订。 |
| [视觉与转轴维护](../../语音共享文件/deliverables/2026-10-31_visual_axis_maintenance/) | 原控制器、方向修正、字幕/性能、摘要验收及新 boot 转轴试验。先查看具体阶段证据日期。 |
| [语言模型分析](../../语言模型分析/README.md) | 较新业务方向和接续状态；本次该入口比共享总入口更新。 |
| [原业务主目录](../../共享文件夹/aura/) | 保留完整工程结构和较早交付框架；代表性源文件已落后于语音目录。不能直接覆盖较新修改。 |
| [根目录早期副本](../../aura/) | 更早的代码副本，保留追溯。 |
| [FPGA 设计框架](../../aura_fpga/readme.md) | 历史规格与提交矩阵，状态表不是当前板测结果。 |
| [项目资料导航](/home/ghmd/AMD_Smart/PROJECT_BOOK_INDEX.md) | Ubuntu 方案、参考资料与日志导航；新证据在共享交付中继续积累。 |
| `/home/ghmd/aura-pan-wide-20261028/` | 宽脉宽联合平台的 RTL、BD/XDC、实现、配套固件、控制器及独立审查。 |
| `/home/ghmd/fpgachina26-amd/` | 本地保存的赛事指南仓库。本轮未联网复核公告或登录队伍后台。 |
| [比赛提交框架](../../语音共享文件/aura/submission/aura_junior/README.md) | 明确标注 FRAMEWORK_NOT_FINAL_COMPETITION_RELEASE，final_release_id 仍为空。 |

家目录另有 152 个 `aura-*` / `kv260-*` 工作目录，多为分阶段构建、候选、故障分析与板测证据。当前发布所需内容要按清单追溯，不能按目录名字或修改时间直接挑选。

## 较新的实际记录

### 板端语音与业务

[应用状态](../../语音共享文件/deliverables/2026-10-30_board_owner/integration/production_business_acceptance/CURRENT_PUBLICATION_STATE.json)与[软件检查说明](../../语音共享文件/deliverables/2026-10-30_board_owner/integration/dialogue_repair/joint_balance_20261101/continued_validation_20261101/软件检查与恢复说明.md)一致记录：

- startup `ec12fccf…`、manifest `b1445363…`、voice_first 源 `54fa17ac…` 已应用，380 组件清单中其余 379 项保持。
- `production_ready=false`；最后记录 MainPID=0、unit failed、GUI API 不可用。
- 原始错误为 `Persistent ALSA start failed`，硬件元数据中 MCP01 未枚举；声卡连接/枚举恢复仍待验证，未确定 USB 缺失的具体硬件原因。
- 启动重试和硬件轮询已按此前用户要求停止。恢复应沿原设备窗口与既有受保护启动流程进行。
- 板端负责业务、ASR/音频前端、视觉、存储、记忆与播放；Windows 继续承担现有 27B 和 OmniVoice 推理。这里只核对现有实现和交接，未查询当前 Windows 服务健康。

此前 `22317f79…` / `de04c6cd…` 版本的字幕两栏与完整播放回执保留为历史通过证据，不能据此声称 ec12 版已 READY 或仍处于运行中的 PAUSED 页面。

### 视觉、FPGA 与转轴

联合 wide 平台已经有构建、配对、时序/路由、上板及三模型视觉证据。10 月 28 日离线独立审查记录 setup/hold 无失败、路由错误为 0；其旧“待上板”字段应结合后来板端证据阅读。500..2500µs 是控制能力，真实机械 ±90° 和零点未据此验收。

11 月 1 日较早的原人脸随动短测完成方向 +1 修正，并获得用户近似认可。之后发生新 boot，最新[转轴试验目录](../../语音共享文件/deliverables/2026-10-31_visual_axis_maintenance/reviews/axis_priority_20261101/evidence/)记录时间为 UTC 14:48–14:54：

- 新 boot `3c94e7a0…` 上恢复 wide 与匹配 VART，恢复相机，并记录 YOLO/YuNet/SFace 计数推进及身份后端就绪。
- 有限初始化 1500→1505µs 后出现实体异常，试验中止；记录状态为 `PHYSICAL_ANOMALY_ABORTED_OUTPUT_CLOSED`。
- 最后保存 flags=0、lease=0、active=false、armed=false，脉宽读回 1505µs、无剩余运动进程，GUI 不可用。这些是保存时点的寄存器/进程读回，不是当前现场状态或机械角度。
- 最后一份文件只确认重复初始化已准备，ARM/COMMIT 均未发送；未找到该重复动作执行回执或本轮完整随动验收通过回执。不能把 ROOT_AXIS_PRIORITY 的 IN_PROGRESS 当成当前仍在执行。

新 boot 与 ec12 应用 spec 中的旧 boot/owner 绑定不同，后续启动和运动前需要由原操作窗口重新核对上下文。本次未做任何设备操作。

### 记忆和界面

自然五分钟存储检查已有证据：同一公开输入的用户/助手正文在约 115.80 秒时各 1 行，约 333.44 秒后各 0 行，同时保留有效摘要和已提交任务；没有强制改时钟或执行清理。

同会话精确追问和新版暂停后续接的真实验收仍待完成。此前跨会话追问答错保留为原场景记录，不能直接归因于同会话摘要检索。状态投影减负、字幕和完整播放已有旧版本验证；声纹标定、多小时稳定性、真实声学首声及新版本全流程仍未闭环。

10 月 31 日 CPU 78.65%、DPU 忙时 6.27%等短窗资源数据属于当时实例，不能作为 ec12 或新 boot 的实时负载/性能结论。

## 文件一致性与规模

盘点排除了 Git/同步内部目录、指定缓存与虚拟环境目录及符号链接；大小为文件逻辑字节之和，不是磁盘实际占用。

| 位置 | 文件数 | 逻辑大小 |
| --- | ---: | ---: |
| Win共享文件（全部已盘点子树） | 109,530 | 57.83 GiB |
| 其中 tmp | 41,107 | 29.57 GiB |
| 其中 语音共享文件 | 51,939 | 11.94 GiB |
| 其中 共享文件夹 | 9,861 | 9.63 GiB |
| AMD_Smart 项目资料（排除 .codex-home 等） | 364 | 99.79 MiB |

共享目录发现 27 个 `sync-conflict` 副本，其中语音目录 21 个，涉及 GUI、音频、身份、配置等。存在冲突副本不证明生产选中了它们；本轮保留文件并记录路径，没有自动合并或删除。

以已应用 ec12 spec 的 380 项 SHA256 为基准：

| 对照范围 | 核对结果 |
| --- | --- |
| `语音共享文件/aura` 同相对路径 | 268 项一致、56 项不同、56 项缺少 |
| 语音目录中的历史交付、修订包与源树合计 | 380 项对应字节全部找到 |
| 可运行的统一最终发布包 | 本轮未组装或验证，现有比赛目录仍为框架 |

其中 379 项通过同名文件加 SHA 定位；GUI 配置以方向修正包 `new_gui.json` 的别名定位，第 380 项 SHA 一致。完整匹配只说明应用清单对应内容可追溯，不证明启动脚本、模型资源、相机独立清单、原25文件控制器和系统环境已收拢成可复现发布物。

已定位的关键实际修订包括：

- 记忆策略：`memory_negation_v24_candidate_r2/after/board/runtime/board_memory_policy.py`（d6e459f9…）。
- GUI：`release_v21_asr2_display_candidate/payload/tools/board_avatar_gtk.py`。
- 字幕/投影：`joint_balance_20261101/subtitle_repair/after/tools/production_memory_presentation.py`（de04c6cd…）。
- 暂停后继续：`joint_balance_20261101/continued_validation_20261101/pause_resume_candidate/after/tools/voice_first_recording.py`（54fa17ac…）。
- 原控制器与宽版固件有独立发布/核验清单，应与应用 380 项分别对齐。

### 入口过期与完整性

`后续任务_先读这里.md` 和 `PROJECT_BOOK_INDEX.md` 在本轮更新前的最近头记录为 10 月 31 日，语音 README/AGENTS 顶部仍是 22317 版本；语言模型分析入口和 canonical 状态已更新到 ec12 未就绪。它们反映不同历史时点，需要按具体证据判断。

36 个去重清单引用中，34 个本地文件的 SHA/已声明长度一致；1 个属于板端路径，本轮未访问；另 1 个已失配：

`2026-10-31_visual_axis_maintenance/LATEST_REVIEW.json` 的 `latest_joint_performance` 声明目标 LATEST.json 为 1003 字节、SHA `3b1ca6c7…`，实际为 3510 字节、SHA `1d574484…`。这是已确认的索引过期，不能据此把旧状态提升为当前运行状态。本轮未改写这些历史发布文件。

原 `项目.zip` 为 435 个条目、364 个文件；全包 CRC 检查通过，SHA256 为 `90a4c04ef0f7262701702617ec0be03107ad452792db2d7f7ee703f58b371d0c`。

## 后续顺序与边界

1. 接续原转轴试验的异常诊断和收尾，补齐新 boot 的最终停止与验收回执；设备操作权仍按既有交接处理。
2. MCP01 恢复可用且原窗口获准恢复硬件工作后，按当前启动事务核对实际 READY；保留暂停偏好与旧故障证据。
3. 在同一已核验版本和合法同会话下完成自然五分钟摘要召回、字幕、完整音频与停止/恢复；再补长稳与冷启动复验。
4. 按应用、相机、控制器、FPGA、Windows、模型和依赖清单生成统一封版；逐项审查同步冲突，补最终提交矩阵、复现和报告。清理大目录或对外发布另按明确任务执行。

## 本轮操作与验证

本轮进行目录盘点、入口及代表性文件阅读、SHA/长度核对、组件字节定位、原资料包 CRC 验证。无板卡连接、UART/SSH、模型请求、服务启停、采集/播放、运动或业务源码修改；未读取真实身份/对话数据库。受保护的历史 SD rootfs 备份未展开，也未执行全量代码审计或重新运行既有功能测试。

新增本报告和[元数据证据](review_evidence.json)，并在共享入口、项目导航及 Ubuntu 当日日志加入本轮复核记录。Windows 收件与同步状态未核验。

