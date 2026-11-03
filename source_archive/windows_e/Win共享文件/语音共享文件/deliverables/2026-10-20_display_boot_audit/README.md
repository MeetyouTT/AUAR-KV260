# 每次开机花屏：本次启动的只读核查

用户报告“屏幕每次开机都花屏”，进一步确认每次上电有问题、实际拔插HDMI后恢复。本轮读取当前启动、显示设置、内核/Xorg/DRM信息，私下检查软件截图，并审查启动器、离线注入失败；没有切换显示模式、执行输出开关、重启服务/板卡、改开机配置、改像素格式或恢复转轴。

**证据最支持冷启动显示识别/同步没有完整建立，真实热插拔后重新建立。** 本boot早期EDID为0，Xorg实际先使用1024×768，启动器随后添加保存的1024×600时序；同boot稍后EDID恢复到128字节、与既有屏幕完全匹配。用户关于实际插拔可恢复的反馈与这些变化一致，但当次插拔的准确时间尚未取得独立回执，不能把EDID恢复的触发动作完全定死。分配器初始化、驱动热插拔路径与屏幕上电时序仍需进一步区分。

## 实际证据

| 检查 | 结果 |
| --- | --- |
| 本次boot | `567106f3-6d07-4476-b44a-11a6576ff14a`，首次取证时运行约146秒；不是上一轮转轴测试的boot |
| 实际启动入口 | `aura-render24-budget-20261020/e06409743174/startup`，GUI监督1072/子进程1464 |
| 每boot输出重建 | 配置仍为true、关闭2秒；setup记录`startup_output_retrained=true`。代码存在OFF失败也可标成功的漏洞，因此该标记不能独立证明完整2秒关闭已执行 |
| 早期屏幕识别 | DP-1显示connected/enabled，但EDID为0字节；早期复读仍为0 |
| 启动时序 | Xorg日志17.335秒明确`using initial mode 1024x768`；启动器等待22.276秒后按保存的49MHz/1024×600/59.85Hz时序设置输出 |
| 同boot后续状态 | EDID变128字节，SHA为已验证屏幕727d3e18…；校验和、首选1024×600/49MHz/59.85186Hz独立解码通过。Xorg约481.637秒开始记录ADA/product4及正确EDID时序 |
| 软件回读 | Xrandr与DRM均为1024×600，link-status Good、CRTC active；这些结果不能证明实体屏幕已正常同步 |
| 像素格式 | X根窗口16位TrueColor，掩码f800/07e0/001f；DRM RG16、pitch2048、1024×600，格式一致 |
| 软件画面 | 本机私下查看X11抓屏，文字、布局、人物清楚，没有发现软件截图中的整屏花屏；共享只保留截图元数据，未导出图片 |
| 驱动告警 | 启动约4秒出现dpdma_ref_div1设分频、dpll_int禁用的ret=-13；历史正常桌面时也记录过，不能单凭该告警确诊本次花屏 |

对应[启动与链路](evidence/startup-and-link.json)、[驱动及像素格式](evidence/driver-and-format.json)、[开机能力](evidence/boot-capabilities.json)、[截图元数据](evidence/screen-metadata.json)、[实际启动器](evidence/active-launcher.py)。UART源/返回体完整性记录在[provenance](evidence/provenance.json)，包清单见[verification](verification.json)。

后续证据见[HPD/EDID只读复查](evidence/hpd-and-edid.json)、[同boot后状态](evidence/later-state.json)、[EDID解码](evidence/decoded-edid.json)。最后一次DRM读取CRTC inactive，同时[xset查询](evidence/idle-state.json)明确600秒息屏且Monitor Off；这是另一个已确认的空闲熄屏状态，不将它混写成开机花屏或热插拔失败。

## 为什么真实拔插会恢复

