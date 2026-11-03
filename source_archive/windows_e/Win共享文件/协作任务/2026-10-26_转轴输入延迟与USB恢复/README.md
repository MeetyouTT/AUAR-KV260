# 转轴输入延迟：USB恢复与等价预处理快路径

2026-10-26，主要证据约10:57～11:59 UTC。承接Windows交接复核，用户先指定三路、随后改为单路、最终改为两路。本轮最终由主端独占UART/板卡，另一路仅做本地审查、位等价测试与快路径实现。没有并发写串口、创建第二个DPU owner或部署未完成的控制r13。

**本轮确认并处理了两处实际瓶颈：MCP01 USB告警风暴带来的系统负载，以及YuNet输入准备中的冗余转换。当前控制仍r12，输入为source-v16；视频/身份服务恢复，转轴STOP，最后命令1458µs。真人随动快慢与平顺性未在本轮验收。**

## 一、先恢复系统资源：USB告警源属于MCP01

基线仍同boot `16a07283-9e14-45e6-816d-3bda4cf333a7`，控制manifest `93001618…`、source-v14 `edb81dae…`、camera604389/GUI137253，自动关闭、flags0/lease0/width1458。用户前轮确认的自动方向+1保留，未回1420。

5秒线程采样显示多个视觉线程有明显runnable等待；3秒全进程CPU点测发现GUI实际子进程约141.77%单核、相机117.81%、systemd-journald44.59%、syslogd33.28%、音频worker24.96%，loadavg约10.37。总负载接近四核容量，不能把这些等待误称DPU执行时间。[线程CPU](single-terminal-thread-cpu-20261026.json)、[全进程点测](single-terminal-system-load.json)

