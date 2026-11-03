# 当前GUI运行与回退

接受版目录`/home/root/aura-video-cpu-20261023/66cde810eb059dce`，当前boot `7924ac9f-311d-4fcd-98be-57bf023cf1aa`。相机499773/unit29786434…、GUI监督535987、Xserver1077是本次核验时点；以后以服务和health实际PID为准。

GUI入口`startup/launcher.py --config startup/config.json`，runtime为同目录下`runtime`。新override：

`/etc/systemd/system/aura-avatar-ui.service.d/zzzzzzzzzzzzz-aura-video-66cde810eb059dce.conf`

只读核对已实际通过：

```bash
/usr/bin/python3 -B /home/root/aura-video-cpu-20261023/66cde810eb059dce/restore_previous.py --check
```

需要恢复前一GUI时：

```bash
/usr/bin/python3 -B /home/root/aura-video-cpu-20261023/66cde810eb059dce/restore_previous.py --restore
```

该入口要求自然空闲、无录放音/开麦/运动，检查boot、源码/config/身份库哈希、dropin集合和偏好；先arm独立恢复timer，再关GUI、确认PCM closed，仅移除本轮override并恢复原GUI/runtime及原页面。相机PID/unit、现有YuNet锁定和计数保持。恢复完核对argv和服务，再停timer。默认或`--check`不执行恢复；`--guard`属于timer内部路径。

当前GUI之前的完整相机回退入口绑定较早dropin集合。需要完整相机回退时，先通过上面的GUI入口恢复前一GUI，再重新核对相机回退流程；不要删其它override或绕过SHA/boot保护。新boot、源码、偏好或其它服务变更后，旧helper可能拒绝，需要重新审查当前状态。

本轮曾因验收失败实际恢复上一GUI，当前已接受版没有再次手动撤销；当前手动入口仅只读核对。两个试运行controller和各自timer均已结束；有界恢复与30ms/5ms保护没有被修改。

离线测试可在本交付根目录运行（标准库，无板卡依赖）：

```bash
python3 -B -m unittest discover -s tests -p test_preview_lifecycle.py -v
python3 -B -m unittest discover -s tests -p test_trial_review.py -v
```

`real_gtk_helper.py`、`activate_gui.py`绑定旧PID、boot和一次性报告，不应直接重放。若要新一轮板测，先核对当前版本并生成新的受保护试运行。
