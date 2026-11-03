# 感知模型调度与时效验证 · Skill B

用一台普通电脑重放 KV260 的相机健康日志，回答三个实际问题：YOLOX、YuNet 和 SFace 各获多少服务，记录到的处理阶段各耗时多少，有逐请求证据时，结果送到消费端时是否还在期限内。全部离线示例使用 Python 3.8 或更新版本的标准库，单进程顺序执行。无需 DPU、GPU 或摄像头。以下命令在本技能目录执行。

## 首次复跑

```sh
python3 -B -m unittest discover -s tests -v
python3 -B scripts/analyze_counters.py examples/public_counters.json
python3 -B scripts/validate_metadata.py --profiles config/model_profiles.json --metadata examples/xir_three_models.json --model-kind yolo
python3 -B scripts/analyze_schedule.py --input examples/jobs_pass.json
python3 -B scripts/validate_metadata.py --profiles config/model_profiles.json --metadata examples/yunet_metadata.json --model-kind yunet
python3 -B scripts/validate_metadata.py --profiles config/model_profiles.json --metadata examples/sface_metadata.json --model-kind sface
```

若同时有工程包中的模型，可在对应元数据命令尾部加 `--artifact ../../models/dpu/sface_public_int8.xmodel` 或 `--artifact ../../models/dpu/yunet_public_int8.xmodel` 校验实际字节。工件文件名和完整 SHA-256 见 `evidence/model_bytes.json`。已有编译工件和 XIR Python 环境时，`python3 scripts/inspect_xmodel.py MODEL.xmodel` 可读取分区与 tensor 接口。这个可选命令需要匹配的 XIR 环境。

## 实测与分母

`examples/public_counters.json` 由 2026-11-02 同一次约 180 秒实测中基线与随后 90 条 camera 健康响应投影得到，仅含同一开机及相机进程标识、单调时间、调用计数、阶段次数与总耗时。可通过 `python3 -B scripts/analyze_counters.py --raw board_numeric.jsonl --project` 从原始数据再生成。原文件名、哈希和计算结果保存在 `evidence/`。

| 模型 | 指标分子 | 窗口增量 | 观测频率 | 阶段平均耗时 |
|---|---|---:|---:|---:|
| YOLOX-Nano | 主路径 primary_calls | 1781 | 9.9069 Hz | 15.9237 ms，含原生运行与解码 |
| YuNet | 可选任务 native_completed | 1773 | 9.8624 Hz | 2.4114 ms，原生租约阶段墙钟时间 |
| SFace | 可选任务 native_completed | 133 | 0.7398 Hz | 8.4221 ms，原生租约阶段墙钟时间 |

三个模型共享一个 B4096。分母是 179.773885 秒，即首末 camera 健康请求完成时刻之差。各阶段耗时按同阶段累计总毫秒增量除以该阶段计数增量计算。进程/开机变化、观察时钟倒退、计数回退会中止计算。窗口内频率受场景及任务准入影响。硬件忙碌率、逐帧 P99 消费年龄、独立核时、极限 FPS 均无此窗数据。同期主窗口实际监听暂停、转轴停止，两个观察窗重叠约 137 秒。声纹 ECAPA 在板端以 CPU/ORT 执行，不进入三项 DPU 统计。

## 逐请求时效

`examples/jobs_pass.json` 和 `jobs_fail.json` 是公开构造样例。自有日志按同样格式生成一行一任务。毫秒时刻取同一 boot、同一单调时钟域。deadline_ms 是绝对截止时刻。来源、排队、开始、结束与消费端各有独立字段。不同机器的时钟不能直接相减。排队和执行按可相减的样本计算；消费年龄取 consumed_ms 减 source_ms；P95/P99 使用最近秩，单列有效样本数。分母纳入排队被拒绝等所有到达。及时消费要求 outcome 为 ok 且 consumed_ms 不晚于 deadline_ms。缺少证据返回 null 或 UNKNOWN。

样例中 YuNet 两个已完成任务有一个消费过期，SFace 有一个成功及一个拒绝，两者及时消费率均为 1/2。运行 `python3 -B scripts/analyze_schedule.py --input examples/jobs_fail.json` 应返回退出码 1，分别指出跨时钟与时间倒序。PASS 表示日志可分析，业务阈值由现场需求确定。累计健康快照不提供逐请求配对，因此不能用它来构造这类消费端分位数。

## 来源与复用边界

- 历史基线来自 2026-11-01 的《Skill交付规划》、其 `skill_delivery_v1/skill/dpu-model-validation-and-scheduling` 及两份已冻结的编译模型元数据。保留了调度日志分析、XIR 元数据对照及原来的反例测试。SFace 样例中的 1000 对数据来自公开 LFW 留出集的主机模拟，未分发人脸图像。
- 当前三模型的运行计数引自 2026-11-02《收尾性能实测》的 `data/board_numeric.jsonl`，独立对照来自同日 `performance_measurement_20261102/DPU_LOCAL_CROSSCHECK.json`。本技能新增了可公开的数值投影、重放脚本和独立断言。该次重放没有触发板端推理。
- 历史 YuNet/SFace profile 固定模型哈希、DPU 指纹、输入形状及 fix_point。另一个模型或新版本需提供对应的预处理、量化/编译记录与冻结接口。三份部署 XMODEL 已由 ghmd 主机上的 Vitis AI 3.0 实际解析，均含单个 DPU 分区，目标指纹同为 0x101000056010407。YOLOX 输入为 [1,416,416,3]，xint8，fix_point 为 -2。ECAPA 采用现役 CPU 路线。独立现场识别质量、实际人脸位置误差要有真值才能评价。
- 换设备可保留逐请求日志接口；用新设备数据替换 counter 适配器中的模型字段、阶段和时钟，固定观察窗及任务到达条件后单独做比较。没有自定义 PYNQ Overlay 加载、现场改参、音视频采集或控制接口。此技能未做非作者跨板复用验收。

## 本次复跑记录

Windows Python 3.10.11 完成 31 项回归。另在 ghmd 所在 Ubuntu 20.04.4 LTS x86_64、Python 3.8.10 通过内存载入同一份脚本及公开输入，复算数值、逐任务正反例、历史两份与本次新增三份 XIR 元数据、ECAPA 排除条件均通过。证据见 `evidence/validation.json`。Ubuntu 此项是脚本重放；整机推理、XIR 重新编译和另一台低核机器上的现场执行未在这项验证中进行。原始日志周期间隔提供开机标识，投影在相邻观测间沿用最近标识；每次采样另核对相机进程及各计数的单调性。