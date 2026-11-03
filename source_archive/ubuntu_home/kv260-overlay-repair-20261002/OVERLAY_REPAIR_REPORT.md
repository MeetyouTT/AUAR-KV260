# KV260 overlay / ZOCL 修复报告

日期：2026-10-02。状态：**主机侧已定位缺陷、生成补丁并编译通过；板端修复效果待验证。** 用户已确认目前没有板卡，板卡留在实验室。

用户随后要求需要板卡时先暂停。本轮已保存检查点并暂停后续工作；用户通知继续前不启动新的构建或板端操作。

## 1. 结论和证据边界

已确认原 XRT 2.14 ZOCL 存在设备查询引用未释放的缺陷：`bus_find_device()` 增加设备引用，`zocl_get_zdev()` 获取 driver data 后直接返回，没有配对释放。原镜像模块的反汇编包含相同调用路径。

平台设备最终释放时才执行其 `of_node_put()`。设备引用残留会阻止这一步，足以解释 `/axi/zyxclmm_drm` 在 overlay 删除时仍保留一个额外节点引用的现象。**这是具体的源码和二进制缺陷证据；尚未通过板端实验确认它是旧日志错误的唯一原因。**

旧板测中，官方应用与 DPU 4.1 对照应用各卸载一次，都记录 actual refcount 2、expected 1。两次卸载命令的真实返回码均为 0。这是卸载过程的内核内存泄漏诊断，不能由命令返回 0 判定不存在问题，也不能据此断言卸载命令失败。

原日志中的动态属性泄漏警告另行保留，本补丁没有删除诊断或修改规则。未在板卡加载修复驱动、切换应用、访问寄存器、烧录或重启。原参考工程、官方固件、DPU 4.1 对照工程、M3 工程及旧封存索引均保持为输入。

## 2. 精确版本定位

| 输入 | 固定版本或证据 |
|---|---|
| 官方配方仓库 `meta-xilinx` | `rel-v2022.2`，commit `2e60ee606a1a9a08db72b69e018b1ed1fd2d1047` |
| 原 XRT / ZOCL 源码 | commit `43926231f7183688add2dccfd391b36a1f000bea`，配方版本 `202220.2.14.0` |
| 原 Linux 源码 | commit `19984dd147fa7fbb7cb14b17400263ad0925c189`，Linux 5.15.36 |
| 目标内核 release | `5.15.36-xilinx-v2022.2` |
| 原驱动 srcversion | `0991D1B457855C8987936E6` |
| 目标 vermagic | `5.15.36-xilinx-v2022.2 SMP mod_unload aarch64` |
| 配方的 dfx-mgr | `bc06691eb35d7f0acb7c2508b6d050d77b0264a0`，版本 1.0 |
| 配方的 libdfx | `f2b7bbca9d6936141024becfb92266600eeefc2b`，版本 1.0 |

XRT `2022.2` 分支当前下载的 HEAD 是后续更新后的 `c833695062f3fd8d20427a66f632737047922657`，没有使用它构建修复。独立 `XRT_baseline` 和 `XRT_patched` worktree 都固定在原配方 commit，硬件参考工程版本没有重新选择。

从已有官方 rootfs 镜像只读提取 `zocl.ko`、XRT 核心库和 manager 二进制。XRT 核心库实际含有版本 `2.14.0` 和上述完整 commit；驱动 srcversion/vermagic 与历史板端记录一致。**这些提取结果是离线镜像证据，仍需核对实验室板卡的实时文件哈希。** 所有提取命令、字节数和哈希保存在 [extraction.json](evidence/image_files/extraction.json)。

## 3. 调用链和补丁范围

