# 当前入口与受控回退

先查CURRENT_STATE.json、final-audit.json和systemd实际ExecStart/DropInPaths，不能只用原unit SHA297…判断活动版本。当前持久覆盖`zzzz-aura-vision-recovery-c76110abefc304bb.conf`优先于两个已保留的`/run`旧覆盖。启动文件和4源SHA见deployment-manifest.json；GUI运行175源保持。

当前boot的GUI-only只读回退检查入口为：

```text
/home/root/aura-vision-persistent-20261023/promotion/c76110abefc304bb/gui-context-29563/restore_previous.py --check
```

它验证的是GUI上下文，不等于完整相机回退已实际演练。换boot/PID/配置后先重新只读核对；旧固定上下文应拒绝，而不是改PIN强行通过。不能拿旧66cde…上下文直接覆盖当前相机版本。

本轮相机保护回退由哈希固定helper的`--restore`执行：

```text
/usr/bin/python3 -B /home/root/aura-post-power-20261022/helpers/c76110abefc304bb/source.py --restore
```

该入口属于当前boot/版本，不要跨boot盲跑。执行前确认当前相机owner未fenced、处于可停止的空闲业务状态、来源/hash/PID仍匹配；未知native完成不得创建第二owner。控制器先arm独立guard，再停止GUI关闭PCM、停止相机；删除的仅自身且SHA匹配的持久覆盖。旧代码的保护入口写入`/run`并保持两optional停用，下一boot该临时入口消失，不留下固定旧boot的启动器。原unit和旧覆盖不删除。

本轮未为验证而实际撤销最终接受版；读回与GUI-only --check通过、回退控制器在fake服务/临时文件中验证。换boot后需建立新上下文，不能把旧检查通过沿用为未来通过。

SFace恢复条件：completed/status0/body正常/hardcap-only→10s冷却→YOLO新完成且无新增primary超限→普通准入→3次合格；600秒最多2轮。COOLDOWN/PROBATION的UI业务ready=false，真实输入不足时等待，不用空作业凑次数。guard、完成未知、owner fence或预算耗尽保持LATCHED；恢复不清faults/overruns/attempt history。

`dpu_protection_allow_new_boot=true`只允许真实不同kernel boot重新开计数窗口。旧快照SHA和来源保留；同新boot重复启动有独立消费marker并锁住optional，不能借重启清预算。这条启动分支已CPU和KV260隔离验证，实际断电冷启动没有执行。

统计/探针的证据读取必须同时查看worker退出、cleanup/统计停止、timer inactive、页面恢复及源码/模型/库SHA。phase墙钟含调度/断点/复制，不能命名为纯DPU时间；CU driver busy、CPU占用、模型吞吐与FPGA LUT/DSP资源分开报告。resource_snapshot.py第一次非零累计门槛拒绝的记录保留；修改后的门槛不重置别人正在使用的统计。

原始UART、完整ELF、反汇编及私有偏好原件仅在Ubuntu本机和板卡私有目录；共享代码包不带生物数据。Windows只更新自己的回执，Ubuntu不代填接收/本机服务/实板业务验收。
