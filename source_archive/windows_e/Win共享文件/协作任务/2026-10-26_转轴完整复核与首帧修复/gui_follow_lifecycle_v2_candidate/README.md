# GUI随动子进程生命周期修复候选

本候选直接取自实板读回并验SHA的258-pin GUI，而不是历史host副本。原`tools/face_pan_controls.py` SHA：`9374b8d37e60c967aa3b248f9540ce511aa7d5b0b8cc2e56e2d88ac0451adb55`。取回证据：`aura-pan-board-20261024/uart/20261026T125456.403868Z-unattended-pinned-follow-gui-source/response.json`。

## 已复现的缺口

Popen成功后，`communicate()`抛出非TimeoutExpired异常时，原GUI只记录FAILED，然后清掉child句柄并尝试重建manual backend。真实类的内存fake复现显示：旧child仍alive、没有SIGTERM/kill，但GUI runningFalse且childNone。独占flock阻止第二个MMIO owner，却不能停止仍存活的第一个跟随进程。这是独立软件反例，不是已经证明本轮实体顿挫由此造成。

## 改动

- `follow_process_cleanup.py`是纯进程清理helper：poll确认自然退出，否则SIGTERM＋wait最多2秒；必要时kill＋wait最多2秒。使用wait而不是依赖可能已坏的stdout/stderr communicate。只有实际poll/wait得到整数returncode才视为退出已确认。
- `face_pan_controls.py`的所有Popen后退出路径都先调用上述清理。旧child退出已确认，才清句柄、重建manual backend并按原配置恢复manual符号。
- 如果终止或wait无法确认退出，保留child句柄、running=True与STOP入口，界面显示停止尚未确认，不创建第二个manual owner。只有原worker已结束、没有清理线程运行时，后续stop/close才能启动一个受锁保护的清理重试；原worker尚活着时只发停止信号，防止两个reaper同时重建manual。
- 清理期间暂停读取旧运行报告，避免覆盖原始communicate异常。主异常、进程清理错误、manual恢复错误分别保留；线程启动失败不会制造runningFalse但仍有未跟踪child的状态。

未改变manual范围、自动方向、左右人脸边界、GUI布局/视频行为、跟随控制器、输入源或`follow_readback.py`。后者实板SHA仍为`a4a0a5d5d0430a1670a989d94d9e206216f03d51558d983a8d61429a96bfb52b`。

## 验证与部署边界

`python3 -B -m unittest discover -s /home/ghmd/aura-pan-follow-shadow-20261024/gui_follow_lifecycle_v2_candidate -p 'test_*.py'`

22项本地主机行为检查通过：正常退出、用户STOP、communicate OSError/其他异常、SIGTERM失败、kill升级、wait失败、退出未确认保留owner/STOP、stop/close重试、不创建第二owner、主异常不被清理/恢复/状态刷新覆盖、符号保持、线程启动失败，以及一个无关本地sleep子进程的真实终止与wait回收。新增Event并发回归把原worker卡在except已标记pending、finally尚未开始实际清理的位置，连续STOP不得启动第二reaper；该回归在补存活检查前实际失败，补后通过。未访问板卡、相机、模型或MMIO。

候选需由主端分别安装到GUI运行目录的`tools/face_pan_controls.py`和`tools/follow_process_cleanup.py`，更新组件pins并正常重启GUI；本目录不修改现役服务或部署manifest。`HOST_GUI_LIFECYCLE_VALIDATION.json`记录候选指纹与静态UI不变检查。