| 位置 | 原行为与处理 |
|---|---|
| Linux `drivers/base/bus.c:322` | `bus_find_device()` 在匹配后执行 `get_device()` |
| ZOCL `zocl_drv.c:285` | `zocl_find_pdev()` 将带引用的 device 转成 platform device 返回；此函数的所有权保持不变 |
| ZOCL `include/zocl_drv.h:297` | getter 临时查询 `zyxclmm_drm`，修复后先取得 driver data，再 `platform_device_put()` |
| ZOCL `cu.c` | 补齐 `user_manage_irq`、`configure_irq`、`cu_probe`、`cu_remove` 的中断设备查询释放；包含 IRQ 注册失败出口 |
| Linux `drivers/base/platform.c:550` | 平台设备 release 才释放对应 OF 节点引用 |
| Linux `drivers/of/dynamic.c:464` | changeset 销毁时检查附加 overlay 节点的引用数并输出实际错误 |

只有独立候选源码的三个文件发生改动：`include/zocl_drv.h`、`cu.c`、`zocl_drv.c`，21 行新增、6 行删除。最后一个文件只补充所有权说明。补丁见 [candidate-patch.log](evidence/source_review/candidate-patch.log)，原始文件及固定源码副本见 [源码证据清单](evidence/source_review/manifest.json)。

原 `zocl_drm_platform_remove()` 已配对执行 `drm_dev_unregister()` 和 `drm_dev_put()`，原二进制也有这两个调用，本补丁未重复添加释放。

getter 返回借用的 driver data，调用者仍需要与 ZOCL remove 串行化；本轮没有宣称修复任意并发 hot-unplug。ERT、reset_ps、soft-kernel、Versal OSPI 的其他直接 lookup 路径不在本次 KV260 DPU 最小补丁范围内，未宣称整个 ZOCL 所有平台的引用问题均已修复。中断设备引用和 OF 节点引用也不能按调用次数直接等同计数。

## 4. 实际编译与核验

复用现有 Vitis 2022.2 SDK 的 AArch64 工具链：GCC 11.2.0，GNU assembler/ld 2.37.20210721。内核配置从原 Image 的 IKCONFIG 区域提取，不使用通用 defconfig。

`olddefconfig` 后只有 `CONFIG_CC_VERSION_TEXT` 多了 `.real`，所有其余配置一致，包含 `CONFIG_GCC_VERSION=110200`、SMP、模块卸载、OF overlay 和结构相关配置。配置差异保存在 [config-changes.json](evidence/build/20261002T154613.267004Z-prepare/config-changes.json) 与原始 `config.diff`。

