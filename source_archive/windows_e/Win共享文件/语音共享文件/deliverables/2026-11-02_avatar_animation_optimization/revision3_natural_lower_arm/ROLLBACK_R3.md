# R3回退

本轮原字节位于 board_results/backup：tools/libaura_yuki.so、config/yuki_pair.formal.json、tools/formal_yuki.py、config/board_avatar_gtk.json 和 startup.json。对应前版为 R2/startup3faab0eb…，不是更早的原始角色包。

当前维护者先取得新的明确设备交接，现读boot、startup、完整380来源、GUI/GTK及相机寿命、播放/录音/跟随与实际监听偏好。实际空闲后沿原保护流程正常停止GUI（本次唯一临时KillMode=process/SendSIGKILL=no/TimeoutStopSec=infinity），核实进程寿命结束并恢复原unit属性。确认停稳、相机owner未变且源仍精确为R3后，以CAS成套恢复上述4组件及startup原字节，重核380项，再核对原8797健康并构造新的正常GUI启动事务，恢复实际接手偏好。

板端 publish_r3.py --rollback 包含停稳条件及逐文件CAS核对，可由取得新授权的维护者审阅后使用；R3生命周期的已封存one-shot、旧PID与旧handoff不能直接重放。后续若有其它业务发布，先合并其增量，避免旧startup覆盖新内容。R2更早的回退材料仍在原R2交付包中。此说明不自动执行设备动作。
