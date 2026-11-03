# SFace正式DPU迁移与三模型本人实测

用户明确要求开始解决SFace正式迁移/三模型/收益等未完成事项，并两次确认当前为已登记本人，随后确认正对镜头/准备好。按规则先读ZIP README、AMD_Smart规则、最新共享入口/语音约定、当前unit048ee59及实际source，主任务串行接UART，未开agent。旧版source20份回读带SHA，模型12b2ff5c…和compiler manifest d52e4343…实板存在。只读SQL确认旧库identities1/templates1，committed archive1/revision15，26图（25帧+selected），包含5张原登记留出验证图。

实现迁移模块：旧库只读，要求唯一身份/模型维数绑定、唯一committed归档与当前revision精确匹配，检查文件哈希、拒绝链接/路径逃逸、selected与五张验证帧不重叠。先用旧FP32模型重现selected特征并比对旧模板，再在camera停用且独占原DPU锁期间用同SFace INT8模型重新计算，写入新模型域命名且0600的独立SQLite库，保留原ID和称呼。旧向量不复制到新库，旧库/照片/config/hash均保持。0.50阈值和0.10 margin在验正样本前已固定，不据5个正样本拟合；unknown-person/多身份现场误接收尚未测。

实际迁移重现旧模板余弦0.9999999999991561，5张原留出图INT8 score0.79054/0.84434/0.89373/0.84659/0.84049，独立11次offline DPU作业（selected1+probes5+store验证5）通过。原库SHA前后e0d2113e…，新库model binding sface-int8-12b2ff5c7de15713/128，1身份1模板保留。名字/ID/图像/embedding只在板端私有路径，报告只保留计数、分数和哈希。

真实挫折都留档：首次迁移在store.match拒绝numpy.float32输入时失败，未启用且恢复旧版；修正CameraFaceExtractor DPU分支输出为普通float tuple，迁移verify调用normalized tuple。最早三模型60.449秒计算达到YOLO9.992/YuNet3.706/SFace1.853Hz，112次SFace native，无overrun/gap/USB，但本人快照只有2/13，故未接受并恢复。后来用户确认正面时，私有预览一帧仍低头/反光（仅检查可见性/姿态，不人工辨认身份），请其直接看镜头；一次开始提示与45秒ready窗口不同步而提前结束，明确承认并改为controller等待操作员marker后再计时。没有降低阈值、清历史UNKNOWN或以计算通过代替身份通过。

另有几次只读preflight被旧camera的“Camera stopped producing frames”watchdog重启、免按键enabled但mic实际关闭/WAITING_SERVICE误拦，均在source/unit切换前退出；有界30秒预检需同PID连续3次新帧，判断实际mic/录音/播放与pending状态并保留用户enabled设置，不越过活跃采录限制。两项预检反例加入部署检查。一次并行UART访问被既有锁拒绝，未发送命令，等待原传输完成后串行恢复。先前所有失败controller和guard timer均inactive，恢复报告逐次verified。

最终helper **00b792619ce222d2…**（与已测代码相比只加操作员开测marker的流程）源25项、候选20模块。在停止原音频/确认PCM关闭后作离线迁移，启动新camera/config/DPU身份，原GUI按原偏好恢复。83项软件（包含真实extractor→store浮点类型边界、迁移元数据/链接/帧独立/模型域、双模型通知、实际匹配计数）、36项发布/PIN/回退/事务反例通过。等待operator-frontal-ready明确开测后，连续3次KNOWN才开始观察；身份sample和计数不含等待阶段。独立restore timer600秒先ARM，controllerRuntimeMax480秒，成功完整首尾核验才停timer并保留新unit。

**正式接受窗口60.344932秒：** YOLO9.95941Hz，YuNet发布3.56285Hz/215次新native完成；SFace正式1.739997Hz/105次新native和特征返回，实际KNOWN95/UNKNOWN10/AMBIGUOUS0，本人接受率90.476%；13状态快照11点为确认本人。CPU66.5036%，USB0、freshness gap0、所有optional overrun0，独立取消锁busy/withdraw0，未新增primary周期超限。累计进程启动时一次primary周期超限保留，不称全生命周期零故障。已知本人窗口不同于陌生人准确率，多人/unknown/冷启动/长稳仍未验。

**当前实板：** unit SHA `a29082bae1d382d7a43505d5a1d3a51fa2203081423755900e9d72836385e343`，release `/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-sface-int8-9025bd49fe52-333217`，camera333557/GUI333586/Xserver1077；正式identity backend DPU_SFACE_INT8，YOLO/YuNet/SFace均共享同一owner和B4096平台。新库私有 modelid-333217.sqlite3；fallback是原048ee59c/Windows SFace/旧库。新runtimeentry0.001秒GIL、YuNet/SFace100ms outside-slot通知、30ms/5ms、1000ms源TTL保持；native运行成功后才统计真实completed。

额外15.19708秒整板/XRT窗口CPU64.6931%、DPU任务busy6.27598%、231命令，SFace新完成31次；未另开runtime制造负载，finally结束CU统计后计数冻结验证通过。此前双模型窗口约55.33%CPU/4.934%busy与本次不同输入/业务量，不能直接作为同输入速度/降耗因果。current三模型任务busy不是PL资源率。

最终只读审计：新原数据库隔离/原库SHA不变、绑定与人数、source/model/config/GUI/owner、controller和restore timer inactive、音频IDLE_READY均过；手动回退--check实板通过，成功后未为测回退而再次撤销本版本。关键16源和1ms启动记录从当前板端回读，880 runtime package seal验证。交付在共享deliverables/2026-10-23_sface_formal_dpu，源码/软件及实际数值/失败与恢复/SHA/current placement/回退齐备。私有人像、音频、向量、库、原始UART不共享，Windows回执未动。

封存最后核验：87份工件SHA/长度、66个Python AST、全部JSON解析和16源与device-export一致通过。接受后同进程只读回查SFace累计1091次完成，YuNet3131准入，两模型optional overrun0、gap0、SFace wait511全ready；此时用户已放松，face_count0且UI UNKNOWN，是无当前目标时正常关闭身份显示，不伪算已知窗口准确率。当前原Windows库仍保留，正式SFace字段与ACTIVE_RELEASE/旧入口指向一致。
