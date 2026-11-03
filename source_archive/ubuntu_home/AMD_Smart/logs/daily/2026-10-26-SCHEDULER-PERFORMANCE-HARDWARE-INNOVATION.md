# 调度性能测量与硬件创新路线

用户要求具体说明硬件加速方法、现有DPU多模型调度性能及提高创新性的论文。本轮沿用ZIP/最新断电状态，核对原生r4实际插桩/快照、30ms＋5ms准入及前轮量化/系统审查；在线查看RTAS2026、PREMA、AXI-REALM/AoI、H3M作者海报及AMD预处理/PL FFT资料。未启动agent、板卡/Windows、推理或业务改动。

新增明确发现：原生路径的yolo.schedule_wait在进入Python primary上下文之后、实际native调用之前取样；该上下文只announce和保存线程局部期限，不能将字段当完整DPU排队时间。PipelineMetrics为最多256最近样本P50/P95，不是全量P99；不能相加各阶段分位数。提取旧快照YOLO路径20.51/33.17ms、发布图龄65/105ms、YuNet lease2.201/7.246ms、SFace lease7.950/9.875ms，标明样本/时点/调用范围，不与180秒业务窗混算。

建议先保留主任务/30ms/5ms，比较可准入可选任务的FIFO、轮询、EDF、等待补偿，再研究误差价值与PL绝对源截止。HLS预处理/音频FFT-Mel、分块及AXI预算按画像选择；没有承诺新核能塞入现役时序资源，未把P99当WCET或将预算当硬抢占。

新增[共享方案及实验矩阵](/home/ghmd/Win共享文件/协作任务/2026-10-26_调度性能评测与硬件创新路线/README.md)，全部实验标PLANNED_NOT_EXECUTED，旧G0—G5未改；证据JSON提取历史数据/源码SHA并核对语义。PREMA/H3M部分PDF超时后用原文HTML/作者海报与出版信息，未声称全部PDF通读或论文复现。共享入口、项目导航新增链接，未替Windows回执，断电/机构暂停保持。
