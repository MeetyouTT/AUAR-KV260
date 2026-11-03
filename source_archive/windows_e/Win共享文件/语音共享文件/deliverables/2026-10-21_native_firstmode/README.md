# 开机首次输出改为1024×600：实板软件重启已验证

UTC2026-10-21 13:44～13:55，14:02～14:05补记。用户先确认屏幕当前正常，随后明确要求优先修复板卡先输出1024×768的问题。本轮完成两处配置修改，并实际进行一次受控软件重启。**本次Linux启动不再创建早期1024×768 framebuffer，Xorg首次即选择1024×600。用户随后反馈本次改动有效、闪屏形式改变，但仍有规律性条纹，整体闪屏未修复。**

## 问题与改动

改动前boot bec99c5a…：内核fb0名称xlnxdrmfb，模式U:1024x768p-0、虚拟尺寸1024×1536、16bpp；Xorg22.152秒也选择1024×768，然后启动器再设置1024×600。只改Xorg不能覆盖更早的内核出图。

| 活动文件 | 实际修改 |
| --- | --- |
| /boot/uEnv.txt | 在原bootargs末尾增加drm_kms_helper.fbdev_emulation=0，停用早期fbdev模式提交；原启动参数和原Image选择保持 |
| /etc/X11/xorg.conf | DP-1关联AURA-HDMI，固定49.000MHz、1024 1072 1168 1312 / 600 603 613 624、-HSync/-VSync；设PreferredMode和16位Display首选为1024×600 |

开机前段由Xorg接管前不显示fbdev控制台，随后首次按本屏原生模式出图；现有串口console=ttyPS1保留。启动前检查没有发现进程打开/dev/fb*，当前业务使用Xorg/DRM。

Xorg配置复用此前已审查的屏幕专用时序，SHA64457c25a844ef95cd4ae62bacba80b0cbec5ae1a54efdc15e3ec02775c0555a；新uEnv SHAd120b2f78e40ec690fcda92f5c0791a93d587cf75d399695301005c45800d369。本轮没有重装旧GUI启动器；原Image/DTB/boot.scr及audio-frontend实际启动器/配置五份SHA保持。原power_on_delay_ms=5000仍保留，本轮不改变其时点或将它标为已有效。

## 实板验证

新boot **c393d68c-f733-499e-99b5-1a26a6cb9b8e**，仍运行原2022-10-03 #1内核：

- cmdline包含fbdev_emulation=0，运行参数为N，无/sys/class/graphics/fb[0-9]*，启动日志未创建fb0。
- Xorg15.812秒使用AURA-HDMI配置，15.864秒记录`Output DP-1 using initial mode 1024x600 +0+0`；首次模式列表仅1024×600。
- 当前扫描为1024×600/49MHz/59.85Hz、原生同步极性；EDID128/SHA727d3e18…保持，显示模式列表无1024×768。
- GUI1077、相机1016、Xserver监督1076均active/NRestarts0；GUI IDLE/main、error空，人物持续显示计数非零；相机529帧、采集9.73Hz/检测9.49Hz，两个错误字段空。这是启动后快照，不是长稳测试。
- 目标配置和五份受保护文件均回读通过，UART回显恢复。实际只发出一次系统重启，启动期间不向U-Boot发送输入。

主机安装/回退检查最终6项全部通过，覆盖原参数保持、两个原子替换点之后的故障恢复、后续改动拒绝覆盖、以及与UART实际加载方式相同的无__file__执行。没有通过这些测试来替代实板启动；实际首次模式另由上述新boot验证。

14:02～14:05又读到新boot975f931a-927b-4a06-b784-ebda8463177f（本轮未发起这次重启，启动方式未确认），fbdev仍N、无fb0，Xorg16.868秒首次仍是1024×600。EDID再次变为空，三业务服务保持active，用户仍见规律性条纹；因此“消除先768高输出”与“修复全部闪屏”须分别记录。用户已确认屏幕USB取电KV260，后续[供电控制对照](../2026-10-21_screen_port_power/README.md)另记，不撤回本项已验证改动。

第一次安装在备份阶段因UART执行环境没有__file__而失败，发生在两个活动文件写入之前。已独立回读两个原件未变，并保留该不完整备份为/boot/aura-native-firstmode-20261021-incomplete-a715d0d551032aee。改用函数编译文件名定位源文件并新增对应检查后，第二次安装完成；失败记录没有删除或掩盖。

## 回退

完整原件及准确安装清单在板端/boot/aura-native-firstmode-20261021。通过串口root运行：

```bash
python3 /boot/aura-native-firstmode-20261021/rollback.py rollback
```

回退先核对两个目标和原件哈希，拒绝覆盖之后的用户改动，再恢复本轮修改前的Xorg和uEnv；不会自动重启。Xorg需重载、内核参数需下一次启动才恢复。原内核Image始终保留，无需重建内核或更新主启动固件。

## 证据边界与交接

[过滤证据](evidence/)区分安装前、首次安装错误、受校验备份归档、修正后安装和真实重启。[源码与配置](src/)保留本轮准确工件；原始UART仅留本机。verification.json核验归档完整性；用户已反馈仍有规律性条纹，物理闪屏修复未通过。用户此前“现在屏幕正常”对应修改前时点，不能代替修改后验收。

本轮仅两份活动配置和专用备份/回退工件变更，保留当前audio-frontend与相机入口，未发送运动命令或修改CPU优化。Windows回执未代填，微力同步状态与本次板端模式验证分别记录。

参数作用依据[AMD对应版本drm_fb_helper实现](https://raw.githubusercontent.com/Xilinx/linux-xlnx/xlnx_rebase_v5.15_LTS_2022.2/drivers/gpu/drm/drm_fb_helper.c)，其中初始化/热插拔恢复路径在停用fbdev时返回；具体模式由现有Xorg/DRM设置。首选模式与输出关联依据[X.Org官方配置说明](https://www.x.org/archive/X11R7.5/doc/man/man5/xorg.conf.5.html)。本机已核对相应源码与实际参数存在性，实际效果以上述新boot为准。
