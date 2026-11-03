# DPU 4.1 新构建固件：备用卡加载、复测与恢复

状态：**候选安装、加载、实际 DPU 查询、同图分类及六轮性能复测通过；测试后核验及恢复正在执行。Overlay 引用计数问题保留为未解决项。**

用户在确认下一步方案后授权本轮操作：在备用卡测试新构建 DPU 固件，复用已固定模型和图片，并验证恢复官方应用。原 SD 卡、固定源码、厂商规则及主机原构建产物保留。测试范围为 DPU 推理；未连接执行器，未测试未完整约束的 MIPI、IIC、音频等接口，不修改 QSPI 或默认开机应用。

## 输入与恢复条件

主机工作目录：`/home/ghmd/kv260-dpu41-control-20261001`；固定参考源码 commit `a3a83f179503792226adf83082aee7c05de620b4`。DPU 4.1 IP 与构建来源见 [DPU41_BUILD_REPORT.md](DPU41_BUILD_REPORT.md)。完整测试包 14 项 SHA-256 校验均通过。本轮运行文件为下表四项，未传入预编译镜像固件、主机合并 DTB 或 HWH/BIT 审阅文件。

| 文件 | SHA-256 |
|---|---|
| `kv260-benchmark-b4096-dpu41.bit.bin` | `4d2fd04adc41cafc46ac6edcc7050f2edc9283d28aacfffc85e380a7ff1aebbf` |
| `kv260-benchmark-b4096-dpu41.dtbo` | `d19426602f7b4873eb8151099066e280313999cd58b5fbdc7fe89301f68ed39d` |
| `kv260-benchmark-b4096-dpu41.xclbin` | `4d9fae142e0a952ea1d1fd1f75395afbb2d485c1b66f507aa9d4cb317532894b` |
| `shell.json` | `a13dbd0a508de4656c3ba22aa9f8a41494a5082bcd585589fc366a56cc5ba1c1` |

打包后 gzip 为 3,285,722 bytes，SHA-256 `74470f03231a21ddd4b4525f299688b498910c23b3e85f658791c9b34ee3c80d`。通过串口以 1070 帧传入，逐帧与整包校验成功，记录见 [03-runtime-transfer.result.json](evidence/candidate_board_20261002/03-runtime-transfer.result.json)。板端运行目录 `/lib/firmware/xilinx/kv260-benchmark-b4096-dpu41/`；解包只接受预期四个普通运行文件及 `SHA256SUMS`，再次校验后原子移动到独立目录，拒绝覆盖现有目录。`shell.json` 为 `XRT_FLAT`、1 slot；BIN 前 64 字节与原运行 BIN 一致，主机 DTBO 的 `firmware-name` 已核查。安装证据：[04-install.results.jsonl](evidence/candidate_board_20261002/04-install.results.jsonl)。

切换前确认 SD CID 与已识别的 32 GB 备用卡一致，根分区为 `/dev/mmcblk1p2`，可用 21 GB；官方 app active slot 0。保存 `/home/root/kv260-test-20261001/baseline-backup/`：

- `baseline-files.tar.gz`：官方固件完整目录、ResNet18 模型目录、分类/性能程序、固定图片及列表；SHA-256 `964c04afac0d7de7e36b78d6bdd87f5f4a656bb47b3b7e1a7169510f5dfaa371`。
- `baseline-live.dtb`：从 `/proc/device-tree` 导出的实际设备树；SHA-256 `f5e27ba62910eb75d08afe82cb54e84946fb6da5e4ab90184f7290ea606bef2e`。
- `dmesg-before.txt`、`dfx-mgr-before.txt`：切换前内核与 daemon 日志。

备份目录创建时拒绝覆盖，官方固件目录保持原样。DT 导出存在警告，原文保留在 [02-save-baseline.backup_live_state.output](evidence/candidate_board_20261002/02-save-baseline.backup_live_state.output)，未隐藏规则或修改设备树。每个切换动作重新确认备用卡身份，并检查没有分类/性能等 DPU 客户端运行。

## 加载方法与证据

板端 `/usr/bin/xmutil` 的 `loadapp`/`unloadapp` 仅调用 `subprocess.run`，没有将底层返回码传给 shell。因此本轮直接执行其对应的官方底层命令，记录实际 client 返回值，再确认活动 slot；不修改该脚本。

```bash
dfx-mgr-client -remove
dfx-mgr-client -load kv260-benchmark-b4096-dpu41
dfx-mgr-client -listPackage
env XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096-dpu41/kv260-benchmark-b4096-dpu41.xclbin xdputil query
```

guard 脚本同时核对切换前/后应用状态；任何非零返回码、输出不完整或状态不符均停止后续命令。官方卸载已返回 `0 (Ok)`、活动 slot 验证为空，见 [05-unload-official.results.jsonl](evidence/candidate_board_20261002/05-unload-official.results.jsonl)。候选实际加载返回 0，活动应用仅候选为 slot 0；FPGA manager 为 `operating`，实际设备树 `firmware-name` 为 `kv260-benchmark-b4096-dpu41.bit.bin`，见 [06-load-candidate.results.jsonl](evidence/candidate_board_20261002/06-load-candidate.results.jsonl)。

