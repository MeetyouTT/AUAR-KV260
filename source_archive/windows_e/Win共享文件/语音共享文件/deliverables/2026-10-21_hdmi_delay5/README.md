# HDMI显示链路等待5秒：已配置，待冷启动验收

用户要求电源重新接通后延迟HDMI通信5秒。本轮在实际KV260的SD启动分区新增 `/boot/uEnv.txt`，保留全部原始内核启动参数，仅追加 `zynqmp_dpsub.power_on_delay_ms=5000`。另加一条uenvcmd提示文字，便于串口确认导入；不包含sleep或额外启动动作。配置已落盘并回读，当前运行内核仍是4ms，下一次启动才会采用候选参数。未执行重启、断电或显示关开。

## 延时的准确含义

[实际内核版本对应的AMD驱动源码](https://raw.githubusercontent.com/Xilinx/linux-xlnx/xlnx_rebase_v5.15_LTS_2022.2/drivers/gpu/drm/xlnx/zynqmp_dp.c)提供power_on_delay_ms，默认4ms。encoder enable在检测为connected时，先通过AUX发送D0电源唤醒请求，再等待指定时间，然后在请求成功时进行链路训练并启用主数据流。本次将此等待设为5000ms。

因此，它不是从接电瞬间计时的“HDMI所有通信静默5秒”，也不推迟早期HPD或EDID探测，更不等同物理插拔；无法用它保证解决所有EDID为空的问题。每次走该输出启用路径都可能等待5秒，启动期间若多次启用输出，总耗时可增加不止5秒。原启动器单次命令超时8秒，服务启动超时90/240秒；未改这些限制，实际链路训练与初始化是否在期限内需下次启动检查。只读确认参数存在于板端，并核对公开版本实现；未证明板端二进制所有代码与公开源码完全一致。

驱动为内建CONFIG_DRM_ZYNQMP_DPSUB=y，参数权限0444，应通过[内核命令行](https://raw.githubusercontent.com/Xilinx/linux-xlnx/xlnx_rebase_v5.15_LTS_2022.2/Documentation/admin-guide/kernel-parameters.rst)设置。已导出的实际boot.scr支持从SD读取uEnv.txt并env import，随后启动内核；[U-Boot相应源码](https://raw.githubusercontent.com/Xilinx/u-boot-xlnx/xlnx_rebase_v2022.01_2022.2/common/fdt_support.c)以bootargs环境变量设置chosen/bootargs。是否实际导入仍须下一次启动读取cmdline及参数确认。

## 本轮实测与改动

预检boot为fc221b0d-b9f4-40a2-b509-6c53478a89d0，已不同于上一轮物理插拔恢复的8817dc71…；本轮未发起这次重启，不把上一boot的现场恢复回执作为本boot验收。预检EDID128、三服务active/零重启，原启动器/Xorg/配置SHA保持。

- 新增启动配置：`/boot/uEnv.txt`，SHA256为05cd73695dc8797899ee32a02ba5081403f02d5b28b8b89b3b71ffe503279ffe。
- 备份与回退：`/boot/aura-hdmi-delay5-20261021/`，记录原uEnv不存在、原bootargs、boot.scr/system.dtb原件及配置SHA；提供rollback.py。
- 原boot.scr、system.dtb、Xorg、业务启动器与配置保持，未改分辨率、色深、运动控制或语音模型。
- 安装器经独立UART传输，所有分片及执行退出0、响应校验通过、串口回显恢复；安装前后三服务PID1049/988/1048保持，零重启。
- 本机核验原bootargs完整保留，并在临时目录验证回退拒绝覆盖后来修改的配置、保留停用文件、重复停用无副作用。不是冷启动测试。

## 冷启动验收

1. 正常关机后再断开并接通板卡电源，HDMI全程插着；记录屏幕取电方式，保持其供电条件与故障复现时一致。
2. 等待系统与界面完成启动，观察是否仍整屏黑闪。不要看到早期暂时黑屏就拔插HDMI，否则会混入物理恢复变量。
3. 串口只读确认 `/proc/cmdline` 包含 `zynqmp_dpsub.power_on_delay_ms=5000`，且 `/sys/module/zynqmp_dpsub/parameters/power_on_delay_ms` 返回5000；同时记录新boot、EDID、显示模式、服务状态和实际画面。
4. 参数生效与实屏消除黑闪分别验收。若仍黑闪，先保留故障态证据，再使用已验证的物理HDMI重插恢复，不能把重插后的正常画面计为延时成功。单次成功也不能代替多次冷启动可靠性验证。

## 回退

在板卡Linux运行 `python3 /boot/aura-hdmi-delay5-20261021/rollback.py`。脚本只在uEnv仍为本轮精确内容时将其移至备份目录 `uEnv.disabled`，保留文件，下一次启动恢复原参数。当前运行内核值不会立刻改变。若uEnv已被他人修改，脚本拒绝处理，避免丢失后续设置。若系统无法进入Linux，可断电后在电脑挂载SD启动分区，将本轮uEnv.txt移出启动分区根目录；不要替换boot.scr或system.dtb。

共享src保存安装器、准确uEnv内容和回退工具，evidence保留过滤后的预检、安装、回读与离线检查。Windows同步尚未确认。最终状态为“已安装待下次启动生效”，不是“黑闪根治”。
