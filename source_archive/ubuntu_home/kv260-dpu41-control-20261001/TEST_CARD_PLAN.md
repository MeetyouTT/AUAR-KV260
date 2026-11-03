# DPU 4.1 独立测试卡复测与恢复

本文件创建时是后续操作方案。随后经用户授权，已完成独立测试卡的官方镜像烧录、启动核验、Win11 SSH 和官方 ResNet18 基线复测，见 [TEST_CARD_FLASH_REPORT.md](TEST_CARD_FLASH_REPORT.md)、[BASELINE_INFERENCE_REPORT.md](BASELINE_INFERENCE_REPORT.md)。**2026-10-02 已完成候选安装、实际加载、同输入分类、单/双线程各三次 60 秒测试及恢复；最后实测官方 active slot 0、候选 inactive。** 结果见 [CANDIDATE_BOARD_TEST_REPORT.md](CANDIDATE_BOARD_TEST_REPORT.md)。以下保留已采用的部署与恢复方法；两次卸载的 overlay 引用计数错误尚未解决，暂不重复切换。

## 1. 保存原基线

使用另一张 SD 卡复制相同官方 PetaLinux 2022.2 / Vitis AI 3.0 镜像；原卡保管。若要克隆原卡，先关机并卸载卡分区，确认源/目标设备后制作整卡镜像和 SHA-256；这里不提供猜测的 `/dev/sdX` 写入命令。

基线固件目录 `/lib/firmware/xilinx/kv260-benchmark-b4096/`、模型目录、推理示例二进制、固定图片和列表已备份到测试卡 `/home/root/kv260-test-20261001/baseline-backup/`；实际 DT 和切换前日志也已保存。命令、备份 SHA-256 和恢复核验见候选测试报告。已知基线：

| 项目 | 预期 |
|---|---|
| 活动 app | `kv260-benchmark-b4096` |
| XCLBIN UUID | `eedb44e9-3f77-0244-9ea9-23b953894638` |
| DPU/模型 fingerprint | `0x101000056010407` |
| CU | 1 个，`0xa0010000` |
| 原 XMODEL SHA-256 | `4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef` |
| 原 BIN SHA-256 | `7d12c877e0fde40a243d2350b1a2227f565788bf9e2dcae4439d07f213d40a3f` |
| 原 DTBO SHA-256 | `36338937904e5ec988566d7341f6504edba34c01bd7e2e3f2025ab0069337e35` |
| 原 XCLBIN SHA-256 | `fc3abb934eec544e49a17c484336cf177258f475522cefc994ec458b726f69ac` |

历史图片路径/哈希、历史 FPS 测试窗口/命令尚未确认。现已采用固定 PyTorch ResNet 示例图片建立新的官方 app 对照：图片 SHA-256 `f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a`，板端路径 `/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg`，列表 `samoyed.list` 位于同目录。官方 Top-1 0.949879，单/双线程各三次 60 秒中位数 214.961/238.777 FPS；候选复用相同文件、程序和命令，Top-5 一致，中位数 214.944/238.826 FPS。不声称已确认历史原图身份；用户此前的 214.381/238.479 FPS 仍保留为历史参考。

## 2. 审核并复制候选包

主机 bundle 位于 `test_bundle/`。运行文件只有：

```text
lib/firmware/xilinx/kv260-benchmark-b4096-dpu41/
  kv260-benchmark-b4096-dpu41.bit.bin
  kv260-benchmark-b4096-dpu41.dtbo
  kv260-benchmark-b4096-dpu41.xclbin
  shell.json
```

在主机和复制到测试卡后的 bundle 根目录各执行 `sha256sum -c SHA256SUMS`。只将上述独立 app 目录安装到测试卡 `/lib/firmware/xilinx/`，不覆盖原 app，不把 `provenance/host-merged-system.dtb` 或其他审阅文件放到 `/boot`。

这套硬件为完整 XRT_FLAT 配置，不能当作原基线 shell 上可叠加的小块 partial bitstream。`.bit.bin` 从本次 BIT 用 Bootgen 的 ZynqMP PL BIF 生成**带 Bootgen 头的完整 BIN**，其前 64 字节须与原镜像中的运行时 BIN 匹配。DTBO `firmware-name` 精确匹配其文件名。官方 Makefile 从 XCLBIN 删除了 BITSTREAM section，因此仅让运行时注册 XCLBIN 不能代替加载对应的 PL 配置。

原 DTBO 仅改固件文件名，保留 dmabuf 属性。主机 DTC 1.7.2 合并已通过，但主机 libfdt 不等同于测试卡 kernel/dfx-mgr。测试时仍须保存完整加载日志、dmesg 和实时 DT，检查 dma-buf/firmware lookup/ZOCL 初始化是否成功。

