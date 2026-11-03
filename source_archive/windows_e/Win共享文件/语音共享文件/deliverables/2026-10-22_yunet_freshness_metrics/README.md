# YuNet 数字时效观察候选

2026-10-22。**仅本地候选完成，默认关闭，23 项真实固定源＋虚拟时钟检查通过；没有接板或部署，没有收益/开销通过结论。** 原准确生产 `face_targets.py` 为 `d03e2aee39a43f31705494dd679ad4ce7d9b49ddf7bd1185f5e021cdb8990aa0`，不是迁移前的 `live-source`。

只新增 `board/identity/face_freshness_metrics.py` 纯标准库聚合器，并对上述准确源做观察接线。没有修改模型、VART、DPU 调度、30ms/5ms、200ms 工作周期、SlotUnavailable 保留旧 stamp、TTL、身份模板或回调语义，没有加重试。源码、基线 diff、证据与 SHA 见 `manifest.json`。

## 显式启用与默认行为

`FaceTargetService(..., freshness_metrics=True)` 才创建记录器，默认 `False` 不导入/创建记录器，不增加热路径时钟、记录器锁、准备模型或推理次数。默认 `health()` 的键和值保持原样。候选尚未修改 `camera_faces.py` 或任何配置；当前已有调用方不会自动开启。主任务若审核通过，应在独立候选调用点显式传入参数，并把新源 SHA 纳入部署保护，不改原生产。

启用时，`health()['freshness_metrics']` 才出现 `schema_version=aura-face-freshness-metrics-1`、`enabled=true`、`collecting/closed`、计数、时长汇总和有界数字事件。记录器初始化/调用失败不会改变业务异常、结果或工作周期；`observer_failures` 饱和计数且快照失败返回 `collecting=false, observer_unavailable=true`，不能把不完整记录当通过。记录器不读 proc、不打印日志、不存图像、姓名、target key、frame ID 或 embedding。

## 统计口径

- 计数区分 offer/接受/关闭拒绝/latest 替换、attempt/finished/在途、SlotUnavailable、输入 TTL 丢弃、检测后 TTL 丢弃、检测后关闭、发布正观察/负观察/多人、process/callback 异常。`published_positive` 仅指过滤后脸数大于 0，包含多人，不等于确认单人目标或身份成功；`published_negative` 是新鲜的无脸观察，不能混为源帧失效。
- 连续拒绝只统计连续完成且 outcome 为 SlotUnavailable 的 attempt；任一其他 outcome 重置当前连续值，最大值保留。没有改变原拒绝后 200ms 等待。
- 时长统计 attempt 和 detect 的 monotonic 墙钟/调用线程 CPU，输入年龄、原 TTL 检查年龄、锁外提交后观察年龄/间隔，以及下述空窗上下界。固定汇总仅 count/total/min/max/last/mean，不声称逐帧分位数或身份延迟。所有数字都是启用后累计，不能和其他 PID 窗口直接拼接。
- 默认最多 16 个数字事件，可构造为 1～64，满后覆盖旧事件并计 `events_evicted`；计数饱和至 `2**63-1`。时间戳只接受非负有限整数，时长必须有限且非负。同线程 CPU 端点才配对；缺值/逆时/异常/不匹配会计拒绝并跳过汇总，不填 0。空汇总 `count=0, mean/min/max=null`；`total_ms=0` 表示空集合和，不是一次 0ms 测量。

## 提交时刻与空窗边界

原 TTL 检查在 state.lock 内，候选复用原来那一次 `self.clock()` 的值作为 `P_i`，不额外在持业务锁期间取时钟。实际提交 `C_i` 随后发生。释放本方法 state.lock 后，再取 `self.clock()` 和 monotonic/线程 CPU 作为观察点 `O_i`；线程可能在提交与观察间被调度，偏差时长未知。因此所有相应字段明确为 **post_commit observation**，不能将观察年龄达到 TTL 解释成原 TTL 门槛接受了过期输入，也不能将其间隔称为精确提交间隔。

对于相邻两个被观察到的有效提交，前一次源帧 stamp 为 `S_prev`，TTL 为 `T`。先把区间裁剪在前一次观察 `O_prev` 之后，令 `A=max(S_prev+T, O_prev)`，本次原 TTL 检查点为 `P_i`，观察点为 `O_i`，则给出：

```
clipped_gap_lower_bound_ms = max(0, P_i - A)
clipped_gap_upper_bound_ms = max(0, O_i - A)
```

这样按前一次 **源 stamp+TTL** 计算，不用前一次提交时间+TTL。下界大于 0 才计 `definite_clipped_gap_intervals`；上界大于 0 计 `observed_gap_intervals`。它们只对应上述裁剪区间，不外推首段/尾段、不声称整段失效占比，不能把上界总和当真实空窗总时长。首次只有 anchor，没有伪造一个 0 间隔。

数值需同时满足 source 单调/顺序、`O_prev <= P_i <= O_i` 及 source 间隔与 monotonic 间隔对齐（默认容差 50ms）。缺值、倒退或对齐失败会增加 `source_clock_pairs_rejected`，本对不输出空窗，下一次重新建立 anchor。这个拒绝也可能来自两次钟读取之间的调度间隙，不能当物理时钟跳变的证明；“下上界”依赖这一有效时间轴假设。原业务判断不因此改变。

发布计数与观察 finish 有短暂在途差异，例如观察点已记录但 callback 尚未结束；`active_attempts` 与 `attempts_finished` 用于识别这一状态。快照是记录器自己锁下的一致副本，不是 camera/service/recorder 的跨模块原子事务。更新钩子在本方法业务锁外执行；现有 CameraState/IdentityService 的 health 调用方可能仍持外层共享 RLock，不能声称 health 全链无 state 锁。记录器从不反向取得业务锁，但其快照复制与锁等待仍须纳入板端开销前置。

## 验证与剩余工作

运行：`python3 -B -m unittest discover -s tests -p 'test_*.py' -v`。23 项覆盖默认源行为和时钟次数对照、原 200ms 拒绝周期、latest 单槽、正负观察、输入/发布/关闭丢弃、拒绝连续值、真实源 stamp 空窗公式、前检查/后观察上下界、模拟延迟后观察过 TTL 而原门槛仍有效、业务异常保留、观察异常/错误 token/初始化失败隔离、缺钟/逆时/对齐跳变不填 0、有界事件/饱和、并发一致副本及幂等关闭。

第一次运行中，测试替身把浮点等待余量四舍五入为 0，停在虚拟 wait；约 10 秒后已中断。修正仅限测试替身：向前跨过 1ns 并设置等待次数上限，随后 23 项 0.084 秒通过。没有为修测试改变候选业务周期。最终完整输出和运行元数据见 `evidence/`。

下一关由主任务决定：在板卡只运行合成输入的准确回调/worker 微基准，先核对新开销、事件/快照锁开销、关闭和恢复，再决定真实短诊断。观察本身可能影响时效，当前没有板端开销、真实 DPU 保护或 TTL 改善证据；不可直接常驻，也不要在同次测量叠加 GIL、核分配或短退让。保持原模型和 30ms/5ms 验收口径。
