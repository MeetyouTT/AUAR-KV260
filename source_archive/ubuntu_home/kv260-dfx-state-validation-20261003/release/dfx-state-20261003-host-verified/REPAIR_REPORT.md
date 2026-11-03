# DFX manager 本机回归与加载器验证结果

## 结果

**本机验证已通过，板端尚未替换。** 8 项普通回归、8 项 ASan/UBSan（开启泄漏检测）全部返回 0；原系统镜像加载器枚举检查通过。本轮无需继续修改修复源码：139 个文件与上一轮编译输入完全一致，使用同一份 AArch64 候选 daemon。

测试目录为 `/home/ghmd/kv260-dfx-state-validation-20261003/`。本机日期为 2026-10-03；证据目录使用 UTC，日期为 2026-10-04。原修复目录、候选包和封存证据均保留。

## 验证内容

测试直接编译真实 `daemon_helper.c`、JSON parser 和输出/断言代码，使用真实 Linux inotify 和临时文件系统。仅 FPGA 加载/卸载、shell UIO 查询调用由显式测试替身实现；测试替身的成功、失败与进行中返回值用于验证 manager 状态，而非模拟真实 FPGA 性能。

| 用例 | 实際结果 |
|---|---|
| 列包重扫描 | 10000 轮；内部监听及内核监听均保持 4 |
| 父设计/多层子目录清理 | 200 轮；每个父设计含 3 个子包、6 个孙目录；完整回收，父槽位复用无残留，相似前缀邻目录保留 |
| 活动设计生命周期 | flat/DFX 都通过；删除目录后保持已加载槽位，卸载失败和进行中保留状态，成功后回收；线程私有 UIO 路径在卸载后仍有效 |
| 事件与移动 | 移入、重命名、未知描述符和队列溢出后的消失路径清理通过 |
| flat 包生命周期 | 1000 轮实际创建/删除，监听回到 4 |
| 容量与非法参数 | watch 500、子包 10 的容量边界；登记失败无孤立内核监听；非法槽位/小缓冲区通过 |
| 列表缓冲区 | 63 个包；输出 8121 字节，未超出 8192 字节容量 |
| 并发 | 8 线程：8000 次列包、600 次目录变化、1000 次模拟加载/卸载；结束后 3 个基准包、4 个监听，状态一致 |

这 8 项在普通版本和 ASan/UBSan 版本各执行一次，全部通过。没有检测到本轮用例中的越界、未定义行为或泄漏。TSan 未执行：现有 GCC 9 缺少 `libtsan_preinit.o`，没有安装额外依赖；本轮并发压力通过不能替代 TSan 数据竞争检测。

此外，对上一 watch 修复版本运行同一父目录删除用例，实际复现 **2 个残留子包**：内核监听由 14 只降到 13，未回到基线 4。新候选在相同布局下完整回收。

## 证据与候选身份

- 测试源码：[state_regression.c](/home/ghmd/kv260-dfx-state-validation-20261003/tests/state_regression.c)。
- 本机结果：[status.json](/home/ghmd/kv260-dfx-state-validation-20261003/evidence/20261004T065645.836651Z-host-tests/status.json)，包含真实 argv、退出码、用时、结果行及完整日志摘要。
- 原镜像 ABI/加载器结果：[status.json](/home/ghmd/kv260-dfx-state-validation-20261003/evidence/20261004T065849.413940Z-runtime-review/status.json)。四个 ELF 的强符号均能解析；原 AArch64 加载器在 QEMU 中执行 `--list` 返回 0，manager 本体未启动；客户端 `.text` 保持一致。
- 编译输入对应关系：[reused_cross_build.json](/home/ghmd/kv260-dfx-state-validation-20261003/evidence/reused_cross_build.json)。与上一轮 AArch64 构建的 139 个输入文件逐项 SHA-256 一致。

最终 daemon 为 117856 字节，SHA-256 保持：

`369c7fb0ddd023a7cf7af14896a7fda6036219a36f4980c73640889720c95dfd`

本轮打包目标为 `release/dfx-state-20261003-host-verified.tar.gz`，新增本机验证证据和测试源码；归档核验及补丁回放结果见本目录 `PACKAGE_VERIFICATION.json`。相对上一已板测 watch 版本的实际修复仍只涉及 `src/daemon_helper.c` 和 `example/sys/linux/dfx-mgrd.c`。

## 遇到的问题与处理

1. 首次尝试 TSan 编译缺少 `libtsan_preinit.o`，将其记录为环境缺项，不计为通过。
2. 沙箱内 ASan 的泄漏检测在结束时因 ptrace 限制失败，虽然扫描用例本身已执行，该轮不计为通过。说明原因并获得沙箱外执行许可后，完整重跑了普通与 ASan/UBSan 用例，开启泄漏检测并正常结束。失败日志保留。
3. 未发现需要继续修改候选源码的回归失败，原候选及已封存输入保持一致。

## 下一步

接回 KV260 USB UART 或提供板卡 IP，然后按 [板端计划](/home/ghmd/kv260-dfx-state-validation-20261003/BOARD_VALIDATION_PLAN.md) 先只读核对状态、保存恢复点，再临时切换候选，验证官方 DPU 推理和热更新。当前仍未检测到串口设备，没有本轮真实 FPGA、服务切换或冷启动证据。

本机复现：

```sh
cd /home/ghmd/kv260-dfx-state-validation-20261003
python3 scripts/run_host_tests.py
python3 scripts/review_runtime.py --loader-check
```

泄漏检测需要可用的进程检查权限。`--no-leak-check` 仅用于环境限制下运行内存/UB 检查，使用该参数不能记为泄漏检查通过。
