# HDMI 冷启花屏：重训候选与原生长尾观测

**最新决定：用户明确确认“未拔查，仍花屏”，本次软件恢复失败；随后要求暂不解决显示问题。HDMI排查已暂停，保留物理拔插作为临时恢复办法，未将候选装入启动流程。** 后续工作转向转轴、原生长尾、实际负载与严格收益验收；下文“等待实屏反馈”仅为此前步骤记录，不再表示当前状态。用户说拔插能恢复，未据此推定本次新boot已再次实际拔插。

本轮按用户“只用一个终端”执行，无新代理。**两小时观察已完整结束；用户重新上电后仍花屏，已在该现场完成一次软件恢复候选，等待实屏结果。** 原生r4生产代码、三模型、身份域、阈值和登记库保持；未刷新固件。新boot `c5f247b9-76b9-40a3-85ca-96578055eb5c`，相机1309、GUI1310、X1077已自动恢复，NRestarts0；前一boot检查点与归档逐对象相等、SHA核对通过。首次查询界面尚未就绪的失败记录保留，未重启业务绕过。

本次冷启动用户明确反馈“仍然花屏”，显示缓存connected/enabled/On；运行一次冻结474b…控制器后，train_loop入口1、encoder enable/disable0、调用返回、VBLANK返回、模块/自身trace清理、维护单元success退出，相机新增24帧且原PID保持，新模型超限0。后续相机继续到2238帧、约9.83Hz，worker及SFace ready，配置/身份库SHA保持，无新增所筛选内核错误。**这仍只证明软件执行及业务存活，尚无用户反馈证明画面恢复；不安装启动项，也不再重复触发。** 整个过程包括接口捕获/VBLANK查询，不能将潜在恢复唯一归因于最后一次训练调用。[冷启前置与归档核对](evidence/cold-return-before.json) · [真实花屏场景调用](evidence/cold-return-train-result.json) · [后检查](evidence/cold-return-postcheck.json) · [用户观察状态](evidence/cold-return-visual.json)。转轴仍FAULT/automatic_following=false，不报全项目完成。

[当前三模型、实际文件大小及CPU/DPU分工](CURRENT_BOARD_VISION_MODELS.md) · [用户回来后的明确验证步骤](RETURN_TEST.md)

## 已获得的实测证据

- 用户测试屏幕外部USB供电后仍花屏，随后多次确认“上电等一会，再拔插HDMI能恢复”。具体屏幕型号、电压和线缆未测，不能据此全面排除供电/连接问题。
- 同一次启动 `25b3d8ed…`，159.274秒、1542次缓存采样：花屏到用户物理拔插恢复正常，扫描参数及显示时钟未变，EDID前后均0字节。过滤内核trace共29条、未覆盖，记录到 `538.861014s zynqmp_dp_train_loop <- zynqmp_dp_irq_handler`，另有两次HPD work。它证明重训路径进入，未证明函数内部训练成功或唯一根因。见 [同启动证据](evidence/same-boot-findings.json)。
- 真实冷启延迟首次Linux输出到 uptime 60.21秒：此前43个样本无活动CRTC/无fb节点，相机已运行。用户仍报告花屏，再物理HDMI拔插恢复。**60秒延迟方案失败，自己的Xserver覆盖已移除，移除时未重启服务。** 仅能否定该Linux延迟方案，不代表已控制桥芯片的上电自主行为。见 [失败及撤销记录](evidence/late-first-output-failed.json)。

关机前核验启动为 `89d53e38-4726-4c94-b958-53f2dfb3bd4e`，相机1291、GUI1407、Xserver1403，随后受控关机；本次新boot/PID见上。旧资料“正做USB供电对照/板端暂停”已过期。

## 重训候选实际完成到哪一步

候选仅调用现有PS DP驱动的 `zynqmp_dp_train_loop`。不填写私有DP结构布局，不写未知GPIO、I2C、splitter寄存器或Flash。**默认 `enable_action=0`，加载本身不会重训；没有安装开机执行项。** 设备解绑会使捕获对象永久失效；显式执行还需设备仍绑定、单个活动DP输出及一次性触发。锁定DRM模式设置并等待DP IRQ线程结束后，才允许调用；原函数是void，返回不能冒充内部成功。

