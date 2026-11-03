共存probe v2：仅通用解码诊断与启动时序修复；未上板、未跑模型

父源coexist/probe_coexist.py SHA b252e7cc3d09f84557a580bae13356e99f6e3e1c6037271e672dd1c203a45570完整保留，本目录是独立新文件。root唯一设备操作者。本次不要求再给准确率较低的小CTC安排板测，可将诊断协议和sink复用于后续Transducer；各新模型构造/官方flush仍须独立审阅，不能照搬CTC零尾。

此次失败的可复核结论
actual_coexist_1793447410990795800.json：48960samples=153个offer成功；16000samples=50帧未ACK；因此只ACK103帧/2.06秒，约第154个输入帧/3.08秒触发固定1秒积压上限。raw8queue峰3无error，前端threadCPU均值17.3ms。oldest_ack_max843ms是已完成ACK的最大年龄，不是当时最老未ACK年龄。
0.64秒模型块不等于始终扣0.64秒credit：未ready的20ms帧立刻ACK；只有触发decode的一帧及随后到达的帧在等待。不能简单相加0.64+0.4就解释本次溢出，也不能仅凭一次失败断言整机CPU不足。可能是decode成本/冷执行/缓存竞争/调度/发送或ACK推进，需数值区分。

最小变化
1. 新增DECODE_PROGRESS=7诊断帧。每次原decode_stream前后各一次，只有固定phase/序号/计数/样本游标/单调时间/wall/processCPU数值。父严格验证字段、finite、顺序和样本游标；这些消息绝不返credit、不推进ACK序号、不产生转写或结果权力。原ACK仍原4B sample count，队列/优先级/线程/模型/阈值全部不改。
2. 父保留最新active phase和已完成decode总次数、wall/CPU总和、last/max及输入序号；没有解码文本或无限日志。当前最老pending年龄、pending帧数与已ACK峰值分开。溢出/首次失败时冻结一份数值快照，晚到decode/ACK不能覆盖该at_failure；公开快照仍可显示最新状态便于核对。
3. 原代码在GTCRN构造/32帧预热前就启动3秒read超时线程；新版本先完成gate构造，再设置3秒超时并启动sink reader。它修复潜在启动误报，本次已有103ACK，不能拿它冒称本次溢出的确定根因。模型构造失败不启动reader，reader构造失败关闭自己新gate。

准确公开字段
ctc_transport.decode_diagnostics：
  decode_metadata_available；worker_decode_calls；worker_decode_wall_total_ms / worker_decode_cpu_total_ms；
  worker_decode_wall_last_ms / worker_decode_cpu_last_ms；worker_decode_wall_max_ms / worker_decode_cpu_max_ms；
  worker_last_decode_sequence；oldest_pending_current_ms；pending_frames；
  active_decode；active_decode_sequence；active_decode_index；active_decode_phase_age_ms。
ctc_transport.at_failure：首次失败时同一结构的有界数值快照；正常为null。
active phase年龄从worker发开始通知前算，包含该开始通知的IPC；已完成wall/processCPU只包围原decode调用，排除通知send与输入等待。processCPU不等于精确调度等待；wall较大CPU未同步增长提示调度/阻塞，CPU也增长则提示计算/内存/冷执行成本，仍须结合受控环境。
失败快照反映父端当时已经收到的最新通知，不是跨进程强同步镜像；若DONE通知仍在传输，计数可能晚于worker实际完成，不能据一个active标记排除IPC/GIL调度延迟。

范围
沿用原public guard、明确RAW20ms输入、原combined GTCRN/Silero、8帧capture、固定16000sample/1秒ASR在途credit、完整END/ACK、0.66秒模型零尾、独立1线程worker及自己的有限关闭流程。无生产改动、无GUI/身份/视觉降级、无新缓存/ticket/Store/admit路径。
按root最新收敛要求，本版本未新增整机PID采样器或队列趋势线程；若后续Transducer仍需资源归因，可由root使用已有metadata CPU探针与相同输入窗口配对，不必在此增加调度负担。

验证
17主测试/8子例通过。保留原10项socket/RAW/单fake recognizer测试，新增严格decode metadata/不返credit/最老pending真实年龄/失败快照不被晚包覆盖/无正文泄漏/启动顺序/构造失败收尾；fake worker实际跑协议并核2次decode通知。模型、设备、真实库、服务均未执行。
原root调用只需换成本目录新文件与新SHA；参数/依赖不变。不替换b252路径、原失败回执或生产源码。
