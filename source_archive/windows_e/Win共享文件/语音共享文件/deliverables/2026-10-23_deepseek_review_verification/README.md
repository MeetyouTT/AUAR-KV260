# DeepSeek审查结果复核：有效发现、误读与第三次故障

性质：对用户回传的DeepSeek审查做源码/已有证据复核。没有连接板卡、部署、运行新DPU推理或执行原报告建议的实验。源版本仍为a29082ba…，第三次故障依据已有只读交接。

## 结论

报告找到了真实的可用性和计时边界问题，可以作为修复输入，但尚未定位YuNet长尾唯一根因，部分代码事实和实验建议需要更正，不能直接照单实施。

现场已新增第三次82.926870ms超限并越guard，YuNet处于CPU fallback、恢复LATCHED；因此此前对前两次轻微超限的“可能工程可接受”判断不能扩展到当前状态。native仍正常完成/status0，但保护期限已越过。当前已有证据没有证明相应新增YOLO业务超期；guard越界、native失败和实际业务影响分别记录。

## 源码直接支持的发现

1. `DpuVisionSchedule.optional`先计算elapsed，再做统计/恢复/诊断finish，最后active=None/notify_all。记录的scheduler occupancy与真正释放执行权之间有未覆盖的尾部；应补充精确释放端点、评估把诊断聚合搬出关键区，但保持故障判定与恢复状态原子性。
2. 正式SFace disabled后的持续可用性/ready/缓存结果传播确有缺口。已有另一工作包的4源候选92软件与16板端隔离检查通过，尚未部署；应合并该候选，不重复开发或覆盖。
3. `FaceTargetService.work`外围except捕获原生异常后退出worker，直到受控重建。这个fail-closed路径能避免未知错误后继续复用设备/缓冲，不能简单改成catch后无限继续。应先区分已完成失败、未提交取消和完成状态未知，再设计健康可见性与有界监督恢复。
4. estimate只在偏差后上调、最高30ms且未衰减；health在scheduler condition内调用diagnostics.snapshot；fallback缺少专门次数/耗时指标。这些源码事实成立，是否构成主要瓶颈仍需要测量。

## 需要更正的主要说法

| 报告说法/建议 | 对照源码与证据后的结论 |
|---|---|
| 返回侧probe在取now之前，execute_wall包含该采样 | 错。pipeline_metrics.py先在196行取now/cpu，197～199行才做return侧sample。已用真实类＋3ms假probe验证返回时间戳不含return采样；当前实板读回依赖SHA也与审查参考完全相同 |
| A段可能包括shape校验与4个np.empty | 错。runner的校验和np.empty在80～89行、进入slot在91行，发生在获得执行权之前。A段应查诊断begin的锁等待、yield链和start marker等，输出预分配不能直接解释A的22.7ms |
| B的30.22ms全部在execute_async内部，短wait证明此前已完成 | 表述过强。execute marker到return marker之间还夹有start marker收尾、pre_execute和Python/native绑定边界；短wait也可能完成最后一点工作。必须结合匹配VART版本或native入口计时，不能当纯native/纯硬件时间 |
| optional_wall与occupancy的差，能直接算出起点差和finish尾部成本 | 不能。两端都不同，差值为结束偏移减起始偏移。A的-0.490ms不是单独测得的begin延迟；wait_end到optional_end也不含整个finish主体（finish在取now后还有锁和聚合）。只可证明边界不一致，不能精确归因尾部成本 |
| 最长正常SFace trace的wait为0.096ms，证明两模型同一长尾分布 | 原值为0.076061ms。28.172792ms execute marker墙钟与YuNet B形态相似是线索，单条极值不能证明同一分布或相同根因 |
| GIL启动器PIN失效、需要改为ui_camera_service入口 | 错。现役入口board_camera_motion.py会调用ui_camera_service.main；文件SHA1e0e6f…与包装器PIN、正式process_setting一致。实际记录为1ms且已运行，勿重新pin成另一个入口绕开motion feed安装 |
| 实验从默认5ms改1ms | 当前已是1ms。已有5/1ms和CPU亲和性历史实验，新的对照要明确复用哪些事实、补什么缺口；不能说尚未尝试或默认5ms仍活动 |
| 自愿/非自愿切换可在1～3分钟区分GIL和runqueue | 不成立。切换次数不含等待原因/持续时间；GIL、其他锁、驱动等待等均可能自愿睡眠。schedstat的runqueue时间可缩小假设，但低runqueue也不能区分GIL/锁/VART阻塞。短窗口没有罕见事件不能当作排除某机制 |
| 开启完整schedstat模式约75µs即可，环境变量可热关 | 已有完整模式平均额外0.763ms、一次7.234ms慢读，未通过原0.5ms前置。不能借用轻量getrusage的成本。环境变量在构造时读取，修改父shell不改变运行对象；热开关尚未实现 |
| YOLO started在wait前就是锚点错误，应移到帧到达后 | 未证。循环末sleep也按同一个started补足100ms，现有截止与周期相互一致。只移动截止会给可选任务放宽窗口并改变优先级语义，不能由4970次deadline拒绝证明错误 |
| guard捕获旧deadline会漏掉新来的更早YOLO deadline | 先证明可达交错。当前只有一个串行YOLO循环，传入started+100ms随单调时钟递增；后一个deadline通常更晚。min旧/新不自动修复已证缺陷，不能把“共享字段可改”当作确有更早值写入 |
| 2～5秒发布间隔仍可与TTL gap0并列作验收 | 与1000ms源TTL持续有效的要求冲突。分清无脸的有效negative发布与整条结果缺口；业务验收要以同一源帧有效期约束为准，阈值不能随意编造 |
| 3秒19.46%CPU可作为优化前基线、各架构需1周/2～4周 | 短窗不是同输入基线；工期数字也无本项目测量支持。应固定输入、UI/音频与频率，记录CPU核秒/有效发布及源帧龄，再估收益和成本 |

