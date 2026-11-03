# 玩偶开机自启动提速

依据 `/home/ghmd/Win共享文件/后续任务_先读这里.md`、当前 AURA 共享任务、最新板端启动证据和项目启动器记录，针对用户提出的“玩偶自启动太慢”处理。

## 实测基线

只读读取 KV260 当前 boot `605eaf50-c66a-4559-bfc9-5ae177e0f305`。`aura-avatar-ui.service` 在开机后约 17.9 秒运行，GTK 子进程约 45.4 秒启动，GUI API 约 90.8 秒就绪；`configure_display` 阶段耗时 26.182 秒。活动配置 SHA `12af1146…`，显示等待为 EDID 15 秒、身份稳定 3 秒、输出关闭 2 秒。实际输出 `DP-1` 为 `1024x600`，setup 使用 live EDID；这不代表实屏光学首帧已测。

当前实际启动器 SHA `cd168022…`，项目已有修正版 `ea68cb07…`，用于避免输出关闭失败后把重建错误地报为成功。只读核验发现服务 active、MainPID1296、GUI1477。

## 改动与部署

基于修正版构建独立候选：当屏幕 EDID/身份与精确目标模式匹配，或 EDID 未到但输出连接、已验证 Modeline、触摸设备均匹配时，提前启动 GTK 初始化；原显示宽限、稳定等待和开机输出恢复继续并行。systemd 仍需等待 GUI API 和完整显示设置后才报告 READY。

板端 `/home/root/aura-avatar-startup-speed-20261029/` 已保存 launcher/config/drop-in，三个文件 SHA 匹配，板端 `--preflight` 与 279 项组件检查通过。已添加排序在 27 个现有 drop-in 之后的唯一覆盖，并 `daemon-reload`。复核确认新的有效 ExecStart、服务仍 active、MainPID1296 和 GUI1477 不变。没有服务重启或整板重启，因此此提速尚未有下一 boot 实测。

第一次部署脚本收尾的 UART 原始文件句柄顺序错误，导致本机记录显示 `UART.close()` 写文件失败。板端写入和 `daemon-reload` 已成功；随后通过原有 UART 包装器再次只读读取，确认服务、PID、候选哈希正确且 `console_echo_restored=true`。失败回执和补充复核均保留于 `/home/ghmd/aura-avatar-startup-speed-20261029/evidence/` 与 `/home/ghmd/aura-pan-wide-resume-20261029/`。

跨机报告与 Ubuntu 回执：`/home/ghmd/Win共享文件/协作任务/2026-10-29_玩偶自启动提速/`。当前 project handoff 已更新；Windows 同步/回执尚未确认。下次自然开机需比较系统启动、GTK 子进程、GUI API 和实际画面时刻；不能把软件 READY 当成屏幕首帧或实屏通过。
