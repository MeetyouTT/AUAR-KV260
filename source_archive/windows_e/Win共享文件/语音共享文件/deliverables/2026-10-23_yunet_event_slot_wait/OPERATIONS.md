# 当前运行与回退

当前boot `7924ac9f-311d-4fcd-98be-57bf023cf1aa`。camera unit SHA `048ee59cf4f01d84f0442825926b38ae0940e3c566a005449385d34536734e2f`，camera PID298571、GUI监督298601、Xserver1077。release：

`/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-slot-wait-81e6463c3747-298300`

恢复策略、slot notification与独立取消token开启；延迟注入入口不在正式unit。YuNet source TTL1000ms，DPU optional硬占用30ms/YOLO guard5ms，YOLO优先。音频与Windows旧SFace配置保持。

只读检查：

```bash
/usr/bin/python3 -B /home/root/aura-dpu-vision-20261021/postpower-retry-live/release-slot-wait-81e6463c3747-298300/restore_previous.py --check
```

明确回退：

```bash
/usr/bin/python3 -B /home/root/aura-dpu-vision-20261021/postpower-retry-live/release-slot-wait-81e6463c3747-298300/restore_previous.py --restore
```

入口核对当前boot、unit/config/源码/偏好、UI空闲与源版本；建立独立restore timer；停止原GUI并等待USB音频PCM关闭后恢复上一release和unit，然后重启GUI并确认IDLE_READY。上一release为`/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-bounded-61abe4391d3a-251478`，unit SHA `e893930d…`。如boot或用户配置已变化，必须按入口错误提示重新审核，不绕过校验。

首次纯通知候选产生大量状态锁busy撤回和freshness gaps，已被拒绝；受保护地恢复过渡版本后，独立取消信号修正版再上板并接受。曾有一轮父GUI启动后ready等待超时，controller按该流程拥有状态协调停止GUI、关闭PCM并恢复父版，之后重新预检才接受本版。所有trial controller和restore timer均inactive；当前新版CU stats disabled。
