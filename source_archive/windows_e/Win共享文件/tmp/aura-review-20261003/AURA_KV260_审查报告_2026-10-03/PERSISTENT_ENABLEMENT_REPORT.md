# KV260 修复版运行时持久启用与冷启动验收

## 结果

备用卡已启用此前板测通过的 DFX manager 与 ZOCL 修复版，并完成一次冷启动验收。systemd 249 在开机时先成功加载修复 ZOCL，再启动修复 manager；官方 `kv260-benchmark-b4096` 自动加载。`xdputil query` 和原 ResNet18 XMODEL/原图片分类均返回 0，Top-5 与原基线一致。

没有替换板端 PetaLinux、Vitis AI 运行库、官方 BIT/DTBO/XCLBIN 或模型，也没有写 QSPI。只新增独立候选目录和 systemd 配置，原文件保留在原路径并有单独恢复副本。

## 实际操作与验证

1. 备用卡确认：CID `0353445345333247805558c00401a100`，root `/dev/mmcblk1p2`；PetaLinux 2022.2，kernel `5.15.36-xilinx-v2022.2`。
2. 26 项原运行时、官方固件、ResNet18、图片和测试程序 SHA-256 在写入前、重启后均为 26/26 匹配。
3. 候选输入从主机经 UART 传到 staging。包 SHA-256：`ce9dc5f7f24b61c3fdb6fbfa0566b0d893b72a1e8f92a76dce82c4bdc30f6c95`；包内 6 个成员的字节数和 SHA-256 全部匹配清单。
4. 板端 systemd 249 临时解析检查先通过：loader `LoadState=loaded`，manager 解析出 `Requires=kv260-repaired-zocl.service` 与 `After=...kv260-repaired-zocl.service`。临时文件在 `/run` 删除并 `daemon-reload`，确认原 manager 仍 active、无 drop-in、原 ZOCL 和 boot ID 未变。
5. 恢复点保存在备用卡 `/home/root/kv260-runtime-persistent-backup-20261003/`。包含原 manager、客户端、libdfx、原 ZOCL、原 unit 和配置、26 项 SHA 清单/核验、原 baseline 归档副本、安装前状态与 dmesg。备份 10 个原件摘要均通过；目录约 12 MB。
6. 修复二进制安装到 `/usr/local/lib/kv260-runtime-repair/`；unit 放到 `/etc/systemd/system/kv260-repaired-zocl.service`，manager drop-in 放到 `/etc/systemd/system/dfx-mgr.service.d/10-kv260-repaired.conf`。所有安装文件哈希和 staging manifest 一致。首次相对路径拷贝因当时位于备份目录而失败；只留下两个空目录，没有文件覆盖。改用绝对路径后成功，安装状态复核正常。
7. 执行 `systemctl reboot` 后 boot ID 从 `64083069-98b7-409b-a455-b7b3b7158745` 变为 `0251d729-0d3c-44e8-abb9-27121306c081`。新启动 root 仍为备用卡，活动应用为官方 benchmark slot 0。
8. 冷启动顺序证据（单调时钟）：修复 loader `12.990108 s` 开始、`13.042471 s` 完成；manager `13.669094 s` 开始，默认固件检测成功，manager `13.934433 s` 启动；ZOCL 对官方 overlay 的 probe 在 `15.146000 s`。loader 和 manager 的 systemd `Result=success`，ExecMainStatus 0。
9. 修复驱动 srcversion `9BDC942A6014BCCBD1DCB78`，参数 `enable_xgq_ert=1`，refcnt 0。manager 进程为 PID 1012，ExecStart 指向修复版；DropInPaths 指向已安装的 drop-in。
10. `xdputil query` exit code 0：1 CU、`DPUCZDX8G_ISA1_B4096`、300 MHz、`0xa0010000`、fingerprint `0x101000056010407`。
11. 使用相同模型、图片和分类程序再次运行，exit code 0：

   | 排名 | 类别 | 分数 |
   |---:|---|---:|
   | 1 | Samoyed | 0.949879 |
   | 2 | white wolf | 0.00931229 |
   | 3 | Pomeranian | 0.00821807 |
   | 4 | Great Pyrenees | 0.00498451 |
   | 5 | Arctic fox | 0.00388194 |

   XMODEL SHA-256 `4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef`；图片 SHA-256 `f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a`；分类程序 SHA-256 `322dd07736f409cba02416782475c0dc2b5951435ddbb6d0671d3cda8fac0c0e`。

## 遗留系统问题

- `proc-fs-nfsd.mount` 在本次启动失败，原因是内核没有 `nfsd` filesystem。它不影响 DPU、manager 或推理，本轮未更改 NFS 配置。
- 启动日志有 `FAT-fs (mmcblk1p1): Volume was not properly unmounted` 警告。板端没有 `fsck.vfat`/`dosfsck`，本轮没有尝试修复。`/etc/fstab` 仍保留两条 `/boot` 配置；不应把该文件系统警告当作已解决。
- 官方 overlay 原有属性警告和 `zocl` 的 `IRQ index 8 not found` 信息仍出现；本次功能和推理通过，但这些 warning 没有被更改或隐藏。
- 冷启动只验收一次。已通过持续运行阶段的 30 分钟测试在之前运行时复验中完成；此次重启后没有再重复 30 分钟长测、断电测试或 PWM/执行器测试。

## 证据与恢复

板端冷启动记录、完整启动 dmesg、manager/loader journal、query JSON、分类 stdout/stderr、输入哈希及状态摘要保存在：

`/home/root/kv260-runtime-persistent-backup-20261003/postboot/`

`evidence.sha256` 中 13 项证据逐项校验通过；`stock-check.log` 中 26 项原始基线逐项通过。安装前恢复副本位于同目录的 `original/`，其摘要清单为 `backup.sha256`。主机保留候选输入和本报告；板端 staging 包保存在 `/home/root/kv260-runtime-stage-20261003/`。

如需恢复原版：先通过 UART 保存现场；manager 可用时用 `xmutil unloadapp` 正常卸载官方 overlay；停止 manager；删除本方案创建的 manager drop-in 与 loader unit 后运行 `systemctl daemon-reload`；正常卸载修复 ZOCL（禁止 force）；从原 `/lib/modules/5.15.36-xilinx-v2022.2/extra/zocl.ko` 加载原模块，重新启动 vendor `dfx-mgr.service`，检查原 srcversion 和官方 slot 0。原 `/usr/bin/dfx-mgrd`、原 ZOCL、vendor unit、固件和模型未覆盖。若 manager 不可用，先通过 UART 按状态恢复原 manager，再正常卸载应用和模块。

## 当前状态

修复版已在备用卡持久启用并完成一次冷启动 + DPU 功能验收。Ubuntu 主机侧审阅包摘要记录中包含报告、安装配置和板测候选文件；板端原备份和运行证据仍保留。当前运行时仍是易于回滚的备用 SD 卡方案，没有烧写 QSPI 或替换固件镜像。
