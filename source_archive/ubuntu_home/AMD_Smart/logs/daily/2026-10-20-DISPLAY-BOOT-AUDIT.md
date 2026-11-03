# 每次开机花屏：当前boot只读核查

用户要求检查“屏幕每次开机都花屏”的原因。本轮任务转为显示诊断，不继续推进转轴发布或恢复CPU优化。读取ZIP入口、AGENTS、旧HDMI设置/冷启动报告、共享入口与双方回执。Windows回执仍是模板，不代填。

主机UTC2026-10-20T23:58起取证，已是新boot567106f3-6d07-4476-b44a-11a6576ff14a，首次取证uptime145.63。实际入口另为aura-render24-budget-20261020/e06409743174/startup，监督1072/GTK1464，不使用旧WorkingDirectory判断运行版本。

配置保留startup_display_retrain=true、off2秒；本boot setup记录startup_output_retrained=true、edid_missing=true、mode_source=previously_verified_timing、wait22.276秒。DP-1 connected/enabled，但EDID早期0字节，早期复读仍0。Xorg17.335秒明确using initial mode1024×768，正确1024×600由启动器按保存的49MHz时序补入；早期Xrandr/DRM均1024×600/59.85Hz、linkGood/CRTC active，不能把这些回读当物理屏通过。后续源码审查发现重置标记可误报，见下文，不能称该标记证明完整2秒关闭已经执行。

X根窗口为16位RGB565，DRM RG16/pitch2048/1024×600，格式匹配。通过SHA固定的既有X11 capture工具私下抓屏并查看：布局/文字/人物清楚，未见软件帧内整屏花屏；图片只留私有UART证据，不进入共享包。若实体此时仍花，更应检查扫描输出/HDMI链路/屏幕同步，不能仅由截图排除物理异常。用户随后进一步确认每次上电异常、物理拔插HDMI后恢复；已据此收敛冷启动与真实热插拔路径差异，当次准确插拔时间及目前物理状态仍待回执。

启动约4秒出现dpdma_ref_div1设分频和dpll_int禁用ret=-13，与历史正常显示时既有告警相同；没有据此宣称直接根因。当前/etc/X11/xorg.conf只有DefaultDepth16，无Monitor/ModeLine/Modes固定时序。/proc/config.gz明确CONFIG_DRM_LOAD_EDID_FIRMWARE未启用，相关edid_firmware sysfs参数不存在，不能建议只加内核EDID参数就生效。Linux官方EDID文档/AMD官方DP驱动说明仅作为一般机制依据，外部根因未最终确诊。

新boot固件为官方kv260-benchmark-b4096.bit.bin，旧临时保护256477已经退出，记录属于旧boot，不能继续称锁还在。当前手动接口FAULT/Boot mismatch、配置仍绑定3e1add36…，阻止打开运动硬件。本轮不重连、不启运动、不重写中心或加载联合固件。

结果与建议详见[共享诊断报告](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-20_display_boot_audit/README.md)。七轮取证命令均无modeset/输出开关/服务或板卡重启/开机配置修改/运动控制；截图仅生成后清理临时文件。读到的启动器原件、过滤JSON、截图元数据和源码/返回SHA保存，无相机/人物图片或原始UART。未改旧冻结工件，更新共享入口/Ubuntu回执/资料导航；Windows同步与物理修复仍未验收。

## 进一步确认：热插拔路径与误报

同boot后续EDID恢复128字节，SHA727d3e18…与已验证屏幕一致；校验和及首选1024×600/49MHz/59.85186Hz独立解码通过。Xorg约481.637秒开始记录ADA/product4和DDC时序；助手期间只读，没有发重置。与用户拔插恢复现象一致，准确外部触发动作尚未对齐，未冒称已受控复现物理插拔。后续CRTC inactive由xset q确认600秒DPMS熄屏/Monitor Off解释，不混作开机花屏。

AMD官方KV260架构明确STDP4320 DP/HDMI分配器；BIST官方说明EDID可能由分配器提供、外部断线仍可读，所以connected/EDID/linkGood均不能单独验收下游HDMI。Xilinx2022.2对应公开DP驱动含HPD通知/异常链路训练路径，普通DPMS启停与物理下游拔插不保证状态变化等效。本机无drm_dp_aux字符设备，未盲写I2C/GPIO或尝试分配器固件命令。

对实际启动器cd168022…离线注入OFF命令失败，恢复/回读模拟成功后仍返回startup_output_retrained=true/marker software_modeset_verified=true。一项专项复现通过，所有显示命令mock；原代码OFF前先设retrained、后续重试绕过OFF能成功返回。已向用户更正早先“完整重置已执行”的过强判断；离线证明机制，不代表本次实际OFF失败。未修改现网启动器，建议先纠正各阶段状态、前移正确时序与就绪检查，再按真实HPD/分配器证据设计恢复。

最终交付完整性通过：17内容文件、14个本地报告链接、七轮UART源/返回SHA、当前启动器SHA与复现输入一致；原九份交付共219个冻结内容文件长度/SHA保持。共享包不含真实截图或原始UART。共享入口、Ubuntu回执和资料导航已更新为当前boot事实，未把旧临时锁继续标作存活，Windows同步和实物修复仍未确认。
