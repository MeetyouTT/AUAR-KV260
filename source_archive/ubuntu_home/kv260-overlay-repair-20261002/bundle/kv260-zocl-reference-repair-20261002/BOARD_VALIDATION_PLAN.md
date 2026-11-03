# ZOCL 修复候选：备用卡验证与恢复

状态：待执行。用户目前没有板卡。主机候选已编译和核验，不能作为板端修复验收。

## 1. 接续条件和实时输入

回实验室后用备用卡启动 KV260。板网口继续直连 Win11（Win `192.168.50.1/24`，board `192.168.50.2/24`），UART USB 接 Ubuntu。不改变原 SD/QSPI，不自动重启，不连接执行器。

先确认串口没有其他程序占用，使用新目录的只读采集器：

```bash
cd /home/ghmd/kv260-overlay-repair-20261002/evidence/board_preflight
python3 collect_serial.py 01-readonly
```

采集器按 4 字节 / 至少 40 ms 输入，只在确认板端 root prompt 后执行 manifest；任何失败或不完整输出都会停止，不发送 Ctrl-C、reset 或重复执行。它限定备用卡 CID `0353445345333247805558c00401a100`、K26 和 kernel release `5.15.36-xilinx-v2022.2`。

板端 `gzip -dc /proc/config.gz` 要与离线原配置逐项比较。原模块 SHA-256 预期为 `215fe760dafb6766545e308d8bc207c31712154fe5a8ed08342a101a5482a98d`，srcversion `0991D1B457855C8987936E6`；核对 XRT 核心库、manager、libdfx 的哈希与 `extraction.json`。任何不一致先分析，禁止强加载来绕过。

同时记录根分区、当前 app、FPGA manager 状态、firmware-name、ZOCL holders/refcnt、`/sys/module/zocl/parameters/*`、所有打开 `/dev/dri/*` 的进程及完整内核日志。首份 manifest 只读采集身份、内核配置、客户端和 dmesg；模块参数及加载前状态在下一份只读阶段补采。

## 2. 保存原状态并准备临时候选

在新建且不存在的板端目录（例如 `/home/root/kv260-zocl-repair-20261002/`）保存实际原模块、原模块参数、软件包信息、原 app 文件哈希、实时设备树、运行时配置和模型/图片/程序哈希。不能覆盖已有 `/home/root/kv260-test-20261001/baseline-backup/`；原备份 tar 的 SHA-256 为 `964c04afac0d7de7e36b78d6bdd87f5f4a656bb47b3b7e1a7169510f5dfaa371`。

修复 bundle 传输至新的 staging，先验证归档 SHA-256 和成员，再执行 bundle 的 `sha256sum -c SHA256SUMS`。只接受预期普通文件，拒绝绝对路径、`..`、链接和设备文件。原驱动留在 `/lib/modules`；候选模块只从 staging 临时 `insmod`，不执行安装、`depmod`、开机配置修改或覆盖 `/boot`。若传输经过 Win11，Ubuntu 不直接使用缺少路由的板卡 IP；也可沿用已验证的 UART 分帧及整包校验方式。

保存本轮起始官方分类和性能基线。官方 app 为 `kv260-benchmark-b4096`，显式选用：

```text
/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin
```

## 3. 一次旧状态退出和临时驱动加载

每个动作前后分别保存 `/proc/uptime`、完整 dmesg、manager 日志和 app 状态。保持串行，没有推理或其他 DRM 客户端时才进入切换。未知客户端不能直接强杀；确认程序已正常退出。

使用此镜像已有并经过旧板测的 `dfx-mgr-client -remove` 单独卸载当前官方 app，核对真实返回码和无 active app。旧 `xmutil` 包装层的返回码不能代替底层返回码。

第一次旧驱动卸载 app 仍可能产生已知节点引用错误；这是退出旧状态的证据，不计为修复后的新循环。只有错误特征与既有日志完全一致、无其他新错误且状态审阅允许时才继续驱动替换；状态不明立即停下。历史已泄漏对象不手工减引用，不强卸载，不假设新模块能回收它们。

确认 app 为空、DRM 客户端为空、ZOCL holders 为空且模块可正常卸载后，单独执行 `rmmod zocl`。禁止 `rmmod -f`。再使用记录下来的原参数临时 `insmod <staging>/zocl.ko`。参数值以实时采集结果为准，不猜测 `enable_xgq_ert`。

核对 `/sys/module/zocl/srcversion` 为 `9BDC942A6014BCCBD1DCB78`，参数符合原值，`/proc/modules` 及内核日志没有加载/解析/异常错误。`modinfo zocl` 仍可能查询磁盘上的原文件，不能用它代替正在加载的候选身份核验。

## 4. 官方应用上的新循环

有限执行至少三个新循环，每次按：加载官方 app → 检查身份 → 同图分类 → 退出客户端 → 卸载 → 审阅新增日志。每个动作单独确认，失败不自动重试。

```bash
dfx-mgr-client -load kv260-benchmark-b4096
env XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin xdputil query
```

要求唯一官方 active slot 0、FPGA manager `operating`、原 firmware-name 和原固件哈希。官方对照为 1 个 DPU CU、地址 `0xa0010000`、B4096、指纹 `0x101000056010407`、XCLBIN UUID `eedb44e9-3f77-0244-9ea9-23b953894638`，并核对模型要求。

沿用原模型、原图片和程序：

```bash
cd /home/root/kv260-test-20261001
env XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin /home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification resnet18 /home/root/kv260-test-20261001/pytorch-resnet-dog.jpg
```

模型 SHA-256 为 `4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef`；图片 SHA-256 为 `f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a`。Top-5 与起始官方对照一致；历史 Samoyed Top-1 分数为 `0.949879`。

分类通过后沿用 `test_performance_classification resnet18 -s 60 -t 1/2 .../samoyed.list`：各线程数先 10 秒预热、再三次 60 秒。记录温度、频率、完整输出与真实返回码，对照同一轮原驱动中位数；性能明显变化先追查原因。历史三次中位数 `214.961/238.777 FPS` 仅作已有证据，不能代替新一轮可比对照。

在每次新 overlay 卸载对应的 uptime 区间，要求没有新增 `expected refcount 1 instead of ... /axi/zyxclmm_drm`、崩溃、UAF 或其他异常。使用完整日志和时间区间区分旧错误；不执行 `dmesg -c`。既有属性警告单独计数，不伪称已消除。三次有限验证不能作为长期热切换或并发安全验收。

## 5. 恢复与后续 M3

结束推理并确认客户端退出；卸载官方 app、确认无 active app，正常 `rmmod zocl`，再 `modprobe zocl` 恢复磁盘原驱动及原参数，加载官方 app。核对加载模块 srcversion、原文件哈希、原 app、firmware-name、指纹与同图分类。磁盘原模块保持原样，此临时试验不应影响下一次正常启动选择的驱动。

任何恢复失败都保存完整证据并停止循环，不能自动重启或替换卡。保留候选及备份供定位。若需要让修复长期生效，再完成独立安装方案和恢复路径审阅。

驱动修复的板端有限验证完成后，M3 另按原封存的 `/home/ghmd/kv260-m3-axilite-20261002/docs/M3_TEST_CARD_PLAN.md` 接续。它有独立切换授权与身份检查要求，本轮不运行 M3，也不写 PWM 或执行器。
