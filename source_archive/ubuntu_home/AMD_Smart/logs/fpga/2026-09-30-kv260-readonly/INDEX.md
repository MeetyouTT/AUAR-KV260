# KV260 只读盘点证据索引

所有证据保存在 Ubuntu 主机。*.serial.raw 是接收的逐字节串口流；*.output 是解码恢复的命令 stdout/stderr；*.results.jsonl 保存命令、传输命令、主机 UTC 时间、退出码和板端生成的输出 SHA-256。板端仅在内存中暂存、压缩输出。

前期异步读取存在缺字；01、01a、01b、02、03 的原始片段保留，但未用于完整数据结论。04 起采用持续接收、限速、序号、gzip CRC 和 SHA-256 校验。

完整校验通过的命令组：23。命令组的退出码属于最后一个命令，不能代替组内每条命令的成功判断；缺失节点、无权限读取等见原始输出。

| 命令组 | 原始输出文件 | 字节数 | 主机采集 UTC |
|---|---|---:|---|
| 04-connection / identity | [04-connection.identity.output](04-connection.identity.output) | 484 | 2026-10-01T04:29:57.739884+00:00 |
| 05-boot-storage / live_dt_identity | [05-boot-storage.live_dt_identity.output](05-boot-storage.live_dt_identity.output) | 488 | 2026-10-01T04:30:24.972349+00:00 |
| 05-boot-storage / storage | [05-boot-storage.storage.output](05-boot-storage.storage.output) | 6960 | 2026-10-01T04:30:26.173266+00:00 |
| 05-boot-storage / tool_sources | [05-boot-storage.tool_sources.output](05-boot-storage.tool_sources.output) | 5865 | 2026-10-01T04:30:35.035561+00:00 |
| 06-logs-services / boot_files | [06-logs-services.boot_files.output](06-logs-services.boot_files.output) | 8003 | 2026-10-01T04:31:01.528445+00:00 |
| 06-logs-services / kernel_log | [06-logs-services.kernel_log.output](06-logs-services.kernel_log.output) | 43794 | 2026-10-01T04:31:03.002514+00:00 |
| 07-services-network / services | [07-services-network.services.output](07-services-network.services.output) | 12039 | 2026-10-01T04:32:06.081154+00:00 |
| 07-services-network / network | [07-services-network.network.output](07-services-network.network.output) | 4928 | 2026-10-01T04:32:08.946213+00:00 |
| 08-board-packages / board_qspi | [08-board-packages.board_qspi.output](08-board-packages.board_qspi.output) | 1650 | 2026-10-01T04:33:17.705780+00:00 |
| 08-board-packages / packages_sources | [08-board-packages.packages_sources.output](08-board-packages.packages_sources.output) | 75820 | 2026-10-01T04:33:20.491194+00:00 |
| 09-live-fpga / live_device_tree | [09-live-fpga.live_device_tree.output](09-live-fpga.live_device_tree.output) | 82055 | 2026-10-01T04:33:59.393410+00:00 |
| 09-live-fpga / fpga_runtime | [09-live-fpga.fpga_runtime.output](09-live-fpga.fpga_runtime.output) | 5715 | 2026-10-01T04:34:06.452080+00:00 |
| 10-overlay-driver / overlay_zocl_metadata | [10-overlay-driver.overlay_zocl_metadata.output](10-overlay-driver.overlay_zocl_metadata.output) | 3328 | 2026-10-01T04:36:29.932542+00:00 |
| 11-peripherals / peripheral_nodes | [11-peripherals.peripheral_nodes.output](11-peripherals.peripheral_nodes.output) | 3505 | 2026-10-01T04:37:03.074379+00:00 |
| 12-tool-sources / query_autoconfig_sources | [12-tool-sources.query_autoconfig_sources.output](12-tool-sources.query_autoconfig_sources.output) | 6927 | 2026-10-01T04:37:18.748266+00:00 |
| 13-health / sensors_health | [13-health.sensors_health.output](13-health.sensors_health.output) | 12930 | 2026-10-01T04:37:33.084046+00:00 |
| 14-boot-hashes / boot_firmware_hashes | [14-boot-hashes.boot_firmware_hashes.output](14-boot-hashes.boot_firmware_hashes.output) | 10698 | 2026-10-01T04:39:54.231430+00:00 |
| 15-runtime-check / runtime_file_integrity | [15-runtime-check.runtime_file_integrity.output](15-runtime-check.runtime_file_integrity.output) | 39132 | 2026-10-01T04:40:55.419384+00:00 |
| 16-model-inventory / models_apps_inventory | [16-model-inventory.models_apps_inventory.output](16-model-inventory.models_apps_inventory.output) | 344259 | 2026-10-01T04:43:12.529839+00:00 |
| 17-autoload-metadata / scripts_kernel_metadata | [17-autoload-metadata.scripts_kernel_metadata.output](17-autoload-metadata.scripts_kernel_metadata.output) | 4800 | 2026-10-01T04:43:29.334156+00:00 |
| 18-model-metadata / model_metadata_provenance | [18-model-metadata.model_metadata_provenance.output](18-model-metadata.model_metadata_provenance.output) | 5690 | 2026-10-01T04:46:35.114070+00:00 |
| 19-live-loaded-metadata / loaded_metadata | [19-live-loaded-metadata.loaded_metadata.output](19-live-loaded-metadata.loaded_metadata.output) | 2126 | 2026-10-01T04:48:25.616261+00:00 |
| 20-final-snapshot / final_snapshot | [20-final-snapshot.final_snapshot.output](20-final-snapshot.final_snapshot.output) | 315 | 2026-10-01T04:50:07.957378+00:00 |

## 边界

Ubuntu 镜像读取未使用挂载、loop device 或 rootfs chroot；mtools 只读取镜像，提取副本仅写入本证据目录。ext4 文件解析只使用 rb，选定文件与板端哈希交叉验证。

未执行：板卡 reboot/reset、SD/QSPI 烧录、固件升级、loadapp/unloadapp、overlay 写入、安装、启动参数修改、模型推理、相机采集、音频采集/播放、I2C 地址扫描、GPIO/PWM 设置、/dev/mem 或执行器寄存器读写。

本轮 xbutil examine 产生了正常的 XRT 客户端创建/退出日志；本轮没有新增 xclbin 注册记录。上轮 xdputil query 的注册和 context 记录发生在本轮只读盘点开始之前，详见 REPORT.md。
