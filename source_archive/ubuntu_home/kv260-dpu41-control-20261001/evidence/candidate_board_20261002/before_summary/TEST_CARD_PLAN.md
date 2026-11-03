# DPU 4.1 独立测试卡复测与恢复

本文件创建时是后续操作方案。随后经用户授权，已完成独立测试卡的官方镜像烧录、启动核验、Win11 SSH 和官方 ResNet18 基线复测，见 [TEST_CARD_FLASH_REPORT.md](TEST_CARD_FLASH_REPORT.md)、[BASELINE_INFERENCE_REPORT.md](BASELINE_INFERENCE_REPORT.md)。**候选应用尚未安装或切换。** 主机构建、routed DCP 审阅与包哈希核对已完成；候选板端步骤须在独立测试卡上按部署前审阅结论及用户授权执行。

## 1. 保存原基线

使用另一张 SD 卡复制相同官方 PetaLinux 2022.2 / Vitis AI 3.0 镜像；原卡保管。若要克隆原卡，先关机并卸载卡分区，确认源/目标设备后制作整卡镜像和 SHA-256；这里不提供猜测的 `/dev/sdX` 写入命令。

基线固件目录 `/lib/firmware/xilinx/kv260-benchmark-b4096/`、模型目录、原推理示例二进制、原 Samoyed 图片和完整推理命令需另行备份。已知基线：

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

历史图片路径/哈希、历史 FPS 测试窗口/命令尚未确认。现已采用固定 PyTorch ResNet 示例图片建立新的官方 app 对照：图片 SHA-256 `f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a`，板端路径 `/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg`，列表 `samoyed.list` 位于同目录。Top-1 0.949879，单/双线程各三次 60 秒中位数 214.961/238.777 FPS。候选测试必须复用这组已固定文件、程序和命令，形成相同条件的对照；不声称已确认历史原图身份。用户此前的 214.381/238.479 FPS 仍保留为历史参考。

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

## 3. 仅在独立测试卡切换

结束原推理进程，保留完整串口会话日志。确认 `xmutil listapps` 能发现独立 app 后再加载；若未发现，先核对该镜像的 dfx-mgr 应用扫描与 metadata，不自行替换 daemon 或 rootfs。

```bash
xmutil listapps
xmutil unloadapp
xmutil loadapp kv260-benchmark-b4096-dpu41
xmutil listapps
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

此前板端只读 inventory 确認分类示例位于 `/home/root/Vitis-AI/examples/vai_library/samples/classification/`。官方 3.0 源码中的 JPEG 和 performance CLI 已保留到 `evidence/runtime_sources/`。若原测试确实使用这些示例，可采用以下模板；`same-image.jpg` 应替换为确认过哈希的原图片，列表只列该图片绝对路径。

```bash
cd /home/root/Vitis-AI/examples/vai_library/samples/classification
env XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096-dpu41/kv260-benchmark-b4096-dpu41.xclbin ./test_jpeg_classification resnet18 /absolute/path/same-image.jpg
env XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096-dpu41/kv260-benchmark-b4096-dpu41.xclbin ./test_performance_classification resnet18 -s 60 -t 1 /absolute/path/same-image.list
env XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096-dpu41/kv260-benchmark-b4096-dpu41.xclbin ./test_performance_classification resnet18 -s 60 -t 2 /absolute/path/same-image.list
```

以上 60 秒窗口是明确的新测试方案，不假定历史测试也是 60 秒。若原测试使用别的程序，应复用原程序/命令并分别在原 app、新 app 执行，不能混用指标。单/双线程各重复至少三次，记录预热、温度、频率、Top-1/分数和 FPS 中位数。精度、加载和运行稳定性通过后，才讨论性能差异及后续运动 IP 集成。

## 5. 恢复

结束所有推理，测试卡上可执行 `xmutil unloadapp` 后重新 `xmutil loadapp kv260-benchmark-b4096`，再让运行时显式选择原 XCLBIN。若卸载/加载失败或出现 kernel 异常，停止软件切换，关机换回保管的原卡；本方案不自动重启。

恢复后核对原 app、固件哈希、原 UUID、DPU fingerprint 和模型哈希，再以同一图片进行短复测。换回原卡是主要恢复路径，复制单个旧 BIT 不等于完整恢复。不要在唯一原卡上演练失败恢复，不接执行器。