- 目标内核 `5.15.36-xilinx-v2022.2`，1856项启用配置（编译器文本除外）与构建配置匹配。交叉编译/导出符号核对通过，源 SHA `ce7e1a510e234f16c04a02f74dcbbfa766f60f1a959f064f6ae6bff0e8b93fa0`，模块 SHA `2e5bd549c33d23a2585710058d73b1a75f7e073b40a6884d426550735196a01d`。不以配置匹配代替运行验证。[构建证据](evidence/module-v2-build-validation.json)
- v1/v2均在实板完成诊断加载、捕获DP及DRM接口、卸载。v2状态 `ready=1 enable_action=0 dp_captured=1 drm_captured=1 triggered=0 action_returned=0 invalidated=0`。3次触发写入分别因参数/关闭动作被拒，**成功触发0次**；正常卸载、无新模型超限、相机PID不变。[实板结果](evidence/module-v2-board-diagnostic-result.json)
- 最初检查被10分钟自动DPMS休眠拦住，未加载模块；之后驱动名自动打开失败、空闲时无IRQ导致捕获超时。改为显式 `/dev/dri/card0` 的只读GETRESOURCES及一次VBLANK等待后通过。失败证据保留本机。一次唤醒使用 `xset dpms force on`，600秒休眠配置未改；它与冷启花屏是不同问题。
- [一次性控制器](source/train_once_controller.py) 默认只读检查已在板执行，旧boot/PID、不可用相机、休眠显示均拒绝；未返回的内核调用保留进程及模块，不强卸载。控制器/观察器/解析、冒烟及故障时间关联共51项离线测试通过，另有上述3项实板拒绝检查。离线分支验证不等于异常解绑实测通过。

**随后完成一次真实驱动调用冒烟：** 页面对照恢复main后，先通过普通DPMS唤醒显示，再采集新的before状态并显式触发一次。`triggered=1 action_returned=1 action_error=0 invalidated=0`；重训段trace恰有1次train_loop入口、0次encoder_enable/disable，之后只读VBLANK查询返回，模块卸载，维护单元success退出。相机44348→44372新增24帧、PID1291不变、worker仍存活，新primary/optional超限0，1024×600扫描状态保持；此段无新增DP训练失败/内核BUG/WARNING日志。[真实调用结果](evidence/driver-train-smoke.json)

这证明控制路径能实际调用并返回。原驱动训练函数为void，且无人观察实体屏幕，`visual_verified=false`、`internal_training_success_measured=false` 均保留。**不能将此次冒烟标为“冷启花屏已修好”。** 整个维护包含一次普通DPMS唤醒；仅重训采集段没有encoder重启，不能把前置唤醒从过程记录中隐藏。

板端最新入口 `/home/root/aura-post-power-20261022/helpers/474b8ce39ba29123/source.py`；模块仅留板端私有诊断目录，当前已卸载。共享目录不提供KO/ELF。构建脚本依赖本机原SDK/内核树且仅在本机私有WORK目录生成ELF，不在共享目录构建模块。下一次已观察到花屏且显示仍On时，先核验新boot/PID，再执行一次候选；保留物理拔插作为后续对照。若有效，还需连续冷启复验后才讨论启动接入。

## 用户离开期间的运行观测

两小时数值观察器 `aura-passive-two-hour-c248c0a96ffebb65.service` 已启动，root `/home/root/aura-display-sequence-20261024/unattended/c248c0a96ffebb65`。每2秒读取既有health，仅留白名单数字/恢复状态/原生报告和CPU利用率，不保存名字、图像、向量或录音，不创建模型或操控显示。PID变更不合并计数，连续查询失败会退出，至7200秒自动结束。其进度及最终结果分别为 `progress.json` / `result.json`；oneshot带MainPID而处于activating是运行中，不能据此认定失败。

早期1066.331秒：YOLO9.9556Hz、YuNet新增4031完成，新primary/optional超限、gap及fallback均0；**SFace新增0，不称三模型持续负载验收**。整板CPU约50.85%为当前无真人要求的非配对窗口，不与旧63–64%直接计算优化收益。[早期状态](evidence/observer-status-early.json)

针对旧原生期4次真实YuNet长尾，已用3.64秒C ABI入口/返回短探针和原生时间区间交叉确认YuNet线程TID1335（runner2），未确认SFace线程；探针及实例均移除，无新增故障。初版发现脚本的帧率端点不一致，已修正代码；原值从吞吐证据排除，线程识别不受影响。[线程识别](evidence/thread-discovery.json)

随后启动有独立清理守护的一小时目标线程调度trace，只保留该TID的sched_switch/sched_wakeup，**不继续保留每次推理的uprobes**。v1 `84fb117db99251b9` 已运行1776.502秒、0新故障，随后正常停止且清理通过。复查发现health计数与上一报告不是原子快照，因此更换诊断采集器为v2 `aura-yunet-sched-06f77083a55985a2.service`，root `/home/root/aura-display-sequence-20261024/scheduler-observer/06f77083a55985a2`。v2继承原一小时的结束时刻，**不重新延长观察窗口**；交接141.228秒未留调度trace，该空档故障计数新增0，明确不叫连续无缝跟踪。模型PID/原故障计数保持。

v2在计数增加后设500ms重试窗口，并校验ABI/task、原生时间顺序、故障标志及其是否落入新计数的观察区间；单次health仍有3秒I/O超时，500ms不是墙钟硬上限。若仍不匹配，记录 `NO_MATCHING_NEW_FAULT_REPORT`，不能把旧正常推理拿来解释新故障。6项关联专项通过，总51项。新采集器正常2.288203ms窗口对齐通过，RUNNING0.723203/RUNNABLE0.008/BLOCKED1.557ms。两版都有独立清理守护，最多2次故障观察或原定期限后退出；不改nice/亲和性/保护阈值，原始trace仅留板端私有目录。[交接及v2状态](evidence/observer-status-v2.json)

