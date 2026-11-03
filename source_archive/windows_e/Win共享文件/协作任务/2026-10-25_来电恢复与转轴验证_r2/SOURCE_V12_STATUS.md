# r7实体观察未通过，输入链路v12已接入

UTC2026-10-26 04:41～04:51。用户要求重新测试后反馈“转轴为什么不动”。这轮25.472秒真实记录：12 ACK、10次目标变化、41次ARM，采样脉宽1448..1451µs。左右都收到有效越线输入；不能用当前在区内否定此前越线后看不到转动的反馈。如此小的命令变化和频繁启停不足以证明实体跟随，用户“没动”作为验收未通过保留；不根据无仪器观察推断精确角度/舵机死区。

新增face-source-v12，减少共享锁耦合：FaceTargetService使用独立RLock，原offer/检测/质量/准入/时效/回调均保留；人脸观测仅在相机锁内读取元数据，释放相机锁后再取flow与face快照，在取得face锁后重新读取时钟检查截止。原250ms图像、500ms实检测锚与运动层20ms余量不变，未更换成身体或预测。

39项软件回归通过：原35项固定锚/边缘/丢脸等检查＋4项锁/时效检查，含真实FaceTargetService在另一个线程持相机锁时仍可offer。初次误用系统python缺cv2，未执行有效测试；改用原有identity虚拟环境后39项0失败，不安装依赖或据此冒充实板效果。7个运行pins通过，新manifest SHA d69a4572837937cc4104561d2f97bc3d24a80f71f5efe9e551a41995372814bf。

先GUI pan_stop并验证STOP/lease0/READY，正常停止camera13537，fresh checkpoint d4982e075f9b7cb411d8cd439cec269a7ccb8367f576ac353d92b8125434cc5b（同boot/exact PID/birth/quiescent/pending0/ZOCL0）通过后切owned v12入口。新camera189651、GUI137253未重启；VSRV固件/FDT和r7参数未换。原native保护历史承接，恢复后primary累计4（此前最新核查2，增量2明确保留），YuNet/SFace超限仍0/0，owner未fence、identity ready。身份正确率和新增锁分离长稳未复验。没有清预算/自动kill/自动回1420；最后恢复时指令1453µs，继续r7持续联动。

新consumer运行20.431s：36 READY均在线内、558 UNCONFIRMED/7 EXPIRED，0ARM/ACK、1453保持、fatal=false，不能称输入连续性已修好。两次15点短窗均UNCONFIRMED，GET中位18.91/17.66ms；旧有脸短窗中位45.98ms，但姿态与有效脸比例不同，不能当作同输入性能提升。完整平顺实体随动仍未通过。

私有现场预览已检查：蓝色人脸框与脸中心在两线之间，大绿色框属于身体；当前这种位置应保持不动，按身体越线不会触发。蓝框曾READY，但低头时确认间断仍有。截图仅在本机private UART证据目录，未复制共享、未做身份识别。视频raw-local/frame_visible=true/update_hz10，无预览error。

[过滤迁移与测试结果](SOURCE_V12_MIGRATION_VERIFICATION.json)、[短窗时序范围](SOURCE_V12_VISIBLE_TIMING.json)、[8文件源码/测试快照](face_source_v12/)。Windows回执未代填。现保持联动监测，用户需要按蓝色人脸框/中心点越线观察；旧“运行中”只表程序状态。
