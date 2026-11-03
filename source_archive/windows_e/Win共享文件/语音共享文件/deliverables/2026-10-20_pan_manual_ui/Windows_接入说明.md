# Windows后续更新保留手动调轴入口

当前KV260界面仍使用voice-barge-in/candidate-667b70d586ca/runtime/aura，原GTK及230项组件未修改。Ubuntu新增5份源码/测试文件、config/pan_manual.local.json及独立启动drop-in；相机入口/身份库/语音打断均保持。当前系统单元WorkingDirectory仍是原runtime，ExecStart通过 `/etc/systemd/system/aura-avatar-ui.service.d/80-aura-pan-manual-20261020.conf` 指向 `/home/root/aura-pan-manual-ui-20261020/staged-v1/startup/launcher.py` 和同目录config.json。

后续Windows发布请保留 `board/motion/manual.py`、`board/motion/manual_vsrv.py`、`tools/pan_controls.py`、`tools/board_avatar_pan.py`、`tests/framework/test_manual_pan.py`。共享打包器新增 `--manual-pan`，将manifest入口设为可选wrapper，同时收集附加模块和文档。原GTK不需要改写；wrapper只扩展“视觉追踪”的第四个操作入口、手动调节窗口及公开状态。完整打包的972项收集已检查，但本轮没有复制整包或替换原230项组件。

本板接口配置不自动装入可移植包，须从实板核验新boot/FDT、配套驱动和联合固件后建立，不复制旧boot许可到另一台板卡。新版本切换runtime时也需要独立校验配置，不允许通过改guard绕过平台身份。不要改写身份数据库，不为此启动第二个相机或DPU进程。

新的启动配置恢复用户既有的HDMI关闭2秒要求，并沿用原同boot标记；后续语音或身份升级须保留。窗口关闭会停止手动动作；该wrapper运行时独占Native运动锁，原台架脚本不应并行执行。中位由用户调好后告知Ubuntu再确认，当前没有自动保存中位或启动跟随。

如需回退，只移除本轮自己的80-aura-pan-manual-20261020.conf后daemon-reload，并在界面空闲时重启aura-avatar-ui.service；原systemd单元、原startup/config.json和launcher.py都保留。先检查是否已有更新版本，不能移除别的drop-in或回灌旧GUI。回退后不再有手动按钮，原视觉/语音入口按原配置运行。双方继续分别填写自己的回执，本轮未改Windows回执。
