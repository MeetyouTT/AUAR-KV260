# 外部线程观测方案复核

**方向可行：改为独立进程读取目标线程proc计数，可避免在相机GIL及DPU lease内增加采样成本。只认可一次60秒的成本/背景排队验证，不据此承诺定位YuNet根因。** 未接板、未改root代码、没有重复主机C测试。

主任务ARM证据`board-result.json`：C编译及7项语义通过，但完整native adapter meanCPU183193ns超过100000ns、P99wall6.856ms超过1ms，所以不能接入生产。隔离Nice19进程的busy段约15.039ms CPU＋21.375ms run_delay≈36.414ms wall，说明那个隔离进程有CPU排队，不能外推到生产故障。

## 当前external_monitor.py的合理部分

- 目标来自实际fault/maximum-normal trace的task_code与calling_thread_native_id，不猜线程名；记录PID/TID start_ticks、inode/device及策略/亲和性。缓存proc fd，结束再次校验代次，不自动转到新PID/TID。
- 每次read前后用同一MONOTONIC时钟包围，保存原始三计数；倒退拒绝，缺失不当零。绝对节拍迟到时跳过missed ticks，不突发补采。
- 记录实际频率、迟读/丢节拍和monitor自身CPU；不读图像/向量/身份库，不新建DPU owner，也不改亲和性、GIL或内核开关。
- align_trace标作扩展的外部计数区间并保留前后端点不确定度，这个限定必要。

## 必须保留的解释边界

1. **remote run_delay是延后记账。** 等待在任务重新到CPU或出队时累计；某次相邻read的ΔQ可能包含此前已经开始等待的段，甚至大于10ms。不能把跳变全分配给前一格，也不能从execute_wall直接扣expanded ΔQ。
2. schedstat的runtime不是精确线程CPU时钟，三字段也非原子。采样排队和目标排队是两回事；monitor读得晚只降低覆盖率，不代表目标当时阻塞。
3. YuNet目前LATCHED，其目标线程继续做CPU fallback。观测到该线程排队，不是新的YuNet DPU/VART证据。SFace的maximum_normal_trace若未更新，即使completed计数增长，也不能捏造新trace端点。
4. `covered_trace_events=0`时，只能报告该生产线程的背景排队。将“成本门槛通过”和“有可归因native区间”分开；两者都不等于GIL/VART根因已确定。

## 当前单文件建议补足的诊断完整性

- setup中的逐目标open及`assert set(targets)=={1,2}`尚在try/finally之前。第二个目标已退出/代次不符时，进程退出会由OS关闭fd，**没有生产安全泄漏**，但无法写结构化失败报告。建议把所有open纳入统一cleanup/report路径。
- 中途读失败/目标退出现在能close fd，但已有numeric samples仅在成功路径落盘。建议失败时也保存有界的partial rows、失败TID/阶段/errno及采样端点；否则最有价值的线程退出窗口没有数值证据。
- 汇总加每目标相邻read时间间隔的P99/max；effective_hz和skipped_ticks不能完整描述覆盖孔洞。现有raw rows已足够计算，无需额外target读取。
- 自身CPU分子目前包含进程启动至raw序列化的CPU、分母从sampling_start算，偏保守；最终report编码/print尚未包含。保持当前2%门槛，并准确标注“到raw序列化为止”，或由外层子进程rusage补完整生命周期，不能称精确全部开销。

最少身份/关联字段：boot、PID/start_ticks、task_code、TID/start_ticks、inode/device；每行before/after mono、runtime/run_delay/pcount；实际采样节拍/丢点/错误；关联trace的event_sequence、task_code、TID和原始execute端点。起止health保留，不重置已有fault/gap；进程或线程代次改变时终止本窗口，不能静默重开。

以上没有要求延长或重复观测。一次窗口若没有新native trace，止于“外部低扰动监测可行/不可行、背景排队多少”；后续受保护的原owner诊断需另行设计，本方案不解除YuNet锁定。
