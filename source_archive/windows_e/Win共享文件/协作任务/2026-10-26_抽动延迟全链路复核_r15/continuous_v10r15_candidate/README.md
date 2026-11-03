# continuous-v10r15

修复疑似过期缓存ACK时间错配，并将live报告文件IO移出运动线程。主机138项回归、KV260纯Fake寄存器8组paired对照和同17710B报告的文件写入对照通过，已在旧boot切换配置；尚未进行r15真人随动，随后用户报告断电。

runtime变化：`deadline_driver.py`、`run_face_motion.py`，新增`live_writer.py`。首次PWM23ms、250ms图/500ms锚/20ms提交余量、4µs/source、方向/边界和硬件监督保持。线程退出失败不写停止收据，原控制/STOP错误优先。

manifest SHA：`c72cfb9138889554b03cf224557dcb79bca1ee70b466a822fda3b09254bba2de`，24个运行文件。`CACHED_ACK_REVIEW.md`含独立审查和8组成对软件反例；继承的r14记录只表示历史，不覆盖本版本状态。

完整真人失败分析、板测与断电恢复边界见[共享回执](/home/ghmd/Win共享文件/协作任务/2026-10-26_抽动延迟全链路复核_r15/README.md)。旧boot许可不能跨断电直接复用。寄存器/软件回归不等于机械平顺验收；主机测试依赖同一工作区的冻结r14、原驱动和Linux轨迹测试库，未称Windows运行通过。
