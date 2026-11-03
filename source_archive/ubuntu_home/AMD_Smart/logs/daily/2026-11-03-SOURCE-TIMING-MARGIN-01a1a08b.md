# 9a4f 源码工程时序余量优化（进行中）

用户本轮新增目标：在原时钟频率及原时序预算下，setup WNS 至少 +0.020 ns，hold WHS 至少 +0.030 ns，TNS/THS 和违规端点为零、路由完整、DRC Error 为零。

前序源码全流程已通过：WNS +0.002 ns、WHS +0.010 ns。原已验基线包保留在 /home/ghmd/下载/AUAR_方案A源码交付_9a4f_20261103，不作为新增余量目标通过的证据。

margin01 在临时收紧 setup 25ps / hold 35ps 的条件下运行。首轮激进 hold 插入50个LUT1，guarded WNS -0.671 ns、WHS -0.024 ns，未达目标；保存检查点时根分区余量约38MB，报 HDDMProto::writeMessage failed。实际 FAIL 回执和完整日志保留在 verification/margin01。

仅对本次已结束、隔离验证树中的重复副本进行 SHA-256 核对后合并硬链接，保留所有路径与字节，未关联当前源码或原始输入。1652项去重，释放1686777856字节，完整清单 verification/deduplication_closed_outputs.json。没有清理原工程、模型、系统镜像、私人数据或历史记录。

margin02 改用 Explore → clock_opt → NoTimingRelaxation；如仍未达到余量，再 Explore / AggressiveExplore。最终恢复原用户不确定度，检查原周期、波形、实际时序、DRC及路由。增加实际输出分区至少1GiB的启动前检查。四项真实负例通过：非有限setup、负hold、源码指纹不一致、/run/lock低容量分区均拒绝，未创建输出也未启动Vivado。

当前状态 RUNNING，未生成符合新增目标的工程包。实际工作目录 /home/ghmd/auar-scheme-a-9a4f-20261103-01a1a08b；实现 verification/margin02，接续状态 verification/margin02-finish.json。验证与构建在Ubuntu执行，未访问实板、部署模型服务或发送机械命令。

## 本轮结束：按用户放宽目标采用已验基线


用户将20ps setup / 30ps hold调整为尝试目标，接受通过且可用的基线。本轮没有得到完成验证的新优化版本，正式保留WNS +0.002ns / WHS +0.010ns、TNS/THS 0、DRC Error 0的已验版本。

margin01：激进hold插缓冲后未达目标，写检查点遇磁盘不足，FAIL回执保留。
margin02：关键路径优化完成后guarded WNS -0.017ns / WHS -0.025ns，进入全局重布线；在用户放宽目标后结束，未完成最终时序报告，不能用中间数字宣称优化成功。

source_patch保存4个实验文件快照，仅供未来在独立工程副本中审查与合入。本目录不是独立可执行工程。实验进程已经结束，主源码已恢复到1687项已验RAR的逐字节版本。正式交付仍为 /home/ghmd/下载/AUAR_方案A源码交付_9a4f_20261103/auar_xuefei_source.rar。

未部署新硬件到实体KV260，未操作机械或Windows模型服务。

最终来源及状态：{"status": "BASELINE_ACCEPTED", "user_steering": "就是看看优化的怎么样，达不到也没事，及格就行，能用就行", "agent_decision": "Stop the unfinished optional refinement and retain the complete qualified baseline.", "setup_wns_ns": 0.002, "hold_whs_ns": 0.01, "TNS_ns": 0.0, "THS_ns": 0.0, "DRC_errors": 0, "routing_errors": 0, "timing_optimization": "NO_COMPLETED_QUALIFIED_NEW_RESULT", "margin01": "FAILED_CHECKPOINT_WRITE_DISK_FULL", "margin02": "STOPPED_AFTER_TARGET_RELAXATION", "processes_stopped": true, "source_files": 1687, "source_restored_to_qualified_archive": true, "archive": "/home/ghmd/下载/AUAR_方案A源码交付_9a4f_20261103/auar_xuefei_source.rar", "archive_sha256": "022422d9d1efa6106c2b247ac901dddd2f439a1a5e8eb19a22539010c3a944f4", "board_verified_this_run": false, "time_utc": "2026-11-03T17:15:00.424883+00:00"}
