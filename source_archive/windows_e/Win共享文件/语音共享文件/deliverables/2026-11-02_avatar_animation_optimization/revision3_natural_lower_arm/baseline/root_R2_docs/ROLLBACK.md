# R2 回退到本轮原版

回退单位是四个组件与原 startup 配置，原字节已在正常停止 GUI 后留存。本说明不自动提交任何设备操作。

| 文件 | 原件 |
|---|---|
| tools/libaura_yuki.so | board_results/backup/tools/libaura_yuki.so |
| config/yuki_pair.formal.json | board_results/backup/config/yuki_pair.formal.json |
| tools/formal_yuki.py | board_results/backup/tools/formal_yuki.py |
| config/board_avatar_gtk.json | board_results/backup/config/board_avatar_gtk.json |
| startup/config.json | board_results/backup/startup.json |

1. 由当前维护者先取得明确设备交接，现读 boot、startup、GUI/GTK 和相机的 PID/birth/命令哈希，以及播放/录音/跟随状态。核对 R2 完整 380 项来源与 release/MANIFEST.json，留存当前监听偏好。原接手或本次 PID 都不能当作未来固定值。
2. 在实际空闲、暂停监听且无自动跟随时，沿原正常 GUI 停止流程，使用 KillMode=process、SendSIGKILL=no、TimeoutStopSec=infinity 的本次唯一临时保护；只提交一次正常 stop，等待 supervisor 与 GTK 原寿命结束。结束后移除本次保护并恢复原 unit 属性。相机保持运行。
3. 确认 GUI 为 inactive/dead/MainPID0、无 Job，原相机 owner 未变，原监听偏好已保存。任务板端目录的 publish_animation.py --rollback 可在这些严格条件下以 CAS 恢复原四项及 startup 原字节；它还会检查当前 R2 哈希和其余376项。完整恢复后必须再次核对380项。
4. 核对原 Windows8797健康及原启动依赖，按新鲜来源创建新的单次正常 GUI 启动事务。实读 READY、角色可见、swap计数增长及故障0，恢复步骤1实际读取的监听偏好。
5. 本轮 gui_maintenance.py/start_after_model_recovery.py 是封存的单次事务，绑定本轮 owner/intent，保留作流程证据；未来回退由维护者用新事实构造事务，不能重放历史 one-shot 或只替换旧PID来绕过检查。模型、库、摄像头、平台和转轴都不属于动画回退内容。

板端备份亦保留在 STATUS.json 对应发布 stage 的 backup/。当前原版 startup SHA 为 c3861fa3d2cbb10fee424804f7b3932eadd576819a2a6290c7ca406d900b9602，原库 SHA 为 b2432e75a75e4dbdebee8e89a141a68ba00671c33b2b258b81ce16794b2c73d2。若在本轮后已有其他发布，先合并这些后续增量并重新核验，不覆盖别人的新版本。
