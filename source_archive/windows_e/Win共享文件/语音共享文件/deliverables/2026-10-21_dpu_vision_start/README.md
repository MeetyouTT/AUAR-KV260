# SFace / YuNet DPU 迁移实施

**后续更新（UTC2026-10-22 07:25后）：YuNet已通过30分钟实时检查并保留DPU配置，MCP01本次告警经重开原应用恢复、观察未复发。SFace又通过真人三模型影子短测（10次完成、平均14.48ms），随后恢复到YOLO＋YuNet常驻，SFace正式身份仍配置WindowsCPU、影子关闭。最新源码候选、状态和比较见[实时接入交付](../2026-10-21_dpu_live_baseline/README.md)。本页下文/release.json记录05:53首轮完成时的回退状态，作为历史证据保留。**

用户于 2026-10-21 授权先实施适合 DPU 的模型、自主规划。本轮完成 **YuNet 与重新校准的 SFace 的 INT8 转换、目标编译及实板固定输入验证**，并完成三模型同进程切换测试。实时常驻切换尚未放行：延长试运行发现调度尾延迟及 MCP01 USB 音频告警，最终已恢复原相机配置。当前业务仍为 YOLO=DPU、YuNet=ARM CPU、SFace=Windows CPU。

最新机器可读状态见 [release.json](release.json)。`artifacts/*/compiler-manifest.json` 保留编译时元数据，板测与最终启用状态以 release 和本报告为准。

## 交付模型与实测提升

两份模型均编译至 `0x101000056010407` / KV260 B4096，各有一个 DPU 计算分区。CPU 负责输入转换、解码、对齐、匹配和业务状态。

| 候选 | 编译体积 | ARM FP32 中位数 | DPU 路径中位数 | 对照范围 |
|---|---:|---:|---:|---|
| [YuNet](artifacts/yunet/yunet_public_int8.xmodel) | 576,254 B | 124.02 ms | 61.41 ms | 40 次固定输入；含 CPU 预后处理，约 2.02 倍 |
| [SFace](artifacts/sface/sface_public_int8.xmodel) | 10,796,375 B | 520.86 ms | 13.56 ms | 8 次固定已对齐人脸；含输入/输出转换，约 38.41 倍 |

YuNet CPU / DPU P95 分别 147.60 / 64.75 ms；SFace 分别 627.78 / 26.60 ms。SFace 对照对象为板载 ARM FP32，当前 Windows 业务链路时延须另测。两组短测分别进行，不构成整机端到端提升或长期性能承诺。

- YuNet SHA256：`54d348bfeee01756a98bda4103c056a2d5e469a26ea887822da6edc28bdbbbee`。
- 新 SFace SHA256：`12b2ff5c7de157133ebd5aa71665fc5ddcd1f65d9e30e2d6e965e0752e467f25`。与旧单图校准 `bee245…` 为不同版本，身份模板须按模型版本隔离。
- YuNet 4 组公共/合成输入的 399,500 个 INT8 输出值、SFace 4 组公共输入的 512 个输出值，均与主机量化模拟逐值相同。
- YuNet 原权重等价提取 43 Conv / 18 ReLU / 5 MaxPool；4 种尺寸 × 2 种输入共 8 组 FP32 对照通过，最大绝对误差 0.00005150；真实 Inspector 全部分配 DPU。Softmax、框与五点解码、NMS、对齐留 CPU。

详见 [YuNet 实板对照](evidence/board-yunet-v2.json)、[新 SFace 及三模型实板对照](evidence/board-three-fixed.json)。

## 量化质量

复用已有 Vitis AI 3.0 镜像，使用官方固定校验的公开 LFW funneled 数据。256 个不同身份作校准，校准身份与 train/test 均无重叠；train/test 身份也无重叠。2,200 对训练配对用于选阈值，独立 1,000 对测试配对用于评估，所有配对均可评估。图像、裁剪、特征数组和原始 UART 全部私有保留。

SFace 独立测试结果：

| 各自在训练配对上选阈值后测试 | 准确率 | 误接收 / 500 负对 | 误拒绝 / 500 正对 |
|---|---:|---:|---:|
| FP32 | 98.8% | 0 | 12 |
| INT8 模拟 | 98.8% | 1 | 11 |

1,549 张独立测试图的同图 FP32 / INT8 特征余弦中位数 0.98242，P05=0.97286。公开工程质量门通过，现场身份阈值、多人歧义及注册模板仍待验收。公开数据的 0.36647 配对阈值未写入业务配置。

YuNet 在 256 张身份独立测试图、0.9 阈值下，FP32 检出 294 张脸，INT8 匹配其中 293 张；匹配框 IoU 中位数 0.97428、五点平均误差的中位数 1.45 像素。这是原模型一致性，缺少场景标注 AP 与全景背景校准。

详见 [SFace 独立评估](evidence/sface-evaluation-report.json)、[YuNet 一致性](evidence/yunet-evaluation-report.json)、[数据划分](evidence/public-dataset-report.json)。

## 三模型共享 DPU

同一进程、同一个项目 DPU 所有权锁，实际运行 YOLO、YuNet、新 SFace。最终固定预编码输入测试中：

