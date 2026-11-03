# AURA·汐蓝项目统一框架实际搭建

任务开始于 2026-10-08，2026-10-09 完成软件框架、文档、源包及移机检查。用户授权：“我想让你搭建好我这个项目框架”。用户此前明确机构等待 3D 模型，本次不驱动舵机。

## 资料与原件

已先读取 `/home/ghmd/下载/项目.zip` 中的 `项目/README.md`、无声源定位完整方案、三人分工及相关 FPGA/主机合同资料，结合日记和最新共享证据判断状态。当前主线按 `Win共享文件/方案/aura_junior_project_framework_20261008.md` 和 10 月 7 日单一创新方案对齐；计划不当作实测。

实际主仓为 `/home/ghmd/Win共享文件/共享文件夹/aura`，未写入同名旧副本。没有 Git 仓库；修改前保存了 README/EventBus 原件与 SHA 至 `/home/ghmd/aura-framework-build-20261008/baseline/`。已有素材、声线、旧测试和报告保留。

## 实际改动

- 新增 `common/{contracts,clock,config}.py`：明确时钟、相机/帧/目标代次、来源证据、命令合同和可移机配置。
- 新增 `board/vision/`：有界最新帧采集、CPU/Synthetic/DPU 插件接口、IoU 参考接入和可选 ByteTrack 适配。旧视觉源码和两份 CPU 权重从本地实验目录复用并校验。
- 新增 `board/identity/`：显式同意登记、模型隔离、已知/未知/模糊匹配、修订号使删除后的缓存失效。
- 新增 `board/fusion/`：目标选择、候选可变有效期、单执行锁与身份任务准入、说话人结果窗口检查。
- 新增 `board/motion/`：唯一虚拟命令写入和来源/期限/恢复代次监督。旧 VSRV 驱动作为参考；没有物理输出。
- 新增 `board/runtime/{application,session,media_session,project_log,scenarios}.py`：组合原 FSM、UiState、校验器、会话与异步主机。图像年龄由运行时计算，失联来源不得用于新图像请求。
- 原 `board/runtime/event_bus.py` 只新增可选的同步不留队列模式，新运行时使用它避免同步事件积压；默认行为保持原约定。
- 新增 `host/model_service/`：有界异步入口及原三阶段 ASR/VLM/TTS 管线接入，原 `protocol/pipeline/backends` 仅统一 LF 换行。
- 新增 `hardware/rtl/visual_servo.sv` 参考与平台能力清单；不是新 FPGA 平台构建，原 RTL 没有绝对源期限能力。
- 新增运行、模型、来源、标定和 G0–G5 实验配置；未标定或未完成项保留 false/null/pending。
- 新增统一入口、Windows/Linux 启动器、源包脚本、框架测试、合成回放、框架/主机/硬件/模型说明；更新主仓 README 为整体框架入口。

具体原件 SHA 和导入方式见主仓 `config/source_import_manifest.json`。用户原有汐蓝声线与动画没有重新生成。

## 软件实测

执行环境为当前 Ubuntu 系统 Python 3.8.10，核心采用标准库。缺少 NumPy/OpenCV、PySide6、pytest/jsonschema 等可选依赖，没有安装或修改原虚拟环境。

| 命令/检查 | 实际结果 |
|---|---|
| `python3 -s -m unittest discover -s tests/framework -v` | 41/41 通过 |
| 默认模拟配置 `doctor` | 通过，YuNet/SFace SHA 相符，无设备访问 |
| 固定期限模拟 `demo` | 10/10 检查通过 |
| 可变期限模拟 `demo` | 10/10 检查通过，参数仅示例 |
| 合成记录 `replay` | 6 条记录处理完成 |
| `python3 -s tools/aura_host.py` | 6/6 媒体管线检查通过，全部阶段 fixture 标记 |
| 本地语法/JSON 解析 | 79 个 Python、12 个 JSON 通过 |
| KV260 配置 `doctor` | 按预期未就绪，退出码 2：缺项目 xmodel、DPU 入口/指纹、NumPy 和 ByteTrack |

本次较早直接调用了旧 EventBus/FSM/UiState 相关测试：12+19+10=41 项通过，另 1 项 pytest 和 2 项 jsonschema 依赖检查未运行。没有执行旧仓完整的 550 项回归，历史结果仍属原报告。

软件输出记录在主仓 `metrics/raw/framework-validation-20261009/validation.json`，其中包含真实命令、返回码、输出和每次联调 trace/summary 所在目录。框架状态见主仓 `docs/FRAMEWORK_STATUS.md`。

## 源包与移机实测

生成框架源包：

`artifacts/releases/aura-framework-20261009T072032Z-a77949-source.zip`

大小 36,501,183 字节；SHA256 `1825f5f9120dc842551ebe4b7c69dcad903ecf7e8e493fe95a0f24e3924cfa42`。121 个条目的内容/长度/SHA 校验通过；其中 120 个源仓文件与包内副本一致，另一个为生成的移机说明。刻意改变包内配置后校验拒绝，错误为 `Bundle integrity mismatch: config/runtime.sim.json`。

解压到 `/home/ghmd/aura-framework-build-20261008/relocation-q74k_l8l/aura` 后，在 `/tmp` 工作目录使用绝对入口启动：doctor、完整模拟 demo、媒体 fixture 管线全部退出 0。证明这些软件入口在新根目录可定位配置和参考权重；未执行 Windows 启动器或图形界面。

源包默认不含约 443 MB 的既有动画素材、个人身份库、原始媒体、环境、大型语音/DPU 模型、bitstream/overlay 和相邻历史交付目录。它是框架源包，不是整机部署发布。详见主仓 `metrics/raw/framework-validation-20261009/package_validation.json`。

## 尚未验证与下一项

本次没有连接板卡，没有运行真实相机、CPU/DPU 实图推理、真实 ASR/VLM/TTS、跨机器媒体传输、MCP01、Qt 窗口、舵机或 FPGA 新构建/加载。

当前执行跟踪为 IoU 参考；ByteTrack 只有接口适配，Light-ASD 只有结果检查入口。项目 DPU 检测/身份模型与专用前后处理待交付，真实模型服务和播放适配待接入。

可变期限误差界、身份阈值与任务成本没有用独立数据标定。虚拟监督依赖软件 tick/poll，不能当作 PL 独立定时停止；原 RTL 仍是相对租约，PL 绝对源期限仍需 ABI/RTL/仿真/板测。G0–G5 目前是实验定义，未完成六组硬件实验。

下一项按已落地接口固定项目检测模型与 DPU 插件，接入跟踪/身份和真实媒体链；机构/PWM/限位标定等待 3D 模型。
