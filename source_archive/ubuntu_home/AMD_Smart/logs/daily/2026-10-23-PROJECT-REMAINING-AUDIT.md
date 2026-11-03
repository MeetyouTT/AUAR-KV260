# 整个项目未闭环问题复核

用户询问下一步及整个项目哪里做错、哪些仍未修正。按规则重读ZIP README/完整方案相关范围、项目规则、最新共享入口/语音规则、两份回执、实测和现役源码；没有新增agent。发现旧总览和执行单仍有SFace Windows/断电暂停等过期状态，较新语音证据则已包含真人插话、记忆更正遗忘与首句提速反馈，不能倒退为未实现。

两轮独占UART只读均exit0、SHA校验/echo恢复通过。当前boot7924ac9f、unit a29082ba、camera333557/GUI333586/Xserver1077均active、NRestarts0；YOLO9.94Hz，正式SFace DPU累计1528次/超限0，身份ready/error空。

重要新事实：本版YuNet累计10678次native完成、2次超限，最大31.162401ms；recovery faults2/attempts2/recoveries2、RUNNING且disabled=false。原一分钟零超限仅该窗口有效，根因未修好。两次分别scheduler30.692/31.162ms；第一例execute4.099/wait0.160ms，主要时间在外围；第二例execute墙钟30.221ms/调用线程CPU1.123ms，不能唯一归因GIL或硬件。当前freshness gap0、primary累计overrun仍1；native_failed0。

新3.066秒/proc采样整板CPU62.61%、相机组19.46%、GUI组36.35%、Xserver组1.92%，均整板四核100%分母；短采样仅热点线索，非收益对照。manual_pan.state当前FAULT，未进一步读取MMIO或发动作，本次原因未定。源码审查显示SFace disabled后只defer、未接YuNet式恢复，顶层ready不能完整反映特征后端停用；这是审查确认缺口，目前SFace没有实际超限，未作新故障注入。

将真实未修故障、未完成精度/性能/功能验收、以前已纠正错误分别记录。未闭环包括YuNet长尾、SFace停用状态/恢复、旧相机断帧/USB根因、陌生人/多人/重返、CPU整机优化和同输入收益、转轴实体修复/发布、显示物理链路、ASD/VLM/PL源期限与仲裁扩展、冻结整机冷启长稳。既有语音/插话/匿名记忆成果保留，不将待验说成当前故障。下一顺序为SFace可用性诊断闭环、GUI热点与API内外对照，再独立精度和同输入竞赛收益；短轮反馈、长稳随业务积累。

共享报告：[项目未闭环问题与下一步](/home/ghmd/Win共享文件/协作任务/2026-10-18_双机联调/项目未闭环问题与下一步_20261023.md)。入口/索引/Ubuntu回执及active优先级、旧执行单已标最新审计，历史工件与Windows回执不改写。此次未改板端service/config、模型/库、语音服务/监听、位流或运动输出；不称已完成新代码修复。

验证：只读脚本AST通过；当前响应JSON、UART exit/echo和unit/identity/2次fault/2次recovery断言通过；问题表5个本地引用均存在，数值证据另附源码及私有响应SHA。没有重跑业务回归、现场负样本或长时测试。
