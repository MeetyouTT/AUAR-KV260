# GUI CPU同输入验证与现役恢复

用户继续授权，主任务独占UART，第二任务仅做本地独立审查。开工已核对ZIP README、现行项目规则、共享入口及最新可靠性日志。

GUI现役profile的core含controller.tick，先以真实素材隔离细分。IDLE身体先材料化再pose可省一次中间图，因此实现4源exact融合候选。初次双core初始化约28+30秒使85秒测试超时；分段留证后改成单core共享只读素材。Q16/float插值差异和vmlaq分步乘加/FMA差异各导致一次画质失败，均拒绝，不调门槛。

最终ARM22组2,165,691通道对照、7组164帧及metadata全部零差；18项Python行为、3项最终封装/基准、3项C++旧分支检查通过。但ABBA各64帧CPU2857.724818→2701.569070ms，仅下降5.4643%，未过10%预声明门槛，**候选未部署，GUI/原库未改**。不将隔离渲染收益写成整板收益。

同一旧camera450495观测3次YuNet占用超限35.295113/31.706147/30.362253ms，均完成status0/未越guard，2次自动恢复后额度耗尽LATCHED。测试关系/CPU竞争归因未证，完整数值保留。所有额外负载结束后一次受保护的同版本相机重启，保留故障快照；首次错误`/dev/dpu`预检无mutation，修正实际renderD128与owner锁后原进程正常退出，现camera499773。GUI450525/Xserver1077、unit29786434…、boot、原模型/阈值/新旧库/偏好均保持。

恢复窗口60.214s：YOLO9.9644Hz、人脸3.7367Hz，无新增optional/主周期超限或gap；新SFace0请求，仅后端就绪，非三模型实际满载/认人验收。最终12份GUI/依赖源SHA保持、回退--check与服务核对过，controller/timer inactive。故障跨恢复仍3次，明确记录显式重启后新进程计数从头开始；不宣称长尾修好。

随后10.171s普通负载：CPU整板63.25%、GUI组38.40%、相机21.94%、Xserver组1.95%；非配对收益，没有新采DPU busy。当前身份/face worker ready、YuNetDPU787调用/0新超限/gap0，YOLO累计快照9.82Hz（与60秒窗口9.964Hz不同口径）。

额外3.023秒线程定位发现GUI `queue1:src`约单核36.71%，为样本最大单线程；下一步先识别实际GStreamer pipeline及其工作，不能因名字直接判定故障或关闭音频/视频。此短样本不作持续CPU结论。

完整源码、测试、失败、恢复与当前状态：[本轮交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_gui_cpu_evaluation/README.md)。后续定位真实GUI线程成本和native等待；SFace自动恢复、异人/多人、冷启动及整机长稳未完成。Windows回执未改。
