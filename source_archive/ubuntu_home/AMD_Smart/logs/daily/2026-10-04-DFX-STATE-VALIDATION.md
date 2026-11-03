# 2026-10-04：DFX manager 本机回归完成，待板端验收

## 结果

承接用户“然后呢”，推进上一轮源码修复的后续验证。8 项普通回归、8 项 ASan/UBSan（开启泄漏检测）全部通过，原系统镜像加载器 `--list` 检查通过。候选源码无需追加修改，AArch64 daemon 与上一轮为同一份二进制。本机测试始于 2026-10-03，归档在本地 2026-10-04 完成；证据采用 UTC。

本轮仍未检测到 ttyUSB/ttyACM 设备，未连接板端、切换服务或取得新板测。已请求用户接回 USB UART 或提供板卡 IP。当前缺口是实际硬件加载/卸载、官方推理对照、板端热更新、持久化及冷启动验收。

## 新增文件

新工作目录：[kv260-dfx-state-validation-20261003](/home/ghmd/kv260-dfx-state-validation-20261003/REPAIR_REPORT.md)。包含：

- `tests/state_regression.c`：真实 helper/parser/inotify 回归；FPGA 调用是明确标注的测试替身。
- `scripts/run_host_tests.py`：保留每轮 argv、退出码、日志、哈希及失败记录，运行普通及内存/UB 检查。
- `scripts/review_runtime.py`：在原系统镜像库中核对 ABI，并执行原 AArch64 加载器枚举，manager 本体未启动。
- `board/90-kv260-dfx-state-validation.conf` 与 `BOARD_VALIDATION_PLAN.md`：临时板端切换模板及实际状态核对/回滚步骤，均未部署。
- `REPAIR_REPORT.md`、各阶段证据、归档验证及源文件对应清单。

## 测试证据

| 验证 | 实际结果 |
|---|---|
| 旧缺陷复现 | 父设计删除后残留 2 个子包，内核监听由 14 只降到 13 |
| 新候选重扫描 | 10000 轮，监听稳定 |
| 多层删除及复用 | 200 轮，每轮 3 子包/6 孙目录全部回收，相似前缀邻目录保留 |
| flat 包创建/删除 | 1000 轮，内部与内核监听回到基线 4 |
| 活动生命周期 | flat/DFX、卸载失败与进行中保留、成功后回收、UIO 路径快照通过 |
| 目录事件/容量/列表边界 | 移入、重命名、未知 wd、溢出清理；500 watch/10 子包容量；63 包列表 8121 字节，均通过 |
| 8 线程并发 | 每轮 8000 次列包、600 次目录变化、1000 次模拟加载/卸载，结束后 3 基准包/4 监听 |
| ASan/UBSan | 同 8 项全部返回 0，泄漏检测开启且正常结束 |
| 原镜像加载器 | baseline/candidate 的 daemon/client 四个 ELF 枚举返回 0，所有强符号解析，client `.text` 一致 |

最初 TSan 编译缺少 `libtsan_preinit.o`，没有安装依赖，明确记录为未运行。沙箱内泄漏检测因 ptrace 限制未正常结束，不计为通过；解释具体原因并取得沙箱外执行许可后，完整重跑普通及 ASan/UBSan 并通过。失败日志均保留。

结果：[本机测试记录](/home/ghmd/kv260-dfx-state-validation-20261003/evidence/20261004T065645.836651Z-host-tests/status.json)、[加载器记录](/home/ghmd/kv260-dfx-state-validation-20261003/evidence/20261004T065849.413940Z-runtime-review/status.json)、[最终归档核验](/home/ghmd/kv260-dfx-state-validation-20261003/PACKAGE_VERIFICATION.json)。

## 最终候选与边界

[最终包](/home/ghmd/kv260-dfx-state-validation-20261003/release/dfx-state-20261004-host-verified.tar.gz) 为 229371 字节，154 个成员逐项回读一致，SHA-256 为 `b6d8ab335041dc7f42e13e167c07c8d00e44d4469ae5278db8013b02e18d7a42`。增量/vendor 两份补丁回放均得到 139/139 个与最终源码一致的文件。

daemon SHA-256 保持 `369c7fb0ddd023a7cf7af14896a7fda6036219a36f4980c73640889720c95dfd`，117856 字节；源码与原交叉构建的 139 个输入逐项一致。上一修复目录 1898 个封存文件重新核对全部保持原哈希。

测试替身验证的是 manager 状态逻辑，不证明真实 FPGA 驱动或加载/卸载正确。本机压力通过不替代缺失的 TSan，加载器枚举通过不替代真实 daemon 执行或板上推理。下一步按 [板端验收计划](/home/ghmd/kv260-dfx-state-validation-20261003/BOARD_VALIDATION_PLAN.md) 接入、只读核对状态、临时切换、验收及回滚；板测合格后再完成持久化与冷启动。
