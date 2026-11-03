# 临时EDID恢复对照候选（2026-10-29 UTC）

**最新实测结论：该候选未恢复用户看到的花屏，已经自动回退，不得接入开机流程。** [真实试验、回退及物理重插恢复](../evidence/edid_trial_result_20261029.json)：新boot3336afd3、GUI1296/X1077/camera1333保持，覆盖读回128字节且原时序重建通过，用户反馈仍花屏；180秒定时器实际清除覆盖、恢复600秒策略并正常退出。用户随后只重插HDMI恢复，覆盖仍为空，真实sysfs EDID128。

后续手动重复清理在停止已被回收的timer时误报失败，独立检查确认实际回退此前成功。保留原v1作为已执行证据；[v2工具修正](edid_trial_v2.py)及[13项检查](validation_v2.json)改为容忍已消失timer、完成后重复回退不再重写显示策略，并修正DPMS停用时xset缺少Monitor行被记false的读数语义。v2仅本地验证、未上板，也不改变本次显示恢复失败结论。下文为试验前的设计与执行方法，不能按早期“尚未执行”描述判断最新状态。

状态：10项本机检查通过，已上板并完成默认只读检查，**尚未执行EDID覆盖或实屏修复验收**。它用于验证“已有正确时序但物理EDID读取为空”时，临时注入同屏识别数据并重建输出是否能代替手动重插。成功也须进一步做真实冷启动复测，不能直接写成永久修复。

当前板端冻结入口：`/home/root/aura-post-power-20261022/helpers/bd572c83085cf336/source.py`，源码SHA256 `bd572c83085cf336d73c5859d37201c20f7058a92155cf0d734a2dbbdcc965ab`。传输/只读结果见[manifest.json](manifest.json)。默认运行只读取，返回`inspect_only`、`mutations=0`。

## 执行条件与动作

1. 先由用户确认当前仍花屏/黑闪，并保存故障快照。每次使用刚读取的新boot、GUI PID和Xserver PID；不要复制上一启动的值。
2. 候选要求EDID为空、没有既有覆盖、连接器force未强制、原49MHz/1024×600时序活动、显示处于On，界面空闲且监听/跟随关闭。正常EDID128、休眠、其他覆盖或进程变化均拒绝。
3. 先创建本轮事务记录及180秒回退定时器，才暂停本次运行时的自动休眠/屏保、写入已核验的128字节EDID并重新探测。随后只做一次输出关闭2秒→恢复原1024×600；显示命令超时15秒，覆盖已知驱动5秒等待。
4. 输出报告必须标明EDID来自注入而非重新物理读取，`physical_panel_verified=false`。由用户观察真实画面是否恢复、是否动态刷新。
5. 手动完成或180秒到期后，回退本事务持有的EDID并恢复原时序/休眠策略。其他调用者已修改覆盖时拒绝覆盖其数据；Xserver换代时不向新Xserver写原策略。中途失败走同一回退路径。不会改持久开机配置、刷新固件、重启业务或发送运动命令。

激活命令中的值必须来自本轮实测：

```text
python3 -B /home/root/aura-post-power-20261022/helpers/bd572c83085cf336/source.py --apply --expected-boot NEW_BOOT_UUID --expected-gui CURRENT_GUI_PID --expected-x CURRENT_XSERVER_PID
```

回退使用激活返回的精确事务目录：

```text
python3 -B /home/root/aura-post-power-20261022/helpers/bd572c83085cf336/source.py --restore RETURNED_TRANSACTION_DIRECTORY
```

禁止把`--apply`加入开机流程，禁止在已被物理拔插恢复的正常画面上声称完成故障修复试验。当前已验证的是软件门槛、回退模拟和板端读取，**真实覆盖、定时器回退及面板恢复尚待本轮验证**。

## 验证与数据来源

[edid_trial.py](edid_trial.py)与[test_edid_trial.py](test_edid_trial.py)对应10项测试：[日志](edid_trial_validation_20261029.log)。覆盖实测EDID字节及SHA、错误数据、启动/PID错配、正常/休眠/繁忙/已有覆盖拒绝、第三方覆盖保护、新boot不写入、切换中断回退以及正常结束回退。执行`python3 -B -m unittest -v test_edid_trial.py`，无需连接硬件。

[原始EDID](screen_verified_727d3e18.edid)来自该屏正常快照，128字节、校验和正确、SHA727d3e18…；最初手录字面量偏差已被测试拦下，最终按此文件生成并复测通过，错误数据没有上板使用。

接口依据为已检查的5.15对应源码：[debugfs EDID写入/reset](https://raw.githubusercontent.com/Xilinx/linux-xlnx/xlnx_rebase_v5.15_LTS_2022.2/drivers/gpu/drm/drm_debugfs.c)、[connector detect](https://raw.githubusercontent.com/Xilinx/linux-xlnx/xlnx_rebase_v5.15_LTS_2022.2/drivers/gpu/drm/drm_sysfs.c)。软件注入不能等同于真实下游HDMI物理重连接；若实屏仍失败，保留失败并回退，不能只凭注入后128字节判通过。