KV260的显示路径为：`ZynqMP显示控制器 → 载板STDP4320 DP/HDMI分配器 → HDMI → 屏幕`。这由AMD的[KV260架构说明](https://xilinx.github.io/kria-apps-docs/kv260/2021.1/build/html/docs/aibox-reid/docs/introduction_aib.html)明确描述，不能把Linux的DP-1直接等同于一根没有中间器件的HDMI输出。

真实拔插触发下游热插拔，能够改变分配器与屏幕的连接/识别状态；对应版本公开驱动的HPD处理会通知DRM重新检测，在链路状态异常时触发训练。普通输出off/on会执行显示管线禁用/启用，但不能据此断言下游经历了与物理拔插完全相同的状态变化。[Xilinx2022.2对应DP驱动源码](https://raw.githubusercontent.com/Xilinx/linux-xlnx/xlnx_rebase_v5.15_LTS_2022.2/drivers/gpu/drm/xlnx/zynqmp_dp.c)。这是版本对应的公开参考，不声称已逐字匹配运行内核的全部补丁。

AMD的[BIST显示说明](https://xilinx.github.io/kria-apps-docs/kd240/bist/1_2/build/html/docs/modules/display.html)另指出KV260的EDID可能从板载分配器取得，某些情形断开外部线缆仍能读到。因此EDID、connected和link-status都应与实屏联合判断；当前也没有直接测出具体分配器内部寄存器/固件分支。本机没有`/dev/drm_dp_aux*`设备，未猜测I2C/GPIO地址或强行复位分配器。

结合“每次上电坏、实际拔插好”、早期EDID0/后续128及清楚的软件帧，最合理的解释是冷启动顺序/初始握手与真正热插拔路径有差异。线缆/接触、供电与屏幕唤醒时序仍是待区分因素，不能仅因插拔有效就宣布某一部件损坏。

## 软件重置的成功标记有漏洞

本轮按实际启动器SHA `cd168022…`进行离线故障注入：让每次`xrandr --off`都失败，随后模拟恢复/模式回读成功，函数仍返回`startup_output_retrained=true`且标记`software_modeset_verified=true`。原因是原代码在OFF真正成功前先设置retrained，后续重试跳过OFF也能进入成功返回。见[复现结果](evidence/marker-reproduction.json)、[测试日志](evidence/marker-reproduction.log)、[复现脚本](audit-tests/reproduce_retrain_marker.py)。所有显示命令均为mock，一项专项复现通过，不是板端故障注入。

因此更正此前“标记证明完整重置已执行”的说法：它证明软件尝试及模式回读，不能证明真正关闭、等待2秒、完整恢复每一步都成功。**离线证实的是误报机制，未证明本次开机的OFF命令实际失败。** 现网启动器未改，后续须分别记录尝试、OFF成功、等待完成、恢复成功和物理确认，不能用一个布尔值混合。

## 可以据此判断什么

上次“关闭输出2秒再打开”的配置本次保留，启动记录声称已重建；由于标记漏洞以及下游握手未验证，不能据此宣称完整重置或屏幕端重新同步已成功。继续增加等待时间不能作为已验证根治措施。

软件帧清楚且RGB565配置一致，降低了当前整屏异常由界面像素格式错配造成的可能。若实体屏幕在同一时刻仍花屏，问题更靠近扫描输出、HDMI链路或屏幕端。没有现场实屏照片/分阶段反馈，不能完全排除驱动扫描输出、特定动态画面或仅开机瞬间异常。

Linux内核文档明确将无法取得EDID列为启动显示异常的一类原因，并说明可配置固件EDID替代读取；这只是一般机制依据，不是本板具体物理根因的证明。[Linux EDID文档](https://docs.kernel.org/admin-guide/edid.html)。AMD也记录部分显示器同步可靠性问题，并说明热插拔事件、DPMS与显示管线启停的关系。[AMD ZynqMP DisplayPort驱动说明](https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/18842105/ZynqMP%2BDisplayPort%2BLinux%2Bdriver)。

## 后续处理方向与限制

1. 用户已确认真实拔插可恢复；仍需把当次实际插拔时间、实屏恢复与同boot的EDID/HPD/驱动状态对齐，避免把迟到识别当作确定的主动重置效果。
2. 针对EDID缺失，核查屏幕上电稳定性、HDMI连接与屏幕端握手；上电顺序或插拔后恢复只能作为诊断对照，不能凭猜测宣布线缆或电源损坏。
3. 软件上应先纠正重置成功标记，并评估就绪后固定已验证1024×600时序、将时序配置前移到Xorg启动阶段，避免先使用1024×768再较晚补模式。现有`/etc/X11/xorg.conf`只有DefaultDepth16，没有Monitor/ModeLine/Modes固定时序。本轮未更改它，早期固定时序是否能解决物理花屏待测；必要时再设计驱动/分配器层受控重初始化，不盲写GPIO/I2C或刷固件。
4. **当前内核未启用CONFIG_DRM_LOAD_EDID_FIRMWARE，相关edid_firmware参数也不存在。** 因而不能直接加一个EDID内核参数并声称修好；内核级固定EDID需要对应内核支持、启动文件和回退方案评审，不能在本轮只读诊断中盲改。

转轴侧：新boot仍为官方`kv260-benchmark-b4096.bit.bin`。上一boot的临时互斥保护进程已经随重启退出，不能继续称其存活；当前运动接口为FAULT/`Boot mismatch`，配置绑定上一boot，未打开运动寄存器或重连。前轮中位记录及修复候选保持，不把它们当作本次新boot已经校准或发布。

主机UTC证据跨2026-10-20/21，板端墙钟仍显示2021，不用于故障排序。七轮取证只读（截图使用临时文件后清理，无持久板端改动），没有执行新的显示/运动控制。Windows同步、实屏修复和冷启动验收均未确认。专项误报复现可将`audit-tests/`复制到本机临时目录后执行`python3 -B reproduce_retrain_marker.py`，避免改写共享冻结证据。
