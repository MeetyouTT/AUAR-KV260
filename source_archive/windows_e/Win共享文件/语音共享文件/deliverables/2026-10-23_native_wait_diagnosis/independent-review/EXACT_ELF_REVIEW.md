# 当前板端 VART Python 绑定的精确 ELF 审查

**已确认这份板端 `execute_async` 绑定在调用 runner 时释放 GIL，并在 runner 返回后、返回 Python 之前重新取得 GIL。** 这项结论来自字节匹配的 ELF 内“方法名→回调→实际调用”路径，已超过“上游源码可能如此”或“库中存在 PyEval 符号”的证据等级。**它仍不能把 event 5788 的 30.167721ms 定位为 GIL 等待或 VART 内部等待**：当前 Python 标记包围了两者及准备/收尾，没有 native 子阶段的运行时间戳。没有因此改写绑定、启用 UProbe、改生产程序或重跑推理。

本审查由第二路代理仅在 Ubuntu 本机执行：`sha256sum`、`readelf`、AArch64 `objdump`、确定性原始字节/事件复算。板端取件与运行状态由主任务提供。恢复后又出现的 YuNet event 521 属于 **21.03748ms、hardcap 未越、guard 越界**，不能写成“所有故障都是 30ms 上限”或“三模型一直恢复”；本报告不扩大为该事件的根因分析，以主任务的 `final-audit.json` 为最新状态。

## 精确对象与证据边界

| 项目 | 本机核验结果 |
|---|---|
| 本地对象 | `../exact-runtime/vart.so`，194720 字节，AArch64 ELF64 little endian |
| SHA256 | `dc6bff9be31b8dc349a72489e06237f8503175805d042025558694823f61de34` |
| GNU BuildID | `e359176b9761d3035b0301d4ec6c48de9a0af577` |
| 与故障进程对象关联 | 与 `preflight.json` 的 camera499773 映射路径 `/usr/lib/python3.9/site-packages/vart.so`、大小和 SHA 相同；下载逐块与整件 SHA 记录在 `../exact-runtime/download-proof.json` |
| 源码提交、调试信息 | 仍未匹配。`.gnu_debuglink` 指向同名文件且 CRC 不符，工具忽略该调试对象；本审查不使用它补符号或行号 |
| 地址口径 | 下列地址均为 ELF 相对虚拟地址；该 ELF 的 `.text`/`.rodata` 地址与文件偏移相同。不是 ASLR 后运行绝对地址 |

执行工具为本机 Xilinx AArch64 `aarch64-linux-gnu-objdump -d -C`。剥离库的反汇编会用邻近导出符号加偏移标注未命名函数，**不能把这些就近标签当函数身份**；下表通过初始化时同一 pybind record 的方法名与回调指针关联。

## 方法名、回调与实际 GIL 边界

`execute_async`：字符串位于 `0x26620`。初始化指令：

```text
0xd4a0  adrp x0, 0x10000
0xd4a4  add  x0, x0, #0x6f0      ; callback = 0x106f0
0xd4a8  adrp x1, 0x26000
0xd4ac  add  x1, x1, #0x620      ; name = 0x26620
0xd4b8  str  x1, [x21]          ; record.name
0xd4c4  str  x0, [x21, #48]     ; record callback
```

该回调的正常成功路径：

```text
0x109f0  bl  0x8cd0 <PyEval_SaveThread@plt>
0x109f8  mov x19, x0            ; 保留返回的 thread state
0x10a04  mov x0, x20            ; runner self
0x10a08  ldr x3, [x3, #16]      ; runner 虚表槽
0x10a0c  blr x3                 ; native execute_async 调用
0x10a10  mov x22, x0            ; native 返回后的第一条指令
0x10a18  cbz x19, 0x10a24
0x10a1c  mov x0, x19
0x10a20  bl  0x8600 <PyEval_RestoreThread@plt>
0x10a24  ldp x19, x21, [sp, #168]
0x10a44  bl  0xecd0             ; 第一个 buffer 注册循环
0x10a74  bl  0xecd0             ; 第二个 buffer 注册循环
```

输入/输出 buffer 的准备发生在释放前（包括 `0x10990`、`0x109d4` 的转换），buffer/job map 登记在重获后；之后还有容器清理、Python 返回值构造及 pybind 返回。Python 的 `execute_return` 标记晚于这些步骤；`execute_start` 标记早于绑定入口，YuNet 还有可选 `pre_execute()` 检查。**即使 native 调用已经完成，`PyEval_RestoreThread` 等待 GIL 也会被 Python 的 execute 墙钟计入；反过来，native 调用自己也可能阻塞。** 不能由“已释放 GIL”推出“没有 GIL 竞争”，也不能由“wait 很短”推出“execute 的 native 虚调用很短”。

