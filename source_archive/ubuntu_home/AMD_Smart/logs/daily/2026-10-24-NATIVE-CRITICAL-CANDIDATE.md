# 原生DPU执行路径修复接续

## 最新单终端定稿

用户最新要求只开一个终端；已中断仍运行的business代理，其他任务此前结束，后续实现/测试/UART均由root串行完成，没有再启动代理。r1冻结native-v2-560d824588eb8f8a；r2 native-v2-d7256b06808509c9为222 Python（214底座＋8新增/5改）及5 C/C++，候选尚未启用。

原生20组恢复/seed/ACK、8仲裁、5 C ABI及20/5两套SAN通过；Python最后62项（业务、新boot、legacy bootstrap、archive hash链接）通过；旧237项235通过/2私有ELF跳过/0失败。真实CDLL→当前C++/fake依赖12项过，7结构全部offset/sizeof对齐。当前C++桥ed0611f6…/leasea080fa4b…、policy a9e82c7f…，AArch64 object7c92beb7…；板上只链接0.795479s、DSOc675ba69…/104480B，无cc1编译。随后仅实际加载DSO读ABI常量，factory0/候选推理0、5/3fault与primary3/PID不变，不能写真实模型验收。

接续只读发现SFace新三次36.081/34.009/31.308ms hardcap-only/status0，两轮恢复后预算耗尽LATCHED，完成755次/ready=false；YuNet5fault4rec仍guard LATCHED CPU。当前只有YOLO DPU约9.95Hz、worker_alive/gap0/primary3、camera29563/GUI29588/X1077三服务active/NRestarts0，原四源/unit/持久覆盖/身份配置/INT8库SHA再次核对保持；own probe/instance0、nice0、真实帧推进时CU统计静止。

r2补真实新kernel入口与legacy首迁移，默认关闭、双opt-in：同boot旧health仍拒绝；新kernel读取完整hash固定数字prefix，旧历史明确下界/unknown tail，要求known completion、不接受fenced/未知，完整归档/fsync和当前boot唯一marker在Context前提交，重复/换seed/失败重试不能重开预算。旧单调时间不重放，新域/旧档分开展示；归档hash链接写后续checkpoint。旧boot不擅自解锁。真实prefixSHA ecda1d52…存私有板目录，5/3已知fault保留；新增13＋2项以该数字样本、fake boot验证，非真实冷启。

222源已513355B零重试传至私有板路径`/home/root/aura-native-critical-20261024/candidates/native-v2-d7256b06808509c9`，拟用config SHA96948ff1…；未安装systemd覆盖。仅preflight实跑，当前boot正确拒绝legacy seed，Context/runner0、服务变更0/reboot0、前后5/3fault不变。真实模型等价/性能、三模型持续业务、身份精度、实际冷启和长稳仍未完成；没有主张利用率收益或根治。共享交付代码/测试/数字证据，排除目标ELF、真实板头、UART、生物数据与配置正文；Windows回执未改。

以下保留此前进行中的原始阶段。

UTC2026-10-24（洛杉矶10-23）。用户要求继续完全修复，最新从两个终端扩到多终端；root单路访问板卡，其余三路分别实现恢复policy、NativeLease/C ABI v2/seed和Python三模型接线/等价基准。项目ZIP README、实际规则、最新日志/方案/双机回执已读。候选在`/home/ghmd/aura-native-critical-20261024`；共享入口[进行中状态](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-24_native_critical_candidate/README.md)。

## 实际运行与新故障

同boot008f3e1b…、camera29563/GUI29588/X1077，三服务active/NRestarts0，原unit29786434…/持久覆盖ebf6d52c…/四生产源/身份配置398ece…/INT8库ee22b…保持。最新只读：YOLO9.96Hz、worker_alive、gap0、primary累计3；SFace391完成/0超限。YuNet累计5fault/4recoveries，event62778约36.5ms、execute35.666ms/线程CPU1.201ms、status0，hardcap/guard都触发，现LATCHED退CPU，不能写三模型仍DPU。未重启或清计数解锁。probe/instance0、nice0、真实帧推进时CU统计不变。

此前第3fault event55499为30.316ms/hardcap-only。历史首版桥编译前后fault3→4，fault4 execute29.525ms/CPU0.992ms、status0、guard0；隔离编译过不等于生产观察干净，编译是否致因未证。后续第5fault发生在没有继续板上编译的阶段，仍无精确新分段trace，不能泛化此前event20476的GIL/runqueue比例。

## 已实现与验证

原生一次调用内准入/提交/wait/确认/保护/释放，30ms/5ms/主任务优先/TTL/动态deadline/unknown fence保持。固定XINT8、VART端口名与顺序、自有有界缓冲、YOLO受控移交与防重复gate、Python移交/创建/关闭记账锁已实现；推理不持Python生命周期锁，未知完成不覆盖/释放，返回结果访问复查源TTL。

8组原生仲裁、6组布局、4独立准入回归、10桥接/SAN、21绑定、5实际CDLL→C++/fake VART检查通过，覆盖重叠不相加。最新C++3dfd77a2…已对实际21板载依赖头本机语法与AArch64对象编译，未做最新目标链接。独立绑定审查edbddc…，之后TTL增量由根21+5检查覆盖，未追认旧审查。历史首版e60e…目标编译链接及8/6 fake检查过，库未加载、DPU作业0；前台35秒超时后只读取回报告，原失败留存。后台有界编译helper已修、未在板执行。最终核验首次漏aura子目录路径失败，修正后通过，均只读。

已只读取得当前214源SHA，从本机匹配199源、板上补齐15源，完整214/214一致闭包在`coherent-baseline/aura`，避免23源patch与旧主目录混用。没有复制模型、配置正文、DB或生物数据到共享。代码/数字报告按阶段保存，尚无完整生产候选。

## 进行中与未验证

独立原生恢复policy a9e82c7f…完成13组/14非法seed/24条轨迹3840步逐状态对照/SAN及操作零分配。调度组在接独立两policy、严格一次seed、native状态与post-release ACK；业务组接三模型/TTL/健康与累计。现役handoff7e8e…若用当前mixed5fault4recovery快照作seed会拒绝，不代表当前既有冻结seed下次必然启动失败；新完整导出/迁移需补精确attempt_times等，不推造零预算或解除LATCHED。YuNet/SFace消费恢复轮的时点不同，SFace GIL晚归后的TTL确认不能提前在native结束时凑成功。

还未完成新路径真实接线/同输入真模型等价、同负载收益、持续三模型/真人精度和冷启。候选不能部署。Windows回执未改，GUI/音频/身份域/阈值/库/PL/运动保持，主任务仍在继续整合。
