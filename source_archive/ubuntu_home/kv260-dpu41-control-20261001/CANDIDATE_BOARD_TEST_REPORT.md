# DPU 4.1 新构建固件：备用卡加载、复测与恢复

状态：**候选安装、加载、实际 DPU 查询、同图分类及六轮性能复测通过；官方应用恢复及恢复后分类核验通过。最后实测官方 app 为 active slot 0，候选为 inactive。Overlay 引用计数问题仍未解决。**

用户在确认下一步方案后授权本轮操作：在备用卡测试新构建 DPU 固件，复用已固定模型和图片，并验证恢复官方应用。原 SD 卡、固定源码、厂商规则及主机原构建产物保留。测试范围为 DPU 推理；未连接执行器，未测试未完整约束的 MIPI、IIC、音频等接口，未修改 QSPI 或开机服务配置。应用切换时 daemon 自动更新的 `/etc/vart.conf` 已随官方应用恢复，未进行重启验收。

板端执行窗口为主机 UTC `2026-10-02 07:52:43` 至 `08:48:24`，每条命令的起止时间、返回码及传输校验保存在原始证据中；板端日历未同步，报告使用主机 UTC。

## 输入与恢复条件

主机工作目录：`/home/ghmd/kv260-dpu41-control-20261001`；固定参考源码 commit `a3a83f179503792226adf83082aee7c05de620b4`。DPU 4.1 IP 与构建来源见 [DPU41_BUILD_REPORT.md](DPU41_BUILD_REPORT.md)。完整测试包 14 项 SHA-256 校验均通过。本轮传输的候选运行文件为下表四项，来源均为本机新构建或该构建配套元数据；测试卡官方镜像中的预编译固件仅作对照。主机合并 DTB、HWH 和 BIT 审阅文件未安装到板卡。

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

相对官方中位数，单线程差异为 `-0.0079%`，双线程为 `+0.0205%`。六轮前后温度采样范围为 **34.132–39.790 °C**；这是三个 `temp*_input` 节点的离散采样范围，不是连续温度峰值。程序、模型、图片和列表沿用官方对照，候选加载后的程序 SHA-256 也与基线一致，见 [07-candidate-runtime.results.jsonl](evidence/candidate_board_20261002/07-candidate-runtime.results.jsonl)。

## 内核 overlay 问题

卸载官方 app 后出现实际内核错误，目标节点为 `/axi/zyxclmm_drm`，引用计数应为 1、实为 2；发生时点早于候选加载。新 overlay 加载时也出现已有节点属性生命周期的内存泄漏警告。两类信息完整保留于 [06-load-candidate.candidate_load_logs.output](evidence/candidate_board_20261002/06-load-candidate.candidate_load_logs.output)，不能把 `dfx-mgr-client` 返回 0 解释为日志没有问题。

卸载候选时，同一节点再次触发引用计数错误。跨三份快照按含时间戳的完整错误行去重，实际观察到两次：启动后 `8399.696048 s`（官方卸载）和 `10304.052132 s`（候选卸载），均为 expected refcount 1、actual 2。属性泄漏警告在切换前的官方基线已存在，不能将其全部归为新候选引入。

| 内核快照 | 实际引用计数错误行 | 属性生命周期警告行 |
|---|---:|---:|
| 切换前保存的官方基线 | 0 | 16 |
| 候选性能测试后 | 1 | 16 |
| 恢复官方并分类后 | 2 | 32 |

这些是当时 `dmesg` 环形缓冲区快照的行数，历史内容会被覆盖，**不是启动以来的累计数量**。切换前完整快照的 SHA-256 与预先保存的 `dmesg-before.txt` 一致。恢复后原始日志见 [14-restored-verification.kernel_after_restore.output](evidence/candidate_board_20261002/14-restored-verification.kernel_after_restore.output)。日志中的 `skip kind 29(AIE_RESOURCES) return code: -22` 也保留；官方和候选均有该信息，后续 `zocl_xclbin_read_axlf` 为 `ret: 0`，不能描述为日志无异常。

