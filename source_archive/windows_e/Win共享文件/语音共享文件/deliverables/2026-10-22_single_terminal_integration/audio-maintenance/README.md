# 音频维护接线审查（独立候选，未部署）

2026-10-22。范围：只读已回收的实际源码，设计可保持 GTK/UI 与相机进程的音频恢复。本文不把 MCP01 的首次故障原因、恢复后长期稳定或实际出声判为已解决。没有操作 UART、板卡、USB、生产源码或共享目录。

**单终端接续更新：引擎层已完成20项软件测试，最终源SHA为`001898f491e026120f668580d0547698bfcfb97d6e0ceb181d40e6e61a866f30`。** 主任务在板端GStreamer1.18.5使用合成静音数据和`fakesink`完成旧管线NULL确认→新管线预热→关闭、重复请求、参考代次及原stop保活检查；没有打开ALSA/MCP01或改变生产。这个结果只验证引擎与本板GStreamer生命周期，尚未完成UI所有者屏障/IPC/AEC接线，也不代表MCP01故障修复。

首轮15项检查中发现重复request未幂等和关闭后stream未拒绝，已修正；随后补充原生poll晚于预热期限返回及poll异常时请求NULL并保持失败态的检查。最终20项覆盖这些边界、异步NULL/超时、关闭失败不创建第二对象、token/有界32请求台账、防重放/冷却、owner线程限制、参考代次与late-ready。重复请求只确认同一事务的受理结果，不重复状态切换；不同内容/旧事务拒绝。普通stop仍保留原管线。

测试命令：`python3 -B test_idle_maintenance_engine.py`。共享交付会附两份与实际版本SHA匹配的引擎源码用于复现，也可用`AURA_AUDIO_SOURCE`指定实际源码根。旧`engine-test-results-initial.txt`保留失败证据，最新结果在`engine-test-results.txt`。本目录最初由agent只做只读审查；以上修改/板端检查由主任务后续单终端完成，下面原审查内容保留其当时范围。

**结论：已有独立播放子进程，能够设计“只关闭并重建音频 pipeline”的维护入口；目前的 `IdlePipelineRecovery` 只是引擎候选，缺少上层原子门控、IPC 确认和 AEC 代次处理，不能直接部署。** 最小 V1 仅允许本来就空闲、无录音/转写/会话请求/参考订阅的状态；忙时拒绝维护，不取消用户正在进行的会话。首版不会自动重试、轮询内核日志或改动现有 `stop` 静音保活语义。

## 已确认的实际接线

源码根：`/home/ghmd/aura-audio-recovery-20261021/live-source`。更早的恢复候选在 `../aura-audio-recovery-20261021/audit`。

| 实际文件与入口 | 当前行为 | 维护接线需要补的条件 |
| --- | --- | --- |
| tools/board_avatar_gtk.py:177、185、209 | 分别建立 GStreamerAudioOutput、ChannelConversationJobs、AvatarRenderWorker；播放设备操作已经在子进程 | 保持原 output 对象及 UI，不从 GTK 线程同步等待 native GStreamer |
| tools/gstreamer_audio_worker.py:62、82 | stdin 线程写入容量32队列；GLib每10ms最多消费16条，再poll/输出状态 | recover 必须成为同一 GLib 执行线程的串行命令；队列为空只是瞬时状态，不能替代生产者门控 |
| tools/gstreamer_audio.py:35；tools/realtime_audio.py:55、75 | send_lock只保护写管道；play/stream/stop的token递增与状态修改在写锁之外 | 控制入口到token变更及命令入队必须按同一所有者顺序执行；不能将send_lock误当完整生命周期互斥 |
| tools/realtime_audio.py:26、33 | reference消息在普通state的token筛选之前转交 | worker实例/管线epoch必须单独校验，不能假设token已挡住旧reference |
| tools/gstreamer_audio.py:23 | reference回调仅收到pcm/at/sequence | 新管线epoch目前无法传给AEC消费者；最小V1要求没有reference订阅者，通用版本必须改消费者 |
| tools/gstreamer_persistent_engine.py:77 | release设置NULL后立即清引用，未检查状态转换返回或实际完成 | 新实例创建前核实旧pipeline已NULL；FAILURE/超时保持维护失败，不允许两个设备实例并存 |
| tools/handsfree_recording.py:162、174、224 | cancel影响监控与偏好；每tick前后可自动启动采集 | 维护要独立barrier，不能借cancel偷改用户偏好；全部自动采集入口需服从barrier |
| tools/barge_in_recording.py:23、80 | barge capture可独立存在，也可转交给正常capture | 只检查recording_state或controller.phase不足；capture、barge_capture、交接/语音证明均需纳入 |
| tools/streaming_controller.py:38 | channel start能创建新轮并begin_stream，后续包按owner/generation匹配 | 转写/流式请求及结果消费必须同属维护barrier，不能只禁录音按钮 |

上述行号是本次已回收源码，不代表共享业务目录版本。

## 最小 V1 的接线顺序

