# 原生受限恢复策略候选

这是供主执行者接入的独立C++策略，**没有接入NativeLease、没有部署、没有连接板卡或执行真实模型**。实现依据现役 `dpu_recovery_policy.py`，参考文件SHA256 `b00d19aacdf211f93bd192ebcbca20d72782bcc1bacae09736f6edaf37f17d62`。模型、量化、身份模板、阈值与30ms/5ms保护均不在本候选修改范围。

`native_recovery.hpp`只包含固定大小plain state、2元素时间数组和整数逻辑，无I/O、动态分配、线程或mutex。每个任务各用一个 `aura::NativeRecovery` 实例，上层使用唯一DPU owner的同一锁串行所有策略调用。实例禁止copy/move赋值，没有reset API，不能重建实例来清除故障。State和Seed可复制用于显式交接。

当前固定：10s冷却、600s滚动窗口最多2次恢复轮、3次合格probe、fault后primary调用必须推进且最近一次年龄≤0.5s。600s相等时旧轮过期，0.5s相等时primary仍新鲜；源TTL相等时已经过期。

| 接口 | 合同与返回值 |
|---|---|
| `fault(now, Fault, Primary)` | 对一条真实结束的故障增加faults、保存primary baseline并清probe数。已完成且仅hardcap允许COOLDOWN；guard/未知完成/body_failed/非hardcap转LATCHED。窗口2轮已用且最早未过600s则LATCHED。返回true表示故障已记入。 |
| `due(now, Primary)` | 只在冷却到期、primary无新超限且已推进/新鲜时返回true，并按需剔除过期轮。它不消费轮、不清disabled、不提供业务ready。 |
| `admitted(now, Primary)` | 仅在普通gate/guard/TTL准入通过后调用；内部再次due。记录一轮、累计attempts++并转PROBATION。多次due不消费轮；PROBATION内再次admitted拒绝。 |
| `success(now, Probe)` | 只对submitted、completed、status0、result_usable且`now<source_expires_ns`的实际完成计probe。前两次返回false，第三次返回true并恢复RUNNING、recoveries++；过期/未提交/不可用不凑成功，也不重置已有合格probe。实际故障必须先经fault而不是传作普通success。 |
| `primary_failed()` | 与现役一样，只即时锁定PROBATION，并保留已有probe计数；COOLDOWN内primary超限由到期后的due比较计数再锁定。返回是否即时锁定。 |
| `normal_allowed()/probation()` | 分别观察RUNNING/PROBATION。PROBATION只是特殊probe许可，不能直接当SFace业务ready；SFace前两probe必须Deferred。YuNet是否发布完成probe由现役业务合同决定。 |
| `export_seed(captured,out)` | 输出完整状态及2元素时间槽，不清计数、不修改状态。 |
| `import_seed(seed,now,current_primary)` | 仅在全新实例的任何操作前导入一次。严格校验版本、枚举/phase/reason、时间范围与顺序、计数关系、phase所需probe/轮、primary baseline和完整队列。无效输入不修改策略；成功后禁止再次导入。 |

所有时间为同一CLOCK_MONOTONIC的正uint64纳秒，限定≤INT64_MAX；拒绝回退的时间与primary计数。`due()==false`且`error()==none`为普通不ready；`error()!=none`表示非法输入或计数溢出，整合层必须保持disabled/fence并记录错误，不能将其当作无故障成功。fault是记录真实新故障的入口，**不得在LATCHED没有新执行时伪造一次safe hardcap来重新开启冷却**；这一点与生产调用约束相同。

## 两个必须保持的接入时点

现役YuNet在optional lease准入时消费恢复轮；SFace在`native_starting()`、真实提交前才消费。策略本身不区分模型，主执行层应在各自位置调用admitted。SFace在提交前撤回不消费轮；YuNet若已经准入再撤回，按现役语义其恢复轮已经消费。未提交永不计success。

现役SFace的`native_completed(usable=self._fresh(stamp))`位于Python yield返回之后，包含重获GIL等待。**不能把新C++ native刚结束时的TTL新鲜直接冒充该标记等价**：Python返回过期的结果仍须Deferred且不能凑第三probe。整合者可用释放native gate后的token/ack作可用性确认，或明确实现等价机制；不应重新握住旧Python lease等待GIL。本候选success依传入now和proof检查，调用/确认时点由整合层负责。

## Seed边界

上层负责校验同boot、同owner、旧/新执行器idle、故障证据来源与保护counter整体一致。一个公开health snapshot只含`attempts_in_window`数量，**不足以恢复完整滚动窗口**；必须提供真正的两个attempt时间和phase相关历史，不能补零或默认RUNNING。导入不剔除过期时间，也不会因为窗口已经过去解除LATCHED；只有原有COOLDOWN在due时按原规则清理窗口。故障、attempt、recovery累计保持，primary全局计数须先交接再导入策略。

## 实际验证

- `test_native_recovery.cpp`：13组通过，覆盖冷却/预算精确边界、窗口剔除但不清累计、三probe正常恢复、过期/未提交/不可信probe、primary故障、unsafe直接锁定、YuNet/SFace实例独立、seed各phase恢复/禁止二次导入、14类非法seed、时间/计数回退及fault计数不回绕。
- `test_no_allocation.cpp`：操作期间全局allocation hook计数0，主机policy大小96B；这是主机软件结果，不是板卡内存测量。
- `test_python_parity.py`＋`recovery_trace.cpp`：24条确定性合法调用轨迹、3840次完整策略状态与现役Python参考相等。对success使用与scheduler相同的资格过滤；admitted只在due成立/普通准入已满足的合同下比较。
- 同13组ASAN/UBSAN编译运行通过，stderr空。首轮parity脚本因相对可执行路径被PATH查找而失败，原结果保留在`validation-first-result.json`；修为绝对路径后通过。不是板端问题或模型失败。

结果分别见`validation-result.json`、`sanitizer-result.json`，源码与结果哈希见`manifest.json`。检查可用`g++ -std=c++17 -O2 -Wall -Wextra -Werror`编译3个cpp，再运行两个test与`python3 -B test_python_parity.py`；所有测试不加载DSO或模型。

仍需主执行者完成NativeLease/C ABI/业务适配与完整seed交接，然后同输入模型等价、真实三模型、恢复/未知完成和长期业务验收。独立策略软件通过不等于已修复生产长尾。
