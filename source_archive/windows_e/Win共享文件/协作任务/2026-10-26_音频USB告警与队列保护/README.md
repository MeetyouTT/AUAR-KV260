# 音频USB专项：队列保护已启用，USB告警暂恢复

> 后续状态：用户于主机UTC约15:19报告断电。下面的服务PID和后台观察为断电前记录，不能声称仍在运行或已完成两小时；来电后重新核验。转轴最新版本和停电交接见[r15全链路复核](../2026-10-26_抽动延迟全链路复核_r15/README.md)。

用户在转轴全面复核期间另指定一个终端解决音频USB告警。音频终端只做本地代码/官方源码审查与候选验证，主端统一串行访问板卡。没有与转轴同时抢UART、另建音频设备owner或重置USB。

**已修复并上板：appsrc内部队列在下游堵塞时可无限增长。USB告警经正常PCM重建暂时恢复，但底层根因仍未确定，不能宣称根治。** 控制r14/输入v17/GUI生命周期v2保持；当前camera720342、GUI772087、音频worker772163，259组件pins。转轴自动关闭，完整STOP读回1402µs不变。

## 现场事实

MCP01实际USB身份`17ef:a03b`、full-speed `1-1.2`、xHCI slot04，播放端点`0x02 OUT`正是告警ep3索引；相机另为`1-1.3`。实物播放格式只有48kHz双声道S16LE ADAPTIVE，捕获16kHz mono ASYNC。未擅自降成不支持的播放格式、禁用语音或更改内核参数。

前轮正常GUI重连后日志暂时为0，本轮13:21～13:25 UTC再次出现`HC couldn't access mem fast enough for slot 4 ep 3`，因此前轮恢复不是根治。此前此类风暴已实际挤占journald/syslog CPU并影响视觉调度。正常空闲GUI-only重连后日志再次暂清，相机保持同owner；3秒PCM检查hw_ptr增144240、appl_ptr增144480帧，约48040/48120帧每秒，窗口0告警。

Xilinx官方同版5.15.36源码把该文本归到`COMP_DATA_BUFFER_ERROR/-ENOSR`，与带宽溢出、split transaction失败、ring underrun是不同完成码。USB播放OUT回调可能继续retire/prepare/resubmit，ALSA指针和RUNNING因而不能保证每个USB包都成功；Gst无ERROR或IDLE_READY也不是USB外部健康证明。官方出处、具体源码hash及适用边界见[USB_NOTES.md](audio_queue_bound_candidate/USB_NOTES.md)。尚未证明板端二进制与官方标签完全无差异。

## 已修复的软件缺口

