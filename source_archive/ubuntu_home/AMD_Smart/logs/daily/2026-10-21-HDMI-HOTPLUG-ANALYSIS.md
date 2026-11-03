# HDMI 实体热插拔差异分析与显示驱动对照

UTC 2026-10-21 14:25～14:51。用户要求重点检查实体 HDMI 拔插前后，参考其 DP splitter / 初始化等待建议分析原因。屏幕 USB 仍由 KV260 供电，接线未改；独立供电对照没有发生。

单次显示驱动对照已执行：在 boot 975f931a…、受保护配置 SHA 与目标核验后，停止原 GUI/Xserver，仅解除 fd4a0000.display，实测移除 5.007 秒再绑定；DPU renderD128 属 zocl-drm，未解除绑定，相机 PID1014 保持。工作器超过自身 65 秒显示就绪预算，独立恢复接管。随后确认驱动绑定、三服务 active/零重启、GUI19803/Xserver19802、audio-frontend 入口保持；EDID 仍0，用户“仍然存在”。没有改生产配置、内核或发起重启；不把就绪超时写成一次无错误成功。

整理历史强对照：同 boot 8817dc71…，软件 OFF/ON 等待2.002秒后仍黑闪/EDID0，实体 HDMI 重插后用户确认正常、EDID128/SHA727d3e18…，49MHz原生模式、16位缓冲、配置SHA与三服务PID保持。热插拔精确事件时刻未记录。另一 boot bec99c5a…已有EDID128仍闪，故不能用EDID恢复代替实屏验收。AMD BIST说明KV260从DP splitter读EDID，驱动源码把HPD事件和条件重训练分开处理；实体HDMI边沿不保证完整上游重训练，当前无实读DPCD lane状态。

新采集前发现另一个因素：Xrandr仍列1024×600/GUI推进，但600秒DPMS休眠导致输出disabled/Off、CRTC0/0、dp_video_ref关闭。仅单次运行时xset dpms force on，后检enabled/On、CRTC1/1、RGB565原生扫描与实际48999993Hz恢复，EDID仍0、PID保持，无永久休眠设置修改。原启动黑闪已有On/active证据，不能归咎于休眠。

基于有效On/active基线启动240秒只读事件观察，2347次采样、最大间隔0.409秒，无缓存变化、无实际DRM内核事件；输出、模式、时钟、四份SHA及三PID保持，服务正常结束。已请求一次仅HDMI实体拔插及前后实屏回执，截至记录时未收到；不能把本轮没有事件写成热插拔失败。首个Off基线观察无效，保留记录；新版修正扫描/时钟过滤，监视器横幅不计事件。

原因优先级为下游分配器/屏幕握手及锁定状态，其次上游AUX/事件协同；屏幕USB启动供电影响未排除。现有5000ms位于D0唤醒后至训练前，不等效延后全部HDMI通信。首次AUX延时候选已撤下，首次原生模式修复保留。下一步先取得实体动作/画面回执与事件差异，再核验可用下游控制接口做单次等效性测试；不继续盲加延时、不写未知splitter寄存器。

[完整分析、源码、过滤证据与验证](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_hdmi_hotplug_analysis/README.md)。本次无永久配置变更、运动或CPU优化；原始UART/图像不共享，Windows同步及冷启动整屏修复未确认。

### 载板 FRU 身份只读解析（UTC 2026-10-22 02:50）

按后续核查计划读取已注册 `1-0051` / `at24` EEPROM 的 Xilinx FRU 非敏感字段。结果为制造商 `XILINX`、产品 `SCK-KV-G`、料号 `5066-01`、revision `2`；公共头和板卡区校验和通过，尾部格式结构解析未完全通过，故保留此边界。未输出序列号/MAC；未扫描总线、写 EEPROM、访问 splitter 寄存器或操作 GPIO。源码 `board_carrier_fru_readonly.py` 和过滤响应已进入热插拔分析交付；载板版本信息仍不能证明 STDP4320 固件、I²C ACK 或控制寄存器状态。参考 AMD UG1089 有 KV260 Rev1.0/Rev2.0 两种载板，下一步应按板号核对官方 Rev2 原理图及已支持的软件固件路径。当前未收到用户新一轮实体 HDMI 重插/屏幕结果，不把它推定为成功或失败。

### STDP4320 控制路径补查（UTC 2026-10-22 03:00）

