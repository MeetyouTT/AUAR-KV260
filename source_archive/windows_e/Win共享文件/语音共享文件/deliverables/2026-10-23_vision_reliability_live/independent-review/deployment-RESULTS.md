# 发布与回退独立审查

结论：**23项离线部署检查通过，未发现新的上板阻断项。** 本副任务未访问UART/板卡、执行真实systemctl/模型/音频，也没有修改业务源或共享回执。仅新增tests/test_deployment_audit.py和本目录报告/清单。

实际执行：`python3 -B -m unittest discover -s tests -p test_deployment_audit.py -v`。最终23项、0.014秒，日志deployment-tests-r3.log。初轮18项中两个fixture缺主任务新加入的owner_fenced字段，补fixture后18项通过；第三轮增加5项GUI克隆及最终primary快照反例，23项通过。所有文件操作均在TemporaryDirectory，service/进程/原板卡路径均被替身拦截。

确认已处理的发布缺口：

- 候选ready使用严格validator，不能把观察结束后恢复完成的新optional超限当作可接受；原版恢复仍允许有完整status0证据的历史3次故障。
- 原GUI dropin文件内容及完整路径集合均保护；只允许增加本会话自有override，foreign新增、原文件改写、自有文件替换或symlink均拒绝。
- observe最后after快照比较primary起点，最后验收前也再次比较，源/DB核验期间的新主周期超期不会仅因optional正常而被接受。

23项覆盖：parent已确认3次故障只作父版本准入、unknown completion/计数不匹配拒绝；candidate新fault/worker/SFace/fallback/diagnostic异常拒绝；non_atomic诊断计数不强求瞬时相等；guard和PCM关闭先于组件切换；sealed restore_entry --guard；GUI活动时拒绝覆盖、只删自有override及幂等精确安装；GUI源仅spoken_query变化、资源链接和设置/旧配置保护；预检失败无service操作；最终primary与真实native_completed差值。

本次没有通过运行整个control.run假装成真实发布验证；主任务负责板端隔离、短窗、source/config/DB/PID、PCM关闭和独立回退守护的实测。仍不代表长尾根因已解决、冷启动/长期稳定/现场精度验收完成，也不把owner_fenced解释为取消或证明未知在途作业已经结束。

审查截止时源码SHA见deployment-reviewed-source-manifest.json；之后这些源码有改动时需据影响重评对应检查。
