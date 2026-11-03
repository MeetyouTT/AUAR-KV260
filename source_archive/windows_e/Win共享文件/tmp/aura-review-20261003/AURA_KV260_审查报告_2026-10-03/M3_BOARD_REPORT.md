# KV260 M3：DPU 与最小 AXI-Lite 模块板测报告

日期：2026-10-02（America/Los_Angeles）。主验证及恢复：`2026-10-03T02:27:55Z–03:11:58Z`；之后补采只读日志、哈希和管理器诊断。

**结果：同一 M3 FPGA 配置中，自研寄存器身份、四图样写读与恢复、ResNet18 同图推理及单／双线程性能均通过有限板测；M3 正常卸载，原驱动及官方应用已恢复。追加日志审阅发现 DFX manager 的目录监视表问题，已定位源码缺陷，本轮尚未修复。**

这证明最小寄存器模块与 DPU 在本配置中分别可用。PWM、运动控制、CPU/DPU 并发及长期可靠性未验收；本报告不表示整个项目或长期部署审阅已经完成。

## 1. 输入和本轮范围

沿用现有备用卡和官方 PetaLinux 2022.2 / Vitis AI 3.0。卡 CID `0353445345333247805558c00401a100`，根分区 `mmcblk1p2`，内核 `5.15.36-xilinx-v2022.2`。Ubuntu 通过 115200 UART 操作，网口保持直连 Win11。

实时内核配置、原 ZOCL/XRT/dfx-mgr/libdfx 文件与上一轮镜像证据匹配。BusyBox devmem 与 `/dev/mem` 存在，`CONFIG_DEVMEM=y`、`CONFIG_STRICT_DEVMEM` 未启用；通过身份门控后才实际访问 M3 寄存器。

复用既有 M3 构建，硬件工程固定 commit `a3a83f179503792226adf83082aee7c05de620b4`。没有重新构建系统、选择源码版本、烧录 SD/QSPI、重启或做执行器测试。

使用已经通过三轮官方应用板测的修复 ZOCL：srcversion `9BDC942A6014BCCBD1DCB78`，SHA-256 `5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412`，参数 `enable_xgq_ert=1`。先核对上一轮板端候选，再复制到本轮独立目录临时 `insmod`。原模块文件没有覆盖，修复没有永久安装。

本轮执行范围见 [EXECUTION_PLAN.md](EXECUTION_PLAN.md)；旧 M3 计划和旧报告保留其封存时的“待板测”状态。

## 2. 独立备份、传输及加载

板端工作目录：`/home/root/kv260-m3-boardtest-20261003T021012Z/`。

其中保存原驱动、模块参数、boot_id、原配置、FDT、实时设备树、官方固件、VART 配置和起始日志；原 `/home/root/kv260-test-20261001/baseline-backup/` 未覆盖。

完整测试包 3425918 字节，通过 UART **1116 帧**逐帧确认和整包 SHA-256 校验；SHA-256：`589e971480d4cdd2a697c8f33253a7ada4acc38cf800c3424b385061a5244702`。安全解包 26 个预期普通文件，拒绝不符路径、链接及覆盖；包内 25 项文件校验通过。

只将四个运行文件安装到新的 `/lib/firmware/xilinx/kv260-benchmark-b4096-m3/`，随后核对 DFX manager 已识别该独立应用。加载为一次完整 PL 配置，DTBO 使用 `fpga_full`；XCLBIN 为元数据文件，不含 BITSTREAM section。

| M3 文件 | SHA-256 |
|---|---|
| BIN | `a48a25265d280f268300f627e6408ec56707a70d4deebe46e358500cf17b2650` |
| DTBO | `51ce617967e0c0657bcc2629f1a0a8efa1e4bad3f3bc8f0b1931aacb5bf91937` |
| XCLBIN | `875ca912d87b2c993716f4c353265a9cf403b0c9890442610e64291787caafc3` |
| shell.json | `802dbc8b3f118313a5a74df46f56dc550a61b687dfd484fc6a8fd5ac7895c344` |