内核版本后缀处理采用原 Honister 构建类的正常步骤：在独立 S/B 创建空 `.scmversion`，保留 `CONFIG_LOCALVERSION_AUTO=y`。该做法来自 [OpenEmbedded kernel.bbclass 的 kernel_do_configure](https://raw.githubusercontent.com/openembedded/openembedded-core/honister/meta/classes/kernel.bbclass)。没有修改 `utsrelease.h`、伪造符号表、强制 vermagic 或强加载模块。

| 实际命令入口 | 结果与原始证据 |
|---|---|
| `python3 scripts/build_driver.py prepare` | 通过；配置比较、`modules_prepare`、`kernelrelease`；[完整状态](evidence/build/20261002T154613.267004Z-prepare/status.json) |
| `python3 scripts/build_driver.py kernel` | 通过；8 jobs，`vmlinux modules`，489.711 秒；[完整状态](evidence/build/20261002T154647.665191Z-kernel/status.json) |
| `python3 scripts/build_driver.py baseline` | 通过；原版模块编译 4.175 秒；[完整状态](evidence/build/20261002T155511.171030Z-baseline/status.json) |
| `python3 scripts/build_driver.py patched` | 通过；修复模块编译 3.765 秒；[完整状态](evidence/build/20261002T155632.273795Z-patched/status.json) |
| `python3 scripts/review_module_artifacts.py` | 8 项主机核验全部通过；[完整结果](evidence/module_review/review.json) |

每个编译阶段执行冻结的 runner 副本，保存脚本哈希、完整 argv、返回码、日志和工件哈希。`vmlinux` 与内核模块构建提供真实 `Module.symvers`，仅用于驱动依赖校验；没有生成或部署新的系统卡镜像。

主机核验结果：

- 三份模块均为 AArch64 relocatable ELF，名称为 `zocl`，vermagic 完全相同。
- 原版重建模块的 srcversion 与镜像一致；`.text`、`.rodata`、`.data`、`.modinfo` 四个 section 的字节哈希也全部一致。整文件哈希不同，未宣称重建 ELF 整文件逐字节相同。
- 三份模块的 216 个强未定义符号集合相同，全部能在重建内核的真实导出表中解析。
- `CONFIG_MODVERSIONS` 原本关闭；三份模块均无 `__versions` section。
- 修复版反汇编在 getter 所在的 CU 创建/删除路径，以及中断配置路径新增配对 release 调用；完整反汇编保留。
- 原版和修复版均保留 4 条编译警告：两个未使用局部变量、一次未检查 `copy_from_user` 返回值、一个未使用的 IRQ flags 变量。没有通过修改警告规则消除它们。
- 新增 Python 工具与嵌入式只读查询完成语法核验；未执行板端测试。

外部 ZOCL 模块自己的 `Module.symvers` 为空，因为它没有导出符号；用于解析导入的 **内核** `build/kernel/Module.symvers` 为 774177 字节，二者不能混为一谈。

## 5. 生成工件

| 工件 | 字节数 | SHA-256 |
|---|---:|---|
| 镜像原驱动，离线输入 `evidence/image_files/zocl.ko` | 337152 | `215fe760dafb6766545e308d8bc207c31712154fe5a8ed08342a101a5482a98d` |
| 原版新编译 `artifacts/baseline/zocl.ko` | 338840 | `81b53b5d5336881bd112d5aa0960dd70a4301d7950835d08e5a8c61da8d562d9` |
| 修复版新编译 `artifacts/patched/zocl.ko` | 339600 | `5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412` |
| 修复版带调试信息 `artifacts/patched/zocl.debug.ko` | 7435624 | `bb0314f3e7e6d5c3fb3a85445215029a67d72fef144c333958eba4c16fad049c` |
| 内核依赖 `build/kernel/Module.symvers` | 774177 | `6e582b60f2a379055924117f930e5ca0fac44c98d56f3b374dc3ce278da7b8ed` |

修复版 srcversion：`9BDC942A6014BCCBD1DCB78`。运行候选 bundle 位于 `bundle/kv260-zocl-reference-repair-20261002`，归档位于 `bundle/kv260-zocl-reference-repair-20261002.tar.gz`，归档摘要与成员核验见 `bundle/archive_manifest.json`。镜像中的原驱动是输入，明确不列为本轮新编译成果。

## 6. 未完成项与接续

**当前具体阻塞：没有板卡。** 用户已确认板卡留在实验室。此前 Ubuntu 的真实 USB 枚举未检测到 UART，到 `192.168.50.2` 的路由走 Wi-Fi 网关，不是板卡直连链路，证据见 [连接状态](evidence/host-connection-20261002T155209.351761Z.json)。

准备好的 `evidence/board_preflight/01-readonly.commands.json` 限定备用卡 CID、K26、目标内核并检查原驱动和运行时文件，只读采集不会切换 app 或访问 PL 寄存器。没有因为缺少设备而执行该采集器。

回实验室后按 [板端验证与恢复方案](docs/BOARD_VALIDATION_PLAN.md) 继续。需要先验证实时内核、配置、原模块哈希与调用者状态，再临时加载候选并在官方 app 上检查推理与新 overlay 的释放。旧泄漏引用不会由修复模块自动清理，首次旧应用卸载与修复后的新循环必须分开归档。

待确认项：原板实时文件是否与离线镜像一致；临时模块能否正常加载；至少三个新循环是否无节点引用错误；同模型同图分类及性能是否保持；原驱动与官方应用能否恢复。M3 加载、AXI-Lite 寄存器验证、运动 IP / PWM 和长期并发运行仍未完成，不计为本轮修复通过项。
