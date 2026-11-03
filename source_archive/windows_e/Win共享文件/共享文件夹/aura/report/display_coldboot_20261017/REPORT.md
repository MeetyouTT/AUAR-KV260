# 断电后花屏：显示启动检查与预防性修复

日期：2026-10-17（America/Los_Angeles）；实际读板证据为 UTC 2026-10-18 04:22—04:30。

## 结论

用户报告：断电第二天开机时屏幕花屏，断开并重新连接 HDMI 后恢复。**当前证据支持优先排查冷启动显示识别/初始化，但尚未确诊是供电顺序、连接链路还是驱动问题。**

已安装启动器 `d2e45eb7fee4fa08`，服务下一次启动时生效。当前界面和相机保持运行，本轮没有实际切换显示输出或重启整板。主机和板端各17项启动逻辑测试通过，真实文件/模块预检通过；物理花屏是否解决仍需下一次冷启动确认。

## 本次实际发现

- 实板 boot 为 `4e34d2fb-8f97-4cda-a598-c01d510e5c99`；本次没有发起该启动，不能据此追加冷启动验收。
- 该次启动的 `setup.json` 明确为 `edid_missing=true`、`mode_source=previously_verified_timing`：开机未取得 EDID，旧启动器立即用了固定时序回退。
- 读取时 `/sys/class/drm/card0-DP-1/edid` 为0字节；Xrandr 仍报告屏幕 EDID 和正确的 1024×600 / 59.85Hz 时序。两处状态不能直接当作同一时刻可靠的面板就绪证明；也不能凭 Xrandr/DPMS 正常确认实物画面正常。
- GUI/Xserver/相机服务 active；GUI PID1349、监督器PID1047、相机PID986。触摸设备在线，界面空闲，音量58%非静音。
- 旧启动器有固定时序校验，但没有给迟到 EDID 留宽限、等待显示状态稳定或强制重建同模式输出的步骤。

EDID 缺失/错误确实可能造成启动显示异常，见 [Linux 内核 EDID 说明](https://cdn.kernel.org/doc/html/latest/admin-guide/edid.html)。[Xrandr 官方手册](https://xorg.freedesktop.org/archive/X11R7.5/doc/man/man1/xrandr.1.html) 区分查询与设置，`--current` 不轮询硬件变化；`--off` 关闭指定输出，`--mode` 选择模式。本项目采用已验证时序的用户态启动补丁，未设置内核 EDID 覆盖或修改驱动。**上述资料说明机制，不能代替本屏硬件根因证据。**

## 修改与生效方式

1. EDID 为空时先等待最多15秒，再考虑固定时序回退；非空但不同的 EDID 不覆盖。
2. 显示身份连续稳定3秒后配置；回退仍要求接口 connected、指定微雪触摸设备在线及原来已验证的49MHz时序完全匹配。
3. 每次开机最多将已确认的 `DP-1` 输出关闭1秒再恢复。关闭前保存当前 boot 的尝试标记，服务失败或重启不反复关闭；即使取消/异常也在 finally 中尝试恢复输出。
4. `/run/aura-display-startup.json` 和会话 `setup.json` 明确记录软件配置与物理面板验收的区别，`physical_panel_verified=false`。
5. 新配置来自当前实板清单，保留 GUI、ASR 及相机热拔插修复的54项组件哈希；没有沿用主仓里较早版本的清单。

新文件位于板端 `/home/root/aura-ui-startup-20261009/releases/d2e45eb7fee4fa08/`。已更新 `/etc/systemd/system/aura-avatar-ui.service` 并 daemon-reload，保持开机启用。**当前运行进程仍来自 `190bbd429af06931`；新逻辑在下次服务启动/开机才执行。**

修改源码：[launcher.py](../../scripts/board_ui_startup/launcher.py)、[配置](../../scripts/board_ui_startup/config.json)、[新增启动测试](../../scripts/board_ui_startup/test_display_startup.py)，并更新 service、release_manifest 和启动文档。

## 验证

- 主机启动测试17项通过，包含旧保护条件在新配置下复测和7个新增时序/失败场景。见 [主机输出](host_display_tests.log)。
- 相同测试在 KV260 执行17项通过，见 [板端输出](board_display_tests.log)；所有 Xrandr 调用均为 fixture，这些是板端软件测试，不是物理 HDMI 测试。
- 新启动器实际 `--preflight` 通过，GUI、54项组件及内核/触摸模块核验通过；5个部署文件大小/SHA与清单匹配。
- 安装前后 boot、监督器/GUI/相机 PID、相机代次和保护文件摘要保持；音量58%非静音。没有重启当前服务、切换显示、操作运动、FPGA或Windows。
- ZIP `display-startup-d2e45eb7fee4fa08.zip` 为13085字节，SHA256 `83f284ba2d5b3af0270f9f2f7f5911c70250f2b9aeb95246d389a9226e366f8a`。见 [构建核验](build_validation.json)、[发布清单](manifest.json)。
- 独立核对36份完整 UART 响应和4份附件、ZIP载荷、5个部署文件、54项保留组件哈希；回显恢复。见 [最终核验](validation.json)、[安装回执](installation.json)、[显示原始状态](display_inspection.json)。

## 仍待现场验收

下次完全断电后开机，保持 HDMI 原样连接，给启动等待留出时间，观察是否无需重新插拔就能正常显示。若仍花屏，先保留故障现场，记录屏幕和板卡的上电顺序，再读取对应 boot 的日志、EDID 和真实面板表现。软件输出恢复也不等同于物理 HDMI 拔插或面板确实恢复。

本次尚未收到“当前仍花屏/已恢复”的现场确认，也未实际复现用户所述花屏；没有将正常界面截图、回读分辨率或服务 active 记作物理屏幕验收通过。需要该次真实冷启动后才能决定是否进一步检查电源/线缆/转换链路或驱动。

## 备份与证据

板端旧 unit/launcher/config 备份：`/home/root/aura-display-coldboot-20261017/release-d2e45eb7fee4fa08/backup/`。如需回退，应使用该实板原件并重新加载服务配置；不要退回此前缺相机新哈希的历史版本。

主机工作目录 `/home/ghmd/aura-display-coldboot-20261017/` 保存修改前源码、打包/安装助手和验证。原始 UART 证据在 `/home/ghmd/aura-asr-integration-20261016/evidence/` 下：

- `20261018T042245.939539Z-display-coldboot-readonly`：启动与显示状态，只读。
- `20261018T042411.183463Z-display-startup-inventory`：实板原始启动器/配置/unit，含独立校验附件。
- `20261018T042705.608107Z-display-startup-install`：安装和板端软件测试；当前进程保持。
- `20261018T042856.255950Z-display-startup-verify`：独立回读新启动文件和板端17项测试原始输出，当前监督器仍为旧版本，恢复标记尚未生成。

本报告、包和主机结果位于微力共享目录；原始 UART 目录位于共享根之外。
