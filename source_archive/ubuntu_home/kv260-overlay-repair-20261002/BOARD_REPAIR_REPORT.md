# KV260 ZOCL 修复：真实板端验证与恢复报告

日期：2026-10-02（America/Los_Angeles）；板端流程结束于 `2026-10-03T01:54:54Z`。

**结论：修复候选在官方应用上完成三轮加载、推理、卸载，均未新增目标节点引用错误；同图分类一致，性能未见明显下降。验证后已经恢复磁盘原驱动和官方应用。修复尚未永久安装，M3 尚未板测。**

本报告接续主机侧 [OVERLAY_REPAIR_REPORT.md](OVERLAY_REPAIR_REPORT.md)。旧报告、旧 README 和旧验证计划保留其当时的“待板测／已暂停”状态，本次事实以本报告和新证据为准。

## 1. 本轮真实环境

| 项目 | 实测结果 |
|---|---|
| 板卡 | `ZynqMP SMK-K26 Rev1/B/A`，KV260 |
| 备用卡 CID | `0353445345333247805558c00401a100` |
| 根文件系统设备 | `mmcblk1p2` |
| 系统 | PetaLinux `2022.2_release_S10071807` |
| 内核 | `5.15.36-xilinx-v2022.2 #1 SMP Mon Oct 3 07:50:07 UTC 2022` |
| 原加载模块 srcversion | `0991D1B457855C8987936E6` |
| 实际原参数 | `enable_xgq_ert=1` |
| 起始及最终活动应用 | `kv260-benchmark-b4096`，唯一活动 slot 0 |
| UART | Ubuntu `/dev/ttyUSB1`，115200；按 USB serial-by-id 核对设备 |
| 网络 | 保留板网口直连 Win11；Ubuntu 通过 UART 执行本轮操作 |

实时 `/proc/config.gz` 解压后为 190806 字节，与镜像提取的内核配置逐字节相同，SHA-256 为 `3d97bf208930f5696093d2d1999b4a0b16bcb121c97d70ca286bb8d4986e81ef`。板端原 `zocl.ko`、XRT 2.14.0 核心库、`dfx-mgrd`、`libdfx.so.1.0` 四份文件的实际哈希全部与镜像输入一致。

ZOCL 对应 `card1/renderD128`；Xorg 只打开显示驱动的 `card0`，没有占用 ZOCL。切换动作前检查 ZOCL 客户端、holders/refcnt、应用状态、卡身份及本次 boot_id；没有强杀桌面或强卸载模块。

板端墙上时钟不准确，没有修改它。日志隔离采用主机 UTC 与板端 `/proc/uptime`。实测核验见 [preflight_and_diagnostics_review.json](evidence/board_validation_20261003T005805Z/preflight_and_diagnostics_review.json)。

## 2. 原因及实际修复

固定输入保持不变：XRT/ZOCL commit `43926231f7183688add2dccfd391b36a1f000bea`，Linux commit `19984dd147fa7fbb7cb14b17400263ad0925c189`。本轮使用上一阶段已经编译并核验的候选，没有重新选择源码版本或重建硬件平台。

原驱动的 `zocl_get_zdev()` 经 `zocl_find_pdev()` 调用 `bus_find_device()`，取得设备引用后没有释放。平台设备的最终 release 因残留引用不能完成相应 `of_node_put()`。最小补丁为 getter 补齐释放，并补齐 CU 中断设备查询的成功及失败出口释放；三个文件共 21 行新增、6 行删除。源码和原模块反汇编证据见旧报告及 [fix.patch](bundle/kv260-zocl-reference-repair-20261002/fix.patch)。

本轮在原驱动下再次卸载官方应用，内核真实记录：

```text
[ 2066.695999] OF: ERROR: memory leak, expected refcount 1 instead of 2, of_node_get()/of_node_put() unbalanced - destroy cset entry: attach overlay node /axi/zyxclmm_drm
```