原现役engine SHA`f257cf2d…`设置`block=False/max-bytes=7680`，却不处理enough-data或检查current-level-bytes。[GStreamer官方appsrc说明](https://gstreamer.freedesktop.org/documentation/app/appsrc.html)指出达到配置阈值后应用应暂停推送；非阻塞配置不会自动阻止继续积队。

新engine SHA`f5d987904aec0dc679936da27018f404f9cc77f42d300e0579a3b52a95f0655c`在每次push前检查实际内部队列。现有字节数加下一块≤7680才提交；满时不弹出真实PCM、不创建播放interval或伪造完成，短暂恢复后保持PCM及offset顺序。连续满两秒或查询异常，按既有fail流程明确报错并释放管线。保持block=False、20ms空闲静音、格式、worker/API、播放时钟和正常首音时序；没有自动重放语音或新增USB复位。

这修的是异常态队列有限性，**尚未证明现场告警发生时appsrc确曾积队，也没有用队列补丁替代USB根因分析**。

## 验证与启用

- 主机17项行为回归通过：原7项内容合同与新10项队列/保序/异常/有限等待；正常每buffer PTS、duration、PCM、首内容时刻及snapshot与原版一致。
- 原/新实际engine配受控Fake下游复现：旧版2秒100块/96000B、仍IDLE_READY；新版≤7680B，持续满后ERROR释放。
- 本机Gst1.16.3与KV260 Gst1.18.5的真实appsrc→fakesink阻塞对照均通过，不打开ALSA/USB。板端旧版最大106560B、新版最大7680B且有限超时释放；完整r2对照8.17秒，业务音频owner751765保持。它不是声学或USB传输验收。
- 首轮3.6秒自有子进程限时试验失败，进程已回收、业务未改；r2阶段计时显示独立baseline包含GI导入/初始化约0.85秒、测量至约3.26秒，probe移除/NULL约毫秒。不能把重试通过追认为原试验通过或已精确定位首次超时原因。
- 空闲时正常停止GUI751680 exit0，备份`before-audio-queue-bound-v1`后仅替换engine及其组件pin，再正常启动GUI772087。camera720342未重启、方向/边界/模型/固件未改；最终259pins及STOP收据通过。启动初期unit仍activating时核验未通过，保留原STARTING并等待，后正常READY，没有重复强杀或启动。

最终startup配置SHA`3ce0248ba168955d84876bb0b3561567edd3df4dead99d01705d4d74fba29565`。从本目录[FINAL_RUNTIME_STATUS.json](FINAL_RUNTIME_STATUS.json)核对实际版本，备份不等于已执行回退。

## 持续观察与剩余工作

新的低频只读观察进程774182，最多7200秒，保存服务PID、READY、STOP、PCM业务状态及每分钟有界内核计数；owner变化或连续读取失败会退出，无运动/重启/恢复动作。13:52 UTC取回的185秒/38个样本中，4个内核窗口告警0、读取错误0、自动跟随0、primary累计29保持、可选超限0/0。这是已完成短窗，不能提前称两小时通过。[观察回执](POST_PATCH_OBSERVATION.json)

14:05 UTC继续读取：已完成985.826秒（约16分钟）/198样本、17个内核窗口告警0，读取错误0、跟随0、primary29保持，观察器仍运行。较早14:01回执的730.619秒/147样本、13窗口0保留为历史。[14:01回执](FINAL_OBSERVATION.json)、[最新接续回执](CONTINUED_OBSERVATION.json)。旧观察753305在GUI维护期间连续3次HTTP连接拒绝后自行退出，实际935.809秒/188样本；这是有记录的维护中断，不能当新版本长稳通过。[观察器生命周期](MONITOR_LIFETIMES.json)

板卡墙钟仍显示2021年，以上交接时间使用主机UART归档UTC，观察跨度使用单调时钟；没有为本任务改系统时间。所有原故障和日志保留。正常GUI关闭会走原有STOP，报告中的“0新运动指令”指没有ARM/COMMIT/试转，不将其解释成从未写STOP。

仍需在同格式业务中观察是否复发；若复发，先收集同窗PCM/CPU/IRQ/拓扑和端点状态，不清日志或盲套quirk。未找到可直接适用于`17ef:a03b`的官方补丁证据。必要的线缆/端口/供电hub/共享上行对照须用户返场逐项进行，不将待验证实验写成供电或带宽故障结论。当前没有承诺无人自动重置设备。

转轴主线进度及行程限制见[完整复核回执](../2026-10-26_转轴完整复核与首帧修复/README.md)。Windows原交接未改，同步接收、Windows运行和真人/声学验收未代填；共享内容不含个人图像、录音、身份库、权重或虚拟环境。

## 新增复发现场记录（14:15～14:16 UTC）

音频终端实现独立[`usb_incident_capture.py`](usb_incident_capture_candidate/usb_incident_capture.py)，SHA`c7f423236faf2576a63eac753848672771e4ac0c8cb06aab78b6b7545eea3759`，15项离线行为检查通过。每10秒读取本boot末120条内核记录，按单调微秒过滤启动前/重复/未来条目，仅匹配现有slot4ep3文本；最多3次现场、间隔至少60秒，最长7200秒，总输出≤1MiB。owner/设备变化或读取错误就退出，不恢复或重启设备。

主端KV260完成明确标记为BASELINE的3秒数字快照：MCP01身份/slot对应正确，hw_ptr和appl_ptr都增144000帧，power/control为on、runtime_status为active，STOP1402不变；不是故障发生时采样，也不证明根因。[基线检查](INCIDENT_BASELINE.json)

实际20.009秒只读试运行正常结束，2次轮询、0新告警/0触发。每轮末120条包含99条历史同文本告警和21条其他记录，均按真实时间正确过滤；这证明旧告警未被当成复发，不能把截断窗口当完整告警率。[20秒验证](INCIDENT_WINDOW20.json)。它与已有每分钟窗口观察并行，仅增加低频读取，不改GUI/音频/相机配置。

14:17 UTC已启动正式有界只读记录器PID808617，证据目录`/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/usb-incidents-v1/watch-45376794182135`；启动owner核对成功，最多运行7200秒。[启动回执](INCIDENT_WATCH_STARTED.json)

同次继续取得原稳定性观察器的1711.434秒（约28.5分钟）/343样本：29个每分钟内核窗口0告警、0读错、0自动跟随，primary29/可选0、0保持，audio IDLE_READY/STOP1402。仍未达到先前约1小时55分钟的复发时长，不能称根治或两小时验收。[最新已完成观察](LATEST_OBSERVATION.json)