1. 在 AvatarRenderWorker 的现有命令所有者线程处理 `audio_maintenance`，先建立维护屏障，然后在该线程读取并判断全部本地状态。GTK显示值只是快照，不能作为授权。屏障期间手动开始、自动重启采集、barge采集、转写提交、channel开始、示例播放均拒绝；取消与关闭仍可执行。
2. 第一版只接受已经空闲：controller.phase=IDLE、无pending/ready/audio_waiting/stream；output非active/paused；capture与barge_capture不存在；无未消费utterance/语音证明；转写队列/正在执行请求/channel结果队列均为空；无reference_handler。monitor_enabled=true也要在屏障内阻止自动采集，保留其原值及磁盘偏好；若无法证明无异步工作，拒绝。
3. 在同一命令所有者中分配request_id、记住worker_instance、expected_token、new_token=expected_token+1。修改facade token与发送维护命令是一次序列化动作。生产者完成屏障后再发命令；worker还要复查其active/paused/audible/queue/intervals与token，不能信任上层boolean。若有早已排队的内容，拒绝并报告原因；不能默默丢当前用户语音。
4. worker先确认请求，旧pipeline请求NULL；使用非阻塞状态查询在后续tick核实NULL完成，之后才创建新pipeline。NULL失败或不能确认关闭时保留错误状态。不能单靠`set_state(NULL)`的Python调用返回就宣布PCM已关闭；native调用本身若卡住，外部watchdog才能界定超时。
5. 清旧reference队列、内容时间/next_pts/队列及intervals，推进pipeline_epoch，保留全局reference_sequence单调。重建后继续原静音保活，tick执行暖机；到达device_ready只标记`READY_UNVERIFIED`，不写成真实扬声器已出声或USB端点已健康。
6. 父进程只接受当前worker_instance/request_id/new_token/pipeline_epoch的应答。重建期间丢弃旧epoch参考与旧普通状态；新epoch参考也只有在消费者准备好后才可传递。最小V1因没有订阅者，无需伪造AEC reset成功。
7. worker就绪后，确认新的空闲状态、无捕获/异步请求、独立低开销端点告警观察，再解除屏障。保留原monitor/auto模式及偏好；重新允许自动逻辑按原条件启动。真实出声/录音另做业务验收，零内核告警也不等价声学正确。

## IPC 与超时约定（拟议，尚未接入）

请求包含 `type=recover_idle`、`request_id`、`worker_instance`、`expected_token`、`token=new_token`。worker状态回执统一带上述关联信息、`pipeline_epoch`、`recovery_state`、枚举型reason；日志只保留这些状态，不附音频、转写文本或用户名称。

状态顺序为 `REQUESTED -> CLOSING -> WARMING -> READY_UNVERIFIED`；任何阶段可以进入 `FAILED_HELD` 或 `CLOSED`。超时后保持屏障，晚到ready不能重新放行。close始终可达；普通stop仍只停本轮内容并维持静音pipeline，不能借stop解除维护屏障。无需把USB告警条件写进底层engine，这应由独立控制器判断。

暂用关闭确认2秒、暖机8秒、父进程总期限12秒作为待验工程参数。同步pipe.write/flush也可能阻塞，父进程不能把写操作与长等待放到GTK线程，且不能在持有生命周期锁时等待读线程。若worker native调用不返回，仅允许有界结束**已记录的该音频子进程**并等待退出，确认旧设备所有者退出后才可新建；禁止按名称pkill或重启整个UI作为自动兜底。现有SelectedAudioOutput.close的send本身可能阻塞，其后wait超时并不覆盖send，所以不能直接声称已有完整有界超时恢复。

重复request_id应返回原状态；不同request_id在维护中拒绝。工程限频可沿用旧候选60秒冷却、10分钟最多2次，但首版显式触发，不增加自动故障watcher。使用工作线程单调时间，不依赖板上错误的墙钟。

## 后续支持活跃 AEC 的附加工作

不允许在仍运行的capture/AEC上仅清参考队列继续使用旧filter。需要停止采集并确认线程退出、解除旧订阅、清AEC/Speex状态和参考序列/时间映射、以新epoch创建或reset消费者、重新订阅，再按新参考足够新鲜/连续的条件允许采集。远端在途ASR/对话请求必须取消或等其归零，结果按generation丢弃；网络取消完成不等价本地结果队列为空。此项必须结合实板实际 `barge_in_capture.py` 和 `echo_cancel.py` 证实，当前不作为V1已实现能力。

## 接线验证与实板准入

软件验证必须覆盖：维护与play/record/auto-tick/channel-start同时到达；前置旧命令/迟到结果；token重复/错误worker实例；NULL返回FAILURE或ASYNC；暖机/pipe阻塞/worker退出；超时后的晚到ACK；cancel/close可达；监控与偏好不变；普通stop继续保活；旧epoch参考无法进入新AEC。

实板先只读核对当前源码SHA，再执行原本空闲且未订阅参考的单次维护：UI/相机/Xserver PID保持，只有原音频拥有者被维护；原配置/偏好SHA保持；旧PCM关闭、新PCM正常唯一打开；无新端点告警；最后按实际麦克风及扬声器验收。即使全过，也只证明受控恢复可用，不证明USB初发根因解决。当前没有部署、没有实板维护结果、没有新的听音/录音验收。

## 当前待补源

为避免用共享旧版冒充活动版本，已请主任务独占UART从实际runtime根回收：`tools/board_avatar_worker.py`、`tools/board_recording.py`、`tools/barge_in_capture.py`、`board/runtime/audio/echo_cancel.py`、`board/runtime/audio/channel_jobs.py`。回收后补充所有者线程、跨线程事件入口及可实施补丁的精确接线点。已有引擎mixin保持原件，不写覆盖补丁、不宣称已完成恢复接线。

后续已回收上述5份及`board/runtime/audio/transcription.py`，共6份，见`actual-source-manifest.json`。原件保存在私有actual-source，不以共享旧版代替。实际所有者为AvatarRenderWorker，转写队列另有condition/active/results；因此单靠公开pending=false或暂停录音按钮无法证明维护窗口成立。引擎层测试完成后仍需显式上层准入与worker回执，未将本mixin导入生产。
