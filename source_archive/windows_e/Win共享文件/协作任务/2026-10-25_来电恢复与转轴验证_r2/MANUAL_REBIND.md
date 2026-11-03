# 新启动手动控制绑定恢复

UTC2026-10-26T02:46更新。**控制入口已恢复READY，实体保持停止；本轮没有ARM/COMMIT，也没有回中。** 中位1420µs仍为用户报告参数，当前width/target1445µs、epoch3/ack42、flags0/lease0与上一轮观察后完全一致。

用户问“下一步呢”后，本轮完成的是控制入口准备与恢复；没有将该问句当作解除实体动作暂停。下一步现场工作是先确认左右方向，再接入r2并测试左右越界/回区保持/丢脸停止；尚未开始这些运动测试。

旧GUI绑定boot463c…和旧FDT，当前boot16a…因此正常拒绝MMIO。新版本从当前258组件GUI复制，使用本次已确认的20µs往返试验及用户观察回执建立全新的OBSERVED_MANUAL_VSRV2 release，实际范围1445～1465µs；没有把旧boot改成新boot绕过。该范围只是本次小幅观察范围，不是机械限位，也没有将用户中位1420改写成1445。

新GUI `/home/root/aura-pan-current-20261024/16a07283/gui-manual-bound-v1`；监督PID54830、手动后端54907。只正常重启GUI，相机13537保持，editor14694保持，identity ready、primary2/可选超限0承接原值。原GUI、原dropin和r2源码快照均保留。新覆盖仅为`zzzzzzzzzzzzzzzzzzzzzzzzzz-aura-pan-16a-manual.conf`，服务READY且NRestarts0。

新增明确的`automatic_following_enabled=false`准入：点击人脸随动直接提示“人脸随动尚未开放，请先完成方向确认”，在释放手动owner或创建运动子进程前拒绝。只保留旧v9路径作待替换配置，mode为pending_current_boot_direction；不会在新启动中调用旧运动上下文。r2实体部署和本次方向确认仍未完成。

验证结果：

- 6项源码测试通过，覆盖原owner交接/预检失败、锁定时无子进程且保留手动owner、非法准入值拒绝及显式开放仍保留预检。
- 新GUI全部258组件pins及manual load_release预检通过，预检无MMIO。
- 实际API点击随动被准确拒绝，手动后端PID/readback不变、READY/自动关闭，0ARM/0COMMIT。
- 视频已切回vision页面，raw-local预览正常；12次实际屏幕采样匹配实时相机、12个不同画面。没有导出图像。
- 首次API探针将仅有error字段的正常拒绝误判为格式失败；按实际API响应修正断言后复查通过，原始失败保留。不是实体故障，也没有试转。

[源码及6项测试](manual_binding_v1/)、[源码指纹](manual_binding_v1/SOURCE_SHA256.json)、[本轮6份过滤证据](VERIFICATION_MANUAL_REBIND.json)。原[恢复与20µs测试证据](VERIFICATION.json)是前一阶段历史，不用本轮READY覆盖其当时FAULT。
