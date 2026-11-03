# SFace event 5788独立复算（原始两行已核验）

**该事件真实触发30ms保护、正常完成且未越guard。外部包围窗报告run_delay增量0，支持这一次长尾主要不来自可观测runnable排队；仍不能认定GIL或排除VART/驱动/设备等待。不能泛化到此前YuNet故障。** 本任务只读主任务保存的JSON，没有接板或重跑推理。

原始单调ns重算：

| 区间 | wall ms | 调用线程CPU ms |
|---|---:|---:|
| optional起点→execute标记 | 0.270613 | 0.263822 |
| execute两标记 | 30.167721 | 0.580727 |
| execute返回标记→wait开始 | 0.299763 | 0.292422 |
| wait | 0.077041 | 0.076451 |
| optional两端 | 30.982100 | 1.410934 |

execute标记wall减CPU为29.586994ms。事件voluntary+3、involuntary+0；native_completed=1、failed=0、status0，guard_exceeded=0、hardcap_exceeded=1。reported occupancy30.914269ms；lease两个ns标记至release decision为30.948949ms，属于不同端点口径，均不能叫纯DPU硬件时间。

外部配对窗39.587666ms＝execute30.167721＋前缘0.383234＋后缘9.036711ms，恰好包围该execute标记区间。同TID499788、代次稳定、policy0/nice0。现已独立核验原始317/321两行：Q均为4060123226ns，确实Δ0；runtime8990318315→8993766269ns，Δ3.447954ms；pcount10385→10390。两次read各约49.7µs，计数实际快照区间可落于39.488335–39.587666ms，execute标记完整位于其中。见`event-5788-recalculated.json`，不是仅相信摘要配对。

可以缩小：

- 没有证据支持“该30ms由调用线程持续CPU计算”或“wait阶段花30ms”；wait只有0.077ms。
- 在计数正常、身份稳定、包围端点有效的条件下，0累计Q强烈不支持**这一事件**由CPU runnable排队贡献约30ms。目标在execute结束标记前已经再次运行，期间的已完成排队应已记账；不能用延后记账把该0随意解释成30ms隐藏runqueue。
- 没有native失败/硬件被30ms中断或guard越界的证据。

尚不能排除：GIL重获、Python诊断锁、绑定缓冲/job映射锁、VART内部同步、驱动/设备阻塞等。execute标记在Python侧，仍有mark后Python工作到native入口的盲区；SFace没有YuNet的pre_execute回调，但不等于整个区间已定位到某条native指令。外部runtime也不能与区间内CPU直接相减，后缘还包含约9ms其它工作且se.runtime可滞后。

外部采样4.979%单核超过2%门槛、有效约91.84Hz，**仪器成本验收失败，不常驻**。真实事件和数值证据仍保留，但不能称无扰动自然故障率或长期稳定性证明，观测负载的间接影响未排除。此前SFace28ms正常长尾支持该类结构早已存在，但仍不能证明此次越线与旁路完全无关。

run_delay的延后记账主要限制对正跳变的精确时间分配；本次包围窗Q为0的结论仍限定为“没有观测到已记账排队”。下一项是匹配当前vart.so的具体wrapper与GIL释放/重获边界；仅发现PyEval符号不足以把30ms归到GIL。当前ELF等待主任务只读落地，独立任务不接板。
