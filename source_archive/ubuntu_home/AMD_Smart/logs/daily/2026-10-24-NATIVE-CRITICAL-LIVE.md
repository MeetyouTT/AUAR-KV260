# 原生三模型执行路径实际启用

用户要求继续，且最新只允许一个终端。root串行完成控制器、两次软件重启、同输入真实模型对照、业务启动、失败修复和验收，没有再启动代理。项目ZIP入口、规则、最新状态和双机回执均按要求核对。交付[实际版本/源码/证据](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-24_native_critical_live/README.md)，本机`/home/ghmd/aura-native-live-20261024`。

## 当前结果

已保留`native-live-r4-dc4602e2b2b7398c`。boot a69299ef-17d0-446f-a0df-56c0a08cd2fb，camera2174/GUI2206/X1075；唯一DPU owner PID2174，native DSO实际映射，三模型DPU路径ready并真实执行过。最新累计YuNet2326准入、SFace64完成，optional超限0；primary累计2分别含前失败版1和新启动1，未清零。相机/GUI active、NRestarts0只表示自动重启计数，不代表本轮没有受控重启/切换。GUI IDLE/IDLE_READY/vision，未主动开麦或播放。

60.264723秒真实业务YOLO9.939480Hz，新增primary/optional超限/gap0、SFace新0。180.841166秒YOLO9.936897Hz，SFace新增46次完成，新primary/optional超限/gap0，三模型短业务覆盖通过；不作本人/陌生人/多人准确率结论。最终审计源/配置/身份库保持，identity cfg398ece…/INT8库ee22b…；原unit297…、旧覆盖未改，仅添加自有维护/执行覆盖。

## 真实推理与执行范围

在生产owner已退出的维护窗口，同一project owner先旧YOLO再adopt，新旧YuNet四头与SFace两种公开合成INT8输入按名字逐字节相等；6对/16次执行API均确认完成并释放。YOLO两例结果均空，不能冒称已验证非空人体框精度。新native库c675ba69…、C++/ABI v2保持候选冻结版，30ms/5ms/TTL不变；不刷空任务制造利用率。

代码将准入/execute/wait/确认/保护/释放放同次原生调用，所有三模型共用gate，输出准备/发布在执行权外。最终实流指标：YuNet原生决策区间均值2.638ms、最大18.126ms，释放后至Python返回观察最大19.079ms；SFace原生均值8.216ms/最大12.136ms，释放后返回观察最大9.719ms。后者包含C尾部/拷贝/调度/GIL等，不等于纯GIL或硬件计算；只证明当前范围的执行权已经释放，不外推任意Linux负载的硬实时保证。

## 失败全部保留

第一次reboot：008f3e1b…→89760db2…，启动隔离/真实对照过。首次生产启动因源码包漏ByteTrack LICENSE/upstream_manifest失败，marker已消费；补原SHA附件、前置校验及tracker初始化后，没有删除marker重开预算，而是第二次软件reboot到a69299ef…。实际断电冷启动0次。

第二boot的一次原比较流程准入/结果TTL拒绝，已确认关闭、无cap/guard/unknown，原工具没保存完整拒绝Report，不能进一步证明哪段拒绝或断言绝未提交。将旧参考放在真实YOLO primary窗口之前、保留原100ms/30ms/5ms后，22工具检查及真实比较过。systemd-run Typeoneshot客户端曾8秒超时但unit继续执行，未重新提交或kill，后来取回通过结果。

r3业务因新增统计stage未注册、primary拒绝计数误放时长接口，真实PipelineMetrics抛ValueError导致YOLO线程退出；此前fake observer未覆盖。r4注册四个native时长、primary拒绝改独立counter，新增真实enabled observer/实际UI循环回归。r3正常shutdown导出精确seal checkpoint再退出，primary1/overrun1和旧档hash链同boot承接到r4，无第三次reboot、无恢复预算清零。早期已有执行覆盖碰撞和观察任务在启动锁忙时拒绝均留日志；只退役自身确切hash的旧覆盖、控制器结束后再开观察，没有并发DPU owner。

## CPU/DPU与清理

首15.075秒CPU62.9536%、camera33.2833/GUI23.4990/X3.6981%整板，DPU busy5.0%/205驱动命令；次15.076秒CPU64.2422%、camera22.2210/GUI36.6315/X3.4161%，DPU busy约5%/202命令。第二段SFace64→64无新增，不称三模型同时负载。捕获帧率/页面/输入不同于旧基线，都是非配对资源点测，不主张CPU收益或加速比。stats已结束且实际YOLO帧推进时计数不变、两cleanup timer inactive，own probe/instance0、nice未更改。

维护控制16项、修订比较22项、r4业务/迁移/启动与真实metrics67项通过；既有237运行235通过/2私有ELF跳过。C++20/8/5＋SAN、12实际CDLL/fake验证为此前同核心检查，不混作本轮独立新用例数。

旧kernel YuNet5/SFace3故障与4/2恢复通过prefix ecda1d52…和archive9f7573bb…保留为历史下界/unknown tail；新计数域单独报告，不能拿当前0故障称旧故障消失。新内核一次marker、同boot精确checkpoint、unknown保活与不自动替换owner保留。相机Restart=no/SendSIGKILL=no/TimeoutStopSec=infinity；完成未知时native入口保留owner。救援timer已disable，任务完成/失败controller已退出，journal失败历史保留。

旧码回退hook16项软件/actual函数注入通过，要求native未fenced、正常stop＋精确checkpoint＋原PID消失后才启旧代码，两个optional保持LATCHED、计数承接。本轮没有为了演练而停掉已工作版本再实际切回旧码，实回退仍未验收。长期罕见长尾、身份准确率/陌生人多人、持续真实音视频、严格配对CPU/DPU收益和实体断电冷启仍待验证。

交付只含自有源码/必要ByteTrack许可附件、数字证据和SHA，排除模型/ELF/权重/UART/人脸/向量/库/配置正文。Windows接收回执未代填。下方旧候选“当前只有YOLO/未启用”是此前阶段，后续以本实际版本为基线。

最终共享交付269条SHA/270文件（含清单），235 Python AST/22 JSON核对及全SHA二次核对通过；目标二进制/权重/UART未共享。当前保留版本及下一步按本日志开头执行。
