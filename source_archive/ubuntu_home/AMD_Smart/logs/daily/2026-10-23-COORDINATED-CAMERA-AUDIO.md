# 相机与常驻音频协调切换

最新状态纠正（后续用户询问优化是否完成时只读复查）：同boot/相机198117/unit af337bce…在进程启动2263.609秒后再次YuNet硬超限31.340203ms，当前CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN；YOLO DPU约9.95Hz、3秒30帧推进，正式SFace仍Windows、音频IDLE_READY。原实板审计再次运行在ready(candidate)断言失败，随后独立健康取证确认超限，未错误复用旧response作为新通过。故障native status0/completed1，execute墙钟30.547485/调用线程CPU1.011459ms，总可选墙钟31.352864/线程CPU1.801477ms，硬上限超、guard未超；自愿3/非自愿1次切换，不能唯一归因。内核末5000记录最早单调12398.3204秒，覆盖进程启动及故障±60秒，匹配USB告警0。CPU退回后两次3秒点测65.08/70.57%，不报不同输入收益；未重测当前DPU busy。板端墙钟2021不可信，时间使用同boot monotonic/进程tick。只读探针首版误读events键和journal grep选项未取得故障数组；修正为fault_events及原兼容journal尾窗，第二次封装3805B超过3800B线长在本机被阻断，压缩减字后实板exit0/回显恢复。最新共享交付runtime_overrun_recheck与入口/Ubuntu回执已更新；原68工件封存不改，30分钟通过仍保留但长期验收未通过。本轮未重启/改运行代码/放宽30ms或5ms，下一步先解决长尾/恢复再SFace正式迁移，CPU整板同输入收益待验。

用户再次明确离开两小时、后续自主决定并修复问题；沿用最多两个终端，仅主任务串行接板，无新agent。阅读ZIP README、项目规则、最新共享任务/回执与原失败/恢复证据。目标先修复测试切换流程，再评价50ms候选；原模型/Windows身份/30ms/5ms保持。

新增独立`/home/ghmd/aura-coordinated-switch-20261023/handoff.py`：原cfg/source/unit/model/manifest/偏好SHA、新boot与MCP01/ALSA映射、UI无录音/播放/转写/运动校验；独立restore timer必须先armed，关闭原音频并确认PCM closed后才切相机，目标相机健康后恢复原偏好并启动原音频。故障恢复走同一个有源码/状态校验的独立进程，flock串行且original already-ready幂等，不覆盖后来外部修改。相机/音频PID允许预期变化，Xserver PID和原GUI源/config不放松。未改模型、语音或运动代码。

16项协议故障注入/PIN反例检查通过。首个只做流程的baseline helper `eb4e29a1…`（模块SHA12a6a4ea…）上板完成120.566秒：YOLO9.95303Hz、YuNet2.50485Hz、CPU55.1835%、USB0/硬超限0，25样本，最大可选占用22.5390ms。warning cursor在PCM关闭后、camera/audio启动前采，覆盖启动及整个窗口。原相机147824/UI147850/Xserver1077 active，原unit84116d8f…保留；独立恢复代码执行original already-ready幂等通过，guard disarmed。仅短测流程验证，不证明USB驱动根因已修复。

同版协调模块集成至原89项已测的50ms恢复候选，模型/runtime/GIL封包逐字节不变；新增6项生成器接线与可执行准备流程检查，连同16项共22软件通过。候选helper`fda2e51c…`，原camera/source/config检查保留，UI PID检查换成等价source/config/preference/health复核，观察期间仍锁定新UI PID，Xserver PID从未豁免。540秒监督/600秒独立回退，运行结束总是协调恢复原相机及原音频。当前120秒试验进行中，不能预报收益。

候选短测完成并通过：有效120.990秒，YOLO9.89334Hz、YuNet3.19860Hz、CPU56.8499%，USB0/硬超限0，25快照源帧龄max401ms且全程gap计数0，计数器无观察错误。当前50ms恢复wait累计28（含候选预热期，非全部窗口增量），max关键区26.1019ms/estimated budget偏差1，原30ms/5ms不动。协调恢复原服务verified=true，原GUI源/config/偏好复核通过，恢复UI153765。helper28b4a68b…已开始同源600秒延长（121样本、RuntimeMax1200秒、独立回退1500秒），扩展后finalizer AST与协调短测相同；新增UI生命周期需要额外监督余量，不把参数延长当已完成。旧未协调755c97c3…长测仅准备、未执行。

