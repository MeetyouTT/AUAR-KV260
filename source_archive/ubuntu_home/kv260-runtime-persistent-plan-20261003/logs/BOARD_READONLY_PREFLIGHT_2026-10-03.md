# KV260 UART 只读预检

采集方式：Ubuntu 上通过 Xilinx USB UART `/dev/ttyUSB1`、115200 连接，板端 root shell。所有命令均为读取/查询；没有写文件、切换 app、卸载模块或重启。

## 身份与当前基线

- model：`ZynqMP SMK-K26 Rev1/B/A`；`xmutil boardid`：carrier `SCK-KV-G`、serial `XFL1EMEBC1R5`，SoM `SMK-K26-XCL2G`。
- OS：PetaLinux `2022.2_release_S10071807`；kernel `5.15.36-xilinx-v2022.2`。
- root：`/dev/mmcblk1p2`；CID：`0353445345333247805558c00401a100`（匹配备用卡）。
- boot ID：`64083069-98b7-409b-a455-b7b3b7158745`。
- `xmutil listapps`：`kv260-benchmark-b4096` slot 0 active；`kv260-benchmark-b4096-m3` inactive (`-1`)。
- `dfx-mgr.service`：active；FragmentPath `/lib/systemd/system/dfx-mgr.service`；DropInPaths 空；ExecStart `/usr/bin/dfx-mgrd`；ExecStartPre `/usr/bin/xlnx-firmware-detect`。
- 原 manager SHA-256：`bdbd8ee09b3f767a53bd5111240c9ade3bb19b1da83d73bd06785ae86260e9a2`。
- 原 ZOCL srcversion：`0991D1B457855C8987936E6`；模块文件 SHA-256：`215fe760dafb6766545e308d8bc207c31712154fe5a8ed08342a101a5482a98d`；`enable_xgq_ert=1`；refcnt `0`；holders 空。
- DPU DRM 节点 `card1`、`renderD128` 上未发现打开进程。

## 启动顺序证据

1. `/boot/ramdisk.cpio.gz.u-boot` 是 23,214,690 B 的 U-Boot legacy AArch64 initramfs。用 `dumpimage -l` 检查头部，并通过 `dd bs=64 skip=1 | gzip -dc | cpio -it` 流式列出归档，没有在板端落盘。归档无 `lib/modules`、`zocl`、modules-load 项；initramfs 的 `/init` 是标准 rootfs 切换脚本。
2. 根文件系统 `/etc/modules` 为空/不存在；`/etc/modules-load.d`、`/usr/lib/modules-load.d`、`/lib/modules-load.d`、`/etc/modprobe.d`、udev rules 和 systemd unit 搜索没有 `zocl`/`xocl` 配置命中。`/boot/system.dtb` 与 `system-zynqmp-sck-kv-g-revB.dtb` 也没有 zocl/embedded_sched 字符串。
3. `/lib/modules/5.15.36-xilinx-v2022.2/modules.alias` 存在 `of:N*T*Cxlnx,zocl* zocl` 等 OF modalias 映射，因此 overlay 新增兼容节点时，内核仍可能自动请求该模块。
4. 完整读取 `/usr/bin/xlnx-firmware-detect`：当 `/etc/dfx-mgrd/default_firmware` 为 `kv260-benchmark-b4096` 且目录存在时直接成功退出；它不执行 `xmutil loadapp`、`modprobe`、`insmod` 或 overlay 加载。默认 manager service 已 enabled；modules-load 和 udev-trigger 在 `sysinit.target` 前完成。
5. `systemctl --version` 为 systemd 249.7+；板端没有 `systemd-analyze`，因此无法在板端运行 `systemd-analyze verify` 或 critical-chain。拟议 loader 排在 modules-load/udev 后、manager 前；冷启动顺序仍未实测。

## 结论与边界

证据没有发现 initramfs 或显式 boot config 在 manager 之前加载原 ZOCL。新的 oneshot loader 以 `Requires`/`After` 保证在 manager 之前装入已板测的修复模块；此时后续 overlay modalias 会命中已加载的修复模块。loader 遇见 srcversion 不符会失败关闭，不会卸载原模块。该设计可进入 unit 静态审阅和安装前备份阶段。

本次 26 项历史原文件哈希全部重新计算并与记录一致；没有安装配置、切换 app 或重启。持久写入前仍需建立本轮新恢复点；首次重启须验证模块 srcversion、参数、manager 启动时间和官方 app 推理。
