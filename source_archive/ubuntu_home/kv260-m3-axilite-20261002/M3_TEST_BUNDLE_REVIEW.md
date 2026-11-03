# M3 独立测试包：主机审阅与下一步

## 结果

**包含 DPU 4.1 B4096＋最小 AXI-Lite 寄存器的新测试包已准备并通过主机一致性核验。M3 尚未加载到板卡，寄存器和 DPU 共存尚未实测。** 本轮没有板端安装、切换、重启或烧录，也没有重新构建 Linux 系统。

工程沿用固定 commit `a3a83f179503792226adf83082aee7c05de620b4`。硬件成果和原始审阅见 [M3_BUILD_REPORT.md](M3_BUILD_REPORT.md)。本报告及打包文件作为新增补充，原 11 项工件、68 项审阅索引以及父工程的 15 项工件、104 项板测证据索引均重新校验通过。

## 已通过项

| 检查 | 实际结果与证据 |
|---|---|
| 新构建来源 | BIN、XCLBIN、HWH、arch.json 的复制文件与本轮 M3 原始工件 SHA-256 一致；没有将旧预编译固件列为新硬件成果。 |
| BIN 加载格式 | 完整 PL Bootgen BIN；前 64 字节与官方镜像原 BIN 相同。这是格式对照，不是 M3 上板证据。 |
| 文件名和 shell | 独立 app `kv260-benchmark-b4096-m3`；`shell_type=XRT_FLAT`、`num_slots="1"`；DTBO `firmware-name` 与 BIN 名精确相同。 |
| DTBO 内容 | 使用官方镜像 DTBO，只改变 `firmware-name`；`fpga_full` fixup 保留，无 `partial-fpga-config`，保留 `fpga-config-from-dmabuf`。候选 DTS 可重新编译并往返保持语义一致。 |
| 设备树主机合并 | 未修改的官方 DTBO 和候选 DTBO 均用已有独立 DTC/libfdt 1.7.2 合并成功；合并后的语义差异也只有固件名。没有重复旧 1.6.1 合并失败对照。 |
| 硬件地址 | 本轮新 HWH：M3 `0x80080000–0x80080fff`，DPU `0xa0010000–0xa0010fff`。 |
| 架构和元数据 | 沿用已封存 M3 审阅的 HWH/XCLBIN 元数据；DPU 4.1、ARGMAX=1、1 CU，指纹 `0x101000056010407`，匹配原测试模型要求。XCLBIN 不含 BITSTREAM section。 |
| 检查工具 | 新增板端检查工具已解析 Python 语法；默认 preflight 不访问 PL 寄存器。尚未执行任何板端阶段。 |
| 完整包 | 25 项文件哈希校验通过，运行归档 5 个普通文件，完整测试归档 26 个普通文件；归档成员集合、路径安全和解压字节内容检查通过。 |

最终打包命令为 `python3 scripts/prepare_m3_bundle.py`，实际返回 0；其 21 条受控子命令均返回 0。命令、起止时间、输出日志和哈希保存在 [command_results.json](evidence/m3_bundle_review/command_results.json)。静态检查结果见 [bundle_review.json](evidence/m3_bundle_review/bundle_review.json)；完整 bundle 清单为 [SHA256SUMS](test_bundle/SHA256SUMS)。

运行 DTBO 是复用官方二进制后以 `fdtput` 改固件名生成，新增 JSON 为手工生成的配置元数据；它们不是另一次硬件综合成果。DTS 重新编译仅用于审阅往返验证，不替换运行 DTBO。

## 独立运行文件

目录：`test_bundle/lib/firmware/xilinx/kv260-benchmark-b4096-m3/`。

| 文件 | 字节数 | SHA-256 |
|---|---:|---|
| `kv260-benchmark-b4096-m3.bit.bin` | 7,807,932 | `a48a25265d280f268300f627e6408ec56707a70d4deebe46e358500cf17b2650` |
| `kv260-benchmark-b4096-m3.dtbo` | 3,015 | `51ce617967e0c0657bcc2629f1a0a8efa1e4bad3f3bc8f0b1931aacb5bf91937` |
| `kv260-benchmark-b4096-m3.xclbin` | 39,145 | `875ca912d87b2c993716f4c353265a9cf403b0c9890442610e64291787caafc3` |
| `shell.json` | 51 | `802dbc8b3f118313a5a74df46f56dc550a61b687dfd484fc6a8fd5ac7895c344` |

候选 XCLBIN UUID 为 `c5255f48-d8da-4df0-e36e-a7c7d21b9dd8`；寄存器预期值为 `IP_ID=0x41555241`、`ABI_VERSION=0x00010000`、`BUILD_ID=0xa5078450`。完整源码身份为 `a5078450b0777a556c6c349af6599310413535d84fe4e2767e7a7a80f3bd95be`；BUILD_ID 不是整个配置的哈希。

