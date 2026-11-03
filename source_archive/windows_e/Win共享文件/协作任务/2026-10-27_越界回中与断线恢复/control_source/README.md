# v11越界触发后回中：独立PS候选

冻结r15副本，只改3个运行文件：continuous_face_control.py、continuous_session.py、run_face_motion.py；原r15、GUI、板卡未改。继承目录中的r15 deployment/upload清单是历史副本，不能直接用于部署，由主终端按新源生成新清单。

recenter_on_edge默认False保留旧行为。新入口启用：原左脸框线/右脸中心线只负责触发；触发后回原区仍继续，直到真实脸中心进入0.5±0.03，或同一目标经原大跳门禁确认跨过中央，就保持，不追赶区内日常头动。靠近中心按实际脸速减速。新profile为maxspeed30、acc120、gain200、velocity_gain24；minfloor6、jerk800和原OneEuro/Ruckig保持。

2秒缓存只保存“同一目标仍需回中”的语义及context/最后实际源ID，不保存滤波、速度、ARM、lease或原图权限。缺源立即完成当前脉冲并STOP；重新得到同脸、同service/camera epoch且真实更新图像后，仍重新确认并等待post-ARM新帧。旧READY不续租；换人/epoch、多脸、操作停止或意图过期清除。10秒segment上限仍物理STOP，随后只可用新源重新确认同一回中意图。

中央区不作无效预ARM；接近任一原触发线前0.05画幅才允许原有no-PWM预ARM。已回中沿用原SAFE_ZONE_HOLD，不额外断PWM。reason仍EDGE_FOLLOW/EDGE_BRAKING/SAFE_ZONE_HOLD；control/session增加recenter_active、recenter_state、target_center_ratio供overlay显示。触及软限位仍HOLD_AT_LIMIT，不能冒称已回中。

154项主机检查通过（138旧＋16新），覆盖真实ContinuousSession右.86→.76继续→.52保持、左框触发、区内保持/近线预ARM、跨中保持、短缺源STOP与新源恢复、旧帧拒绝、意图过期、换目标/epoch/body、多脸、原TTL/每源4µs与限位。RECENTER_REPLAY.json含6组合成回放，均非实板手感验收。原图250ms/检测锚500ms、PL1400..1600、STOP后清理reader/writer顺序未改，不包含启动大跳或硬件绝对源期限保证。
