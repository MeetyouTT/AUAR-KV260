# 运行状态复查：YuNet 再次超限并退回 CPU

2026-10-23 UTC 主机时间核查。此记录更新前一轮协调切换交付中的当前健康状态；原120/600/1800秒通过和实际启用通过仍是历史实测，不能代表后续长期无故障。

当前同boot `7924ac9f…`、相机198117及unit `af337bce…`保持。YOLOX-Nano仍在DPU运行，健康接口累计约9.95Hz，3秒观察30帧推进；YuNet现为`CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN`。正式SFace仍`WINDOWS_CPU_SFACE_ORT`，音频`IDLE_READY`。本轮仅只读取证和文档更新，没有重启服务或修改运行配置。

YuNet在相机进程启动后2263.609秒（约37分44秒）触发一次硬占用超限：scheduler occupancy31.340203ms，原30ms上限；guard未超，VART native status0、native_completed1。execute墙钟30.547485ms/调用线程CPU1.011459ms，整个可选区墙钟31.352864ms/调用线程CPU1.801477ms。调用线程有自愿3/非自愿1次切换；不能由这些数据唯一归因于GIL、Linux调度、VART内部等待或硬件。该线程CPU不包含其他runtime/kernel线程。

内核最后5000条记录的单调时钟最早为12398.3204秒，覆盖当前进程开始及故障±60秒窗口；匹配`WARN: HC couldn't access mem fast enough`的新增记录为0。故障证据不支持把本次归为已观测的USB告警洪泛。逐发布gap累计仍0，主周期超限累计仍1，YuNet可选超限累计1且disabled=true。

两次约3秒整板CPU点测65.08%与70.57%，均在YuNet已退CPU后，仅短窗现状，不与此前约55%不同输入窗口计算收益。未重新采集DPU busy；之前4.934%是双模型DPU历史窗口，不能当作当前值。板端实时时钟不可靠，故障定位使用同boot单调时钟及进程启动tick，日期以Ubuntu主机为准。

当前结论：DPU迁移部分完成、长期稳定性未完成；CPU完成过调度/失败恢复等阶段优化，整板同输入性能收益尚未验收。下一步先定位并解决YuNet长尾、设计有界恢复并延长验证，再接入SFace独立INT8身份域和真人精度；CPU预处理/拷贝/后处理以剖析结果推进，最终同输入比较CPU占用、延迟、吞吐、DPU任务忙碌率和身份准确率。30ms/5ms原保护仍在。

证据见`current-status.json`（含硬超限事件）、`fallback-cpu-first-sample.json`和只读探针`optimization_status_readonly_20261023.py`。原始UART、图像、音频、身份向量、库和偏好原件未共享。Windows同步接收未代确认。
