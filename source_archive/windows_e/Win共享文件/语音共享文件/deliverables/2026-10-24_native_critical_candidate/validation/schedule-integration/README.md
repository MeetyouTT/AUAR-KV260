# NativeLease恢复与保护交接 ABI v2 候选

**本目录仅完成本机实现和隔离验证；没有连接板卡、加载目标DSO或提交真实模型作业。** 源码已冻结供root整合/目标链接检查，不能凭本结果部署、解除现役保护或宣称长尾根治。接口细节见[CONTRACT.md](CONTRACT.md)。

## 改动

- `native_lease_v2.hpp`在同一原生执行权内完成准入、execute/wait回调、确认、30ms/5ms保护及释放。主任务等待优先、源TTL与更新后的更早primary deadline复查保持；unknown完成fence共享owner，新任务不得提交。100ms是执行权外的通知等待，不能取消VART在途作业。
- 两个可选模型独立复用`native_recovery.hpp`，该文件逐字保持此前独立验证的`a9e82c7f…`。10s冷却、最多2轮/600s、3次真实合格probe，guard/未知完成及primary异常按现役语义锁定；YuNet恢复轮在lease准入消费，SFace仅真实提交前的时间点消费。
- PROBATION的native成功只生成单次token，不提前计probe。执行权先释放，Python获得GIL后复查业务TTL，再ACK；C侧再次检查TTL。SFace第1/2个ACK仍不可发布，第3个才ready。原始确认完成输出可在ACK前保留/校验，不能因为尚未ready而丢掉第3次输出。pending不阻塞YOLO或另一模型，不可覆盖/重放；晚primary会锁定PROBATION，旧ACK不能复活。
- 首次idle严格seed导入，boot/结构/来源与完整状态校验，现有计数不得重置。同一次固定DSO的Context关闭不允许创建fresh Context恢复；固定的DSO与Python层生命周期协议仍是调用合同。checkpoint先在gate内seal，再导出完整状态，返回后来源不能继续执行。精确旧owner已停止、SHA/进程来源与消费次数由上层验证。
- 历史时间字段缺失只能显式opaque且LATCHED，保留已知fault/attempt/recovery累计，不能用零队列制造恢复预算。health-prefix种类必须fenced、两任务opaque LATCHED，不具有执行权限。旧生产没有seal导出接口；健康快照不能伪称精确最后状态，也不能通过重启或新seed解除当前YuNet 5fault/4recovery、SFace 3fault/2recovery的两个LATCHED。
- 补上主任务早拒绝漏记：入口或等待中错过原period deadline，虽然未提交仍计primary周期、未提交与period overrun，并锁定恢复中的PROBATION。`admissions[0]`仅真实lease；`primary_calls`包含已结束的早拒周期；last_primary只在native成功更新。sourceTTL过期而period尚未迟到，不计虚假period overrun。

`native_bridge.cpp/h`提供C ABI v2、受控YOLO所有权移交/自有BGR与输出、可选VART自有INT8缓冲、元数据查询、seed/checkpoint/ACK与状态查询。三个模型必须只通过同一个Context使用DPU；初始化/移交/创建runner在业务worker开始前完成。unknown后模型/缓冲与owner留存，不允许再次覆盖输入或关闭资源。旧Python active锁不得跨这些native调用持有。

## 实际验证

最终命令：`python3 run_checks.py`，完整参数、结果和源SHA见[checks-result.json](checks-result.json)。此前16组证据单独保留为`checks-before-primary-refusal-fix.json`，没有追认旧结果覆盖新代码。

| 检查 | 结果 | 范围 |
| --- | --- | --- |
| 恢复/seed/ACK集成 | 20组通过 | fake时钟/编译回调，无VART或设备 |
| 原仲裁回归 | 8组通过 | isolation模式无恢复；不等于生产许可 |
| C ABI控制流 | 5组通过 | fake VART/XIR/YOLO与注入registry |
| ASAN/UBSAN | 上述20组、5组分别通过 | 无内存/UB报告；覆盖重叠不另加总 |
| ABI实际布局 | Report88/Ack32/Recovery104/State432/Seed520 | 本机C++ sizeof；对齐由Python侧另核对 |
| 实板匹配头文件 | 最新源语法检查通过 | 只用root此前只读回收的21份头文件 |
| AArch64对象 | SDK GCC11.2交叉编译通过 | 未链接目标库、未加载或运行模型 |

新增4组覆盖：连续入口过期不取得lease但保持周期计数/PROBATION保护及checkpoint继承；源TTL拒绝不捏造周期迟到；被optional占用时primary等待到期仍计late；两个当前LATCHED状态分别承接5/3fault和4/2recoveries，不解除保护。旧组覆盖三个ACK、GIL晚归/过期/不提交不凑成功、pending隔离、一次checkpoint/seal/seed、双恢复预算窗口与unknown fence。

核心SHA：

- `native_bridge.cpp`：`ed0611f6c8ae23d37a26b92e2703f529315493bef66e21355ab35fddc364c106`
- `native_bridge.h`：`d909177ae843046d511ff124c2d6a0b61502333700aab25c9dd3b0014db79eff`
- `native_lease_v2.hpp`：`a080fa4b53c020889434a2bab8a9d0cd7b0729f2ad96716104db598f3409a547`
- `native_recovery.hpp`：`a9e82c7f06b585036465d28993273f88fb4d7cbf4c509d4610d006e82d1cd1cd`
- `tensor_layout.hpp`：`b6bf838240eeb8ab07074baca950edeea8982c866047d78332d0b2ad10cc4733`

对象`native_bridge.v2.aarch64.o`仅留本机，SHA `7c92beb74a9318325aa1caf7279f496a8b29439841eb726b861abd3fb28d65f1`；root后续只能将其目标链接结果另记，不能当本轮已做板测。共享交付排除所有ELF/对象与板载第三方头正文；自有fake依赖属于测试源码，并不替代真实VART。

## 未完成

由root整合Python facade/三模型调用和完整来源交接，做真实ctypes/目标DSO/同输入INT8输出等价、维护窗口恢复、实际业务时效/资源收益、真人身份精度和长稳。普通Linux仍可能在native执行时被调度走；四时间点分别记录release决策与unlock后观测，不是任意负载硬实时保证。现役服务与保护没有被本任务改动。
