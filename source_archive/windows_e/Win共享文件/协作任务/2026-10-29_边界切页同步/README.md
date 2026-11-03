# 视觉边界切页同步：已部署并通过板端窗口状态验证

用户反馈：视觉追踪切到玩偶交流时，两条边界不能随页面同时消失，会滞留一段时间。

UTC2026-10-29 完成修复。原边界由独立 `aura-face-zone-editor.service` 的 GTK popup 绘制，每0.5秒读取一次主界面页面，HTTP失败时还保留旧的显示状态；因此主界面切换和边界隐藏没有同步。

现在主界面离开视觉页前，通过本机 Unix socket 通知边界进程隐藏全部浮层，收到 GTK 隐藏及显示服务器同步后的回执，再切换页面。页面序号/进程代次用于丢弃过期消息；离开视觉页后的旧轮询回调也不能重新显示边界。返回视觉页会立即唤醒状态刷新。通知等待上限200ms，避免边界进程异常时无限阻塞导航；正常显示判断仍保留原轮询。

实际验证结果：

- 本机16项定向回归通过：既有几何、拖动保存、人脸时效检查，以及隐藏回执、过期回调、快速切页等检查。
- 实板连续4轮 `vision → main`，两个边界在切页命令返回后的 X11 状态均为 `unmapped`；再等0.65秒仍隐藏。
- 另做 `vision → main → vision → main` 快速切页，最终边界、中心线及提示均隐藏。
- 四轮隐藏回执分别为32.577、20.379、10.012、21.537ms。最终另一次回执12.611ms，边界进程应用耗时2.871ms，ACK无错误。
- 早期v1采用60ms等待时，有一次未及时收到回执，未判通过；v2增加耗时记录及200ms有界等待后完成上述验证。

当前部署：

| 项目 | 实测值 |
| --- | --- |
| boot | `55152f95-ea3a-4c6c-82e6-51bd553d96fd` |
| GUI | `/home/root/aura-boundary-nav-20261029/gui-page-sync-v2`，supervisor PID114923 / GTK PID114988 |
| 边界编辑器 | `/home/root/aura-boundary-nav-20261029/editor-page-sync-v2`，PID115144 |
| GUI启动配置SHA256 | `12af11467b3ca0c0a1e6b57ac203e887d658a9799a159e39dfa90dbff60037d4` |
| 相机 | PID21824保持，未重启 |
| 宽版范围 | 500..2500µs，manual READY，跟随关闭、flags0 |

保留原宽版和设备技能；原278个GUI组件中277个字节不变，只修改主界面切页文件并新增通知模块，现配置共279组件。边界编辑器另行更新，并对齐当前控制器的settings路径；左右边界、中央目标和viewport几何值已比对相同。未修改FPGA固件/模型/运动参数，未发送试转指令；回读的宽度、目标、参考及ACK序号均保持。测试结束恢复玩偶交流页 `main`。

文件与复现：

- [源码与定向测试](source/)、[两个原文件的补丁](changes.patch)、[源码指纹](SOURCE_PINS.json)。改动文件为 `board_avatar_gtk.py`、`face_zone_editor.py`，新增 `boundary_visibility.py`。
- [本机测试输出](evidence/host-tests-v2.log)、[实板原生窗口状态](evidence/live-verification.json)、[当前部署状态](evidence/board-state.json)、[最后隐藏回执](evidence/page-delivery.json)。原始UART、相机图像、音频和数据库没有放入共享目录。
- 本机复现：在 `source/` 下执行 `python3 -B -m unittest test_zone_editor_v5 test_boundary_visibility`。板端窗口验证脚本见 [live_verify.py](verification/live_verify.py)，只切UI页面和读取X11状态，不发送运动指令。

启动绑定通过各自systemd drop-in切到v2，原文件及旧运行目录保留。v2的drop-in路径和SHA见 `board-state.json`。回退原宽版前应停止GUI/边界进程，核验v2文件；另只读确认同任务后缀且ExecStart指向 `gui-page-sync-v1` / `editor-page-sync-v1` 的v1文件，再移除本任务的两代drop-in并reload/start，保留其他drop-in。只退v2会回到早期v1，不是原宽版。本轮未执行回退。

验证边界：已验证本boot板端GTK/X11窗口状态，尚无用户肉眼复测或屏幕光学计时，也未重新断电验收。板卡时钟未同步，证据时间以 `verified_host_utc` 为准。Windows同步/收件及业务验收未确认，Windows回执未代填。Ubuntu本地完整工作目录：`/home/ghmd/aura-boundary-nav-20261029`。
