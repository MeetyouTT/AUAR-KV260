# KV260：实体 HDMI 热插拔与软件重初始化的差别

更新至 UTC 2026-10-22 03:24：已纠正 FTDI 接口映射，STDP UART 是 C 通道/接口02，经9条身份查询取得9个有效校验响应；先前接口03无回复记录不作为芯片状态证据。无需复位或厂商工具也能完成这组身份查询。黑闪仍未修复，应用固件版本和 HDMI 状态/控制寄存器定义仍未知。

原因仍优先排查分配器与屏幕之间的启动握手及恢复状态。实体 HDMI 重插曾恢复画面，源端关开、延时和显示驱动重新加载均未获得同等实屏效果。当前新boot中首次1024×600修复保持；末次检查输出已DPMS Off，实屏对照前需先唤醒。

用户本轮要求：“你重点检查下热插拔hdmi后的区别后，参考我的建议，分析原因”。本次保留已验证的首次 1024×600 配置，围绕同启动前后差别取证。

## 已测差别

| 项目 | 故障 / 操作前 | 实体 HDMI 重插后 | 能得出的结论 |
|---|---|---|---|
| 早先同 boot 8817dc71… 的实体画面 | 用户确认整个屏幕黑闪 | 用户确认“画面已经正常” | 这一次实体重插有效；非永久冷启动验收 |
| 同次 EDID | 反复 0 字节 | 128 字节，SHA 727d3e18…，8 秒后检保持 | 识别状态改变；不能单凭 EDID 判定实屏 |
| 当前显示模式 | 1024×600，49 MHz，约 59.85 Hz | 保持本屏同一时序 | 恢复不需要更换为 1080p |
| Xorg / 扫描缓冲色深 | 16 位 / RGB565 | 同模式、原配置保持 | 不是“改到 16 位”带来的恢复 |
| 同 boot 的 GUI / 相机 / Xserver | PID 1057 / 988 / 1048 | 相同，配置 SHA 保持 | 当次恢复未伴随应用重启或配置替换 |
| 软件 OFF → 等待 → ON | 实测输出关开，等待 2.002 秒 | EDID 仍 0，用户仍黑闪 | 软件输出关开不等同实体重插 |
| 显示驱动解除绑定 → 等待 → 重新绑定 | fd4a0000.display 实际移除，等待 5.007 秒 | 驱动恢复、三服务恢复，EDID 仍 0；用户“仍然存在” | 更完整的源端重初始化也未证有效 |

历史热插拔精确时刻没有记录，以上不是逐毫秒同步的受控抓包。原始证据引用见 `evidence/historical-comparison.json` 和相邻已冻结交付目录。

还存在关键反证：boot bec99c5a… 中已经读到相同的 128 字节 EDID、原生时序和实际 48,999,993 Hz 时钟，用户仍反馈条纹后缓慢闪屏。因此 EDID 缺失既不是所有闪屏的必要条件，也不能把 EDID 恢复作为唯一修复标准。

## 对用户建议的核对

