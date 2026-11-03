# 软件显示重初始化无效：官方建议核查与后续分支

用户在一次实际OFF→2.002秒→ON完成后明确反馈“仍然黑闪”。因此上一轮的软件执行通过不能解释为物理修复；本轮记录为**实屏未修复**。未再次执行显示关开或部署启动配置。

## 当前实测

UTC2026-10-21 12:00～12:01，同boot8817dc71…，EDID仍0。没有/dev/drm_dp_aux*，内核CONFIG_DRM_DP_AUX_CHARDEV未启用；DP AUX以I2C适配器名出现，不等于可以用普通i2cset访问原生DPCD/分配器HPD寄存器。本轮未扫描I2C总线、写寄存器或改U-Boot。

当前驱动内建CONFIG_DRM_ZYNQMP_DPSUB=y，power_on_delay_ms=4、aux_timeout_ms=50，参数权限0444；没有动态调试支持。实际启动5.15.36-xilinx-v2022.2，Xorg色深16、当前扫描RG16与原49MHz1024×600保持。

**新增能力：** /sys/kernel/debug/dri/0/DP-1/edid_override和force存在，权限0644。CONFIG_DRM_LOAD_EDID_FIRMWARE未启用仅限制固件参数路径，不代表所有EDID覆盖途径不可用。debugfs临时覆盖是可评估的候选，不是已执行修复，也不生成真实HDMI热插拔。不可将注入EDID后的128字节声称为物理读取恢复。

本轮筛选日志无新增USB断连/过流、AUX错误/超时或链路训练错误条目；没有日志不能证明电气信号正常。INA260原始数据仅保留在证据，尚未核对测量电源域，不能拿它替代屏幕端电压或纹波测量。

## 对用户提供建议的核查

1. PS DP经STDP4320至HDMI/DP的架构以及KV260通过分配器取得EDID，有[AMD架构文档](https://xilinx.github.io/kria-apps-docs/kv260/2021.1/build/html/docs/aibox-reid/docs/introduction_aib.html)及[AMD BIST说明](https://xilinx.github.io/kria-apps-docs/kd240/bist/1_2/build/html/docs/modules/display.html)支持。但这不等于已确定本次具体芯片/时序根因。
2. [2022.2对应DP驱动](https://raw.githubusercontent.com/Xilinx/linux-xlnx/xlnx_rebase_v5.15_LTS_2022.2/drivers/gpu/drm/xlnx/zynqmp_dp.c)encoder enable包含唤醒与条件训练，HPD EVENT通知重新检测，HPD IRQ根据链路状态决定训练。不能断言每次HDMI拔插必定重置完整通路。本源码为公开版本参考，未与实际内核二进制全部补丁逐字映射。
3. [AMD驱动说明](https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/18842105/ZynqMP%2BDisplayPort%2BLinux%2Bdriver)有DefaultDepth16示例，现场已满足；不能概括为所有24/32bpp必然异常。
4. 未找到足以证明本板“U-Boot固定1080p最有效”的证据。当前屏幕已验证1024×600/49MHz，没有本屏1080p60支持证据，不按通用示例改分辨率或持久启动环境。
5. 原生DP AUX、I2C-over-AUX和物理HPD不是同一操作接口。缺少具体分配器寄存器、接线及恢复验证时，不能实施盲写。实际可用的临时EDID覆盖由[DRM debugfs实现](https://raw.githubusercontent.com/Xilinx/linux-xlnx/xlnx_rebase_v5.15_LTS_2022.2/drivers/gpu/drm/drm_debugfs.c)提供；当前仅确认能力，未写入。

## 下一步与阻塞信息

已请求保持电源不变，仅拔插HDMI一次并观察10秒，同时询问屏幕取电于KV260 USB、独立适配器还是电脑。尚未收到本次物理对照结果，不能将历史“拔插有效”当作这次已完成。

- 若物理插拔恢复：对齐本boot的EDID、热插拔及实际画面，优先评估启动/分配器/屏幕同步路径；再决定固定启动时序、受支持的驱动恢复或显示参数兜底。
- 若物理插拔仍黑闪：核对屏幕取电与具体型号，逐项对照已知正常线缆、独立供电或显示器；不得同时改变多个条件而失去判别依据。
- 临时EDID覆盖可帮助区分参数检测与下游同步问题，但需明确记录注入来源、回退和实屏结果，不能把它自动当作永久解决方案。

## 本轮改动与验证

新增本机只读接口检查脚本；两次串口只读返回均退出0/SHA验证通过/回显恢复。共享新增报告、过滤证据，更新项目日志与Ubuntu回执/入口。板端文件/配置修改0、显示控制0、运动命令0，未重启服务。上一轮隔离恢复脚本保留；Windows回执未代填、同步未确认。

