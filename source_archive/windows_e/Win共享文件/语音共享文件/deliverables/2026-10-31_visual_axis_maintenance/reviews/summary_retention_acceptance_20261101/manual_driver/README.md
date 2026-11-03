# 手动单轮入口：仅完成本地准备

13 项公开假状态检查通过，远端组合源码通过 Python 3.9 语法解析。尚未用此驱动操作设备，不构成手动录音或同会话检索实测。

沿用 8ebb 观察器的原隐私投影及“首个被接受的新请求 + 匹配完整播放 ACK”判据，仅改为 PAUSED 状态下本地 RECORDING 的 READY 门槛，并加入单次停止控制。差异见 ../evidence/manual_observer_minimal.patch。

执行时只走现有 UI service_action 的 record_start/record_stop。先读取公共 ui_runtime 的 capability/modules，拒绝远端音频路由；开始后必须看到 local_recording.state=RECORDING。自动聆听保持 disabled/PAUSED，automatic_conversation.enabled=false。monitor_owned 无独立公共读回，不能以 visual_bound=false 代替；只能基于固定源码暂停不变量推导。

驱动默认只做本地组合检查。实际开启前需要目标范围和摘要／原文条件成立，并确认用户已准备好在 20 秒内说话。收到用户说完后，通过本次 trial 的 STOP.json 传一次停止控制；已自然结束则不重复停止。观察超时会自然等待，绝不取消正在回答的任务，也不切换自动聆听。

生产源码、配置、selection、时钟、数据库及原跟随控制器均不由此驱动修改。FROZEN_MANIFEST.json 固定材料，现役变化后会拒绝复用。
