# R4成套回退

本轮精确前版是 R3/startup31d379389…。原字节保存在 board_results/backup：tools/libaura_yuki.so、tools/native_yuki.py、config/yuki_pair.formal.json、tools/formal_yuki.py、config/board_avatar_gtk.json，以及 startup.json。

后续维护者取得新的明确交接后，先核验实际boot、startup、完整组件、GUI/GTK及相机进程寿命和实际偏好。空闲时沿正常GUI停稳与属性恢复流程，以逐文件CAS成套恢复五组件和startup，再重核来源、正常启动和就绪。R4已封存的stop/start意图、旧PID与handoff不得重放。

若声纹等后续版本已经发布，应先合并其组件映射与改动，避免旧startup覆盖新业务。publish_r4.py --rollback只适用于其严格来源条件；本说明不自动执行回退。R3更早材料仍保留于原R3目录。