| 阶段 | YOLO 次数 | YuNet 次数 | SFace 次数 | 100 ms 周期超时 |
|---|---:|---:|---:|---:|
| YOLO 10 Hz | 20 | 0 | 0 | 0 |
| YOLO 10 Hz + YuNet 5 Hz | 40 | 20 | 0 | 0 |
| YOLO 10 Hz + YuNet 5 Hz + SFace 2 Hz | 40 | 20 | 8 | 0 |

三模型阶段的 submit/wait 中位数：YOLO 原生调用 6.78 ms、YuNet 2.36 ms、SFace 8.41 ms。该阶段输入预先编码，体现模型切换与计算容量，实时采集、脸部目标、对齐及身份业务仍需联合验收。

## 实时试运行、回退与当前状态

已回收板端真实运行源码，候选在 [candidate/aura](candidate/aura) 中保留现有脸部跟踪、多人拒绝、照片策略和 Windows SFace，加入 DPU YuNet、检测优先和截止时间调度。CPU 输入编码与输出反量化移到 DPU 锁外。普通预算估计失配与真正越过保护边界分开记录，保留 30 ms 占用上限、超限 CPU 回退及独立服务回退定时器。

首轮固定测试发生 `-11`：XIR 输出集合顺序与 VART 端口顺序不同，导致缓冲区大小放错端口。已改用 VART 的输入/输出接口，并加入端口顺序互换回归；后续所有板级输出逐值通过。

实时初版在 20.65 ms 触发 CPU 回退；v2 一次断言回退只保留了空异常文本，精确触发点未能回溯。随后补齐 last_state、错误原因与越界诊断。v3 短观察达 YOLO 约 9.50 Hz、YuNet 约 2.10 Hz、0 次真正越界。延长采样测得一次 28.04 ms、估计预算更新至 30 ms，仍保持 DPU。

随后发现 USB 音频告警与日志负载，已主动恢复原配置作对照：

| 15 秒采样 | 总 CPU（四核总量） | 相机进程 CPU（四核总量） | XRT DPU 任务忙时 |
|---|---:|---:|---:|
| 迁移前 | 75.21% | 40.07% | 4.13% |
| YuNet v3 试运行，USB 告警期间 | 87.09% | 20.77% | 4.93% |
| 回退 CPU 后，USB 告警仍持续 | 90.31% | 26.89% | 4.45% |

告警设备实读为 xHCI slot04 / 地址4 / `1-1.2` 的 Lenovo MCP01 USB 音频设备；摄像头在 slot05 / 地址5。日志为 `HC couldn't access mem fast enough for slot 4 ep 3`。回退后仍出现，故当前证据不能确认触发根因，也不能将总 CPU 或采集帧率差异归因于模型迁移。Linux 对应分支为 `COMP_DATA_BUFFER_ERROR`，根因须继续排查；[内核源代码](https://code.googlesource.com/linux/torvalds/linux/+/d97ae6474ca0411bb8c2696e5764ec946dba43d0/drivers/usb/host/xhci-ring.c) 将其与带宽超限、传输环欠载等分开处理。

XRT 忙时来自支持的 CU 统计接口，采集后已关闭；它表示驱动任务忙时。位流、静态 LUT/DSP/BRAM 资源不因本轮多模型编译改变。

最终核验：boot `215c4292…`；相机 PID106407、检测持续推进、无 camera/detector error；相机服务单元已恢复原字节、`dpu_schedule=null`、`face_backend=null`、`feature_backend=windows_sface`。GUI 主服务与 Xserver active / NRestarts=0，未改显示、运动、身份库或恢复此前暂停的全局 CPU 优化。[最终核验](evidence/final-audit.json)

## 源码、验证和后续顺序

[source](source/) 包含校验下载、数据准备、等价重构、量化、编译、单批次导出、实际 VART 端口运行器、调度、受控板测/回退和补丁传输。新 SFace 通过旧工程权重的校验字节补丁传输，重建全文件 SHA 后才执行；原模型保留。18 项软件回归通过：5 运行器、6 调度、4 现行业务集成、3 补丁完整性；另有 8 组 YuNet 浮点对照及上述实板验证。

复用环境入口：`python3 source/run_vai.py <script.py> ...`，依赖本 Ubuntu 现有固定 Docker 镜像及脚本列出的挂载。独立评估后另用 `export_sface_batch_one.py` 导出 batch=1；编译脚本再次检查所有 DPU 端口 batch=1。

后续按顺序推进：MCP01 USB 音频异常及稳定基线 → 三模型实时长稳/CPU核秒/帧龄/丢弃率 → 精确模型版本的 SFace 登记库和现场阈值验收 → 有业务收益的提频或多目标。可展示的工程工作是共享帧、检测优先、CPU/DPU 分工、失效回退与可复核测量；PL 仲裁扩展尚待资源与时序验证。

Windows 只接收候选、模型及过滤证据；其同步/回执未验证。候选必须匹配 `candidate/patch-manifest.json` 的实际运行基线后集成，现有业务目录和配置不应被旧候选覆盖。私有原始证据目录：`/home/ghmd/aura-dpu-vision-20261021`。
