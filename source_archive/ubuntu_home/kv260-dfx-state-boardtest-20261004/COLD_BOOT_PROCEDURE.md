# 本轮断电冷启动操作与证据

用户于 2026-10-04 明确要求开始断电冷启动。已在原 boot ID `a7733edd-db41-4527-b8fb-cefdcbfe7b3a` 下，核对同一备用卡、持久化 20 配置、候选哈希和原 26 项文件，正常卸载官方应用，确认实际 overlay/render 已移除，停止 manager 并执行 `systemctl --no-block poweroff`。

主机于 `2026-10-04T08:27:11.393822+00:00` 确认串口内核 `reboot: Power down`，安全关机成功。串口 echo 已在关机前恢复。

[安全关机证据](/home/ghmd/kv260-dfx-state-boardtest-20261004/evidence/20261004T082705.497631Z-19-safe-shutdown/status.json) 和该目录 `serial.raw`、`prepare-coldboot.output` 保存全过程；没有直接拔电或强制复位。

用户操作：保持 USB UART 连接，拔板卡电源插头，等 10 秒后重新插回，等待自动启动并确认完成。`watch_coldboot.py` 已在动作前启动，仅读串口、发送 0 字节，避免在 U-Boot 倒计时中输入回车。物理断电是否完成以用户确认和新启动证据分别记录，不能只凭 boot ID 改变推断冷启动。

新启动后运行板端 `validate_v5.py postboot`，再将完整新证据传回主机并使用 `review_board_evidence.py ... postboot` 独立核对。核对项目包括同一 CID、新 boot ID、已修复 ZOCL、持久化 20 配置的实际程序/依赖、官方默认加载、5 个监听、DPU query、原模型原图 Top-5、原 26 项哈希、FAT/boot 挂载及完整启动日志。

## 实际结果

用户确认“已重新上电”。该确认按此前物理操作说明记录在 `POWER_CYCLE_CONFIRMATION.json`，没有将用户消息时间或实际断电时长伪造为测量值。

仅读采集器捕获新 U-Boot/Linux、root 自动登录和提示符，52410 字节，UART 输入 0 字节。[被动启动证据](/home/ghmd/kv260-dfx-state-boardtest-20261004/evidence/20261004T083113.097618Z-coldboot-observation/status.json) 与原始 `serial.raw` 保留。

板端 postboot 验收通过，取得新 boot ID `01ca88c1-93b6-414f-9646-774482d4b2f0`。新 manager PID 999 自动启动；ZOCL 实际装载完成于 13.214874 秒，manager 实际启动于 14.038433 秒。默认官方 DPU、原图完整 Top-5、原 26 项哈希、5 个监听和 boot 挂载通过。

完整回读归档 5223 文件及累计 23 次有效阶段分类经主机独立核对通过；[冷启动验证](/home/ghmd/kv260-dfx-state-boardtest-20261004/reviews/20261004T084536.786164Z-postboot/COLD_BOOT_VERIFICATION.json) 单独关联安全关机、用户确认、仅读串口、boot ID 和实际功能结果。NFS/TPM/clock/overlay 等已有告警仍保留，见 [最终板端报告](BOARD_REPAIR_REPORT.md)。