末600条日志集中在0.582秒，约一半为内核`HC couldn't access mem fast enough for slot 4 ep 3`，其余主要是journald漏内核消息的提示；计数只是有界窗口，实际丢失消息数未知。上游[Linux5.15 xHCI处理](https://github.com/torvalds/linux/blob/v5.15/drivers/usb/host/xhci-ring.c#L2546)把这条文本对应到DATA_BUFFER_ERROR/-ENOSR，**不能只凭该文本判定带宽不足、供电故障或DPU损坏**。本板kernel5.15.36-xilinx-v2022.2读到相同文本，未修改内核或屏蔽日志。[告警记录](single-terminal-kernel-log-storm.json)

debugfs确认slot04名称为`1-1.2`、地址4、full-speed；sysfs/ALSA对应Lenovo MCP01，播放端点0x02 OUT、48kHz双声道S16LE，正是该索引的输出端点。摄像头为另一个设备1-1.3，640×480 YUYV/30fps。原先仅怀疑USB/摄像头的说法到此收敛为MCP01播放端，不再把摄像头当该告警来源。[设备与格式](single-terminal-usb-capture.json)、[slot/PCM](single-terminal-slot4-audio.json)

当时产品phase=IDLE、playing=false、audio_output_state=IDLE_READY、麦克风PCM关闭，但持久音频引擎按设计仍输出静音、播放PCM保持RUNNING。现役worker SHA `5f7f56849a92f03f34af89d52282f9c581549940cb522650fe4a427afc5af6fd`，engine SHA `f257cf2d4cf9749b0d83d377d78c2b963d989496fdfe322131f7f476beb39d8c`，已核对，不能拿r4旧音频文件当现役。[现役指纹](two-terminal-audio-current-source-hashes.json)

处理采用已有正常生命周期：确认空闲/STOP和258 pins后，仅正常停止并启动自有GUI，让其音频worker释放、重建ALSA管线。原相机604389保持，没有在此阶段重启DPU/相机、发运动、改音频配置或取消语音。GUI137253→647839；停止exit0、PCM closed，恢复后PCM RUNNING/IDLE_READY、手动READY和完整readback与原来相同。首次请求因额外假设SendSIGKILL=no不成立而在停止前被检查拒绝，未动服务；随后按实际服务策略正常停止成功，没有发强杀。[恢复状态](two-terminal-audio-reconnect-status.json)

启动初18秒尚未就绪，保留STARTING，没有重复restart/kill；后续正常READY。恢复vision页及前台后，视频raw-local可见、error空。新的同页CPU点测里journald/syslogd不再在热进程列表，音频约15.32%、GUI140.86%、相机126.87%；短窗loadavg约4.41（滞后平均值，不能作严格收益比例）。数次相隔多分钟的末8秒日志窗口为0，journald重启计数停在16。[恢复后负载](two-terminal-restored-system-load.json)、[最后日志窗口](two-terminal-final-kernel-log-check.json)

这是一次有证据的恢复，**尚未证明USB底层根因或永久消除复发**。没有修改、删除历史告警或把系统日志关闭；音频代码审查没有找到能证明该硬件错误由Python逻辑直接引起的证据。持久stop只重置内容并继续静音，不能当释放PCM；本轮使用正常close/重建才真正释放设备。现役“IDLE_READY”不等于USB外部健康证明。原7项＋3项Fake时钟有限复核通过，未据此新增自动恢复或默认关闭语音。

## 二、再定位计算：输入布局与INT8编码是明确热点

source-v15只加轻量分段墙钟/本线程CPU计时，不改模型、检测输出、owner、调度或跟踪。54项本地源测试＋另一路6项隔离审查通过，长数字压力观测包4009B<8192B。保持原v14跟踪算法，因此algorithm_version仍14；目录15表示诊断包装版本。

按每份记录自身的frame_id/source_mono_ms对齐，不能把两个相邻finally发布的诊断默认当同一帧。实流3.012秒23轮全部精确对齐，NoFace样本如下：[完整记录](two-terminal-v15-stage-profile.json)、[汇总](V15_STAGE_SUMMARY.json)。阶段嵌套，不能将各行中位数直接相加成整机延迟。

| 阶段 | wall中位ms | 本线程CPU中位ms |
| --- | ---: | ---: |
| resize | 3.636 | 2.904 |
| blob | 4.638 | 3.146 |
| layout/normalize | 15.087 | 9.351 |
| INT8 encode | 23.322 | 12.653 |
| native调用及结果处理 | 14.280 | 4.092 |
| 原生lease（样例，不是该行wall） | 约2～3 | 非纯DPU核计时 |
| identity回调 | 0.088 | 0.087 |
| 整个process | 86.479 | 41.902 |

这说明原输入准备值得优化；本窗口身份回调没有表现为主热点。wall减本线程CPU仍包含调度、GIL和等待，不能强行分配给某一种原因。此前高负载/有人窗口的pre/post更长，不能用新NoFace窗口直接算真人收益。

## 三、逐字节等价的快输入适配

source-v16只对原生YuNet、fix7、NHWC[1,320,320,3]启用。原真实路径的uint8 resize→float32整数blob→/256→encode可合并为：先提升uint16，再`(pixel+1)//2`、截顶127、变成NHWC int8。提升是必要的，不能让255+1在uint8溢出。Fast setInput仍检查固定shape/dtype、有限0..255且为整数；不把一般分数张量悄悄改成该路径。

只替换该实例的输入网络；沿用原`_native_scheduled`与完全相同的admission guard对象、源截止、NativePinnedRunner、输出布局转换、decode/NMS及模型。CPU/legacy和保护触发后的原fallback保留。没有另建模型、改阈值、降低身份频率或清预算。

固定256灰阶、随机/白/黑/非连续BGR及resize场景逐字节等价；6项guard、异常、空输出、legacy检查通过。与原跟踪/诊断组合后60项主机回归通过。[代码与测试](yunet_input_fast_20261026/)、[当前输入源](face_source_v16_candidate/)

板端独立进程微基准：OpenCV4.5.2/1线程、20帧交替先后顺序，包含resize/blob、完整setInput/forward与新严格验证；两边native执行均为同一fake，输出布局均identity，不开DPU、相机或MMIO。20帧及256灰阶全等价，非法域5项拒绝、原guard对象保持。中位结果：整段53.739→43.763ms，适配部分35.504→24.457ms。样本有限且调度有噪声，不等于模型推理或机械首动延迟。[板端对照](two-terminal-fast-input-board-benchmark.json)

完成正常STOP及fresh exact-owner checkpoint后启用v16。实际服务再次取得23轮对齐NoFace样本：fast_input_encode本线程CPU中位14.805ms、wall28.583ms；total_process CPU35.055ms、wall80.737ms。相较前一独立窗口的两段9.351/12.653ms，有更少的计算；这些是两个非严格配对现场窗口，不用相除宣称整机提升。新native调用、输出转换与回调正常，DPU_YUNET_INT8、worker_faults0、owner未fence、可选任务未disabled，快阶段名在实流中出现。[实际快路径](two-terminal-fast-source-live-contract.json)、[实际阶段](two-terminal-fast-source-live-profile.json)

## 当前状态与未完成项

- 控制仍continuous-v10r12，manifest `93001618e139810d7809b418e7da84fa2e3d378661d4f80b19c16a33e7c2c767`；输入source-v16 manifest `e51fea44364a35e1cd513d849244167e119ac14db757f9af0d3a9146a57a3607`，10 pins。算法v14、250ms图像/500ms锚/20ms提交余量及4µs/新源不变。
- 最后camera673020/GUI647839，控制21 pins/GUI258 pins保留，身份服务ready，视频raw-local可见、约11.79Hz、error空；不是外部HDMI扫描时序或身份精度验收。
- 转轴自动关闭，手动READY、flags0/lease0、最后命令1458，完整读回与本轮开始一致；没有自动回1420或新试转，自动方向+1和左右人脸边界不变。
- 原生primary累计：前轮尾7→本轮开始15→高负载点测22→GUI关闭前25→v15启动26→v16启动27；原生记录全部保留，不能仅凭时间顺序给每个增量定因。YuNet/SFace超限保持0/0。GUI重连没有重启相机；之后两次相机切换分别按fresh CP正常承接。没有通过重启清保护历史。
- 本轮实际样本主要无脸，快输入保持相同模型输出意义；**没有新一轮真人起步、连续随行、换向和平顺性通过记录**。仍需用户入画后做约30秒左右越线/回区复测；没有有效脸时不应输出动作。
- USB一次恢复不代表根治；原生主周期超限累计27也不能隐去。Q09最终检查到MMIO写入之间的竞态仍按前轮报告单列，没有把本轮性能修复当硬件绝对截止已完成。

两个候选的真实运行入口/模型与数据均未被历史代码覆盖。v15作为可回退的诊断基线保留，v16只启上述经字节一致验证的快路径；未部署未完成的控制r13。第一个空闲GUI停止请求被前置条件拒绝，以及一次UART重复打开被独占锁拒绝，均在没有相应板端动作时记录；不是成功验证。后续操作按串行完成，没有重入串口。

## 复现与后续

1. 源代码和指纹位于本目录候选文件夹。输入快适配独立微基准命令：`python3 board_benchmark.py --runtime-root <当前aura路径> --iterations 20 --max-seconds 12`；只能称合成输入适配比较，不能当DPU或电机测试。
2. 人脸重新入画后，使用现有按钮运行r12＋v16：区内静止，左脸框越绿线、回区，右中心点越橙线、回区，最后小幅换向。记录当前独立source间隔、锚龄、不同target与实体起动；不能用ARM次数代替运动。
3. 若人脸源已连续而实体仍顿挫，再根据本轮已有有界时序/命令轨迹区分轨迹截断、量化与机构响应；维持区内即时保持规则，不借平滑名义在丢脸/过期后继续运动。
4. 保留USB告警复发和原生超限的观察证据，必要时再做USB专项；本轮不默认关闭语音、不加无人看管USB重置、不改内核、不给旧框换时间戳。

共享资料只含代码、数字和筛选报告，不含个人图像、身份库、语音录音、模型权重或虚拟环境。Windows原交接未修改，Windows同步/运行/实体验收未代回执；原窗口与失败资料保留。
