# 自有无 DPU fixture 的 UProbe 隔离检查审查

**根代理第三轮实板隔离检查已通过；前两次 setup 失败保留。** 第三轮只改无seek的append接口，保持fixture SHA与同一BTI入口offset，四探针500轮、2000事件完整，新增均值线程CPU20.272µs/四探针，清理与全局恢复通过。这只证明自有fixture观察路径与成本门槛通过，**尚未采样生产 VART，也没有证明真实长尾根因或生产成本**。

已审查 `/home/ghmd/aura-native-wait-20261023/trace_isolated.py`：最新 SHA256 `9c8f8702f68a4d24c76be06e1c1ad575d0c53a77e353a78b8bb89b15e1e658e4`。本代理只读本机源码/内核参考文件并运行 fake tracefs 检查，没有接板、创建真实探针或提交 DPU 作业。

## 已修正并复核

- 初版按字符串比较 `path:offset`，与内核读回时将 offset 补足16个十六进制位的形式不兼容，会保留自己的 event。根代理已添加 `same_target`：路径严格相等、偏移按十六进制整数相等，仍要求定义只有两字段；不同路径/偏移或 refcount 扩展保留不删。已用内核规范化例子及 fake cleanup 复现修复有效。
- 当前记录真实 `displayed_fraction_digits`，最多9位；6位小数换算成 ns 仍只具µs量化，报告明确不以单位代替精度。
- 当前要求 per-CPU stats 非空、`overrun`/`commit overrun`/`dropped events` 三字段全部存在且为0；遗漏字段将进入异常与清理路径。
- 前两次板端 setup EINVAL 后，根代理将 tracefs append 接口从 `Path.open('a')` 改为 `os.open(O_WRONLY|O_APPEND|O_CLOEXEC)` 加一次 `os.write`，不寻址、不truncate、不create；partial write判失败并关闭FD，不拼接重放。保留同一BTI函数入口offset，只改I/O接口，避免同时换指令掩盖机制。

## 实际失败与接口定位

根代理提供的 `transfer-native_trace_isolated_r1/result.json`（源码6781bbb1…）及 `r2/result.json`（源码e977c9df…）均为 failed。r2增加文件/值上下文，确认第一条 `uprobe_events` 定义写入 EINVAL，尚未到 event enable；两轮自己的event/instance均已清空、全局状态保持、guard inactive，production_changes=false、DPU jobs0。mono/nop可用、nsecs不存在且被跳过，own error_log无记录；不能把失败定为BTI、CPU指令不支持或DPU问题。

本机非修改性实验只 open/close `/proc/self/comm`（不写）：`Path.open('a')`在open成功后发出 `lseek(fd,0,SEEK_END)`，返回EINVAL；`os.open(O_APPEND)`不调用lseek，成功关闭。`strace`实际记录和脚本保存在本目录。参考内核 `trace_uprobe.c` 的 `uprobe_events_ops.llseek=seq_lseek`。随后根代理r3使用新接口、相同fixture SHA与同BTI entry offsets成功注册/命中/清理，对“append隐式seek导致前两轮setup失败”的解释提供强支持；没有板端syscall trace，所以仍区别于直接观察了板端失败的lseek。

参考5.15内核定义注册路径仅解析regular file、offset、名字并注册trace event，真正 `uprobe_register`/ARM指令分析在enable路径；组名25字符和native_enter12字符有效、0x7b0是合法整数。不能从“fixture入口为BTI”直接推出定义写入EINVAL的原因，也不应为此改生产文件或内核。

## 边界检查

