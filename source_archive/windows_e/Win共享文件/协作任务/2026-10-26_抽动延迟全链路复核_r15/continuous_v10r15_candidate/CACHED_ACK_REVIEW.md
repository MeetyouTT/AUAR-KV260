# r15：对疑似过期的缓存ACK只重读一次

本文件记录独立控制审查子任务。未接板、UART、HTTP、MMIO，未修改r14或原固件。主端负责本候选`run_face_motion.py`和writer，本文只冻结`deadline_driver.py`、新针对性测试及回放。manifest未由本子任务修改。

## 实测证据与不能推断的地方

实测文件`/home/ghmd/aura-pan-board-20261024/uart/20261026T144445.927911Z-r14-user-twitch-delay-full-trace/response.json`记录234条接受指令、99次目标变化、14次ARM，范围1402..1449，最终1426/STOP。用户明确反馈仍抽动和响应迟。

本轮结束heartbeat46848382、elapsed28.036秒，对应开始约46820346。timeline初段混有上一轮同r14的旧GUI报告，不能按同boot/manifest就计入本轮；final 28条事件完整：13次越线ARM、1次区内预ARM，对应5次SOURCE_HORIZON_ENDED、4次SOURCE_SUBMISSION_EXPIRED、3次SOURCE_LEASE_EXPIRED、1次CONTROL_TICK_LATE及1次OPERATOR_STOP。bounded live采样加final只能重建220/234命令，早期14条未保留，不能冒称全命令轨迹重建。

两次`delayed_submissions`中，最后一次post-ACK检查时now=46832.37168031、source截止46832.556，缓存readback lease_left=185，二者相加仅高于截止0.68031ms。这个数据支持排查缓存时间错配，但缺少ACK原采样时刻，**不能据此证明该实际报警一定是假阳性**。另外两次早期提交失败附近，旧命令租期本已接近结束；3次flags64/reason4同owner过期是真实硬件许可丢失，不能绕过。

本轮publish最大57.868ms、总控制轮最大101.135ms，出现一次CONTROL_TICK_LATE；reader排队最大57.794ms。这些为主端迁走文件IO的依据。7.7秒无可接纳人脸不是可以延长旧源来补的空档。

## 可复现的软件缺陷

父driver读到ACK后，Python可能被暂停。旧外层把较早ACK的`lease_left_ms`加到更晚now，可能虚构一个更晚的硬件截止。

独立20ms PWM latch＋独立倒计时模型：COMMIT10.000、硬件截止10.230、原图截止10.250；ACK快照之后暂停25ms或80ms，旧r14误报SUBMISSION_TOO_LATE并STOP。实际硬件截止没有延长，第二帧已经开始输出新目标；这是明确可重复的误停逻辑，不是声学/机械仿真结论。

## 最小修复

若缓存ACK计算疑似越过原图/锚截止，且当前尚未超过原20ms余量截止，仅额外读取一次status：不写COMMIT、不重设lease、不更新观测时间。重新核对session/epoch/ACK/target、flags15/reason0及正剩余lease，配当前时间重新检查原截止。符合才保留接受，并将新读回交给session。

若重读期间真到期，则同owner精确expiry返回SOURCE_LEASE_EXPIRED并STOP；其他context或flags异常返回UNKNOWN/ACK_MISMATCH并STOP。读取异常先STOP再原样抛出；STOP本身失败不会伪装成功。第二次读也耗时过大或仍不能证明原期限，则继续拒绝，不循环重试。首次23ms lease、原250ms图/500ms锚、20ms提交余量以及最终native写入竞态Q09声明均保留。

新增诊断：`readback_rechecks`、`readback_false_alarms_avoided`、`last_readback_recheck`，包含两次有界数字读回/检查时刻与原截止。只有真的fresh读回证明合法才增加avoided；不是每次重查都算修复收益。

## 验证

14项新针对性回归＋原115项共129项通过；主端另有writer测试，整合总数以其回执为准。8组成对回放覆盖25/80ms缓存暂停、真实25/300ms native写入迟到、真实源过期、fresh再暂停、普通及时路径；仅缓存误停场景改善，所有真实截止违规仍STOP。

`CACHED_ACK_REPLAY.json`保存对照。板端无运动隔离可运行`replay_cached_ack.py --baseline-root OLD_R14 --candidate-root NEW_R15 --driver-root ORIGINAL_DRIVER`，并把`test_cached_ack_freshness.py`与脚本置同验证目录；脚本仅创建Fake寄存器，不打开transport或设备。它仍不能替代下一轮真人验收。

## 主端writer修订复核

初稿曾复现：控制循环已有异常、STOP成功后，finally中的显式publisher.close错误覆盖原控制错误。该问题**已在当前r15由主端修复**：finally先保存pending_control_error，STOP后调用close_after_stop；writer错误单独记录，原错误存在时抛回同一对象，清理失败跳过最终STOP proof。新的9项writer行为测试独立重跑通过；按实际finally顺序、真实LatestReportWriter故意注入写盘错误复核，也保留了原ValueError、STOP已确认且未写最终proof。主端整合总数已为138项，不应将初稿反例描述成当前仍有的缺陷。

## 实测首个不同目标提交时间

`r14_timeline_audit_20261026/FIRST_SUBMIT_DELAYS.json`用“同epoch快照的ACK数等于保留下来的完整命令前缀长度”作为首命令证据，只纳入14段中可证明的10段（1、2、3、6、7、9、10、11、13、14），其余不从缺失命令猜首ACK。

这10段ARM到首个不同目标的**提交起点**为197..338ms，中位256ms。`command_trace.mono_ms`位于driver.submit之前，不是ACK完成时刻或机械首动时刻；上述数字因此是对应输出延迟的下界。首次本轮右越界输入接收至首提交为268ms，从该首次输入的原捕获时刻至首提交为363ms；用户可能在窗口开始前已越界，所以这不是精确“穿线瞬间到机械首动”测量。

220/234保留命令样本的轨迹速度绝对值中位8.0946µs/s，最大13.9123µs/s；其中不同目标样本速度中位9.2701µs/s。它们是软件轨迹速度，不能当机械角速度或宣称遗漏14条没有更高速度。

当前静止起步的零速度/零加速度、jerk800与加速度100约束下，理想连续轨迹仅走到0.5µs整数舍入阈值的理论下界约155.763ms；尚不含确认、新图等待、tick量化、native提交、下一PWM帧或实际舵机死区。说明修复误停和文件IO能消除一部分额外拖延，但不能把既定平滑起步约束下的首次响应宣传为零延迟。没有因此擅自调快或放宽本轮参数。
