# M3 备用卡验证与恢复步骤

本文件是待执行方案。主机已生成包含 DPU 4.1 B4096 和最小 AXI-Lite 寄存器的完整 PL 配置；本轮未在板卡加载 M3，也未验证寄存器或 DPU 共存。模块没有 PWM、外部输出和执行器连接。

## 1. 保持已有连接和原基线

继续用备用 32 GB SD 卡启动官方 PetaLinux 2022.2 / Vitis AI 3.0。原 SD 卡保管。板卡网口保持直连 Win11：Windows `192.168.50.1/24`，板卡 `192.168.50.2/24`；UART 接 Ubuntu。Ubuntu 当前没有直达这个网段的路由，不能把 `scp root@192.168.50.2` 当作 Ubuntu 已可用的传输方式。

先通过串口或现有 Win11 SSH 只读确认当前 app、测试卡身份、FPGA manager、内核和访问工具。最后一次旧板测已恢复官方 app，但这不是新的实时查询。解包测试归档到一个新的 staging 目录后，可以运行：

```bash
python3 board/m3_board_check.py preflight
```

默认 `preflight` 只检查身份、应用状态、配置名称、工具和内核选项，不访问 PL 寄存器、不切换 app。它限定已经识别的备用卡 CID 和根分区 `/dev/mmcblk1p2`，拒绝在 Ubuntu 主机上访问 MMIO。目标 kernel 的 `/dev/mem` 权限、实际 AXI 总线访问能力仍待板端核查；有设备文件并不等于能访问寄存器。

## 2. 保存并核对官方对照

已有板端备份位于 `/home/root/kv260-test-20261001/baseline-backup/`。先验证 `baseline-files.tar.gz` SHA-256 为 `964c04afac0d7de7e36b78d6bdd87f5f4a656bb47b3b7e1a7169510f5dfaa371`，同时核对当前官方固件、模型、图片、标签、预处理配置和程序。不要覆盖这份备份。新一轮将新的实时 DT、dmesg、dfx-mgr 日志、温度、应用列表和 `/etc/vart.conf` 另存到新证据目录。

| 官方对照 | 预期 |
|---|---|
| app | `kv260-benchmark-b4096`，唯一 active slot 0 |
| XCLBIN UUID | `eedb44e9-3f77-0244-9ea9-23b953894638` |
| DPU | 4.1、B4096、1 CU、`0xa0010000`、约 300 MHz |
| 架构指纹 | `0x101000056010407` |
| BIN SHA-256 | `7d12c877e0fde40a243d2350b1a2227f565788bf9e2dcae4439d07f213d40a3f` |
| DTBO SHA-256 | `36338937904e5ec988566d7341f6504edba34c01bd7e2e3f2025ab0069337e35` |
| XCLBIN SHA-256 | `fc3abb934eec544e49a17c484336cf177258f475522cefc994ec458b726f69ac` |
| shell.json SHA-256 | `2967ccbc1f75c8d4accd1b6fecc11b16a32a5d7992e56c6eebceb99a3410f777` |
| IP 内部生成标记 | `2022-11-30 19-15-00`、git `ce8dd1` |

历史同输入对照 Top-1 为 Samoyed `0.949879`，单/双线程各三次 60 秒中位数 `214.961/238.777 FPS`。如果环境或输入哈希变化，重新建立官方对照，不能直接和旧数字比较。

## 3. 传输、核验和独立安装

主机提供运行归档和包含审阅资料、检查工具的完整测试归档；归档路径及 SHA-256 见 `evidence/m3_bundle_review/archive_manifest.json`。网络维持直连 Win11时，可以把主机归档复制到 Win11，再由 Win11 `scp` 到板卡的新 staging 目录；也可以在经批准的串口会话中采用旧板测的逐帧、整包和解包校验方法。传输方式确认后再实际操作，不更改网络连接。

解包前核对归档 SHA-256。归档只接受预期的普通文件，拒绝绝对路径、`..`、符号链接和设备文件。运行归档解包后执行 `sha256sum -c SHA256SUMS`；完整归档在完整 bundle 根目录执行相同命令。安装时只复制以下独立 app 目录，目标已存在则停止，不覆盖：

```text
/lib/firmware/xilinx/kv260-benchmark-b4096-m3/
  kv260-benchmark-b4096-m3.bit.bin
  kv260-benchmark-b4096-m3.dtbo
  kv260-benchmark-b4096-m3.xclbin
  shell.json
```

不要将 provenance 中的合并 DTB、BIT、HWH 或主机文件写到 `/boot`、SD 整盘或 QSPI。BIN 是带 Bootgen 头的完整 PL 配置，DTBO 使用 `fpga_full`，没有 `partial-fpga-config`，保留 dma-buf 属性；XCLBIN 不含 BITSTREAM section，需要与此 BIN/DTBO 配套。

## 4. 切换前停点与有限验证

旧板测两次卸载都在 `/axi/zyxclmm_drm` 出现 expected refcount 1、actual 2。引用持有者尚未定位，长期热切换可靠性未验收。在 M3 加载前先审阅当前日志和 kernel/ZOCL/dfx-mgr 身份；现有问题没有因打包或恢复官方 app 而修好。**本轮不执行切换；后续须明确同意一次备用卡验证及恢复范围。** 不自动反复卸载/重试，不修改 kernel、厂商 DRC 规则或忽略指纹检查。

