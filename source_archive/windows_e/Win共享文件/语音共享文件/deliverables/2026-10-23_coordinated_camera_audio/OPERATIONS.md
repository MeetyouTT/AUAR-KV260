# 当前运行与回退

活动unit：`aura-camera-ui.service`，SHA `af337bce5d7f274b35cb79046078220ca6e3fbdbdcdb1d62570e106289dc6f7b`。

活动目录：

```text
/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-recovery50-946d1a0d500f-197870
```

879个包文件封装SHA `946d1a0d500f5f34dacbd2d7fd96025d0e53c0287f243922afbcc34ae2a90689`。实际源码9份已导出到`active_source/`，主机图表/CSV是已完成验证窗口，不是实时仪表盘。进程内1ms不等于OS时间片。

原camera unit和原目录完整保留，原unit SHA `84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c`。回退工具默认只读：

```bash
python3 -B /home/root/aura-dpu-vision-20261021/postpower-retry-live/release-recovery50-946d1a0d500f-197870/restore_original.py --check
```

需要回退且界面空闲时，显式执行：

```bash
python3 -B /home/root/aura-dpu-vision-20261021/postpower-retry-live/release-recovery50-946d1a0d500f-197870/restore_original.py --restore
```

`--check`已实板通过；为保留新版本，未对最终保留的版本执行这个手动`--restore`。其协调恢复协议已在多轮试验/失败启用时实际执行，手动入口另有3项软件检查。它先校验boot/源/config/偏好和自有unit，先arm独立恢复timer再关闭音频、恢复原camera，成功后停止timer；失败保留timer。旧库不迁移或删除。

工具绑定当前boot `7924ac9f-311d-4fcd-98be-57bf023cf1aa`，新boot或后来GUI/config更新会保护性拒绝，须先读取新实际状态再生成对应会话，不能强行绕过校验。正式运行入口已按boot UUID隔离日志，可用于后续启动，但真实冷启动尚未做现场验收。

后续升级/热重启相机时继续使用“空闲校验→关闭原音频并确认PCM closed→相机健康→恢复原音频”的顺序。旧写死unit `84116d8f…`的试验helper已不对应当前活动unit。Windows继续开发GUI/语音时保留本camera unit和当前runtime，回执与实板业务验收分开记录。
