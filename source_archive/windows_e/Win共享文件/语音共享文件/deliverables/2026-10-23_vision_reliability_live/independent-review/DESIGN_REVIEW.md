# 独立审查与故障测试边界

副任务仅写`tests/test_release_audit.py`和本目录，不访问板卡/UART、不启动真实模型或音视频、不修改候选业务源或共享记录。先读ZIP README、项目规则及当前复核清单。

当前测试设计覆盖：辅助诊断begin/finish/error/snapshot的Exception与BaseException；native/body自身异常保留而不泄漏执行权；非准入调用不能清除他人owner；begin诊断耗时仍纳入30ms；完成标记/硬超限/guard/恢复在释放前更新；finish阻塞时真正YOLO线程能前进且旧finalizer不能覆盖新owner；health阻塞snapshot时不持scheduler condition；known preexecute withdrawal不误判native失败；人脸worker未知故障保持线程存活但明确不可用并拒绝新帧。

实施注意：

- 诊断finish迁出后，不应把缩短的关键区计时解释为根因消除；健康返回应明确诊断与scheduler副本非原子，避免部署断言误比较同时计数。
- 若begin已发布thread-local trace后异常，需有安全的detach/诊断错误口径，避免迟到native_mark污染旧trace。只要物理active可释放不代表诊断数据一定一致。
- 未确认native结束时不允许自动重投；保持worker等待、ready=false/fault_latched并需协调重启是本轮合理收敛，不要求重建所有者进程架构。
- 30ms/5ms、YOLO原周期锚点、native_not_submitted和恢复次数语义保持。

主任务通知第一版候选完成后，首轮15项通过，补查trace身份/fallback/关闭状态后第二轮23项通过。详见RESULTS.md；这些是离线合成/并发检查，不是实板或长期验证。