## 可传输归档

| 归档 | 大小 | SHA-256 |
|---|---:|---|
| [运行文件归档](downloads/kv260-benchmark-b4096-m3-runtime.tar.gz) | 3,275,727 bytes | `36cd4336b4cf688456f925777898483ef80eb0bba4246013425cceb45e814af6` |
| [完整测试归档](downloads/kv260-benchmark-b4096-m3-test-bundle.tar.gz) | 3,425,918 bytes | `589e971480d4cdd2a697c8f33253a7ada4acc38cf800c3424b385061a5244702` |

运行归档只有四个运行文件及针对这四项的 `SHA256SUMS`。完整归档另外包含设备树来源、合并审阅文件、新 HWH/arch、元数据、身份、板端检查工具和操作方案。`provenance/` 不能写到 `/boot` 或充当 SD 系统镜像。归档索引见 [archive_manifest.json](evidence/m3_bundle_review/archive_manifest.json)。

## 打包过程中的修复

第一次执行返回 1：主机 Python 为 3.8.10，不支持 `Path.is_relative_to()`。改用父目录成员检查，未升级 Python；四份原索引在此失败前已经通过。失败日志与未完成目录保存在 `evidence/m3_bundle_review_attempt01/`、`test_bundle_attempt01/`。

第二次执行返回 0，运行文件和归档成员校验通过。收尾检查发现 `stderr` 合并捕获导致审阅 DTS 夹带 DTC Warning 文本。已分开保存源码输出与完整诊断日志，并补充 DTS 编译及反编译往返检查。第二轮结果保存在 `test_bundle_attempt02/`、`evidence/m3_bundle_review_attempt02/` 和 `downloads/*-attempt02.tar.gz`。旧记录中的路径是移动前的路径；当前交付使用没有 attempt 后缀的目录和归档。后两轮的运行 BIN/XCLBIN 都使用相同的本机新构建成果。

修复后第三次执行返回 0，DTS 文件以 `/dts-v1/;` 开头，往返语义检查、全部原索引、最终包及归档校验通过。没有修改厂商 Tcl、DRC 规则、原构建工件或已经封存的旧报告。

## 实际问题与待确认项

| 类别 | 状态 |
|---|---|
| 既有板端 overlay 问题 | 旧板测两次卸载都发生 `/axi/zyxclmm_drm` 引用计数错误，持有者未定位；本轮没有消除该问题或验收热切换可靠性。 |
| 时序和 DRC 范围 | 已约束路径 setup/hold/pulse-width 通过；7 个输入、9 个输出 delay 缺口仍在，621 条实际 DRC Warning 保留，setup 裕量仅 +0.009 ns。 |
| DTC 诊断 | 原 DTBO和候选反编译各 5 条 Warning；原合并 DTB和候选反编译各 16 条 Warning，数量和文本相同。原日志保留，未禁用检查或把返回 0 说成无警告。 |
| 寄存器访问能力 | 目标板 BusyBox devmem applet、`/dev/mem`、kernel 选项及实际总线访问尚未核查；无额外 UIO 驱动或 kernel 改动。 |
| M3 验收 | 实际加载、三项身份寄存器、SCRATCH 保存/写入/回读/恢复、同模型同图 DPU 推理及官方应用恢复均待执行。 |
| 其他范围 | AXI 协议专门仿真、字节写选通、CPU/DPU 同时操作、PWM、外围接口、长期运行及真实执行器均未验收。 |

这里的 `host_package_consistency_pass=true` 只表示主机打包一致性检查通过，不能替代目标板许可/访问检查、kernel overlay 问题审阅或板端推理验收。

## 下一步如何做

1. 备用卡保持开机，USB 串口接 Ubuntu，网口继续直连 Win11。先只读核对卡身份、当前官方 app、内核/ZOCL/dfx-mgr 来源、既有卸载错误和寄存器访问工具。
2. 保存并校验官方对照，确定传输路径。只安装新的独立 M3 目录，核对归档和四个运行文件的 SHA-256。
3. 对现有 overlay 问题完成停点审阅并明确一次验证及恢复范围后，加载候选，读模块身份，受控读写 SCRATCH，再用相同 ResNet18 模型、图片和程序做分类与单/双线程各三次 60 秒复测。
4. 保存全部证据并恢复官方应用，核对 UUID、IP 生成标记、模型/固件哈希和同图分类；出现异常不自动反复切换或重启。

准确命令、停点、输入哈希和恢复核验见 [M3_TEST_CARD_PLAN.md](docs/M3_TEST_CARD_PLAN.md)。本轮的主机准备已完成；接下来的目标是板端有限验证，不需要重新烧录系统卡。
