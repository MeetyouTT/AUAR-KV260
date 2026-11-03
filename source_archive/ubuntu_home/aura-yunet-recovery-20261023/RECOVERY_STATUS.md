# 失败轮次恢复节拍候选

light3受保护120秒诊断定位一次实际更新空窗：源帧供给13次，尝试7次，其中时隙拒绝5次、共享锁busy取消1次、随后成功；发布观察间隔1038ms，前次源帧TTL之后缺口下/上界175/175ms。该轮YuNet关键区最大21.713ms，硬超限0，USB告警0，自动恢复确认通过。稀疏健康快照没有捕获这个短暂缺口，独立gap记录保留了证据。

在独立副本增加`retry_recovery_ms=None`（默认关闭）。显式`slot_retry=True,retry_recovery_ms=50`时，没有发布结果的轮次使用50ms等待；成功发布（含真实无脸结果）仍等待原200ms。等待释放共享锁，仍需新帧供给，原每轮两次重试/25ms退让/200ms提交截止/1000ms TTL/30ms硬上限/5ms guard/YOLO优先均保持。仅新增数字`recovery_interval_ms`和`recovery_waits`显示实验配置。

89项软件测试通过，包括原85项及4项恢复配置/失败节拍/成功节拍/新帧恢复测试；板端同源observer合成功能35项通过，新增CPU正常路径0.280494ms、拒绝0.155680ms、满32条gap记录health 0.287587ms，低于原0.5ms门槛。这些不是运行收益证据。

受保护120秒试验helper `7b9b767de12aaea3…`和只换namespace的r2 `10261c1b5b2b7458…`均在观测开头因新增USB告警停止，回退均verified；两个故障时recovery_waits均0，不能据此判断50ms策略效果。第一次故障后原服务又26.91ms越过guard，切CPU；约5秒窗口达到5000条xHCI slot3 ep3告警上限/CPU90.29%。空闲音频生命周期恢复后8秒USB0/CPU51.88%，再次切换候选仍复发。最终再次恢复原音频与原相机后8秒USB0/CPU52.18%，原相机130028/UI130049/Xserver1077 active，guard timer inactive。这是短窗恢复证据，USB根因仍未定。

下一步先实现并验证相机切换与原音频的有界协调顺序，再复测同候选，不能放宽YuNet硬cap/guard或把无结果轮次当native完成。