| 项目 | 本地审查结论 |
|---|---|
| 全局 event 定义 | 注册和删除均只用无seek的 `O_APPEND` 单条写 `uprobe_events`，没有全局截断写；删除仅限唯一 hash group 中已登记 path/offset 的 event。fake 测试确认外来 group 保持。 |
| trace 配置/清空 | `current_tracer`、buffer大小、时钟、filter、enable、清 trace 都限定到新建唯一 instance；不写全局 tracer/clock/PID 设置。完成后对全局四项与定义 SHA 作前后比较。 |
| 生命周期 | 初始拒绝同名 instance/自身 group 预存在；ownership 原子写入且独立45s timer确认 active 后才创建 instance/注册 events。注册至循环都在 try/finally 中；普通异常与KeyboardInterrupt会走finally，SIGTERM/SIGKILL依赖独立guard清理。 |
| 清理所有权 | group绑定脚本SHA，元数据核对脚本SHA/boot；不匹配的 event 保留并判失败。清理优先关闭自己的instance及event，再按单条定义删除。若timer与finally重叠，可能有“已被另一清理删除”的保守失败，但不授权删除外部event。 |
| 中断窗口 | 准备期尚无真实探针；timer arm之前被终止不会留下探针。timer arm成功而active查询失败时仍无探针且finally清理。45s后guard可中止本次测量，结果应失败；不能据此延长负载或自动启生产。 |
| ELF偏移 | `nm` 取函数VA，`readelf -lW`取各LOAD的offset/VA/FileSiz，用 `file_offset = p_offset + symbol_va - p_vaddr` 且要求恰好一个匹配，未沿用VART的VA=offset假设。实际板编译和注册支持仍待执行。 |
| 事件解析 | 支持当前group前缀可有可无、6或9位小数；恰好2000条、严格四相位循环顺序、fixture计数增加2000联合约束。实际内核输出是否匹配将由隔离运行验证，解析失败不会通过。 |
| 成本门槛 | baseline与启用后各500轮同一 `ctypes.CDLL.step`，报告完整调用线程CPU和wall；增量均值CPU≤100µs/四探针，启用后P99 CPU≤500µs，门槛未扣减探针成本。前后运行波动仍可能影响增量，不能外推为真实生产native事件成本。 |

`guard` 的控制服务与 timer 名均由源码SHA限定；在本脚本 staging 路径保持原件不变的前提下，清理能定位原组。不可在运行中覆盖该 staging 源码，否则基于文件SHA重算的组/所有权会变化。若清理失败，保持结果失败并读回残留，不直接扩大到全局events清除或反复重试生产。

## 实际验证

`python3 independent-review/test_uprobe_isolated_review.py`：**最新8项通过，0.010s**，绑定9c8f8702…源码 SHA。覆盖补零偏移匹配、不同路径/偏移/refcount拒绝、append保留已有定义、只删除匹配的自身定义、目标变化时保留、执行实际run函数中的解析AST处理6位及9位时间戳；新增no-seek/flags/单次write与partial write拒绝/关闭FD。此前6781bbb1…的6项检查通过不包含这个新I/O合同。fake只模拟event定义的内核规范化和删除行为；不模拟ARM指令单步、真实tracefs实例删除或systemd中断恢复。

根代理r3结果见 `../trace-isolated-result.json` 与 `transfer-native_trace_isolated_r3/result.json`。源码9c8f8702…，fixture SHA仍 `da51697f821fddea0a6e37e51af56297820f6757b3fc0121859decdb4373f566`，offset仍0x7b0/7d0/7f0/810。报告显示500轮、2000条严格四相位顺序、计数增加2000；四CPU的overrun/commit overrun/dropped events均0。基线完整线程CPU均值4.759872µs→25.031912µs，增20.272040µs，P99 CPU34.69µs、P99 wall56.12µs，均满足原门槛。显示6位小数，量化1µs；cleanup passed、instance/event剩余0、global_state_unchanged=true、guard inactive。此处逐项核对保存的结果JSON，并复算均值差；本代理没有亲自接板或读取完整2000行raw trace。

未重复既有17项采样器测试，未把8项本地fake检查算成实板测试。上述实板通过只适用于fixture；后续生产探针仍需另行限定PID/TID、调用代次、异常端点及成本，并在短窗结束后解除所有探针。fixture成功不授权改变30ms/5ms或创建新DPU owner。