实际 `xdputil query` 为 v4.1.0、B4096、1 CU、300 MHz、控制地址 `0xa0010000`、指纹 `0x101000056010407`；内核记录候选 UUID `fffc3c97-c2d3-8e30-acd1-6fc7c367c274`，`zocl_xclbin_read_axlf ret: 0`。IP 内部生成标记为 `2023-02-21 21-30-00`、git `7d32c41`；官方基线为 `2022-11-30 19-15-00`、git `ce8dd1`。该实际寄存器标记差异提供了新 DPU 已被配置的额外证据。完整核验见 [candidate_runtime_gate.json](evidence/candidate_board_20261002/candidate_runtime_gate.json) 及 [07-candidate-runtime.results.jsonl](evidence/candidate_board_20261002/07-candidate-runtime.results.jsonl)。

## 同输入复测

复用 [BASELINE_INFERENCE_REPORT.md](BASELINE_INFERENCE_REPORT.md) 中的 XMODEL、`.prototxt`、固定 JPEG、列表及程序；只将 `XLNX_VART_FIRMWARE` 指向候选 XCLBIN。预期硬件为 DPU 4.1、B4096、1 CU、300 MHz、`0xa0010000`、指纹 `0x101000056010407`，候选 XCLBIN UUID 为 `fffc3c97-c2d3-8e30-acd1-6fc7c367c274`。分类通过后运行单/双线程各一次 10 秒预热、各三次 60 秒正式测试，保存前后温度、完整输出与哈希。

候选 Top-1 为 Samoyed 0.949879，前五个类别和分数与官方基线在程序打印精度下完全一致，见 [classification_comparison.json](evidence/candidate_board_20261002/classification_comparison.json)。候选单/双线程预热分别为 214.787/238.532 FPS，不计入正式统计。

| 线程数 | 候选第 1 次 FPS | 候选第 2 次 FPS | 候选第 3 次 FPS | 候选中位数 FPS | 官方中位数 FPS |
|---|---|---|---|---|---|
| 1 | 214.987 | 214.926 | 214.944 | **214.944** | 214.961 |
| 2 | 238.837 | 238.826 | 238.678 | **238.826** | 238.777 |

六轮正式测试均返回 0，窗口均为 60 秒，输出传输校验通过，见 [10-candidate-performance.results.jsonl](evidence/candidate_board_20261002/10-candidate-performance.results.jsonl)。性能差异很小，不据此宣称性能提升。此 FPS 来自预加载、预缩放图片的官方 benchmark，不包含相机、逐帧 JPEG 读盘解码或运动控制整条流程。

## 内核 overlay 问题

卸载官方 app 后出现实际内核错误，目标节点为 `/axi/zyxclmm_drm`，引用计数应为 1、实为 2；发生时点早于候选加载。新 overlay 加载时也出现已有节点属性生命周期的内存泄漏警告。两类信息完整保留于 [06-load-candidate.candidate_load_logs.output](evidence/candidate_board_20261002/06-load-candidate.candidate_load_logs.output)，不能把 `dfx-mgr-client` 返回 0 解释为日志没有问题。

官方同版本 [dynamic.c](https://github.com/Xilinx/linux-xlnx/blob/xlnx_rebase_v5.15_LTS_2022.2/drivers/of/dynamic.c) 的 `__of_changeset_entry_destroy()` 检查遗留节点引用并记录诊断，该函数没有错误返回；[overlay.c](https://github.com/Xilinx/linux-xlnx/blob/xlnx_rebase_v5.15_LTS_2022.2/drivers/of/overlay.c) 的属性处理也可记录生命周期警告并继续成功操作。下载源文件及哈希见 [kernel_source_review.json](evidence/candidate_board_20261002/kernel_source_review.json)。源码基于对应官方 tag，板端完整 patch 身份未核对，实际持有引用者尚未定位。

[Linux overlay 生命周期说明](https://docs.kernel.org/devicetree/overlay-notes.html) 要求遵守节点和数据的生命周期；该问题仍需独立追踪引用取得与释放。实际候选加载、寄存器/UUID 检查和推理均成功，本轮仅完成有限的一次切换、推理与恢复验证，不据此验收长期反复热切换。本轮未修改 kernel、ZOCL、厂商 Tcl 或规则。

## 恢复及限制

测试结束后卸载候选，重新加载 `kv260-benchmark-b4096`，核对官方 BIN/DTBO/XCLBIN、UUID、模型/图片哈希及实际 DPU，再以同一图片分类验证恢复。不会自动重启；若软件恢复失败，应停止进一步切换并通过原卡恢复。恢复执行结果待完成后填写。

本次加载/推理通过也不代表所有接口或全部模型已验收。[DEPLOYMENT_REVIEW.md](DEPLOYMENT_REVIEW.md) 中 600 条 DRC Warning、16 个 I/O delay 方向缺口和 `0.001 ns` setup 裕量仍保留；后续加入运动 IP 必须重新综合、布局布线、约束审阅和板端验证。