该次底层 `dfx-mgr-client -remove` 返回 **0**，应用已退出；内核引用错误实际触发 **1 次**。这说明命令成功不能代替内核释放检查。

随后正常 `rmmod zocl`，从独立 staging 临时 `insmod zocl.ko enable_xgq_ert=1`。实时 `/sys/module/zocl/srcversion` 确认为 `9BDC942A6014BCCBD1DCB78`。没有 force 加载、伪造版本、覆盖磁盘原模块或修改内核诊断。

修复后三轮未再触发该错误，结合源码与原二进制证据，支持这份引用释放补丁解决了本次 KV260 官方应用串行卸载场景的目标缺陷；不能扩展为所有 ZOCL 路径、长期运行及并发卸载均已无泄漏。

## 3. 执行步骤与结果

只读预检 4 条命令成功；主验证的 25 个阶段共 **48 条命令**全部返回 0，输出完整性校验通过。候选归档通过 UART 36 帧确认传输，整包及解包成员 SHA-256 校验成功。

独立板端目录：`/home/root/kv260-zocl-repair-20261003T005805Z/`。其中保存实际原驱动、模块参数、boot_id、内核配置、启动 FDT、完整实时设备树、官方固件、VART 配置和起始内核日志；旧基线备份没有覆盖。

| 阶段 | 同图推理 | 卸载新增目标引用错误 | 新增异常／其他 ERROR |
|---|---|---:|---:|
| 原驱动对照 | 通过 | 1 | 0 |
| 修复第 1 轮 | 通过 | 0 | 0 |
| 修复第 2 轮 | 通过 | 0 | 0 |
| 修复第 3 轮 | 通过 | 0 | 0 |
| 恢复原驱动及官方应用 | 通过 | 本轮恢复后没有再次卸载原应用 | 加载过程 0 |

每个动作分别保存命令、真实返回码、UART 原始字节、解码输出、uptime 与内核日志快照。`uptime_after` 表示 AFTER 快照开始，不能当作日志截断上界。例如原错误时间 `2066.695999` 晚于 AFTER 快照起点 `2066.64`，仍被正确计入。

恢复时的内核日志保留区间为 `1159.484426–3743.387299`，覆盖原驱动退出后的起点 `2202.59` 及全部修复循环；该起点之后没有新的 `expected refcount` 错误，排除了这段已保留区间内的延迟诊断。

证据入口：[board_validation_summary.json](evidence/board_validation_20261003T005805Z/board_validation_summary.json)、[cycle_controller.result.json](evidence/board_validation_20261003T005805Z/cycle_controller.result.json)。`progress` 和两个 checkpoint 是执行中的历史快照；其中未更新的中间状态不能替代最终结果。

## 4. 同模型、同图片与性能

所有轮次及恢复后均核对：一个 DPU CU，`DPUCZDX8G_ISA1_B4096`，300 MHz，地址 `0xa0010000`，指纹 `0x101000056010407`。沿用原官方 XCLBIN，UUID 为 `eedb44e9-3f77-0244-9ea9-23b953894638`；IP 为 v4.1.0，生成时间 `2022-11-30 19-15-00`。

模型为板端原 `resnet18.xmodel`，图片为原 `pytorch-resnet-dog.jpg`。模型 SHA-256：`4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef`；图片 SHA-256：`f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a`。

原驱动、修复三轮及恢复后的 Top-5 分数全部一致：

| 类别索引 | 类别 | 分数 |
|---:|---|---:|
| 258 | Samoyed | 0.949879 |
| 270 | white wolf | 0.00931229 |
| 259 | Pomeranian | 0.00821807 |
| 257 | Great Pyrenees | 0.00498451 |
| 279 | Arctic fox | 0.00388194 |

同一轮原／修复驱动分别使用原程序与图片列表，各线程数先预热 10 秒，再运行 3 次 60 秒；每次温度前后快照、程序输出和返回码完整保留。

