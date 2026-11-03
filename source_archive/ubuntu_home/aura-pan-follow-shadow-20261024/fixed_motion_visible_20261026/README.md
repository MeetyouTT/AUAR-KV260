# 5秒15µs可见固定往返候选

用户反馈原2秒5µs往返幅度太小。此独立候选冻结 `1420→1405→1420`，速度指令为−10/0/+10/0µs/s，各持续1.5/1/1.5/1秒。20ms采样共251点；执行前248点到4.94秒，最后40ms预留QUIESCE/STOP。所有计划脉宽都在原manual1402..1420内，最大偏移15µs；没有提高速度、加速度或jerk。

`run_fixed_motion.py`复制自已修复PWM三值过渡/ACK下界的entry core `09e4f8c5…`，只改5秒、251/248点和15µs限幅合同。`fixed_bench_adapter.py`复制自 `fa13b637…`，只改最大5秒和15µs；仍使用原BatchDriver等固定SHA依赖、单步≤1µs、租约≤100ms、20ms余量、首次≥23ms、窄范围、原异常优先及最终STOP。原entry/adapter未修改。

`plans.json`顶层`samples`保存全部251点及`plan_sha256`，板端入口可直接读取冻结计划，不需要加载主机Ruckig库。`CODE_MANIFEST.json`绑定3个运行模块及plans.json。必须由主终端的新boot现场参考/独占owner/有限窗口收据入口调用；本core CLI默认PLAN_ONLY，`--execute`仍拒绝直接执行，不能把默认1500或旧1420当新物理位置。

23项主机测试通过：完整248ACK返回1420/STOP；首COMMIT和第30COMMIT延迟的PWM相位反例；未知width、过期、错ACK、截止改变、窗口/步长、16µs偏移拒绝、原错误保留、批读上下界、251点端点与原速度/加速度/jerk，以及CLI拒绝。`MODEL_RESULTS.json`包含普通与相位延迟的完整模型记录。

本子任务未访问板卡、UART、MMIO或修改生产；本5秒方案尚未实体验证。Q09的native内部最终COMMIT暂停仍可能造成迟到输出后被软件STOP，`hardware_absolute_deadline_guaranteed`保持false。
