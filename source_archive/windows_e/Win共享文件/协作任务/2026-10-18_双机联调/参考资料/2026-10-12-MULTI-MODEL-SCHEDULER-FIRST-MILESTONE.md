# 全模型 PL 调度：下一步实施清单

日期：2026-10-12。性质：根据用户最新方向整理的实施建议；不是代码完成记录、实测结果或已冻结寄存器 ABI。研究依据见[完整调研](/home/ghmd/AMD_Smart/reviews/2026-10-12-FPGA-WINDOWS-MODEL-SCHEDULING-RESEARCH.md)。

## 第一轮目标

KV260 持续运行真实 YOLOX-Nano/ByteTrack；板端 MCP01 录音经网线交给 Windows，分别执行 Paraformer、Qwen、OmniVoice，再回板端实际播放。四个真实模型的执行均有任务编号、授权、开始、完成和取消记录。

这轮先用可替换的软件仲裁后端提供 PL 的参考行为和性能基线。最终目标仍是 PL 决定任务准入和次序，PS/Windows worker 负责执行；不能把完成软件基线当作完成硬件调度。

## 已确认的可复用入口

项目根目录为 `/home/ghmd/Win共享文件/共享文件夹/aura`。

| 已有位置 | 实际情况 | 接入动作 |
| --- | --- | --- |
| `board/vision/ui_camera_service.py` | 实际 YOLO/ByteTrack 相机服务 | 在现有 DPU 唯一所有者内加入申请/授权/完成接口，继续使用同一相机 |
| `board/fusion/scheduler.py` | detection/identity 两类任务、线程锁、成本估计 | 保留原有对照；在上层加入全局模型任务编排，避免直接破坏旧实验 |
| `host/model_service/pipeline.py`、`protocol.py`、`backends.py` | 已有管线、媒体合同、阶段耗时和取消；README 的可运行示例仍为 fixture | 复用合同和生命周期，接真实后端并暴露各阶段授权；明确文本 LLM 与 VLM 的能力差异 |
| `board/runtime/audio/asr.py` | `SherpaOfflineRecognizer.transcribe` | 作为 Windows ASR 后端封装，输入来自板端 PCM |
| `tools/dialogue_host_ollama.py` | 当前文本对话服务与 Ollama 调用 | 复用对话策略，在模型执行前接资源门；记录实际在线模型标签 |
| `board/runtime/audio/omnivoice_voice.py`、`tools/selected_voice_service.py` | 真实 TTS 包装、子进程及语音任务 | 保留声线和 16 步参数；统一授权与完成回报，结果取消不冒充计算停止 |
| `tools/realtime_stage.py` | 现有 Windows 界面分别触发 ASR、对话和合成 | 接统一任务入口，避免 UI 绕过资源控制 |
| `board/runtime/media_session.py`、`tools/board_avatar_worker.py` | 板端媒体结果校验与播放相关入口 | 接真实返回的音频及当前会话代次，沿用迟到/取消拒用规则 |

## 按依赖推进

### 1. 固定任务合同和实测表

复核 Windows 实际服务、Python/CUDA 环境、Qwen 标签、显存与网络地址；4B 交接基线和用户报告的 14B 分开记录，不擅自替换。列出四个首轮真实模型及身份、ASD、VLM 等后续注册项，未验证后端不能声明 READY。

任务合同至少包括 `job_id`、`model_id`、`backend_id`、会话/取消代次、输入引用、业务期限、预计成本和资源需求。定义 SUBMIT、GRANT、ACCEPTED、STARTED、DONE/FAILED、CANCEL_REQUEST/CANCEL_ACK。终态去重，重连不重复执行；取消结果消费和归还执行资源是两件事。

候选新增位置：`common/inference_tasks.py`、`common/schemas/inference_task.schema.json`、`config/model_registry.json`。这些名称是实施建议，本轮没有创建业务代码文件。