以下是该 2022.2 镜像旧板测实际使用的底层入口，不是本轮已经执行的命令。旧 `xmutil` 未传递底层返回码，后续仍核对 client 返回码、唯一活动 slot、manager 状态、完整加载日志和实时 firmware-name：

```bash
dfx-mgr-client -listPackage
dfx-mgr-client -remove
dfx-mgr-client -load kv260-benchmark-b4096-m3
dfx-mgr-client -listPackage
```

先结束所有 DPU 客户端。每个动作单独记录和审阅。任何非零返回码、状态不符、新内核错误、引用计数错误或输出不完整均停止后续动作，保存证据并决定恢复方式，不把命令返回 0 当作日志没有问题。

候选加载后预期 manager `operating`、实时 firmware-name 为 `kv260-benchmark-b4096-m3.bit.bin`。先验证安装文件哈希，再显式选择候选 XCLBIN：

```bash
env XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096-m3/kv260-benchmark-b4096-m3.xclbin xdputil query
python3 board/m3_board_check.py identity
python3 board/m3_board_check.py scratch
```

`xdputil query` 可注册 XCLBIN并访问硬件，归为加载后验证。候选 UUID 应为 `c5255f48-d8da-4df0-e36e-a7c7d21b9dd8`，DPU 指纹/地址应与官方对照相同，IP 生成标记应为继承 DPU 4.1 的 `2023-02-21 21-30-00`、git `7d32c41`；实际值待查询。

检查工具仅允许 32 位访问 `0x80080000/04/08/0c`。必须先读到 `IP_ID=0x41555241`、`ABI_VERSION=0x00010000`、`BUILD_ID=0xa5078450`，才允许写 SCRATCH；原值先打印保存，写四个固定图样并回读，最后尝试恢复并确认原值。失败、信号、总线错误或板卡无响应时不能假定恢复成功。它使用板上已有 BusyBox `devmem`，不替换访问工具；缺少该 applet、`/dev/mem` 或实际权限时停止并报告。不在官方配置下盲读新地址，不访问保留或非对齐地址，不写只读寄存器。

## 5. 同模型同图验证 DPU 共存

输入与程序哈希在 `provenance/runtime_manifest.json` 中固定。原模型为 `/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel`，SHA-256 `4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef`；固定图片 `/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg`，SHA-256 `f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a`。复用同一分类/性能程序、prototxt、标签和 `samoyed.list`。

```bash
cd /home/root/kv260-test-20261001
env XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096-m3/kv260-benchmark-b4096-m3.xclbin /home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification resnet18 /home/root/kv260-test-20261001/pytorch-resnet-dog.jpg
env XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096-m3/kv260-benchmark-b4096-m3.xclbin /home/root/Vitis-AI/examples/vai_library/samples/classification/test_performance_classification resnet18 -s 10 -t 1 /home/root/kv260-test-20261001/samoyed.list
env XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096-m3/kv260-benchmark-b4096-m3.xclbin /home/root/Vitis-AI/examples/vai_library/samples/classification/test_performance_classification resnet18 -s 60 -t 1 /home/root/kv260-test-20261001/samoyed.list
```

分类 Top-5 和打印分数与官方对照一致后，单线程三次 60 秒；双线程先一次 10 秒预热，再三次 60 秒。上例分别替换 `-t 1` 为 `-t 2`，保留相同图片列表。记录每次真实返回码、完整输出、前后温度/频率和 FPS 中位数。推理前后再次检查 M3 身份及 SCRATCH 原值；程序均退出后操作。这里只验证同一配置中二者可用，未验证 CPU 与 DPU 并发访问、字节 WSTRB、AXI 协议或运动闭环。

## 6. 恢复官方对照

退出全部测试程序并检查卡身份、当前 app 和日志。经停点审阅允许软件恢复后，单独执行 `dfx-mgr-client -remove`，确认没有活动 app；再执行 `dfx-mgr-client -load kv260-benchmark-b4096`，确认只有官方 active slot 0。若再次触发引用计数错误或恢复失败，停止反复切换，保存证据；安全关机/冷启动/换回原卡必须另行明确授权，不自动重启。

恢复核验 manager、实时 firmware-name、默认 `/etc/vart.conf`、原固件/模型/图片/程序哈希、官方 UUID、DPU 生成标记 `ce8dd1`。使用官方 XCLBIN 显式复跑同图分类，确认 Top-5 与基线一致。不要在恢复官方后访问 M3 地址。恢复成功与否都保存独立日志和哈希。

## 范围与资料

主机约束覆盖仍缺 7 个输入 delay 和 9 个输出 delay；621 条 DRC Warning 及很小的 setup 裕量保留。外围接口、长期运行、长期热切换、PWM、真实执行器、完整 AXI 仿真都未验收。

官方说明的运行包需要 BIN/DTBO/JSON，XCLBIN 视应用使用；DFX manager 管理文件系统中的配置和设备树。这里的部署形式另以旧板测实测文件和命令作依据：[AMD Kria 固件仓库](https://github.com/Xilinx/kria-apps-firmware)、[AMD DFX manager](https://github.com/Xilinx/dfx-mgr/blob/master/README.md)。寄存器访问参数依据 [BusyBox devmem 文档](https://busybox.net/BusyBox.html#devmem)；目标板实际编译选项仍须核查。