实际传输使用仅含四个运行文件及 `SHA256SUMS` 的归档，逐帧、整包和板端解包后三次校验通过；主机归档为 `downloads/kv260-benchmark-b4096-dpu41-runtime.tar.gz`。独立 app 目录现已安装并保留，恢复后处于 inactive；不得重新运行本轮拒绝覆盖的安装脚本来覆盖该目录。

## 3. 仅在独立测试卡切换

结束原推理进程，保留完整串口会话日志。确认应用目录能被发现后再加载；若未发现，先核对该镜像的 dfx-mgr 应用扫描与 metadata，不自行替换 daemon 或 rootfs。实测此镜像的 `xmutil loadapp/unloadapp` 未传递底层进程返回码，本轮使用对应的 `dfx-mgr-client` 命令，并由 guard 脚本每步核对备用卡 CID、无 DPU 客户端、真实返回码及活动 slot：

```bash
dfx-mgr-client -listPackage
dfx-mgr-client -remove
dfx-mgr-client -load kv260-benchmark-b4096-dpu41
dfx-mgr-client -listPackage
dmesg | tail -n 150
```

任何非零返回码、配置失败、ZOCL 异常或 app 状态不符，停止推理并按恢复步骤处理。新 XCLBIN UUID 应与本次主机 `evidence/xclbin_info.log` 一致；不能用原 UUID 作为新 app 的预期值。

对查询及推理显式选择候选 XCLBIN，避免默认路径注册原基线文件：

```bash
env XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096-dpu41/kv260-benchmark-b4096-dpu41.xclbin xdputil query
```

此查询可能注册 XCLBIN/访问硬件，因此属于已切换后的测试步骤，不标为纯只读基线检查。实际硬件应为 DPU 4.1、单 CU、`0xa0010000`、fingerprint `0x101000056010407`。指纹或地址不符立即停止，不改模型 fingerprint、不关闭检查。

## 4. 同一模型与同一图片复测

模型保留为 `/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel`，先核对 SHA-256。同时核对 `.prototxt`、类别标签、示例二进制、图片和列表文件的哈希；预处理/CPU 后处理也会影响分数。

实际测试使用 `/home/root/Vitis-AI/examples/vai_library/samples/classification/` 中的分类和性能程序；二进制、模型、图片及列表哈希已固定。官方 3.0 源码中的 JPEG 和 performance CLI 已保留到 `evidence/runtime_sources/`。下列为实际测试命令，性能测试单/双线程各执行三次，之前各做一次 10 秒预热：

```bash
cd /home/root/kv260-test-20261001
env XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096-dpu41/kv260-benchmark-b4096-dpu41.xclbin /home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification resnet18 /home/root/kv260-test-20261001/pytorch-resnet-dog.jpg
env XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096-dpu41/kv260-benchmark-b4096-dpu41.xclbin /home/root/Vitis-AI/examples/vai_library/samples/classification/test_performance_classification resnet18 -s 60 -t 1 /home/root/kv260-test-20261001/samoyed.list
env XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096-dpu41/kv260-benchmark-b4096-dpu41.xclbin /home/root/Vitis-AI/examples/vai_library/samples/classification/test_performance_classification resnet18 -s 60 -t 2 /home/root/kv260-test-20261001/samoyed.list
```

以上 60 秒窗口是本次官方/候选对照的实际测试窗口，不假定历史测试也是 60 秒。六轮候选测试均返回 0，已记录前后温度、频率、Top-1/分数和 FPS；性能接近官方，不宣称提升。推理检查通过不消除 overlay 引用计数错误和原 DRC/接口约束缺口。

## 5. 恢复

结束所有推理，在确认备用卡身份、客户端已退出及当前活动 app 后，执行 `dfx-mgr-client -remove`，确认活动 slot 为空，再执行 `dfx-mgr-client -load kv260-benchmark-b4096` 并确认官方 active slot 0。本次两条命令均实际成功，默认 `/etc/vart.conf` 随 daemon 恢复官方 XCLBIN 路径；恢复查询和分类仍显式设置 `XLNX_VART_FIRMWARE` 为官方路径。若软件恢复失败，停止进一步操作，安全关机后换回保管的原卡；本方案不自动重启。

恢复后已核对原 app、固件和输入哈希、原 UUID、实际 DPU 指纹及原 IP 生成标记，再以同一图片分类验证 Top-5 与官方对照一致。证据见 [14-restored-verification.results.jsonl](evidence/candidate_board_20261002/14-restored-verification.results.jsonl)。板卡现在保留官方 app 运行对照；本轮没有测试关机换卡恢复，也未连接执行器。复制单个旧 BIT 不等于完整恢复。两次卸载的引用计数错误仍待定位，不据此继续反复热切换。