官方同版本 [dynamic.c](https://github.com/Xilinx/linux-xlnx/blob/xlnx_rebase_v5.15_LTS_2022.2/drivers/of/dynamic.c) 的 `__of_changeset_entry_destroy()` 检查遗留节点引用并记录诊断，该函数没有错误返回；[overlay.c](https://github.com/Xilinx/linux-xlnx/blob/xlnx_rebase_v5.15_LTS_2022.2/drivers/of/overlay.c) 的 `add_changeset_property()` 检查目标节点的 `OF_OVERLAY` 标志，未设置时记录属性生命周期警告；警告本身不改变属性操作的返回值。下载源文件及哈希见 [kernel_source_review.json](evidence/candidate_board_20261002/kernel_source_review.json)。源码基于对应官方 tag，板端完整 patch 身份未核对，实际持有引用者尚未定位，不能据此确定为候选 DPU RTL 的缺陷。

[Linux overlay 生命周期说明](https://docs.kernel.org/devicetree/overlay-notes.html) 要求遵守节点和数据的生命周期；该问题仍需独立追踪引用取得与释放。实际候选加载、寄存器/UUID 检查和推理均成功，本轮仅完成有限的一次切换、推理与恢复验证，不据此验收长期反复热切换。本轮未修改 kernel、ZOCL、厂商 Tcl 或规则。

## 恢复及限制

测试结束后卸载候选、重新加载 `kv260-benchmark-b4096`，两条底层 client 命令均返回 0，分别验证无活动 app 和仅官方 active slot 0。见 [12-unload-candidate.results.jsonl](evidence/candidate_board_20261002/12-unload-candidate.results.jsonl)、[13-restore-official.restore_official.output](evidence/candidate_board_20261002/13-restore-official.restore_official.output)。

恢复后四条核验命令均返回 0、输出完整且 SHA-256 与采集记录一致，见 [14-restored-verification.results.jsonl](evidence/candidate_board_20261002/14-restored-verification.results.jsonl)：

- FPGA manager 为 `operating`，实际 `firmware-name` 恢复为 `kv260-benchmark-b4096.bit.bin`；`/etc/vart.conf` 恢复官方 XCLBIN 路径。
- 实际 DPU 恢复到原生成标记 `2022-11-30 19-15-00`、git `ce8dd1`；DPU 4.1、1 CU、300 MHz、地址和指纹均与官方基线一致。
- 内核实际注册恢复官方 UUID `eedb44e9-3f77-0244-9ea9-23b953894638`，`zocl_xclbin_read_axlf ret: 0`。
- 官方四个固件文件及候选四个文件、模型、图片和列表哈希均符合预期；恢复后的 Top-5 与官方基线完全一致，Top-1 为 `0.949879`。
- 备用卡 CID 不变，板端网口仍为 `192.168.50.2/24`。候选独立目录保留为 inactive，原卡和板端备份保留。未重启或修改 QSPI。

汇总脚本已检查原始命令结果、输出哈希、实际架构、输入一致性、六轮统计、活动 slot、默认 VART 路径及恢复后的原 IP 标记，生成 [candidate_board_summary.json](evidence/candidate_board_20261002/candidate_board_summary.json)。报告更新前的文件与校验索引保存在 [before_summary](evidence/candidate_board_20261002/before_summary/)。本轮证据与报告索引为 [candidate_board_20261002.sha256](evidence/candidate_board_20261002.sha256)，原官方基线的当前索引为 [test_card_board_20261001.sha256](evidence/test_card_board_20261001.sha256)。

本次加载/推理通过也不代表所有接口或全部模型已验收。[DEPLOYMENT_REVIEW.md](DEPLOYMENT_REVIEW.md) 中 600 条 DRC Warning、16 个 I/O delay 方向缺口和 `0.001 ns` setup 裕量仍保留；后续加入运动 IP 必须重新综合、布局布线、约束审阅和板端验证。

## 当前结论及后续条件

| 类别 | 结论 |
|---|---|
| 已通过 | 候选实际配置、运行时互操作、固定模型与图片的分类、单/双线程各三次 60 秒复测、一次切换及官方应用恢复。 |
| 实际问题 | 两次卸载的 overlay 节点引用计数错误；已有节点属性生命周期警告；主机 DRC Warning、I/O 约束缺口及很小的 setup 裕量。 |
| 待确认 | 实际持有未释放节点引用的组件、板端 kernel/ZOCL 的完整 patch 来源、长期运行与反复切换可靠性、其他模型及外围接口行为。 |
| 后续动作 | 保持官方应用作为运行对照，先只读核对 kernel/ZOCL/dfx-mgr 来源及已存在的释放路径；确定匹配版本的修复后，在独立测试卡另行验证。运动 IP 集成前补齐相关板级接口约束并重新实现，不能以剩余 LUT/FF 比例保证放置成功。 |