600秒完整通过：有效600.3496秒、1867次窗口native完成、YOLO9.95087/YuNet3.10985Hz、CPU56.4728%，USB0/硬超限0/gap0，121快照max716ms；协调恢复verified、源/config/偏好复核通过、guard停止。继续同版1800秒helper981032db…（361样本，2400秒监督/2700秒独立回退）已有完整观测结果：1800.4395秒，YOLO9.95257/YuNet3.11202Hz、CPU56.4442%，USB0/硬超限0/gap0，primary超限1→1，快照max570ms、关键区max23.6307ms；当前正在恢复，尚不能写成恢复完成。

实际运行准备：runtime_entry.py复用原0cec741d…包装器，按bootUUID与独立launch目录保存进程记录，避免跨boot/PID复用重名，4项检查通过。release_control.py仅接受精确同源、完整1800秒且恢复已通过报告；再协调切换并实测120秒，成功才停止独立回退并保留新unit，失败恢复原unit。10项资格/文件封装检查与4项实际文件/fake设备的accept/USB故障/源变更/不合格反例通过。首次fake缺失quiescent cursor已补齐fixture并保留错误日志，不是板故障。发布helper edaaf2a0…仅准备，未执行；启用不改变模型/Windows身份库/30ms与guard。源与测试已复制共享deliverable供审阅。

1800秒恢复最终verified=true，protected_audio_source_verified=true、timer inactive。只读资格校验按真实完整报告通过（report SHA84ceff8a…，5603次窗口native），非fixture。原版15.150秒XRT取样CPU55.0279%/DPU任务忙碌4.8684%/189命令，统计最后关闭；这是任务忙碌率，不是MAC/PL资源占用。

首次实际启用EDA…复核出现“Optional task overrun: yunet”，15秒前最后正常样本max28.346ms，未存下实际故障快照，不能断言为哪一种超限；已自动协调恢复原192784/UI192810，guard停止。保持失败源/结果。上线采样原本每5秒多做重复源/模型哈希与额外health，对齐已验证长测的一次health＋PID核验，完整哈希保留首尾，另加故障快照；并不证明额外检查是唯一根因，不改原生预算/guard。

R2实际启用helper63d4244d…通过120.315秒：YOLO9.97386/YuNet3.32462Hz、CPU55.7005%、USB0/硬超限0/gap0，源码封装946d1a0d…同经过30分钟代码。停止独立保护timer并保留新camera unit **af337bce…**，活动`postpower-retry-live/release-recovery50-946d1a0d500f-197870`，相机198117/UI198147/Xserver1077。当前1ms GIL、slot retry/light3/50ms失败恢复启用；成功发布200ms，原30ms/5ms与TTL不变，旧unit84116d8f…与原runtime完整保留。旧写死原unit的helper已不对应当前配置。

部署后15.169秒负载：CPU54.9258%/XRT任务busy4.9342%/196命令，非同输入A/B，不报显著利用率或加速比。profile没有新DPU作业且最终统计关闭。当前boot专用`restore_original.py`已安装、只读--check实板通过，--restore先arm独立timer，3项软件检查通过；未为测试手动入口而撤销最终保留版本。

最终只读审计passed：879运行包文件、entry、gil包装、rollback入口、原备份及原模型/GUI/身份配置哈希通过；新unit af337bce…、CPU affinity0..3、音频IDLE_READY、CU统计停止、guard inactive。进程运行1230.27秒时max24.406ms/overruns0/gap0/真实native失败0；诊断native_failed与准入后撤回计数精确相等。正式身份仍WINDOWS_CPU_SFACE_ORT/旧库，未登记人或改语音/运动/位流。图表PNG/PDF/SVG/CSV与实际启用9份关键源码已写共享交付。真人/强语音负载及真实冷启动仍待现场验收，Windows接收未代确认。

交付封存完成：68工件长度/SHA、35份Python AST、18份已有JSON及17个相对文档链接通过，另生成CHECKS/SHA256SUMS两份JSON。共享ACTIVE_RELEASE与独立实板审计、9份当前源码SHA一致，120/600/1800三报告native增量387/1867/5603且回退均通过；首次实际启用失败保留。源/图表/部署状态/回退命令/模型放置说明齐备。无后台试验、统计或保护timer保留；仅原业务服务以已接受配置运行。未修改Windows回执。