`wait`：字符串位于 `0x26630`。`0xd5fc` 构造名字，`0xd600`/`0xd604` 构造回调 `0xfde0`；`0xd610` 与 `0xd620` 分别写入同一 record 的名字与 `+48` 回调。在这条可追踪正常路径，`0xffdc` 设置 timeout=-1，`0xffec` 取 runner 虚表 `+24`，`0xfff4` 执行 `blr x3`，随后开始 buffer/map 清理。**在该 wrapper 围住这次虚调用的路径中未见显式 GIL release/reacquire**。此结论不泛化到未知重载或所有传递调用，也不把其他地址的通用 pybind GIL 辅助函数当成这条 wait 路径的调用。

这些路径在行为上与已保存的官方 v3.0 `runner_py_module.cpp` 对应；这只是交叉佐证，不能把该上游提交当作 ELF 的准确构建来源。

## event 5788 原始端点复算

同 TID499788，原始外部两行字段为 `[before_mono, after_mono, runtime, runqueue, timeslices]`：

```text
left  = [57955940904548, 57955940954238, 8990318315, 4060123226, 10385]
right = [57955980442573, 57955980492214, 8993766269, 4060123226, 10390]
execute_start  = 57955941287782
execute_return = 57955971455503
```

核验结果：两次读取均完整包围 execute 标记区间，读取各49.690/49.641µs；扩展包围窗39.587666ms、最小可能快照间隔39.488335ms。Q 两端均4060123226ns，**ΔQ=0**；runtime Δ3.447954ms、timeslices+5。execute 墙钟30.167721ms，线程 CPU0.580727ms，差29.586994ms。与此前独立复算一致，不是只采用摘要。

在身份稳定、计数有效前提下，这不支持“本次约30ms来自可观测 runnable 排队”；它兼容 GIL 重获、其他主动等待和 VART/驱动/设备阻塞。外部采样自身4.9789%单核，超过2%成本门槛，已经停用；不能把这次故障称作无扰动自然故障率，也不能排除其额外负载的间接作用。Q=0 不自动证明 GIL，不能从总墙钟中扣减 Q 并命名剩余为 DPU 时间，更不能推广排除此前 YuNet 的所有调度等待。

## 最小下一实验（只提出，未启用）

可只针对这份 SHA、当前 camera PID 内 optional TID，记录 `vart.so:0x10a10`（native 返回）、`0x10a20`（RestoreThread 调用前）、`0x10a24`（重获后）的单调时间，必要时加 `0x10a0c`（native 调用前）。前三点可判别返回后→GIL 重获的长尾；加入第四点才可量化 native 虚调用时长。`0x10a20` 是调用站点，不是 `PyEval_RestoreThread` 的函数本体入口；用调用后固定点代替对该 C 函数全进程 return probe，可缩小范围。记录须按 TID/调用代次配对，过滤其他绑定路径；异常路径无正常出口应标记不完整，不能伪造为0。

`readelf -lW` 确认首个 RX `PT_LOAD` 为 fileoff0/VA0、大小0x2d2e5；四个点均在 `.text` 且4字节对齐，故注册所需文件偏移就是上述相对地址。`0x10a0c`/`0x10a20` 分别是 BLR/BL 分支指令，需内核正确解码和模拟；若受控检查希望避开这两类指令，可选非分支邻点 `0x10a04`（`mov x0,x20`，native 调用前三条指令）与 `0x10a1c`（`mov x0,x19`，RestoreThread 调用前一条指令），但计时含参数准备，必须按此命名。不能把这一静态地址核验等同实际探针支持。

主任务后续的只读能力记录 `aura-model-inventory-20261021/native_trace_capability.response.json` 与对应 status（exit0）显示：同 boot，`CONFIG_PERF_EVENTS/UPROBES/FTRACE/UPROBE_EVENTS=y`，tracefs/uprobe_events存在可读写，perf与bpftrace未安装。**配置能力已确认；本独立任务没有创建探针，没有证明实际注册/命中/计时可用或满足成本门槛。** 后续先在无推理受控检查评估探针，再决定是否做有界短窗并自动移除。不能默认启用全局 trace、修改库指令或以“再包一层释放 GIL”当修复。正确性与 SFace 保护后恢复可用性应单独推进，30ms/5ms 与旧故障证据继续保留。

复核脚本 `verify_exact_elf.py` 验证了整件 SHA、架构、字符串、原始指令字和事件绝对端点；本次执行通过。数值结果 `exact-elf-evidence.json`；文件清单 `exact-elf-review-manifest.json`。未重复此前17项测试，未把静态核验计作板端推理测试。
