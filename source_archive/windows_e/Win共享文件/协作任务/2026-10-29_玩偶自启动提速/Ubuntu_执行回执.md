# Ubuntu 执行回执：玩偶开机自启动提速

UTC 2026-10-30 02:08 安装前复核：KV260 当前 boot `605eaf50-c66a-4559-bfc9-5ae177e0f305`；界面服务 MainPID `1296`，GTK 子进程 `1477`，均正在运行。活动配置 SHA `12af1146…`，活动启动器是项目已知旧版 `cd168022…`。实测日志显示 GTK 子进程约在开机 45.4 秒后启动，GUI API 约在 90.8 秒就绪，显示配置阶段 26.182 秒。

我从实际板端配置复制出独立候选，未覆盖共享主源码或现役 GUI。候选采用已知修正的启动器状态处理，并在安全显示模式可用后提前启动 GTK；原显示等待/稳定/恢复值保留，systemd `READY` 仍等待显示与 GUI 两项都完成。

板端部署结果：新目录 `/home/root/aura-avatar-startup-speed-20261029/` 的 3 个文件 SHA 核对通过，板端启动器 `--preflight` 通过，279 项当前 GUI 组件检查通过。添加唯一高优先级 drop-in 并 `daemon-reload` 后，systemd 有效 ExecStart 指向新候选，drop-in 排在现有条目之后；服务保持 active，MainPID `1296` 与 GTK PID `1477` 未变。没有重启服务、相机或整板。

部署脚本第一次收尾时本地 UART 原始证据文件已关闭，`UART.close()` 报 `write to closed file`，因此该次没有回显恢复确认。随即用现有只读 UART 包装器重新连接，成功读回服务/文件/进程状态并确认 `console_echo_restored=true`。安装本身的板端回执为 `complete=true`；完整原始传输保留在私有工作目录，未放入共享目录。

本次只完成“下一次启动入口”部署。没有重启验证，启动提速、屏幕实际首帧和触控仍待下次自然开机核验。Windows 接收与回执尚未确认。
