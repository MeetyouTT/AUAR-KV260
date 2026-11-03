# MCP01 播放异常审查与最小恢复候选

本目录是并行审查产物。只读检查本机回收源码和对应官方内核文件；没有访问板卡 UART、停止服务、改生产/共享入口、采集音频或图片。恢复候选仅经软件模拟，未上板。

结论：现有证据支持“单个 MCP01 播放流进入持续错误状态，正常释放/重开后暂时恢复”。首次触发原因未知，不能归因 DPU；目前已恢复时优先完成 YuNet 长稳，不为本候选再次切换界面。

## 实测边界

下列板端事实由主任务提供，并非本审查重新测量：

- MCP01 `17ef:a03b` / `1-1.2` / slot04，告警 `ep3` 已由接口和上下文确定为 `0x02 / Isoc OUT`；故障时播放 RUNNING、hw_ptr 推进、delay/avail 变化。
- 故障时 `/dev/kmsg` 一次抽样收到 67,020 条警告/8.42 秒，同时 1,597 次 overrun；读取本身约占板端 11% CPU。这里只证明持续高密度异常，不能据此计算可靠告警频率或纯运行 CPU 基线。
- 原应用正常关闭后 3.1 秒无匹配警告，同版本重开静音保活后 8.1 秒无匹配警告；随后 15 秒 CPU 约 63.28%。配置和用户偏好保留。
- YuNet 恢复试运行约 5 分钟时未再发现匹配警告，另一个 15 秒窗口 CPU 约 55.09%、DPU 忙时约 4.66%。这些窗口不同，不能直接当作严格迁移收益。

恢复消除了当前症状，不证明根因永久解决，也没有进行真实听感/播报验收。

## 已核实的源码路径

本地 `build/prepared.json` 记录 commit `19984dd147fa7fbb7cb14b17400263ad0925c189`、release `5.15.36-xilinx-v2022.2`。本审查将 Makefile 与下列三文件逐字节对照官方 commit，四文件 SHA256 全相等，见 `kernel-source-provenance.json`。同名 `xilinx-v2022.2` tag 内容不同，不应误用。源码身份不等于已证明正在运行的内核二进制采用完全相同构建输入。

1. `xhci-ring.c`：L2807 的完成码是 `COMP_DATA_BUFFER_ERROR`，状态设为 `-ENOSR`，属于不改变端点状态的分支；与 USB 带宽超额、ring underrun 是不同分支。isoc 单包落到错误状态，但 L848 的清理流程将 ISO URB 整体状态置零。警告不能单独证明可用 RAM 不足。[Xilinx 固定版本源码](https://github.com/Xilinx/linux-xlnx/blob/19984dd147fa7fbb7cb14b17400263ad0925c189/drivers/usb/host/xhci-ring.c#L2807)
2. `endpoint.c`：L510 的回调只对 unlink/disconnect 等终止码和端点停止作退出处理；OUT 路径调用 retire/prepare，再提交 URB。单包失败不必自动停流；提交失败才触发 XRUN。因此重复警告、RUNNING 和 GStreamer 未报告 ERROR 可以并存。[Xilinx 固定版本源码](https://github.com/Xilinx/linux-xlnx/blob/19984dd147fa7fbb7cb14b17400263ad0925c189/sound/usb/endpoint.c#L510)
3. `pcm.c`：`retire_playback_urb` 不读取单包错误；`urb_ctx_queue_advance` 在排队数据时推进 `hwptr_done`，pointer/delay 是软件进度/估算。播放指针或 sink 时钟推进不等于扬声器成功收到音频。[Xilinx 固定版本源码](https://github.com/Xilinx/linux-xlnx/blob/19984dd147fa7fbb7cb14b17400263ad0925c189/sound/usb/pcm.c#L1236)

回收应用的 `PersistentGstAudioEngine.poll()` 只看 GStreamer ERROR 和时钟，`device_ready` 实际表示已经过一秒 warmup。`stop` 清本轮内容而继续静音保活，这是既有设计，不能用 stop 代替关闭/重建流。

## 恢复候选和接入条件

`idle_pipeline_recovery.py` 是独立 mixin 候选，保留原 stop 行为，新增显式 `recover_idle(...)`：

- 在播放工作线程执行；只有拥有者确认对话和采集都空闲、无待处理命令，且 engine 无 active/paused/audible/queue/intervals 才接受。
- 原 token 必须精确匹配，恢复 token 必须加一；清失效参考队列、旧 bus、PTS 和本轮状态，关闭旧流，再建同设备/格式 pipeline。参考 sequence 保持递增，增加 pipeline_epoch。
- warmup 期间拒绝新 play/stream，8 秒未就绪则失败并释放；工程初值限制为至少隔 60 秒、10 分钟最多两次，防止重开循环。
- `READY_UNVERIFIED` 只表示应用 warmup 完成；`usb_playback_health` 始终保留 `UNVERIFIED`。异常和关闭清未交付参考，不宣称已有回声参考继续有效。

仍缺的生产接入：工作进程协议与 facade 原子更新 token；拥有者冻结新轮/采集并确认旧轮结束；AEC 消费者在 epoch 变化时清状态并重新建立参考；检查 NULL 释放是否完成及独占设备释放；恢复后用独立证据判定 USB 健康。不能直接把 mixin 拷入生产即视为这些条件已满足。该接口不重启 UI，不操作 USB 总线。

若以后接自动检测，低频、限量地统计**当前重新解析设备对应的播放端点**完成码，要求多个窗口持续异常才提出恢复；不要固定 slot04 到以后每次枚举。检测达到读取上限/丢失序号时标记“观察不完整”，不要伪报零异常。避免逐条长期解析高密度日志制造新 CPU 瓶颈。仅 sink/hw_ptr 停滞可作为另一异常信号，不能成为唯一信号；CPU 高也不单独触发恢复。忙时只记录待处理故障，在业务状态机正常取消或结束后再恢复，不丢正在回答的 PCM。

## 验证与下一步

`python3 -B -m unittest -v test_idle_pipeline_recovery.py`：12 项软件模拟通过，涵盖保留 stop、忙时/代次/采集门控、时间基/参考失效、warmup 超时和 start 失败、恢复限次、close 释放。没有加载 Gst、打开设备或合成新音频；这不是板级恢复验证。

当前继续主线长稳，记录告警是否复现。复现时先用保守采样保留 boot/设备映射/状态/时间窗口及监控自身开销，再评审本接口是否已满足接入条件；只有正常流生命周期无法恢复时，再单独调查内核/USB/供电/总线问题，不能直接复位共享 USB 控制器。
