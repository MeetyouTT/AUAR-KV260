# 可选DPU任务超限与音频异常诊断候选

结果：准备了默认关闭的4源码RAM观测overlay，**29项推理/调度回归通过**（原T2 15项＋新增14项），以及只处理离线数据的低频日志过滤器，**6项标准库测试通过**。本agent没有连接板卡/UART、部署、启动/停止生产服务或修改共享入口。实板操作由主任务独占执行；本包本身不是板验结论。

## 当前证据与未确定的因果

本审查读取 `/home/ghmd/aura-cpu-dpu-implementation-20261022/` 的 `longrun-failed-full.json`、`fault-snapshot.log`、`early-load-observed.json`、`audio-recovery-full.json`、`restored-load.json`，以及原音频源码和前一轮 `USB_AUDIO_AUDIT.md`。输入指纹见 `evidence-provenance.json`。

- 三模型长测失败前最后保留的健康快照在55.03秒，SFace实际完成20次、准入20次，当时最大可选区间11.028ms、无已记录超限。下一轮检查报告 `Optional task overrun: sface` 并回退。v2没有保存触发失败的那一帧health，**无法还原首次SFace超限的精确时长、真正deadline/cap触发条件、调用线程CPU或与USB异常的先后关系**。不能把11.028ms当失败执行耗时，也不能称30分钟通过。
- 回退后YuNet出现33.147ms区间、`finish_after_guard_ms=-27.502`、`waiting_primary=0`，说明已见证据对应30ms硬上限触发，而不是已记录的YOLO等待/guard迟到。YuNet自动切CPU。随后独立故障抽样证实MCP01播放端点告警持续，15.46秒整板CPU93.73%，journald11.50%＋syslogd8.98%，合计约20.47%。这是同时期故障现象，尚不能单凭它证明先后因果。
- 正常应用生命周期重开暂时清除了该次播放异常。恢复后15.17秒样本CPU55.62%、XRT任务忙时约5.00%，短窗没有YuNet真正超限。这是恢复状态，不能声称根因已永久消除，也未验收真实出声。
- **更新：主任务随后回传，双模型且SFace影子一直关闭时，YuNet又出现35.9234ms硬上限超限，guard提前约40.4839ms、无等待YOLO。该窗口最新匹配USB告警距快照约1297秒，journald没有新增重启。** 这是主任务回传证据，本agent未重新读取板卡。它表明SFace负载和新USB告警都不是每次YuNet超限的必要条件，不能把所有超限归到音频日志风暴。

目前可检验的假设包括：VART同步wait变长、调用线程被调度出去/等待GIL、提交/返回阶段CPU开销增加，或这些因素的组合。现有wall测量没有调用线程CPU拆分，无法区分。新观测用于缩小范围，不预先指定DDR/USB/模型算子或操作系统为根因。原30ms、guard、自保护禁用和CPU回退保持，不通过放宽门槛掩盖问题。

音频源码保持：`PersistentGstAudioEngine.poll()` 检查GStreamer ERROR/时钟，再向持续pipeline投递内容或静音；`stop`只清本轮，保留流。已有内核源码审查说明单ISO包失败可能不表现为GStreamer ERROR，RUNNING/PCM指针推进不能证明音频真实送达。本包不重复更换内核依据，不增加自动重开、USB复位或设备探测线程。

## 4源码与启用方法

基线是主任务T2的3源码和已验收的 `dpu_vision_schedule.py`，不是T1标定UI，也不含SFace身份迁移。所有4源码SHA已冻结在 `patch-manifest.json` 的 `source_files`，`software_tests_passed=29`；`candidate.patch` 是相对各自冻结基线的小补丁。

只有同时指定以下env才启用诊断：

```text
AURA_PIPELINE_METRICS=1
AURA_DPU_DIAGNOSTICS=1
```

缺省与任一关闭时，diagnostics不打时间戳、不分配trace、不留事件；原stage metrics行为按其原env决定。

| 文件 | 接点 |
| --- | --- |
| `pipeline_metrics.py` | 新增OptionalDiagnostics；thread-local关联调用者；单调ns与thread CPU ns；最多8条纯数值故障事件 |
| `dpu_vision_schedule.py` | 可选注入同一diagnostics；记录准入/拒绝/区间结束；原cap/guard/禁用阈值不变 |
| `dpu_vision_runtime.py` | 在原PinnedRunner的execute_async、wait前后打标；不新建owner/runner，不改变张量或预后处理 |
| `ui_camera_service.py` | 两个显式env；同一CameraState.metrics给schedule与原owner，PinnedRunner仍从owner读取 |

直接读 `health.dpu_schedule.optional_diagnostics`；也在 `health.pipeline_metrics.optional_diagnostics` 提供同一观测的独立快照。两处分别取快照，不能要求它们跨调用逐字段完全一致。区间故障记录在schedule finally持有condition时完成，再释放active并notify；health不会看到已经发布的超限计数却尚未写好的正常事件。diagnostic自身异常隔离为计数，不替换原推理错误。

无新增文件/日志I/O、后台线程、DPU owner、调度任务或高频打印。event只在cap/guard超限、原生错误或区间body异常时写入RAM；正常任务只更新计数/在途状态，不保留逐帧轨迹。

