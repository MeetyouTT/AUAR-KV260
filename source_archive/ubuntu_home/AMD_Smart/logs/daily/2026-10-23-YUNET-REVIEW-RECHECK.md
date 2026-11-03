# 独立YuNet审查回传复核

用户粘贴另一AI的完整审查，沿用当前分工和项目任务。按规则复核ZIP/共享入口、现役固定源、三个已有故障、GIL/亲和性/观测历史及SFace92/16候选。没有启动agent、连接板卡、推理或改生产代码。

有效发现：diagnostics.finish在active/condition内且占用终点取样更早；FaceTargetService.work的native异常退出；fallback可见性、健康查询锁范围及SFace持续可用性均值得处理。SFace已有候选但未正式部署、自动恢复未做，不能忽略或误写上线。

纠正与同SHA源码相反的结论：PinnedRunner输出np.empty在slot前，pipeline_metrics.native_mark的execute_return端点now/cpu在probe前而非后；两端采样排除在记录的execute区间外但仍计入optional占用。duration差不能直接给出begin/finish单独开销，wait_end→optional_end也不是整个finish成本。已接受process-setting明确target board_camera_motion.py、actual0.001，不能改成ui_camera_service入口。YOLO started同时决定整轮100ms节拍，收到帧后重锚会改语义；固定fps/单调started/单primary下更早新deadline未证明可达，旧guard更保守，不能按“必错”改。

只读浏览AMD官方UG1414 3.0的Python execute_async文档（描述阻塞函数）及官方Vitis-AI v3.0 runner_py_module.cpp（准备buffers后gil_scoped_release native execute、返回前重获GIL），Linux5.15 schedstat文档。上游实现未与本板安装二进制逐字匹配，不能直接当板端根因；wait短不排除设备等待、voluntary多不唯一指GIL。完整schedstat曾额外0.763ms未过0.5ms门槛，env只初始化读不是热关；GIL1ms/绑核已有历史，不机械重跑。

recheck.py执行：重算A/B/C三个故障，C execute82.077971/occupancy82.926870ms且guard越界；旧诊断窗口2954.075119757秒，SFace最长正常wait0.076061ms。三个纯软件反例确认旧调度器：20ms业务+20ms模拟finish后仍记20ms/overrun0；finish BaseException后active遗留；begin BaseException后active遗留。是未修缺口的离线证明，不是新生产故障或已修复通过。

输出[共享采纳清单](/home/ghmd/Win共享文件/协作任务/2026-10-18_双机联调/YuNet独立审查_复核与采纳清单_20261023.md)及evidence/ubuntu/yunet_review_recheck_20261023的脚本/JSON/SHA；旧审查包保持不改。后续先逐项加固诊断异常资源清理、SFace状态/worker韧性/fallback可见性，再在保留正确性和观测成本前提下做边界/低成本分段对照，GUI CPU任务继续。不盲捕native未知完成异常继续提交，不回收可能仍在途的资源，不重锚期限或放宽30ms/5ms制造通过。