计数还需更正：10678完成/2次超限只能描述约49.2346分钟的该诊断观察窗；不能保证所有模块都同起点。published与native_completed跨异步边界的差值不能精确当CPU fallback次数。既有7测试未在打包过程重跑，不意味着这些测试历史上从未执行；原交付已有明确运行记录。

## 三条故障与当前现场

| 事件 | scheduler占用ms | execute marker墙钟/调用线程CPU ms | wait ms | guard | native |
|---|---:|---:|---:|---|---|
| A/6326 | 30.692017 | 4.099281 / 1.000611 | 0.160092 | 未越 | status0/completed1 |
| B/10528 | 31.162401 | 30.220712 / 1.122652 | 0.095521 | 未越 | status0/completed1 |
| C/16673 | 82.926870 | 82.077971 / 2.163218 | 0.106431 | 已越 | status0/completed1 |

C前段仅0.235112ms，execute marker区间自愿切换+69、非自愿+0；两次probe读取墙钟总计0.135942ms。它支持继续定位调用区间内的等待/阻塞或绑定/GIL重获，但69次自愿切换不能唯一识别GIL。当前14399次完成/3次超限，YuNet disabled且LATCHED，attempts2/recoveries2；第三次未自动恢复。reason unsafe_or_unknown_completion为恢复策略包含guard越界的通用标签，不意味着本条native完成状态未知。

两处guard增量均保留：last_overrun约+0.358214ms，diagnostic finish约+0.395344ms，系不同结束采样点。逐发布gap仍0，YOLO约9.94Hz、SFace2534次/超限0。材料是已有只读回传，不是本轮新在线探测。

## 已做的本地核验与建议顺序

执行了4类独立检查，结果在evidence/local_verification.json：实际OptionalDiagnostics配假probe证明采样顺序、AST确认分配在slot前、入口SHA/调用链与1ms记录核对、真实scheduler配虚拟时间构造deadline反例。反例中循环0开始、80ms拿帧、84ms结束YOLO、原节拍100ms再起；若仅将deadline放宽到180ms，可选任务84→110ms不触发新guard，却跨过原100ms节拍。它证明报告的改法不能直接接受，不代表现场一定发生了这组时序。

建议先把C与这些事实回给DeepSeek，要求修正归因和补丁。生产现场保持保护锁定及当前单owner，先完成：

1. 明确三种计时边界并用故障注入验证释放/故障计数/trace归属，诊断聚合移出关键区作为单独候选；不能通过移走计时器消除报错。
2. 复用已完成SFace状态候选，先补持续可用性与异常状态；native未知错误维持停用并监督，不直接吞异常继续操作DPU。
3. 补齐匹配VART二进制/绑定信息和低开销分段测量；完整schedstat仅在新的隔离开销前置通过后采用。新故障在当前1ms下发生，重复历史5/1ms或绑核前先说明新的区分价值。
4. 最小native对照保持同输入与背景负载、独立单变量；关闭诊断的最小Python runner只能比较包装/观测开销，不能自动排除Python绑定/GIL，因为仍通过Python。不要把“移动finish＋改guard＋原生对照＋复用buffer”作为一个实验。

真正运行中的状态切换/重启/恢复应先保存C完整数值环，合并现役SFace/GUI候选，再使用匹配的协调流程。本复核没有实施这些生产操作。

## 外部语义核对

Linux官方文档将schedstat第二项定义为等待runqueue的时间，不是GIL归因标签；需结合其他阻塞证据：[Scheduler statistics](https://docs.kernel.org/scheduler/sched-stats.html#proc-pid-schedstat)。Python3.9官方文档说明switchinterval只是理想线程切换间隔，实际可更长且调度由操作系统决定：[sys.setswitchinterval](https://docs.python.org/3.9/library/sys.html#sys.setswitchinterval)。这些资料支持测量解释，不证明本板所装VART的具体实现。

给外部审查者的可直接回传内容见[补充核对提示词](回复DeepSeek_需更正与第三次故障.md)。已有审查包保持冻结；本目录补充第三次故障和复核结果。