DP 分配器这一方向有依据。[AMD BIST 官方说明](https://xilinx.github.io/kria-apps-docs/kd240/bist/1_2/build/html/docs/modules/display.html)明确区分 KV260 从载板 DP splitter 读取 EDID 与直接从显示器读取的情况，且指出拔掉下游线后 EDID 也可能仍存在。这解释了为何 DP-1 仍可能显示 connected，不能用它证明 HDMI 屏端已经锁定。

需要修正的是“重插 HDMI 必然完整重训上游 DP”。实体动作改变下游 HDMI 的连接与握手条件，但是否传递成上游 HPD 事件、HPD IRQ 或触发 DP 重训练，还取决于分配器和驱动的实际处理。[本版本官方驱动源码](https://raw.githubusercontent.com/Xilinx/linux-xlnx/xlnx_rebase_v5.15_LTS_2022.2/drivers/gpu/drm/xlnx/zynqmp_dp.c)分别处理 HPD_EVENT 与 HPD_IRQ；后者在读取链路状态后按条件重训。当前没有实际 DPCD lane 状态读数，不能声称已经证实通道数、电压摆幅或训练参数错误。DRM 属性 link-status=Good 也不足以代替这些读数。

“延迟 5 秒”的思路针对开机时序有合理性，但此前实施位置不等价于延迟全部 HDMI 通信。实际参数 `zynqmp_dpsub.power_on_delay_ms=5000` 位于 encoder enable 内：尝试写 DP D0 后等待、再训练；EDID 的 `get_modes` 走另一个 AUX/DDC 读取路径。该参数确实生效但实屏失败。另一个首次 AUX 注册前延时候选也未通过断电启动，已经退出活动启动路径，不能继续宣称有效。

固定首次模式这一项已经单独落实并验证：关闭早期 fbdev，Xorg 首次即 1024×600，两个 boot 已有证据；用户确认闪烁形式改变，但条纹仍在。当前已经是 16 位缓冲，不再把重复设 16 位或强制 1080p 当作新的修复实验。也没有证据支持“KV260 官方通用推荐 16bpp”这一笼统断言。

## 当前原因排序与边界

1. **优先：分配器到屏幕的启动识别、HDMI 输出或屏端锁定状态没有正确建立。** 同 boot 实体重插恢复、源端重初始化未恢复，与这一方向相符；它仍是推断，不能指定某个器件已损坏。
2. **仍需区分：上游 AUX / DP 事件及其与下游恢复的协同。** 源端重置失败不等于排除了所有驱动问题；物理重插可能触发软件操作没有触发的事件。
3. **仍未排除：屏幕通过 KV260 USB 供电时的上电过程。** 用户确认接线没变，独立供电对照未做。此前逻辑 USB 电源位未保持计划 5 秒，也没有屏端 VBUS 波形，不能据此排除供电或声称已完成 5 秒物理断电。

## 本轮额外发现：休眠须与启动条纹分开

在准备新热插拔抓取时，发现 Xrandr 仍列着 1024×600，GUI 帧仍推进，但 `xset q` 为 Monitor Off，DRM disabled/DPMS Off、CRTC enable=0/active=0，视频时钟关闭。系统空闲休眠阈值为 600 秒。

已单次执行运行时 `DISPLAY=:0 xset dpms force on`，无永久配置修改。独立前后读取确认：输出恢复 enabled/On、CRTC 1/1、RGB565 1024×600，视频时钟恢复 48,999,993 Hz；EDID 仍 0，三个服务 PID 保持。实体唤醒效果待用户回执，不能当作条纹修复。[Xorg 官方手册](https://www.x.org/releases/X11R7.5/doc/man/man1/xset.1.html)说明该命令只强制切换 DPMS 状态。

早先故障记录在 DPMS On、CRTC active 时就有黑闪，因此这个休眠现象只能解释部分后续无扫描输出，不能倒推为原启动条纹根因。

## 新一轮热插拔取证与下一步

已在输出 On / CRTC active / EDID 0 的新基线下启动一次限时被动采集：记录 DRM uevent、缓存 EDID、connector 状态、模式、时钟、配置 SHA 与服务 PID。观察阶段不发 modeset、DPMS 或驱动控制；结束后的 Xrandr 查询与被动采样分开记录。首个基线为 Off 的旧观察不作为有效热插拔对照；新版修正了旧观察器的扫描状态和时钟行过滤问题。

已请用户只重插一次 HDMI、保持板卡 12V 和屏幕 USB 不动，并分别反馈唤醒和 HDMI 重插结果。新一轮实体动作是否发生、实屏结果及事件结论，以本目录 `evidence/current-observation.json` 和 `evidence/field-status.json` 为准；在回执之前不自动认定用户执行。

本轮限时采集已结束，2347 次缓存采样、最大间隔 0.409 秒，EDID 始终 0，输出 On / active、时序、实际时钟、四份配置 SHA 与三个服务 PID 保持；无实际 DRM 内核事件（监视器说明文字不计事件）。观察服务已正常退出。尚未收到用户的实体动作和屏幕回执，所以这只能证明观察期软件状态没有变化，不能认定“物理重插无效”或“没有发生过 HDMI 电气边沿”。

下一项修复须针对实际有差别的阶段：如果确认实体 HDMI 重插再次有效，核实可控的下游 HDMI enable/HPD 或屏端重启机制及对应官方接口，再做单次软件等效性验证；只有它能恢复实屏，才接入“就绪等待 → 下游初始化 → 输出原生模式”的开机流程。目前没有核验出可用的 splitter 寄存器控制接口，不写未知 I2C/GPIO，也不把再次 sleep 当作已经等效重插。若没有恢复，则保留故障并做独立屏幕供电 / 已知正常显示器的单项对照，避免同时改时序与电源。

## splitter 控制入口的只读核查

继续检查板端资料后确认，当前运行设备树报告型号 `ZynqMP SMK-K26 Rev1/B/A`，载板 compatible 为 `rev1` 与 `revB`。运行中 `i2c-1` 是 MIO I²C 总线，注册设备只有 USB hub、两个 PMIC、INA260 和两颗 EEPROM；设备树没有 STDP4320 从设备节点，没有对应的 GPIO line，也没有已加载的 STDP4320 DRM/bridge 驱动。只读枚举没有扫描 I²C 地址、访问 splitter 寄存器或写 GPIO。

板卡设计参考将 HDMI 输出使能 `STDP4320_GPIO5_HDMI_OE_B`、DDC 使能 `GPIO6_HDMI_DDC_EN`、HDMI 电源 `GPIO7_HDMI_PWR_ON` 接在 STDP4320 GPIO 上，说明你提出的“恢复 HDMI 通信”方向有具体硬件落点。但这些不是 PS `/dev/gpiochip*` 上现成可拨动的三根 GPIO；要变更它们需要 splitter 接受并执行配置。

现用 Xilinx 5.15 设备树源把 STDP4320 节点注释掉，并记载当前旧固件会对 0x5C/0x5D/0x70/0x72/0x76 多个地址响应，与 0x70 的器件冲突，设备不可访问；该注释期待的新固件只响应 0x73。当前板端 I²C 客户端表中也没有 0x73 项。这足以解释为什么不能直接加一个盲写寄存器脚本；但设备树没有实例化客户端并不能证明芯片在电气上一定没有 ACK。

### 载板 EEPROM 身份补充（UTC 2026-10-22 02:50）

通过已注册的 `at24` EEPROM 驱动只读解析板卡 FRU，读到制造商 `XILINX`、产品 `SCK-KV-G`、料号 `5066-01`、revision `2`。公共头与板卡区校验和通过；解析器在尾部记录格式上未完全通过结构校验，因此这里只把产品/revision作为 EEPROM 字段读数，不扩展为“STDP 固件版本已确认”。本次没有输出序列号/MAC，没有扫描 I²C、写 EEPROM 或触碰 splitter。过滤结果在 `evidence/carrier-fru-readonly.json`，解析源码在 `src/board_carrier_fru_readonly.py`。

这个板卡身份把硬件缩小到 `SCK-KV-G Rev2`；AMD 官方指南确认 KV260 载板确有 Rev1.0 与 Rev2.0 两版，但仍需按官方各版原理图核对 STDP4320 固件/host I²C 接法。设备树型号 `Rev1/B/A` 属 SOM 型号信息，不能覆盖载板 EEPROM 读数。即使载板是 Rev2，当前运行内核没有 splitter I²C 节点/driver/client，且尚无 splitter 寄存器读回证据，所以软件等效 HDMI enable/DDC/power-cycle 仍不可安全执行。

### Rev2 控制路径继续追查（UTC 2026-10-22）

本机保存的 `ML Starter Kit Carrier Card` 原理图参考（REV B03；与本次 FRU 的精确 revision 对应关系未证实）补出了关键硬件路径：STDP4320 host I²C 标为 7-bit `0x73`，其 GPIO5/6/7 分别连接 HDMI 输出使能、DDC 使能和 HDMI 电源控制，GPIO8 是 HDMI 电源故障输入；STDP4320 的 SPI 口还连到外部 `SST25VF020B` Flash。此处只采用网名/拓扑作为设计参考，不能把它当作用户这块 Rev2 实板的电气测量。

芯片数据手册解释了这条路径：STDP4320 内有 OCM 和 host I²C slave 寄存器，OCM 负责将上游 DP AUX 的 I²C-over-AUX 请求路由到 HDMI DDC；GPIO 可监测 cable detect 并控制电源/外部逻辑；配置固件保存在外部 SPI Flash。资料列出的 OCM I²C 地址 ID 是 `E0/E2/E4/E6`（8-bit 形式，对应 7-bit `0x70/0x71/0x72/0x73`）；这与本机原理图标签 `0x73` 以及 Xilinx 设备树“修复后只应响应 `0x73`”一致。[STDP4320 数据手册](https://www.mouser.com/datasheet/2/936/STDP4320_03c-3105399.pdf)、[Xilinx SOM DTS](https://github.com/Xilinx/linux-xlnx/blob/master/arch/arm64/boot/dts/xilinx/zynqmp-sm-k26-revA.dts)。该对应关系解释了地址写法差异，不证明现场芯片目前有 ACK。

更重要的是，Xilinx 当前公开的 [revB carrier overlay](https://github.com/Xilinx/linux-xlnx/blob/master/arch/arm64/boot/dts/xilinx/zynqmp-sck-kv-g-revB.dtso)（compatible 同时列出 rev2/rev1）仍只把 STDP4320 留作注释，没有 I²C 子节点；SOM DTS 仍记录旧固件会对 `0x5C/0x5D/0x70/0x72/0x76` 多地址响应、与 `0x70` 器件冲突，并期待修复固件只响应 `0x73`。所以 FRU `revision=2` 与“应有修正固件”相符，但本次没有实际读到 splitter 固件身份或寄存器状态，不能据此直接操作 `0x73`。

芯片资料进一步写明，SPI Flash ISP 可经 UART、I²C、DP AUX 或 HDMI DDC 传输，但需要外部 `GProbe` 工具和厂商程序；公开数据手册没有给出足以安全拨动这些 HDMI GPIO 的完整 host 寄存器映射。由此，下一步应先取得匹配此板卡/固件版本的寄存器手册、只读身份查询方法或厂商认可的 GProbe 包。固件升级和寄存器写入均未执行；没有依据先读写未知寄存器，也不能尝试烧录通用 STDP 镜像。

这让热插拔差异的解释更聚焦：**推断**实体 HDMI 重插主要改变 splitter 看到的下游 HPD/DDC/接收端状态，可能使其重新打开 DDC/HDMI 供电/输出路径；上游 DP 的 1024×600 模式、时钟和应用进程无需变化。历史同 boot 热插拔后 EDID 从 0 变为 128 且画面恢复，与这一解释一致；另一次 EDID 已为 128 仍有条纹，说明 EDID 只代表识别路径有变化，不代表视频链路已稳定。当前没有 HPD/供电引脚波形或 STDP 内部状态读数，故这仍是最有依据的假设，不是已证实的根因。

新增过滤对照在 `evidence/splitter-path-analysis.json`。不确定点集中到两个可验证事项：这块 Rev2 板上 splitter 固件是否确实只响应 `0x73`；以及厂商工具/寄存器资料是否允许不重刷固件地做一次 GPIO 控制。获得这两项依据后，才适合设计“只读身份确认 → HDMI 输出/DDC/电源单次循环 → EDID/HPD/显示状态和实屏反馈”试验。

修复路径为核对适用此载板的 STDP 固件/寄存器定义，再设计有正式依据的 HDMI 恢复事务，并同步采集 HPD/EDID/时序及实屏反馈。UART身份路径已在本轮确认可用，所以即使 host I²C 没有 Linux client，也不能把它当作必须先刷固件的理由；当前没有寄存器写入，也没有依据升级固件。

显示驱动重探测阶段的工作器曾超过自身 65 秒就绪预算，独立恢复流程接管；随后只读复核三服务均 active、相机进程保持、驱动绑定正常。报告明确保留超时与恢复事实，不把它写成无故障完成。当前没有待执行重启或周期显示重置；首次原生模式配置、原内核和最新 audio-frontend 业务入口保留。

源码及过滤 JSON 在本目录；不共享原始串口、屏幕截图或人像。`verification.json` 区分证据一致性与未完成的实体验收。本机记录更新不等于 Windows 已同步确认。

### UART 接口更正与有效身份回复（UTC 2026-10-22 03:24）

此前将设计图的空间邻接误读为导线连接：B03第9页实际是 `CDBUS0/1 → U65 SN74AVC2T245 → STDP4320_UART_RX/TX`，对应 FTDI 接口02/ttyUSB2。DDBUS0未连接，DDBUS1接EEPROM写保护控制，接口03不是STDP UART。sysfs 的 ttyUSB3=If3 枚举本身正确，但不证明它连到STDP。旧无回复记录 `evidence/gprobe-getinfo-preflight.json` 已标记为 wrong-interface/superseded，不能作为器件无响应的依据。

对接口02发出1条 `GetInformation index0`，收到15字节0x40应答，12字节载荷；再按[公开 GProbe 实现](https://github.com/radareorg/radare2/blob/master/libr/io/p/io_gprobe.c)读取有界的 `GetDeviceId index0..7`。9条请求共36字节、收到60字节，全部命令号/帧长度/加法校验和通过，未重试。字符串依次为 `PEGBB / ST / IROM / 9f / 9f9f / 2 / 0 / 00`；未找到这些索引的完整字段定义，因此不把它们解释成应用固件版本或认定正在异常ROM启动。此身份查询不读取任意RAM/MMIO、不发送DebugOn/Reset/RunCode、不访问Flash或I²C/GPIO。原始响应仅本机私有保留；过滤结果 `evidence/gprobe-uart-c-readonly.json`，源码 `src/board_stdp_gprobe_getinfo_once.py`，每个允许的命令/索引有独占执行记录，重复执行会在打开串口前拒绝。

这项实测推翻了“必须先有厂商工具/复位才能验证UART通信”的旧前提。RD1参考手册复位是其观察版本横幅的诊断流程，不是所有GProbe查询的必要条件。当前真正缺少的是适配此器件/固件的 HDMI HPD/DDC/OE/电源状态与控制定义；公开实现的通用RAM、复位、Flash命令不能直接当作HDMI恢复API使用。

当前只读基线为新boot `215c4292…`：Xorg16.191秒首次1024×600、fbdev=N；早一次检查On/active/RG16/48,999,993Hz，87秒后末次检查为DPMS Off/inactive，三服务PID1078/1017/1077及uEnv/Xorg配置SHA保持。没有证据把Off归因于UART查询；xset报告600秒休眠设置。板端墙钟仍为2021年，不用于本轮跨机时间对齐，以主机取证目录时间和板端uptime为准。见 `evidence/current-uart-c-checkpoints.json`。

接下来先唤醒后收集实屏回执，完成HDMI保持连接时的独立屏幕电源对照；移动USB同时会复位屏幕，一次恢复不能单独证明供电质量问题。UART后续只考虑有文档定义的状态读取或被动消息记录，取得控制定义后才设计单次HDMI恢复事务。目前没有新启动参数、显示重置、板卡重启或固件更新，现场独立供电/新热插拔回执仍待取得。