以本机的 Xilinx ML Starter Kit Carrier Card REV B03 资料作拓扑参考（未证明该 PDF 与当前 FRU revision 精确对应），找到了 STDP4320 host I²C 标签 `0x73`、GPIO5/6/7 HDMI OE/DDC/PWR 控制线及外接 SST25VF020B Flash。器件资料说明其 host I²C OCM 地址以 E0/E2/E4/E6 的 8 位形式表示，E6 对应 7 位 `0x73`；固件可通过 UART/I²C/DP AUX/HDMI DDC 做 ISP，但需厂商 GProbe 和程序，公开 datasheet 不含足够完整的 HDMI GPIO host register map。官方 Linux revB carrier overlay（rev2/rev1 compatible）仍将 splitter 留作注释，SOM DTS 说明旧固件多地址冲突，修复后应仅响应0x73。

分析结论（推断）：物理插拔可能在 STDP4320 内部重建下游 HPD/DDC/HDMI 电源/输出路径，解释画面恢复而上游模式/时钟不变；EDID128仍闪的反例说明它不是单一 EDID 问题。当前无芯片固件身份、ACK、HPD波形或内部状态证据。没探测0x73、没读写寄存器、没读/写SPI Flash，没写GPIO。只有取得匹配版本的寄存器身份读取/厂商GProbe资料后，才可规划单次软件等效热插拔。[新增路径证据与边界](</home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_hdmi_hotplug_analysis/README.md>)。

### GProbe 身份查询预检（UTC 2026-10-22）

首次 sysfs 预检断言失败由脚本未解析 tty 符号链接造成；修正后只读枚举确认 ttyUSB3=FTDI If 3。随后发送唯一一帧只读 `GetInformation index 0`（4字节），1秒内收到0字节回复。没有重试、寄存器/GPIO/I²C/Flash操作。无 UART 回复不证明芯片不存在、损坏或在其他接口无响应，也没有读到固件身份。证据 `evidence/gprobe-getinfo-preflight.json`。需要适配载板/固件的厂商工具与 UART 协议/接线说明，才继续身份核验；本轮已停止硬件探测。

官方数据手册将 STDP4320 UART 描述为可选工厂调试端口；RD1 诊断流程要求 Kinetic GProbe 硬件/软件，并在复位芯片后观察固件版本横幅。故公开实现单帧无回复是非结论性结果，无法区分板级 UART 映射/电平、固件状态、协议实现或芯片问题。当前不复位板卡；需先取得针对 KV260 载板/固件的厂商流程，并安排可接受显示中断的维护验证。

### 更正UART映射并取得有效回复（UTC 2026-10-22 03:24）

上一节把STDP UART定位到FTDI D/接口03是错误的，原理图文本在空间相邻位置显示网名，不能代替导线追踪。逐线查看B03原理图第9页确认 CDBUS0/1 经U65到STDP UART，实际为接口02/ttyUSB2；DDBUS0未连接、DDBUS1为EEPROM写保护控制。sysfs已核对02与FT4232 0403:6011，未见端口占用。旧接口03无回复记录标记wrong-interface/superseded，不作器件状态证据。

本轮接口02的一条GetInformation index0收到15字节0x40有效回复；有界GetDeviceId index0..7分别返回PEGBB/ST/IROM/9f/9f9f/2/0/00。共9帧请求36字节、9帧回复60字节，按私有原始响应复核命令号、长度、校验和及payload SHA，均通过。未重试、未复位、未发DebugOn/RunCode、未读写RAM/MMIO/Flash/I²C/GPIO。只保留UART身份查询动作，未安装启动配置；脚本用独占记录避免重复执行。应用固件版本与这些索引语义仍未知，不把IROM解读为启动异常。

实测证明UART可在不复位、不先获取厂商工具的条件下回应。RD1复位后观察版本横幅并非所有GProbe查询的前提，上一节等待工具/复位的阻塞判断已被本轮证据替代。仍需适配器件/固件的HDMI状态/控制定义，不能把通用RAM/Reset命令视作HDMI恢复接口。

最新只读状态是新boot215c4292…（非本轮发起）：Xorg16.191秒首次1024×600/fbdev=N，uEnv/Xorg仍d120b2f7…/64457c25…。前一检查On/CRTC active/RG16/48,999,993Hz，87秒后末次为DPMS Off/CRTC inactive；三服务PID1078/1017/1077保持，NRestarts0。板端墙钟2021年不可信，采用主机取证目录时间与uptime。尚无本boot实屏回执，不能把Off归因于UART查询，亦不能当作条纹修复。已询问HDMI/12V不动时的独立屏幕电源对照，现场尚未回执；该操作同时重置屏幕，单次恢复不能证明供电质量。完整报告及新过滤证据见热插拔分析交付。