恢复后四份文件再次校验一致，目录保留，M3 当前 inactive。它们是先前本机构建及打包的输入，本轮新增成果为板测、日志、诊断与报告。

## 3. 实际硬件验证

加载后唯一活动应用为 `kv260-benchmark-b4096-m3` slot 0，FPGA manager `operating`，实时 firmware-name 为 `kv260-benchmark-b4096-m3.bit.bin`。

| 检查 | 实测结果 |
|---|---|
| DPU | 1 CU，DPUCZDX8G_ISA1_B4096，DPU/XRT 查询频率均为 300 MHz |
| DPU 地址 | `0xa0010000` |
| 架构指纹 | `0x101000056010407`，匹配原模型要求 |
| M3 XCLBIN UUID | `c5255f48-d8da-4df0-e36e-a7c7d21b9dd8`，在内核元数据日志中确认 |
| DPU IP 标记 | v4.1.0，`2023-02-21 21-30-00`，git `7d32c41` |
| 自研 IP 基址 | `0x80080000` |
| IP_ID / ABI_VERSION / BUILD_ID | `0x41555241 / 0x00010000 / 0xa5078450`，实际读回匹配 |
| SCRATCH | `0x8008000c`，原值 `0x00000000` |

通过三项身份检查及安装文件哈希检查后，SCRATCH 依次写入、回读 `0x00000000`、`0xffffffff`、`0x55aa33cc`、`0xaa55cc33`，最后恢复并读回原值 `0x00000000`。推理及性能测试完成后再次检查身份和 SCRATCH，均保持预期。

寄存器只进行了四个允许地址的 32 位访问。没有在官方配置下盲读 M3 地址，也未测试字节 WSTRB、协议仿真或同时进行寄存器访问与 DPU 推理。

## 4. 同模型同图及性能

沿用原 ResNet18、原 `pytorch-resnet-dog.jpg`、原图片列表与分类／性能程序。模型、图片和程序的准确 SHA-256 保存在 [baseline_hashes.output](evidence/20261003T021012Z/02-state.baseline_hashes.output)，本轮首尾核验全部一致。

官方对照、M3 及恢复后 Top-5 和打印分数全部相同：Samoyed `0.949879`；white wolf `0.00931229`；Pomeranian `0.00821807`；Great Pyrenees `0.00498451`；Arctic fox `0.00388194`。

各线程数预热 10 秒，再各运行三次 60 秒。原始输出、实际返回码及每次前后温度快照完整保留。

| 线程数 | 官方对照三次 FPS | M3 三次 FPS | 官方／M3 中位数 FPS | 中位数变化 |
|---:|---|---|---|---:|
| 1 | 215.076 / 215.130 / 215.115 | 215.118 / 215.132 / 215.103 | 215.115 / 215.118 | +0.001395% |
| 2 | 238.912 / 238.995 / 239.028 | 238.865 / 239.000 / 238.906 | 238.995 / 238.906 | −0.037239% |

本轮未见明显性能下降。三次同图短时测试不能代表长期稳定性或所有模型的性能。

## 5. 卸载与恢复

原驱动退出官方应用时，底层 remove 返回 0，同时实际出现一次 `expected refcount 1 instead of 2 ... /axi/zyxclmm_drm`，uptime `7167.148050`。该已知错误单独归档，通过既定停点审阅后正常卸载原模块并加载精确修复候选；旧泄漏对象未手工处理。

从修复驱动加载起点 uptime `7235.39` 起，采集的内核日志没有新的目标引用错误或已检查的异常。M3 在 uptime `8164.48` 开始正常卸载，返回 0，新增目标引用错误为 **0**。

随后正常卸载修复模块，`modprobe zocl enable_xgq_ert=1` 恢复原驱动，再加载官方应用。最终及追加只读诊断确认：

