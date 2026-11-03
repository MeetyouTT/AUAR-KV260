# DeepSeek审查结果复核与第三次长尾

用户回传完整DeepSeek审查并说明这是审查结果。本轮独立核对当前源码/已有实测，未新增agent、未接板卡或实施外部建议。共享入口已更新第三次YuNet故障及SFace候选，按当前分工保留现场，不重启或修改YuNet/共享调度/保护。

确认有效发现：occupancy结束在实际active释放前，诊断finish仍在关键区；生产SFace停用状态传播缺口（已有4源候选92软件/16板隔离，未部署）；人脸worker面对原生异常退出为fail-closed路径，需要可见性和有界监督；预算只上调、health嵌套锁和fallback观测不足属实际事实，但根因/优先级未由此证明。

确认报告误读：return侧probe是在取now/cpu之后；np.empty在进入slot之前；当前包装入口board_camera_motion.py SHA匹配且调用ui_camera_service，实际1ms，PIN没失效；YOLO sleep与started同锚点，不能只移动deadline；仅自愿/非自愿切换不能给GIL/runqueue二分类；完整schedstat此前0.763ms/7.234ms开销未过，环境变量不热关。两个计时区间之差不能拆出单端点偏移，SFace正常trace wait真实0.076061ms；短wait不能证明返回时作业已完全结束。已查Linux schedstat及Python3.9切换间隔官方语义，未据此臆断本板VART绑定实现。

实做4类本地检查：真实OptionalDiagnostics配3ms假probe验证返回端点先于return采样；AST核对outputs分配在slot前；入口SHA/调用链及1ms记录；真实scheduler配虚拟时间证明只把deadline放宽到frame_arrival+100ms可允许optional跨原100ms节拍。仅运行纯本地合成，无DPU/runtime或生产操作。

新交接中C事件占用82.926870ms、execute marker82.077971ms/线程CPU2.163218ms、wait0.106431ms，自愿+69/非自愿0，native status0/completed1，但guard越界、当前LATCHED退CPU。累计14399次/3超限，attempts2/recoveries2；YOLO9.94、SFace2534/0超限、gap0。本轮重算3条时间线，未把已有只读回传当本轮在线实读。此前“约1ms偶发抖动可能工程可接受”的评价只覆盖前两条，不能覆盖C。

新建共享deliverables/2026-10-23_deepseek_review_verification：核验报告、给DeepSeek的补充修订提示词、三次完整数值环、本地验证结果及必要源码；原审查包冻结不改。没有向外部服务发送、未修改Windows回执。后续先修正外部审查、明确端点与保护原子性，复用SFace候选，补匹配VART信息及低开销单变量实验，不直接采用其补丁。

报告：[核验结论](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_deepseek_review_verification/README.md)。本轮属于审查核验，尚未完成生产修复或长期验收。
