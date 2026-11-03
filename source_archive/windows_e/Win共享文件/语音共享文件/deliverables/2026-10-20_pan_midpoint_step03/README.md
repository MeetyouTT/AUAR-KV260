# 反向校准第三步：1520→1500→1490µs

UTC2026-10-20 08:42。用户报告上一步1520µs“更偏右了”，记录为在用户描述的视角下，增大脉宽加重右偏。尚未定义机器人坐标/顺逆时针或镜像图像的控制符号，因此未据此修改跟随polarity。

本次从上次已到达的1520µs测试点初始化，按硬件限速保持1500µs两秒，再保持1490µs两秒，结束立即STOP。91条连续ACK、八个0.5秒阶段的端点脉宽读回以及关闭后独立复核通过。最后事件3968.01ms，含guard加载耗时5.515秒；最终flags0/lease0/active=false/armed=false、width/target1490、测试reference1520、epoch3、ACK91。输出许可关闭，未建立机械PhysicalReference或启用跟随。

脚本SHA256 `a1cb5d9731ca63d5386f55a3e561632e93c84fa0c3d0bc19006770251404be18`。精确boot/FDT、CID、程序/固件、联合APP/Native锁/ID/ABI/build、初态epoch2/ACK46/width1520/reference1504/target1520/flags0/lease0全部守卫；新epoch3区分试步。100ms租约、每段读回、finally STOP保持。主机语法、默认仅计划、两段各2秒/4秒总时长、目标1500/1490、缺确认和非板端拒绝及源检查通过，随后板测通过。身份非ENROLLING/SAMPLING守卫保持，不停止语音来强求GUI空闲。

相机106060、现场handsfree/resume GUI141059前后active/PID不变，检测48005→48073、约9.93Hz，身份ready，无相机/检测错误；未修改业务源码/配置、重启服务、切位流或改变HDMI/语音。实际执行时GUI IDLE/STOPPED、身份UNKNOWN，不称为播放并发验证。

用户随后说“重新测试，人嗯他反向转动”。此原话同时包含重测要求和“反向”观察，但尚不清楚指本次校准反转，还是人移动与镜头方向相反。已询问含义，并说明这次是固定位置台架校准，自动跟随未启动。保持输出关闭，尚未执行额外重测，不将该话直接当居中或跟人方向标定。

用户先前“更偏右了”的输入在 `field-input.json`，最新重测原话在 `retest-request.json`；计划/主机保护和实际执行源在本目录，完整ACK及独立最终状态在 `evidence/`，自有执行/只读导出工具在audit。板端事务 `/home/root/aura-pan-follow-20261020/midpoint-step-03` 独占创建，不重跑已完成事务。原始UART、图像和身份库不共享；[长度/SHA清单](verification.json)只验证冻结工件，现场位置/方向和完整跟随仍未验收。