测量冷/热启动、纯推理、预后处理、队列、常驻/峰值显存和网络 RTT/吞吐；成本未知时保留未知，不从论文数据填入。

### 2. 接通 Windows Worker 和板端媒体桥

建议在 `host/model_service/worker.py` 提供统一资源入口，在 `board/fusion/model_coordinator.py` 管理依赖与执行状态。先复用原生 Windows 的既有模型进程，再加入分阶段授权，不新增重复加载的模型副本。

初始 DPU/GPU 各允许一个模型作业，ASR 使用独立 CPU 作业池；这是对照配置。GPU 常驻显存另算，串行执行不代表可以同时装下所有模型。各资源可并行工作，不把视觉和语音排成一个串行队列。

分两小步集成：固定音频夹具通过真实模型、网络和板端播放；随后接 MCP01 实录。现有文本 WebSocket 和媒体合同显式转换，不能仅修改 host 就声称整个媒体链可用。音频二进制传输、中间数据留 Windows，控制与载荷采用有界独立发送队列。

### 3. 统一日志并建立软件基线

每个阶段记录本机单调时间、job_id、资源、模型版本、排队/执行耗时及终态，板端记录从录音结束到实际声音播放。不同机器时间戳不能直接相减。缓存命中单独标记，不能作为真实 TTS 推理成本。

视觉记录源帧龄、检测频率、错误和当前目标代次。使用同一输入/配置比较独立运行与混合负载，观察 Windows GPU 竞争以及对板端视觉的影响。

### 4. 实现同合同 PL 原型

任务合同确定后，可以与 Worker 接入并行开发 `hardware/rtl/model_scheduler.sv`：先做 16 个任务槽、参数化资源池、期限准入与仲裁、完成/取消和事件回读。最初每次模型调用不可抢占，禁止因超时直接回收仍忙的资源。

软件参考模型与 RTL 使用相同事件序列，核对选择结果及状态；覆盖忙资源、过期、重复完成、取消与完成同拍、复位/重连和队列满。完成仿真及独立综合后，与现有 DPU/监督 IP 联合实现，检查资源、约束和时序，再进行板级验证。

PL 调度、DPU 计算和运动输出监督分别报告。运动到期/停止不应在普通模型队列里等待。

### 5. 增加模型与计算优化

获得软件/PL 对照后，接第二个真实 DPU 身份模型，再加入 Light-ASD 与实际 VLM。全局合同从首版就容纳它们，但首轮演示不把未实现模型计入。

OmniVoice FlashInfer 作为独立环境、独立质量/性能对照；DPU 分块只在实测长任务阻塞确有需要时引入。保持现有声线与工具链基线可复现。

## 首轮验收建议

以下数量是首轮功能覆盖目标，非已经通过或最终性能门槛：

- 真实视觉连续运行至少 10 分钟，同时完成至少 20 轮真实模型语音交互，包含固定输入对照和麦克风实录；每轮有完整模型阶段及实际播放证据。
- 至少 5 次打断覆盖等待、生成和播放阶段；被取消的旧结果不得恢复播放，仍运行的后端资源不得提前释放。
- 至少 3 次网络短断/重连；每个已接受业务请求最终可追踪到完成、取消、失败或超期，不能悄悄丢失或重复执行。
- 检测资源不被其他进程争抢，混合负载下记录视觉错误、帧龄与服务频率；量化性能门槛在取得基线后、正式对照前确定。
- mock/fixture 的功能测试与真实模型证据分开；此样本量不足以宣称稳定的 P99 或长期可靠性。

首轮交付：接口说明、模型/资源表、Worker 与板端桥、软件参考仲裁、回归结果、运行证据和待补项。第二轮交付：PL RTL/仿真/实现工件及同条件对照。

## 本轮状态

本轮只对照当前代码整理实施顺序和验收，未修改运行代码、配置、模型或位流；未连接 Windows/KV260 或执行推理。以上拟新增文件和测试均为后续实施项。
