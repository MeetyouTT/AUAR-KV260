# 三模型原生路径的 Python 业务接线候选

**本目录是冻结的本机候选，未部署、未访问板卡、未运行真实模型。** C++ 对应同级 `schedule-integration` 的 ABI v2；完整 Python 底座来自主任务按实板 SHA 回收的 `coherent-baseline/aura`，原 214 份源码一致，本候选新增 7 份、修改 5 份，最终 221 份。全部文件 SHA 见 [candidate-manifest.json](candidate-manifest.json)。本目录不会因旧测试需要而修改实际 GUI 或相机的其它代码。

## 接线结果

YOLO、YuNet、SFace 正常业务全部经同一个原生 Context/gate，不再持有跨原生调用的 Python `active` 执行权。`NativeDpuSchedule.primary` 只保留当前线程的原主周期截止时间；仲裁、等待、原生完成、恢复状态由 C++ 持有，Python 锁只用于生命周期记账和释放后的本地指标，不包住推理调用。

- `native_binding.py`：固定库/模型/manifest SHA、C ABI/每个结构尺寸、VART 端口/量化接口；CDLL 释放 GIL。Context 原子接管原 YOLO 对象，unknown 或中断结果保留 owner/缓冲/runner；明确失败才允许回滚句柄。结果 TTL 在 native 返回及使用时再次检查。
- `native_runtime.py`：保持现有 INT8 编码和输出反量化接口；先保留确认完成的原始输出，回到 Python 后确认 result token，再判断业务可用。SFace 第三个合格 probe 可以返回特征，前两个仍 Deferred；未提交、过期、晚获 GIL 不凑成功。
- `native_schedule.py`：以原生状态提供 health/disabled/recovery/wait。100ms 只是无执行权的通知等待。`primary_calls` 按最终 C++ 合同包含有效周期的早拒，`admissions[0]` 仅表示实际取得执行权；原周期已迟到仍会影响主周期超限和恢复，不靠跳过提交隐藏迟到。
- `native_yolo.py`、`native_errors.py`：保留原 YOLO 算法、person 阈值/NMS、原周期 deadline、捕获源 750ms TTL。普通 deadline/TTL 拒绝抛 `PrimaryAdmissionDeferred`，UI 保留 detector，下一帧仍能运行；不伪造空检测结果。unknown 完成停止新主任务并保留原 owner。
- `dpu_yunet.py`：原模型接口、源 TTL、外层重试截止、native 通知重试及 CPU fallback 保留。LATCHED 不会因新接线被重置或自动放行。
- `dpu_sface.py`：原 INT8 模板空间、输入/输出量化、配置/库/阈值不变；execution/completed 与业务返回分别累计。COOLDOWN/PROBATION/LATCHED 的 ready 与 Deferred 向上层传播。
- `face_targets.py`、`camera_faces.py`：传递原源帧 expiry，临时跳帧仍是 discard；禁止旧 shadow/calibration/producer runner 绕过共享原生 gate。
- `native_startup.py`、`ui_camera_service.py`：在 worker 之前校验完整源码闭包、精确 checkpoint，运行原 YOLO 启动自检后才接管；关停时先停止业务/关闭 optional runner，再由 C++ 原子 seal/checkpoint，写出完整 SFace 辅助累计。attach 清理失败不替换原异常，未知结果不尝试释放 owner。

原 YOLO reference/blank 自检发生在 Context/adopt 与所有业务 worker 之前，不记作恢复所需的业务 primary 推进。保留的 `yolo.schedule_wait`/`native_and_decode` 等指标名称是业务路径墙钟，包含各自包装/准入或返回开销，不能当纯 DPU 计算时间。

## 保护与迁移限制

生产入口只接受同一 kernel boot 的完整 **v2 原生已 seal checkpoint**，固定 SHA、source PID/出生时间、来源 unit/manifest；前任仍活着、pending 结果未确认、重复消费、非法 seed、来源不完整一律拒绝。C 层重新验证 policy、时间/计数和 gate 是否首次使用。`isolated_maintenance_seed` 属于单独测试计数域，生产 loader 明确拒绝，不能用来恢复生产故障。