## 字段与解释边界

schema是 `aura-optional-diagnostics-1`，启动的 `started_mono_ns`、采样的 `snapshot_mono_ns`、各执行边界同用 `time.monotonic_ns`。主任务在部署证据另存boot_id、四源码SHA、候选/原unitSHA及PID，避免跨boot/版本混合。

- `counters.<yunet|sface>`：requests、admitted、rejected与disabled/active/primary_waiting/deadline四种拒绝原因；native_attempts、execute返回、wait进入/返回、native_completed、native_failed；admitted_without_native与optional_finished。
- `admitted`/原scheduler.calls表示准入，不保证运行VART；例如准入后源TTL刚过期会是admitted_without_native。`native_attempts`只表示调用尝试；`native_completed`只有wait返回status0才加。后续特征校验/目标和TTL复核仍可能丢弃，要继续对照既有features_returned/shadow.accepted，不把成功wait当业务消费或认人正确。
- `active_optional`：最多当前可选任务的阶段。phase0尚未进原生、1进execute、2execute返回、3进wait、4wait返回、5原生异常；提供最近打标的wall与**该任务调用线程**CPU时间。health线程不读取自己的CPU去冒充执行线程CPU。
- `fault_events`：最多8条，超过则淘汰最早并累计evicted_events。只含数值字段，包括任务码1=YuNet/2=SFace、可选区间起止、execute_async前后、wait前后、VART状态、实际完成数、区间wall/threadCPU、执行与等待wall/threadCPU、原scheduler占用、guard余量、等待YOLO数、cap/guard分别触发标志。

`scheduler_occupancy_ms`沿用原保护测量；`optional_wall_ms`是诊断打标窗口，起止位置略不同，可能相差少量Python/锁开销，不能强行要求相等。`execute_wall_ms`和`wait_wall_ms`是VART API边界wall时间，包含调用/阻塞、调度/GIL等；**不是纯硬件执行时间**。调用线程CPU不包含VART其他native线程、内核/IRQ、其他进程；wall−threadCPU也不能唯一归因硬件等待或调度。缺失CPU时用-1并声明支持状态，不改用进程CPU冒充。

native wait挂起时仍只能看phase3/起点；Python观测不能抢占它。仍需原进程完全退出后才能重新获取owner，不允许新owner绕过。保护门检查发生于原上下文退出，不能声称执行期间已硬实时抢占。

## 低频、限量的USB告警观察

`tools/bounded_kernel_window.py` **只解析给定JSONL和本窗口的映射断言**，不连接板卡、发现设备或自行执行journalctl。主任务每个观察窗口必须重新验证：当前boot；目标USB VID/PID唯一匹配及拓扑/当前设备地址；当前xHCI slot/context与实际Isoc OUT端点。不得固定slot4，也不得把USB device address直接当slot。mapping观测离窗口结束不得超过5秒，boot不符或映射未确认就返回MAPPING_UNVERIFIED与count=null。

建议在板端由唯一helper每≥5秒一次，RAM读取 `journalctl -k -b CURRENT_BOOT -n 128 --no-pager -o json` 的尾部，最多256条；不用 `/dev/kmsg` 高频逐条追流，也不向前反复扫描长日志。用JSON `__MONOTONIC_TIMESTAMP` 微秒和`_BOOT_ID`过滤窗口开始前/未来/其他boot条目，不能看尾部出现一条旧警告就当“现在又发生”。

解析器默认最多128条，饱和或格式缺失明确标不完整；匹配数始终只是所见条目下限，不给可靠告警频率。即使见0条，也保留usb_playback_health=UNVERIFIED，不能据此证明真实出声。每窗映射真实性由调用者的独立只读设备核验提供；工具报告mapping_verified_by_caller，不谎称自己发现/验收硬件。输出不保留MESSAGE、设备路径或任何原始日志。

## 验证和后续验收

`python3 -B run_tests.py` 29项推理/调度回归实际通过，结果见 `test-results.txt`；该日志对应四源码冻结时的29项。新增离线日志过滤器后另跑 `python3 -B -m unittest discover -s tests -p test_kernel_window.py -v`，6项通过，见 `kernel-window-test-results.txt`。复跑完整discover将包含这6项，合计35项；尚未把未执行的35项完整运行写成证据。

推理测试使用既有Vitis AI CPU容器、无网络、只读挂载和合成native/时钟；验证真实成功wait/失败/拒绝、原30ms/guard逻辑、在途观测、thread-local隔离、8条ring、未支持线程CPU、诊断错误不替换原native异常、输出量化/端口顺序/归一化不变。日志工具只用合成JSON，验证旧警告过滤、boot/设备映射、slot≠地址、饱和下限、0条不证明音频和非法输入。

主任务可先做受保护120秒YuNet-only诊断，把已有CPU fallback记录为基线状态；不同时接入SFace或标定/身份变更。捕获latest_camera_seen再回退，即便触发保护也保存完整故障trace。短诊断没触发只表示该窗未重现；不能因此改写此前失败或宣布长稳。取得wall与调用线程CPU后，再决定是否需要更针对的调度/原生wait/系统负载观察；本包没有性能优化或根因修复宣称。
