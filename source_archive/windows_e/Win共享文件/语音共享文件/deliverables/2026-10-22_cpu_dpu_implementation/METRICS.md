# 分段性能记录候选

`metrics-candidate/aura`含3源码：`pipeline_metrics.py`、保留版本的`ui_camera_service.py`埋点、`dpu_vision_runtime.py`埋点。默认关闭，仅显式`AURA_PIPELINE_METRICS=1`才聚合；本轮没有改生产单元启用它。`combined-candidate/aura`合并标定路由后的11源码，同样未部署。

计时使用monotonic_ns；每阶段累计count/total/min/max/mean，每阶段最多保留最近256个时长，只对最近窗口给P50/P95。它不是完整生命周期P95，更不是每5秒health快照的P95。固定阶段白名单、仅数值、加锁有界更新；不保存帧、向量、名字或目标ID。聚合不占用可选DPU执行区间，已有输入/输出计算语义保持。

| 阶段 | 含义 |
| --- | --- |
| capture.callback_prepare | 从appsink回调拉取/复制到镜像BGR准备；不是相机曝光或驱动全链 |
| yolo.schedule_wait | 进入主检测调度到获得执行区间 |
| yolo.native_and_decode | 现有native调用含CPU预后处理与DPU；不能拆作DPU核心时间 |
| yolo.track / yolo.path | 跟踪处理及现有检测到发布路径 |
| yolo.source_age_at_start / publish_source_age | 沿用appsink-dequeue单调时间的源帧龄，不代表曝光时延 |
| preview.render_encode_publish | 绘制、raw/JPEG发布；不是GUI显示消费或物理屏幕显示 |
| yunet/sface.allocate / slot_wait | 输出分配和进入可选区间时间；拒绝准入不记执行完成 |
| yunet/sface.execute_wait / dequantize | VART提交等待返回及输出反量化；执行时长不等于XRT动态忙时 |
| sface.normalize_input / validate_output | 输入RGB归一化与输出形状/数值检查 |

未覆盖：YOLO native内部逐段、可选模型量化包装、完整脸部检测/对齐、最终身份结果消费、传感器曝光、GUI物理显示。没有声称T2所有阶段已经完成实板测量；先补明确边界和有界工具，后续在隔离候选启用并验证观察开销。

本机标准库统计5项通过；CPU容器里5项测量运行器/相机合约和5项原运行器回归通过，验证INT8输出不变、VART端口顺序、拒绝准入不调用native、聚合发生在区间释放后、默认关闭。合并候选又通过标定46项与上述10项。板端仅执行标准库数值模拟，未创建runner或接入相机。

现有T3实板采样用5秒health和/proc计数，独立记录真实完成/拒绝/失败、相机CPU核秒/RSS/线程数；CSV和摘要由`source/summarize_observation.py`导出。原15秒XRT采样器有独占检查、finally停止及计数冻结复核，独立于本埋点候选。CPU以四核总量100%标注，频率用观察窗口内累计计数差，不把冷启动后的进程平均Hz当稳态速率。
