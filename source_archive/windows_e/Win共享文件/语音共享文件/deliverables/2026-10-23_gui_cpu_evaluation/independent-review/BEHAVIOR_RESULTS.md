# IDLE lazy blend 候选行为复核

结论：**11项合成行为检查全部通过，当前未发现阻断固定输入native像素/性能对照的行为问题。** 没有访问板卡/UART、打开音频/图形服务或模型，没有修改任何业务源码。

验证文件：`tests/test_gui_cpu_review.py`。离线执行使用现有Vitis-AI Docker镜像、只读挂载、无网络；PIL图均在内存合成，NativePixels为假实现，不加载ARM native库。最终日志`behavior-tests.log`，11项、0错误/失败、0.003秒。首次夹具的overlay lambda未接收现役BlinkLayer传入的pose关键字，出现夹具错误；修正为接受kwargs后完整重跑，原日志保存在`behavior-tests-initial-fixture.log`。它不是业务代码错误。

已检查：

- 仅IDLE、非mouth资产、native存在、defer_portrait_offsets=True、idle_gain>0时请求defer_blend。
- idle_gain=0、非native或非deferred时产生真实材料化像素；普通PIL消费者不会收到共享首图的lazy代理。
- SPEAKING/SPEAKING_NEUTRAL及矛盾的IDLE+mouth资产（包括gain=0）保持材料化后再口型合成。
- LISTENING/THINKING/ACK_NOD/DENY_SHAKE/AWAKE/PUZZLED不采样无用IDLE身体，原meta的asset/index/source_position/transitioning保持。
- 运行真实BlinkLayer.apply的合成眨眼路径，确认先materialize后alpha_composite，交最终pose的是实际合成像素；原两帧不被修改。
- IdleBodyTrack默认sample仍材料化，显式defer后下一默认调用恢复材料化；matrix插值与body/core元数据保持。

主任务已取得的真实profile支持这一候选是有限收益目标：24个IDLE帧中materialize_blend19次累计约0.162秒，pose累计约1.054秒；相邻帧先材料化确有工作，但主要pose仍占大头。不能据此宣布整机CPU降低或82ms DPU长尾已修好。

当前候选仅`tools/idle_body_compositor.py`、`tools/realtime_facials.py`与本机固定基线不同；其余6份核心源字节相同。源SHA见`candidate-reviewed-source-manifest.json`。

剩余决定条件：主任务实际native的同seed/同时间/同素材像素与ABBA process-CPU结果。假native测试只证明调用路径和状态契约，不证明真实NEON融合舍入逐像素相同。若有非零像素差，最终报告应写满足预先声明的误差界，不能叫逐字节一致；若质量或CPU门槛不通过，应拒绝候选，不调门槛或把profile当收益。