- 原 srcversion `0991D1B457855C8987936E6`、原参数、原内核和备用卡身份。
- 唯一 active slot 0 为 `kv260-benchmark-b4096`，FPGA `operating`；M3 inactive。
- 原 firmware-name、`/etc/vart.conf`、DPU 指纹、300 MHz、原 IP 标记 `ce8dd1`。
- 原 BIN/DTBO/XCLBIN/shell、模型及 prototxt、图片／列表、分类／性能程序、旧备份等 **11 份文件首尾哈希一致**。
- 恢复后的同图 Top-5 再次通过；M3 四份运行文件的恢复后哈希也一致。

原驱动当前仍有已定位的引用缺陷；本轮修复仅临时加载，下一次受控切换仍须按修复方案处理。

## 6. 新发现：DFX manager 目录监视表问题

完整日志的实际服务为 `dfx-mgr.service`、PID 1010。早先快照查询了 `dfx-mgrd` unit，只有空日志；追加审阅通过实际服务和 PID 补采完整日志，没有用空查询声称管理器无错误。

捕获窗口中有 **44 条去重后的错误行**，首次观测于 uptime `8232.393844`，在恢复原模块及之后的状态查询期间出现：`add_to_watch():554 no room to add more watch: No such file or directory`。这是管理器错误，须与已经通过的内核引用释放检查分开记录。

源码追溯到原配方固定 commit `bc06691eb35d7f0acb7c2508b6d050d77b0264a0`；官方两个文件的 Git blob SHA 与固定 commit 树一致。`listAccelerators()` 每次遍历固件目录，`acell_dir_add()` 在基准设计去重前调用 `add_to_watch()`；后者直接追加，没有按路径／watch descriptor 去重，内部 `MAX_WATCH=500`。源码证据见 [固定 daemon_helper.c](https://github.com/Xilinx/dfx-mgr/blob/bc06691eb35d7f0acb7c2508b6d050d77b0264a0/src/daemon_helper.c#L541)、[固定头文件](https://github.com/Xilinx/dfx-mgr/blob/bc06691eb35d7f0acb7c2508b6d050d77b0264a0/src/daemon_helper.h)。

只读 fdinfo 显示该 daemon 实际只有 **5 个内核监视项**，对应固件根目录及四个 app 目录；内核 `max_user_watches=31576`、`max_user_instances=128`。结合源码报错分支，支持内部重复登记表耗尽这一原因；没有直接读取或修改 daemon 堆内存。此报错分支不是 `inotify_add_watch()` 失败，不能仅凭尾随 errno 文本认定缺文件或建议提高系统限额。

本轮功能／性能／恢复检查通过，但管理器监听可靠性尚未修复。没有重启服务、改 sysctl 或替换管理器。下一步应在独立源码中修复重复登记，保留原 binary／service／配置，再分别验证大量只读列表查询、目录更新及受控加载恢复。不能只扩容内部表或重启后暂时无错就算根治。

详见 [manager_review.json](evidence/20261003T021012Z/manager_review.json) 和原始 [manager_logs.output](evidence/20261003T021012Z/26-post-review.manager_logs.output)。

## 7. 保留问题与证据

动态属性警告仍在：本轮 M3 加载及官方恢复加载各新增 16 条，跨本轮所采快照共观察到 80 条带 uptime 的独立警告行，没有删除诊断。M3 的 +0.009 ns setup 裕量、7 个输入／9 个输出 delay 缺口和 621 条 DRC Warning 仍按原构建审阅保留，外部接口未验收。

53 条主板测及追加审阅命令成功，再加 1 条只读管理器诊断，共 **54 条 UART 命令**成功并完成输出 SHA-256 校验。主结果见 [board_validation_summary.json](evidence/20261003T021012Z/board_validation_summary.json)；管理器补充结论见 manager_review。

现有五份输入索引保留；新证据、源代码副本、原始 UART、报告和当天补充日志使用 [EVIDENCE.sha256](EVIDENCE.sha256)，校验记录为 [EVIDENCE_VERIFY.json](EVIDENCE_VERIFY.json)。待完成项为管理器去重修复、修复驱动持续使用方案、并发／字节选通／长期验证，以及后续 PWM 和运动控制。
