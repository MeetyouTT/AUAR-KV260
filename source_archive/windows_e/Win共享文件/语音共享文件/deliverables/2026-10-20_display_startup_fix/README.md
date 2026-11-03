# HDMI冷启动修复：已安装，等待实屏冷启动验收

2026-10-20本地 / UTC2026-10-21：按“接下来怎么办”继续修复。两个活动文件已经更新并回读哈希，当前运行进程没有重启。**软件测试通过；尚未证明上电花屏已经消除。**

前轮依据见[上电花屏诊断](../2026-10-20_display_boot_audit/README.md)：本次启动早期EDID为空、Xorg先输出1024×768，之后启动器才补1024×600；物理拔插可以恢复。此次修复处理确定的启动时序问题和重置状态误报，不能据此认定具体物理器件的根因。

## 实际改动

- [xorg.conf](src/xorg.conf)：为DP-1关联AURA-HDMI，增加本屏EDID已测得的49MHz、1024×600、1312×624总时序及首选模式，使Xorg从启动阶段就能选择该模式。保留ARMSOC驱动、原设备选项、16位色深及输入设备配置。同步范围只包围该实测时序；这是当前屏幕专用配置。
- [launcher.py](src/launcher.py)：分别记录关闭输出、完整等待和恢复输出；OFF失败/超时不能再被报告为完成重置。恢复后允许界面启动并报告不完整状态；同boot即使失败也不会再次关闭输出，避免重启循环造成反复黑屏。保留原2秒关闭、EDID等待和触摸设备门槛。旧标记只证明已经尝试过，不能补算成功。
- [install.py](src/install.py)：核对板卡、boot、活动入口、配置和原文件哈希；备份后原子替换。失败回退已替换文件，包括原子重命名后的错误；显式回退拒绝覆盖后来的修改。不会重启服务或板卡。
- 共享业务源码只合入显示函数及新增回归；保留它原有GTK入口。此目录的板端候选保留实际活动的`board_avatar_pan.py`入口。**不得拿共享目录历史config/release_manifest覆盖当前板端GUI、音频或241项组件配置。**

## 验证与运行状态

| 检查 | 结果与边界 |
| --- | --- |
| Ubuntu候选测试 | 42项通过：37项显示fixture + 5项临时文件系统安装/回退注入；见[日志](evidence/host-tests.log) |
| 共享业务源码 | 39项通过：37项显示fixture + 2项真实loopback端口生命周期；后者含70秒等待 |
| KV260候选测试 | 同42项通过，1.438秒；显示命令均mock，安装测试只写临时目录，见[板端软件证据](evidence/board-software-tests.json) |
| Xorg配置 | Ubuntu Xorg1.20.13、dummy驱动接受配置并选中1024×600、16位；日志含精确49MHz Modeline。dummy不验证实际ARMSOC、DP-1绑定或HDMI物理链路，见[验证范围](evidence/xorg-dummy-validation.json) |
| 板端预检 | 实际runtime的GUI、241项组件及触摸模块哈希通过；配置SHA保持，关闭时长仍2秒 |
| 安装回读 | 活动启动器`ea68cb07…`，`/etc/X11/xorg.conf`为`64457c25…`；见[完整安装证据](evidence/installation.json) |
| 当前进程 | GUI监督1072、相机988、Xserver监督1056前后不变，均active/NRestarts0；UI为IDLE/vision、无错误 |
| 实际冷启动/实屏 | **未执行、未验收**；当前进程仍运行安装前已加载的代码和Xorg配置 |

实际启动器路径：`/home/root/aura-render24-budget-20261020/e06409743174/startup/launcher.py`。本轮仅替换该启动器与Xorg配置，不新增更高优先级的systemd覆盖项；今后切换runtime时，应把本补丁合入新的启动器。

转轴仍FAULT/Boot mismatch、固件仍官方DPU。旧boot临时锁已经退出；本轮没有重连、运动命令、固件变更或恢复CPU优化。

## 接下来的现场验收

1. 正常关机后再断电上电，HDMI全程保持连接，先不要拔插。
2. 等界面启动完成，记录是否仍花屏。Ubuntu核对新boot、Xorg实际初始模式、早期EDID、重置各阶段和服务状态；不能仅凭软件模式读回判定实屏正常。
3. 正常后继续复验冷启动和普通重启；若仍花屏，先保留启动证据，再记录物理拔插后的变化，继续缩小板载分配器/屏幕热插拔同步路径问题。

此轮没有发起关机、重启、Xorg重启或实际输出开关。安装后下一次Xorg启动才读取新配置，下一次GUI服务启动才加载新启动器。

## 回退

原件在板端`/home/root/aura-display-startup-fix-20261020/48280631334c/backup`，[安装清单](src/manifest.json)保存前后目标。串口root下运行：

```bash
python3 -B /home/root/aura-display-startup-fix-20261020/48280631334c/install.py rollback
```

回退只恢复文件，不自动重启。脚本会核对当前文件仍是本补丁和备份哈希；若其他会话已改过它们，会拒绝覆盖，需先审查差异。实际板端回退未执行；回退逻辑已在Ubuntu和KV260临时目录测试。

## 交接和证据

[操作来源](evidence/provenance.json)记录各UART阶段和主机证据位置。最初20条传输命令及文件哈希通过，但工具关闭UART时日志句柄已提前关闭，报`ValueError: write to closed file`；修正工具后，下一独占UART会话恢复回显并核对候选、完成42项测试，之后才安装。传输阶段另补充了安装异常回退保护及对应测试，最终8个候选文件哈希均与共享源码一致。

共享中只保存过滤JSON、代码、配置和测试，不含实屏/人脸图片、身份库、原始串口日志、密钥或模型权重。Windows回执未代填；共享文件写入不等于Windows同步确认。

Xorg输出关联、Modeline和PreferredMode语义依据[X.Org官方手册](https://www.x.org/archive/X11R7.5/doc/man/man5/xorg.conf.5.html)。硬件路径与内核能力依据前轮报告引用的AMD/Xilinx资料；本轮没有重新构建内核或修改固件。