**调度跟踪现已结束：** v2在原定截止附近以 `DURATION_COMPLETE` 正常退出，本段1682.739秒，新增YuNet故障0，清理通过。现场核对自身trace实例为空、uprobes定义为空、临时显示模块不存在，三个目标内核kprobe均0；相机1291/worker存活、SFace ready。两个诊断阶段及交接分别记录，未当作无缝连续采样。[最终归档及清理证明](evidence/scheduler-final-archive.json)

两小时轻量观察器原字段 `exact_fault_report_available` 仅按last-report故障标志计算，**不是上述严格的时间关联证明**；该观察器只作计数/恢复记录，故障归因采用v2跟踪的校验结果。其部署源码c248…冻结保留，未在运行中修改或抹去这一限制。

正常窗口对齐已通过：总2.105451ms，调度在CPU上0.538451ms、可运行待CPU0.008ms、睡眠1.559ms；释放 bookkeeping仅0.00177ms。这是正常推理示例，不是超限根因。RUNNING是含中断时间的上界，BLOCKED不能区分驱动/锁；覆盖缺失、缓冲覆盖或采样暂停交叠会标记不完整，不能猜测根因。**目前无新超限样本，仍未闭环。**

另完成真实页面 A1/main60s→B/vision180s→A2/main60s 对照，原页已恢复。整板CPU分别51.20%→63.01%→51.43%，GUI进程组单核口径96.02%→148.28%→95.98%；视觉页预览12.52Hz，YOLO9.9607→9.9390→9.9335Hz，玩偶约8Hz，无新增故障/gap。这里只改变页面负载，未创建模型、开麦、播放、舵机动作或重启服务，**不是新旧代码优化收益比较**。两个后台观察窗口包含此页面实验与随后DPMS唤醒/一次重训干预，不能描述成全程固定负载、完全无干预的稳定性窗口。[页面对照](evidence/preview-load-aba.json)

另复用既有有界CU统计脚本完成15.057秒当前主页点测：整板CPU50.45%，相机进程组21.17%、GUI23.69%、Xserver3.54%；DPU任务busy5.00%、驱动任务完成207条，SFace新增完成0。统计器前后均用真实相机进度与冻结计数核对，结束后已关闭、守护timer inactive，未增加模型或合成输入。该driver busy口径不等于FPGA静态资源占用或模型加速倍数。[点测与关闭证明](evidence/resource-current-point.json)

两小时轻量观察现已取回完整 `DURATION_COMPLETE` 结果：7200.054秒，3539次health查询、失败0；YOLO新增71660帧、9.9527Hz，YuNet27119次准入/27116次完成/3次未提交，新primary/optional超限、native失败、gap及fallback均0；整板CPU均值51.31%。**SFace新准入/完成0，仍不是三模型持续满负载验收。** 模型及GUI/Xserver在结束快照中PID保持、NRestarts0，观察单元均已退出；trace/probe/临时显示模块清理已核对。观察包含前述页面/显示干预，不用于计算代码优化倍数。[两小时完整结果](evidence/two-hour-final-summary.json)。[100.7分钟快照](evidence/final-runtime-snapshot.json)保留为历史中间点。

用户返回后，普通DPMS唤醒且实屏确认正常；这不代表冷启花屏已修复。之后用户同意冷启，正常停止GUI及相机，检查点SHA `e6eb4b0d2f1ccb7a2e7d05f22f43a5e1fe6e43fb33e5daafec665921365ee0a6` 已核对，关机控制器报告 `safe_to_disconnect_power=true`、`poweroff_scheduled=true`、无失败。用户已报告断电再上电；串口被动窗口未收到Power down标记，不将其写成已捕获标记。本次新boot的历史归档与业务恢复已核对，花屏软件恢复的实屏结果仍待用户反馈。[关机结果](evidence/cold-return-shutdown.json)

## 资料依据与限制

[AMD BIST显示说明](https://xilinx.github.io/kria-apps-docs/kv260/2022.1/build/html/docs/bist/docs/modules/display.html) 明确KV260的EDID来自载板splitter，画面测试另需人观察，因此API connected/EDID成功不能直接验收实体画面。[AMD设计说明](https://xilinx.github.io/kria-apps-docs/kv260/2022.1/build/html/docs/defect-detect/docs/introduction_dd.html) 给出PS DP经STDP4320输出的拓扑。

[微雪C系列说明](https://www.waveshare.com/wiki/7inch_HDMI_LCD_%28C%29) 包含USB供电不足的提示；本机具体型号不明、用户外供电试验仍失败，未直接套用其端口或树莓派参数。没有找到可直接证明本机唯一根因的厂商结论。

仍待：真实花屏下的一次性候选试验、后续多轮冷启、原生故障调度证据、严格同输入CPU/DPU收益及真实旧码回退。旧4fault/4recovery历史不被本启动0值覆盖；身份阈值0.5/歧义0.1、INT8域/模型/库不变，Windows回执未代写。
