# 同版本可用性恢复脚本快速复核（初版）

更新：已复读修订SHA`d66c2cf284fc9acef2a87c0d7def29f2a85d90a95e120fb7962418c79db58863`。下列3项在该版已修：非guard恢复先确认/补arm；新PID先核对原argv/runtime/单owner，再以内存meta验证后原子rebase；中间systemd态等待且health排除旧PID。操作持GUI restore.lock，调用只读restore-check前已释放，不形成自死锁。**未发现这次复核中的可执行硬阻断，可以推进一次受保护同版本恢复。** 这仅是本地源码复核，不等于板端恢复已完成或根因修复。

最终再次复读SHA`cdb172e26c91629f33c71ed4f9ed631643c79fba72c8c338fa002aa988ac8e2b`：另补旧PID停机前重新核对owner_fenced/worker/3条完成事件；guard失败明确单次尝试已结束、不自动循环，并保留attempt_errors。仍未发现本轮未修硬阻断；`recovery-reviewed-manifest.json`绑定该最终SHA。

复核输入`recover_availability.py` SHA`618f5306d283cc6f0ee4e8519b0f9dfefb90b079913095048353be2beccea35b`。只读，没有接板或修改root源；以下是中断恢复边界，不能将这个版本直接标为全部通过。

合理部分：原3事件均native完成status0才预检；固定boot/unit/880源；复用已验证的GUI stop/PCM closed/start；新进程degraded也只结束一次恢复、不反复reset；旧相机已停但GUI也已停时不再要求不存在的GUI API idle。

需补：

1. **不完整报告恢复会跳过arm。** 初次先写ARMING报告再运行systemd-run；若此间中断或arm失败，下一次`--run`加载不完整report直接进入ensure，未确认任何独立guard。所有非guard mutation前需确认或补arm；guard自身不能因此循环重arm。
2. **rebase先写后验证。** 当前先把session.camera_pid落盘才g.verify/single_owner。应先核对new camera与原实际argv/runtime一致、owner锁一致，使用修改PID的内存meta通过验证，再原子写；最好重读最新session，避免把停GUI期间的元数据更新覆盖。
3. **新PID来源与中间态。** `pid!=OLD_CAMERA`不能单独证明这是本次同版本启动。建议保存原相机cmdline与stop/start阶段，核对新argv；对activating/deactivating先等待状态落定再重评，避免wait_health(None)立即读到旧PID而误判/结束guard。

较低优先级：guard自己的恢复失败时，它是一轮已经触发的一次性timer，不能把“报告未完成”表述成仍会自动再尝试；应记录guard本轮失败/需要人工或主任务接续，不能无限轮询一个已退出guard。

本报告不要求改变30ms/5ms/TTL、GUI源码/override/config或解除保护策略；目标是一次经过证明的同unit服务恢复与原GUI回退上下文衔接。恢复完成不等于根因修好。
