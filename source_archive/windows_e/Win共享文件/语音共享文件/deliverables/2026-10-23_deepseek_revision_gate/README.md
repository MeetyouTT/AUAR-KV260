# 修订版审查：采纳范围与最小补丁验收条件

结论：修订版已撤回多数源码误读，事实分析可作为工作输入；但Patch 1的端点/公式/测试仍相互矛盾，Patch 3的线程存活和未知完成处理也未形成可执行合同。无需再扩写整份审查；下一步应按本页的少量验收条件完成隔离候选。

本轮只核对已有源码、三次故障及修订版伪代码。没有接板、新推理、生产切换、解除LATCHED或替换SFace候选。最新已有快照仍为C事件82.926870ms/guard越界后YuNet退CPU，不能当作本轮新在线实读。

## 修订版仍需纠正的实现问题

### 1. release_mono仍在过早的位置

Patch 1在finally刚进入时就取release_mono，后面还要统计、恢复决策，才执行active=None和notify_all。这是原occupancy取样位置重新命名，不是实际释放点。若后续状态处理停顿7ms，该字段仍少记7ms。即使active=None已赋值，只要condition锁尚未退出，等待线程也不能重新获得调度锁；notify不是解锁。

“只新增字段、不改逻辑”的实验1与实际Patch 1又不一致：代码已把finish移到锁外，改变了并发与时序。应先做纯测量候选，再单独评估移动finish，不能当同一个变量。

### 2. 两个派生字段没有它声称的含义

按提议代码：

```text
occupancy     = release - scheduler_started
release_wall  = release - diagnostic_started
两者相减      = scheduler_started - diagnostic_started
```

两者相减完全不包含finish耗时。因此其测试“finish慢3ms，release_wall-occupancy约3ms”在数学上不成立。另一个finish_after_release取的是finish入口now与release之差，不包含finish取now之后的主体处理；不能用它量化finish主体。

已用伪代码同序的合成7ms状态处理/3ms finish检查：claimed release20ms，实际active清除27ms；release_wall-occupancy为-0.1ms，和3ms finish无关。它是公式反例，不是板端耗时。

### 3. worker_alive与清理并未得到保证

`finally: self.worker_alive=True`会在线程已经退出后仍报存活。合成本地线程已复现；应由实际Thread.is_alive及受锁保护的STARTING/RUNNING/STOPPED/DEGRADED生命周期共同表达，退出finally必须明确终止状态。

`except: diagnostics.error(); finally: pass`同样不能保证trace清理。当前finish在入口时钟或早期字段更新失败时，尚未进入内层清理finally，thread-local与active trace可能遗留。本轮用当前真实OptionalDiagnostics的入口时钟异常复现该路径。新候选必须用独立的无条件清理路径覆盖begin、finish、error自身及BaseException，并在确认没有未知在途作业的诊断异常场景下保证执行权不泄漏。错误继续传播与清理是两项独立要求。

NativeUnknown时只停人脸worker还不够：YOLO/SFace共享同一owner；若释放调度权后其他模型继续提交，仍违反“未知在途状态不再提交”的要求。必须由owner/调度层统一表达不可再提交，并定义进程监督条件。不能用人脸服务中一个未实现的_stop_dpu_submissions方法当作已完成全局隔离。wait非零状态是否意味着安全结束，也应依据匹配VART合同确认，而非一概假定。

## 推断与数字还需保留边界

- C的82.08ms除以69次自愿切换约1.19ms，不是“平均每次睡了1.19ms”。总墙钟包含运行、睡眠和排队，计数没有每次等待时长；与1ms间隔相近只是线索。非自愿计数0也不能排除主动睡眠醒来后等CPU的runqueue延迟。
- 修订版仍从两个duration和未知端点推出“起点偏移约4.4µs”，仍不成立，不能把该反推值当真实时间戳。
- C表中的execute_return相对optional_start应为82.313083ms；82.077971ms是execute_start到return的区间。已按原ns重算。两种guard差的采样点不同，不能再用其中任意一项强行补出未知occupancy起点。
- 新增800ms p95/2倍TTL等数字仍只是建议，未取得本项目业务依据。结果到期取决于源帧时刻，不仅是发布间隔；持续零gap要同时考虑旧结果发布时已消耗的帧龄。既有TTL与保护不因审查建议自动更改。
- 调低预算估计是否衰减是保守调度的设计选择，不宜直接列为已证错误；健康查询锁内snapshot可做隔离优化，但未由此证明C根因。

AMD3.0的[Python execute_async文档](https://docs.amd.com/r/3.0-English/ug1414-vitis-ai/execute_async)本就将其描述为阻塞接口；官方[v3.0绑定源码](https://github.com/Xilinx/Vitis-AI/blob/v3.0/src/vai_runtime/vart/runner/python/runner_py_module.cpp#L257)在native execute周围使用gil_scoped_release。上游事实不能替代本板二进制匹配，但足以否定“execute_async应立即返回”“当前一定没释放GIL”作为默认实验前提。先确认实装版本，再决定是否值得做新的5/1ms对照。

## 收敛后的最小任务合同

1. **先只补测量。** 保留原cap/guard判定、恢复状态和旧字段，分别记录旧occupancy采样点、finish调用前后、active清除前、condition退出后的观测点。所有区间用同一个起点相减；condition退出后的时间戳明确是退出后的观测上界，若本线程随即被换出不能当精确解锁时刻。finish之后才知道的端点不能提前传给已经执行的finish；用明确task token追加观测并标明快照完整性。
2. **单独验证异常清理。** begin/finish/error在提交前或确认完成后抛异常时，不泄漏active/condition/trace，不清故障计数。原生完成状态未知另走owner级停提交，不能与诊断错误混为一类。复用既有三个反例，不重新搭大量环境。
3. **再单独移出诊断聚合。** 正式保护/恢复决定先在锁内完成，执行权安全释放后再聚合；按token处理trace和快照，不改变旧字段计时含义。这个候选测业务等待和CPU成本，不能因移走计时范围就声称修掉82ms native marker长尾。
4. **复用SFace候选。** 4源92软件/16板隔离已有结果，先合并持续可用性与缓存/语音消费修复；它不提供自动恢复。生产接入按相机与GUI各自当前版本协调，不能只改相机就声称GUI消费修复完成。

长期根因工作保留三个互相独立的事实：保护已工作、仍有82ms级等待、该等待发生在execute marker区间。先取得匹配VART版本和低干扰测量，稀有故障没复现只报告对应窗口；不因本轮审查继续盲跑历史GIL/绑核实验或改30ms/5ms。

## 本轮验证

[check_revision.py](check_revision.py)执行通过，[checks.json](checks.json)记录了：释放点仍过早、差值公式不含finish主体、worker退出但alive仍真、真实finish入口异常留下trace、C的relative端点重算。脚本仅导入标准库和已读回的纯Python指标模块，不启动VART/GStreamer或新线程业务；其单个合成线程仅验证生命周期标志。

这些是对提议伪代码的反例和验收条件，不代表修复已经实现或生产通过。原审查包和生产源码保持。
