# 手动调轴修复后入口

本轮修复前一版右转后ACK保护锁定。后续Windows更新请保留7份运行/测试文件：board/motion/manual.py、manual_vsrv.py、manual_process.py，tools/board_avatar_pan.py、pan_controls.py，以及tests/framework/test_manual_pan.py、test_manual_pan_process.py。manual_process必须随包携带，wrapper已改为独立spawn进程，不再在GTK解释器内续租。

共享打包器--manual-pan入口保留，974载荷收集包含新增进程模块和测试，不包含本板local许可配置。原GTK、相机、身份、语音打断等230项核心文件不覆盖；板端只更新前轮附加模块、加入进程模块/测试，并切换独立startup manifest。实际运行路径以部署结果及最新Ubuntu回执为准，勿回灌旧shared GTK。

重新连接仅重建经平台核验的进程，不重放旧动作；100ms租约、有限2秒、1400～1600范围和ACK/STOP监督保持。需要显式新点击才会再次动作。中位仍由用户给出现场正前方读数后单独确认。GUI退出时子进程关闭Native；异常退出依靠独立硬件租约停止，不能以UI心跳无限续期。

原staged-v1的manifest与冻结43份交付保留为历史；修复版启动器/配置在fix-v2/startup，自己的80-aura-pan-manual-20261020.conf指向该入口。回退须同时恢复本轮backup里的旧附加文件和drop-in，再daemon-reload并在空闲时重启界面；不能仅改回旧manifest而保留新源码，否则SHA门槛会拒绝启动。不要动原GTK/身份库或别的drop-in，HDMI2秒设置保持。Windows回执由Windows端自行填写。
