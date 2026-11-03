# YuNet等待长尾与CPU/DPU协同后续方案

用户询问解决方法与方案。本轮重读ZIP README、有效优先级、最新共享入口和故障证据，审查DpuVisionSchedule/DpuYuNet/PinnedRunner。确认一次hardcap/guard超限置disabled后无自动恢复；当前Python worker调用VART，31ms墙钟不能直接当硬件计算或唯一归因GIL。原37分44秒故障、调用线程CPU1.8ms、native status0/guard未超/无新增匹配USB告警作为依据，不新增实板收益结论。

已在共享协作目录写入`YuNet长尾与CPU_DPU协同_后续实施方案_20261023.md`，并更新共享入口/Ubuntu回执。第一阶段为默认关闭的有界恢复候选，明确完成/status0/仅hardcap/健康owner与YOLO前置、冷却及次数预算、计数不清零和故障注入；这是可用性恢复，不当作长尾已解决。第二阶段先确切板端ABI的C++原生对照，再证据驱动单owner独立执行进程；IPC和调用者端到端指标一同保留，不能移动计时边界制造收益。第三阶段为按剖析推进CPU流水线、独立INT8身份域SFace及同输入对照/2小时长测。

查阅AMD官方Programming with VART确认C++ execute_async/wait接口作为方案可行性依据；在线文档版本与板端版本不能混用，本轮未安装/升级VART或编译部署代码。先前GIL/核分配不足以证明彻底修复，方案不再单靠此类参数调整。当前只制定方案、审查代码和更新交接，无新实板测试/配置修改/服务重启，未新开agent。Windows回执与同步接收未代确认。
