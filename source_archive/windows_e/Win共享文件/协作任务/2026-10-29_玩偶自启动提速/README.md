# 玩偶开机自启动提速

**状态：提速版已设为下一次启动入口；本轮未重启服务或整板，冷启动提速尚待实测。**

## 实测基线

只读读取 KV260 当前 boot `605eaf50-c66a-4559-bfc9-5ae177e0f305` 的 systemd 日志和本次启动记录：AURA 界面服务在开机后约 17.9 秒进入启动，GTK 子进程约 45.4 秒才启动，GUI API 在约 90.8 秒就绪；显示配置阶段耗时 26.182 秒。显示最终使用已固定的 `DP-1 1024x600` 与当前屏 EDID，显示重建为 true。**这些是软件启动记录，不是实屏首帧光学计时。**完整过滤记录见 [启动基线](evidence/startup_baseline.json)。

现役启动配置为 15 秒 EDID 宽限、3 秒身份稳定、2 秒输出恢复；当前共享缓存含 279 项、约 2.05 MB。活动启动器的哈希为旧版 `cd168022…`，项目已有修正版 `ea68cb07…`，用于避免显示输出关闭失败后被误记为成功。本候选以修正版为基础。

## 提速改动

候选启动器在显示身份已匹配且精确目标模式已经生效时，立即开始 GTK 初始化；若 EDID 尚未出现，则只有当连接状态、当前模式、原先实测 Modeline 和指定触摸设备均匹配时才允许提前初始化。完整 EDID 宽限、显示稳定等待和每 boot 一次输出恢复仍继续执行。systemd 只有在 GUI API 和显示设置都完成后才收到 `READY`。

板端预检通过后，新增独立目录 `/home/root/aura-avatar-startup-speed-20261029/`，并添加排在现有 drop-in 之后的单元覆盖。`daemon-reload` 已完成；当前监督 PID `1296`、玩偶 PID `1477` 与服务 active 状态保持，**没有重启界面、相机或整板**。配套源码、原配置、覆盖文件和 SHA 清单见 [candidate](candidate/) 与 [发布清单](release_manifest.json)。

## 验证与限制

- 启动器和部署器语法检查通过；远端命令编译及长度检查通过。
- 板端 `--preflight` 通过，核对当前 GUI 和 279 个组件；三个候选文件 SHA 与清单一致。
- 只读回读确认新 ExecStart 生效于下一次启动、drop-in 位于最后、服务仍 active、当前 GUI PID 未变化。
- 部署工具首次收尾时因本机证据文件先关闭，UART `close()` 无法记录回显确认；没有重试部署。随后使用原有 UART 包装器做只读复核，确认控制台回显已恢复，且服务 PID、玩偶 PID 与新 drop-in 均正确。两份过程记录留在 Ubuntu 工作目录 `/home/ghmd/aura-avatar-startup-speed-20261029/evidence/` 和 `/home/ghmd/aura-pan-wide-resume-20261029/startup_speed_verify_after_install.status.json`；共享目录只放过滤后的结果，没有原始 UART 或 API 私人状态。
- 没有运行测试套件或重启服务。新启动时序、实际省下的时间、实屏显示和触控仍未验证；不预报未经实测的提速秒数。

## 回退

回退只需先核对 drop-in 哈希为 `48b46dace7d5d280c06bf2fe1559b4040366ee8770c611b707b028452704295f`，再移除本任务新建的 drop-in 并执行 `systemctl daemon-reload`。这会让下一次启动恢复原入口，不影响当前已运行的界面。若下次启动服务进入 failed，再执行 `systemctl reset-failed aura-avatar-ui.service` 后启动服务。

Ubuntu 执行记录见 [Ubuntu 回执](Ubuntu_执行回执.md)。Windows 同步/接收及回执尚未确认。