| 线程数 | 原驱动三次 FPS | 修复驱动三次 FPS | 原／修复中位数 FPS | 中位数变化 |
|---:|---|---|---|---:|
| 1 | 215.130 / 215.148 / 215.080 | 215.106 / 215.152 / 215.129 | 215.130 / 215.129 | −0.000465% |
| 2 | 238.837 / 238.632 / 238.932 | 238.982 / 238.885 / 238.831 | 238.837 / 238.885 | +0.020097% |

结论是本轮短时实测未见明显性能下降；这些微小差异不能作为性能提升结论，也不代表长时压力验收。

## 5. 产物、恢复状态与证据索引

| 本次使用的已构建候选 | SHA-256 |
|---|---|
| `artifacts/patched/zocl.ko`，339600 字节 | `5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412` |
| `bundle/kv260-zocl-reference-repair-20261002.tar.gz`，108477 字节 | `3126707fe3c9165fd743dcbcc1408247337b538524e8b4de6c4edaa4e997cfef` |
| 磁盘原驱动，337152 字节（输入，未覆盖） | `215fe760dafb6766545e308d8bc207c31712154fe5a8ed08342a101a5482a98d` |

验证结束后正常卸载修复模块，以 `modprobe zocl enable_xgq_ert=1` 恢复磁盘原驱动，再加载官方应用。最终实测：

- 加载 srcversion 为原 `0991D1B457855C8987936E6`，模块参数与起始一致。
- 唯一活动应用为 `kv260-benchmark-b4096` slot 0；FPGA manager 为 `operating`。
- `firmware-name=kv260-benchmark-b4096.bit.bin`，`/etc/vart.conf` 保持原 XCLBIN 路径。
- 官方 BIN、DTBO、shell.json、XCLBIN、模型及 prototxt、图片、图片列表、分类／性能程序、旧备份归档共 11 份文件，首尾哈希全部一致。
- 恢复后的 DPU 身份及同图 Top-5 再次通过。

旧 [EVIDENCE.sha256](EVIDENCE.sha256) 的 177 项继续保留并校验通过；本次新增板测、脚本、报告和当天日志使用独立 [BOARD_EVIDENCE.sha256](BOARD_EVIDENCE.sha256)。校验记录见 [BOARD_EVIDENCE_VERIFY.json](BOARD_EVIDENCE_VERIFY.json)。原 UART 证据均保存在新 run 目录，未编辑诊断内容。

## 6. 实际保留问题与后续

1. **修复未永久启用。** 板卡当前运行原驱动与官方应用，原驱动缺陷仍存在；再次卸载原应用仍可能触发同一诊断。候选及备份留在独立目录，后续应使用受控切换和恢复流程。
2. **动态属性警告未消除。** 起始快照 16 条；修复三次加载及最终恢复加载各新增 16 条。跨快照按带 uptime 的完整行去重，共观察到 80 条；最后内核环形缓冲快照仍保留其中 64 条。它们是 `memory leak will occur if overlay removed, property:`，须与实际 `expected refcount` 节点错误分别统计。
3. **旧泄漏对象未回收。** 原驱动退出时已产生的额外引用不能由新模块自动清理；未手工修改引用计数。本次没有宣称整个启动周期的内存泄漏为零。
4. **三轮属于有限验证。** 长时压力、推理与卸载并发、其他 ERT／soft-kernel／Versal 路径未验收。
5. **M3／运动 IP 尚未板测。** 主机上的 DPU 加 AXI-Lite 工程继续保留，PWM 与执行器不在本轮验证范围。没有加载 M3、写自研寄存器、烧录 SD/QSPI 或重启。

下一阶段先审阅修复驱动在备用卡上的持续使用及恢复方案，再按现有 [M3_TEST_CARD_PLAN.md](../kv260-m3-axilite-20261002/docs/M3_TEST_CARD_PLAN.md) 执行独立的 M3 身份、AXI-Lite 只读检查、同模型同图推理与性能复测。使用本轮已验证候选及原参数，保留原官方基线和独立备份；任何步骤失败先留存证据并停止后续切换。本次报告不把这些后续步骤记为已完成。
