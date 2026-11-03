# YuNet受限恢复候选与快速反馈

用户认为反复长验证耗时，要求优化解决。本轮沿用最多两个终端、仅主任务接板，无新增agent。先读取ZIP README、项目规则、共享当前入口与实测、已有调度/runtime/adapter，回读当前accepted release的schedule/yunet/ui三源并与release manifest核对，候选在独立目录创建，不编辑共享业务源或当前活动包。

实现默认关闭的yunet_dpu_recovery布尔配置和恢复状态机，新增policy/修改schedule、adapter、UI共4源。原30ms/5ms和YOLO优先保留；completed/status0仅hardcap的事件冷却10秒、需新鲜正常primary、原子准入，10分钟最多2周期/3次成功退出观察期。native成功证明由PinnedRunner上下文正常退出提供，旧证明不会跨作业；原计数不清。未知/native异常/guard/主周期异常/预算耗尽停用，明确未提交的前置撤回不被误判成native失败，SFace不复用此策略。

新增24个故障注入/adapter检查和4个实际PinnedRunner包装层的合成集成，连同旧89项共117项offline软件回归通过，执行0.104秒。初次新测试缺bootstrap装载失败，修正工作区bootstrap使用、保留原错误日志后通过；没有隐藏板故障。父版模块逐字节核验；完整源/测试在aura-yunet-bounded-recovery-20261023。

helper SHA336720519ea6523a…、payload c62830541b152932…在当前boot7924ac9f…执行同源KV260 Python3.9.9/aarch64隔离检查：24项通过，0.05969秒；真实DPU新作业0、未加载VART/XIR/numpy/cv2/gi、未改服务/config，前后相机198117/unit af337bce…保持，YuNet依旧CPU fallback。500空合成槽/模式额外每调用线程CPU均值0.027376ms<0.5ms，非整板收益、非真实推理尾延迟。UART传输0重试、回显恢复，原始UART不共享。

新候选默认关闭、尚未正式接入。本轮解决代码层可恢复性设计，不宣称31ms等待根因已消除。共享交付bounded_yunet_recovery、当前入口/Ubuntu回执/实施方案已更新；后续采用每轮约1～3分钟真实业务试跑和故障注入，长期证据在正常运行中积累，不把两小时等待当后续开发前置。当前CPU/DPU实际位置未变、SFace正式仍Windows，语音/身份旧库/运动/位流未动，Windows回执未代改。