最新主任务只读证据 `../current-resume-board.json` 为：YuNet 已 5 fault / 4 attempt / 4 recovery，guard 故障后 LATCHED CPU；SFace 已 3 fault / 2 attempt / 2 recovery，恢复预算耗尽 LATCHED、累计 755 completed、ready=false。只有 YOLO 正常 DPU 约 9.95Hz，原 worker 活着、gap 累计 0。对应两份 LATCHED/opaque 历史及已知计数的业务回归已覆盖，**不代表取得了可执行的精确迁移 seed**。

老版本没有 native seal/export，health 只是一段仍可能继续变化的前缀，缺 `attempt_times` 等内部状态；当前 loader 故意拒绝把它声明成精确最终 checkpoint。程序不得设置外部 `quiescent=True`、停旧服务后补造零预算，或把 LATCHED 设 RUNNING。**所以本候选不能直接从当前旧进程安全启用生产。** 先前已有冻结 seed 的重启语义与此处“用新 health 创建原生 seed”的限制不同，不能据此断言原生产下一次一定启动失败。

`make_native_seed` 有独立 `validated_new_kernel_boot` 数据目的，但本候选的 `native_startup.preflight` 尚未实现完整的新 boot 一次 marker、旧历史归档和新单调时间域启用入口；生产 loader 目前仍同 boot exact only。因此永久启用和实际冷启动尚未完成，不能用该 helper 绕过当前旧 boot 的保护或宣称冷启通过。

## 已运行验证

| 检查 | 实际结果 | 范围 |
| --- | --- | --- |
| 业务集成 | 28 项通过 | Docker 中 NumPy + fake native executor；原 UI nested inference AST 实跑 |
| 原项目回归 | 237 项运行：235 通过、2 跳过、0 失败/错误 | 既有隔离套件；2 项需私有 ELF 的检查按原规则跳过 |
| C/ctypes ABI | 7 个结构的 sizeof 和每个字段 offset 全部相同 | 本机编译最终 C 头 d909177a…，无 DSO/模型加载 |
| 源码闭包 | 221 份 SHA/AST 校验通过 | 与实际 214 源底座比对，新 7 / 改 5 / 删除 0 |

28 项涵盖：SFace 三次 probe 的前两 Deferred/第三特征、晚 GIL 和解码后过期、未提交不计完成、调用者在原生释放后暂停时主任务仍运行、YuNet LATCHED CPU fallback、双 LATCHED 计数保留、原 deadline/TTL、actual UI 首轮拒绝后下一轮仍推理、unknown owner 保留、checkpoint 源存活/重复消费/pending 拒绝，以及 attach 清理失败/中断保留。不同套件有覆盖重叠，不相加作独立业务场景数。

初次 237 项中有 2 项 GUI 语音消费者检查失败：错误地用相机 214 源内的旧 `spoken_query.py` 代表正在运行的 GUI。主任务随后只读核实实际 GUI 175 源消费者 SHA `9bd7a4f6…`；最终测试容器仅对该 GUI 消费者作只读 overlay，生产相机源码没有为测试改动。原失败保留于 `test-legacy.log`；最终范围正确的结果是 `test-legacy-final.log`。其它中间测试失败/增加用例记录也保留，不追认旧结果为最终版本通过。

复现：

```bash
python3 run_tests.py
python3 run_legacy_tests.py
python3 check_abi_layout.py
```

测试使用现有离线 Docker 镜像 `xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106`，禁网、无设备挂载，不安装宿主依赖；runner 与 source 均只读挂载。最新 28/237 结果与源码 SHA 见 [validation.json](validation.json)，ABI 逐字段证据见 [abi-layout-result.json](abi-layout-result.json)。

## 尚未验证

本候选真实 AArch64 模型执行/输出等价、正常三模型业务吞吐/帧龄/CPU/DPU收益、native unknown 的实板运维、原生首次迁移、实际冷启动、真人身份精度和长稳。主任务负责目标链接和维护窗口，不能将本机 fake 成功或 DLL 编译成功写成以上项目完成。代码不主动开麦/播放，不碰身份库、GUI、运动/固件，也不启停服务。
