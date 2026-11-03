# 运行时复现与参赛附件：本轮结果

记录日期：2026-10-02 至 2026-10-03。本轮继续主机准备、复现与证据整理；没有取得新的板端状态。

## 结果

**DFX manager 和 ZOCL 的独立源码准备及新构建入口已在这台 Ubuntu 上执行通过。** 已打包带源码、原许可、补丁、日志、版本说明、协作摘录和 skill/ 的运行时附件。原工程、工具、用户 ZIP、原板卡基线及既有封存证据保留。

这是 AURA 参赛工程的运行时附件，完整应用、PWM、全部自研硬件源码导出、长期板测和最终参赛提交仍需完成。最新评分细则与报名资格未完成核验；没有发布 GitHub/Gitee。

最新文件：

- [附件说明](payload_v2/README.md)。
- [已完整主机复验的源码包](release/kv260_runtime_annex_verified_20261003.tar.gz)：5,815,593 字节，525 个文件纳入索引，526 个压缩包成员回读哈希通过。
- [验证摘要](payload_v2/evidence/verification_summary.json)。
- [构建入口与复现方法](payload_v2/docs/reproducibility.md)。

压缩包 SHA-256：

```text
5cf9f945f9269c8df844e41c49f50d738fa2e7d9fd4d79bf25c97a743033ffab
```

初版包和完整上游快照另行保留，最新交付以 verified 包及 payload_v2 为准。

## 实际完成与证据

| 项目 | 实际结果 |
|---|---|
| 原证据保护 | 五份旧索引共 1,779 条记录检查通过；索引重复引用按记录数统计 |
| DFX 源码 | 固定 bc06691eb35d7f0acb7c2508b6d050d77b0264a0；补丁只改 daemon_helper.c；139 文件逐项核对 |
| XRT 源码 | 固定 43926231f7183688add2dccfd391b36a1f000bea；原完整快照 2,278 文件保留；附件导出 840 个运行时核心文件 |
| 源依赖覆盖 | 原完整构建 .cmd 中 69 份 XRT 源码/头文件全部在导出中；新 ZOCL 完整编译再次通过 |
| DFX 新入口 | 三个独立目录成功；GCC 11.2.0、CMake 3.21.1、并行 4；daemon 84 个强符号依赖全部解析，原镜像 loader --list 通过 |
| 内核准备 | 固定 19984dd147fa7fbb7cb14b17400263ad0925c189；原镜像配置只变化 CC_VERSION_TEXT 的 .real 名称 |
| 完整内核依赖 | vmlinux/modules/Module.symvers 成功；并行 8，实际编译 477.246 秒；与旧符号表逐字节一致 |
| ZOCL 新入口 | prepare/kernel/module 三阶段通过；正常编译、strip、modinfo 与 ELF 检查，无安装或加载 |
| 技能工具 | 9 项本机隔离验证和技能结构检查通过；板端预检拒绝开发电脑的检查通过 |
| 包审阅 | 英文 ASCII 路径检查、相对文档链接、文件索引和压缩包回读哈希通过；部分上游/标准大写文件名保留 |

内核符号表 SHA-256：

```text
6e582b60f2a379055924117f930e5ca0fac44c98d56f3b374dc3ce278da7b8ed
```

完整命令、退出码和原始日志在 payload_v2/evidence/reproduction/；工具失败/成功、历史板测输出和原内核构建日志也随附。大模型材料是注明范围的可见摘录，完整界面对话导出尚待补齐。

## 新输出与已板测输入的区别

| 文件 | 本轮新输出 | 已板测复用输入 |
|---|---|---|
| dfx-mgrd | 117,488 字节，fe77ab54036e7ee5bdbee7d0321b4b24533825f162eb1e47687cdb28473725f5 | db9c25f09f1178177884b1114c57f32c076f1e7f9cdd0d12b7a896039038a46c |
| zocl.ko | 339,408 字节，9c1e7c008b07442e8b7beb8d2938fccf5d5ea950b13fc2a6172d330304715b78 | 339,600 字节，5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412 |

两类文件分别位于 host_rebuild/ 与 tested_inputs/。本次新 ELF 未在目标板执行，不能用编译或 ABI 验证替代新板测；下一步受控启用采用原已板测输入。

新 ZOCL srcversion 与旧修复版同为 `9BDC942A6014BCCBD1DCB78`，vermagic 同为 `5.15.36-xilinx-v2022.2 SMP mod_unload aarch64`。新旧 .text 逐字节一致；变化在 .note.gnu.build-id、.rodata.str 和 .symtab。字符串区将源码路径前缀规范化后逐字节一致；据实际比较记录路径差异，不声称完整 ELF 哈希复现。

DFX 两个初始独立输出的 .text 也相同，完整 ELF 哈希不同，字符串中可见不同源路径。没有为追求相同哈希改变原编译语义。详细比较：[rebuild_comparison.json](evidence/rebuild_comparison.json)、[zocl_module_comparison.json](evidence/zocl_module_comparison.json)。

## 本轮遇到的问题与处理

1. **本机 socket 隔离验证首次被沙箱拒绝。** 创建 Unix socket 返回 EPERM；失败 JSON 保留。取得沙箱外本机验证权限后 9 项通过，没有访问板卡。
2. **完整 XRT 上游快照的 6 个路径包含 ++ / %。** 初次命名审阅失败并保留证据。保留完整快照，按 ARM ZOCL 实际构建范围导出不改变内容的运行时核心；完整新编译通过。没有改名厂商文件或换 commit。
3. **新模块有 4 条编译 warning。** 未使用 flags、slot_id、ret，以及未检查 copy_from_user 返回值。原 baseline、旧 patched 构建也有相同四类警告；本轮原样保留。prepare/kernel 没有 warning: 行，模块阶段正常退出 0。
4. **工具入口与标准/上游文件的大小写。** 英文 ASCII 路径检查通过，严格全小写规则对 CMakeLists.txt、Makefile、SKILL.md 等的处理还需结合提交平台确认；不能把这项检查称为整件作品规则验收。

旧 overlay 属性警告、重复 /boot fstab、既有 DRC/时序限制继续记录。两项原运行时缺陷仍存在于此前恢复的原程序中；本次未作永久启用。

## 下一步

本次末尾 Ubuntu 仍无 /dev/serial/by-id，未获得新 boot ID 或实时板端状态。接回使用备用卡的 KV260 电源和 Ubuntu USB 串口后，先执行新的预检与恢复点备份，再受控启用两项已板测修复，进行 30 轮重载及至少 30 分钟推理/内存/日志采样。网线可继续直连 Win11，无需重新烧录 SD 卡。

操作顺序、同模型同图的完整 Top-5 要求和恢复方法见 [board_next_steps.md](payload_v2/docs/board_next_steps.md)。永久启用、重启验收与 PWM 仍未实施。
