# 断电收尾与恢复入口

本代理本次SSH于15:31:05 UTC在连接192.168.137.141:22时返回Permission denied，未建立会话；没有开UART或做板端动作。用户随后已向根代理确认Windows、Ubuntu、KV260全部断电，实际正常停机由根代理在全部证据落盘后执行。本文件不是关机完成回执；最终以父代理写入的结果为准。

父代理可先执行本目录 `shutdown_host_probe.py`：Windows `Get-Content -Raw` 经现有 `ssh.exe -T ... aura-ubuntu python3 -` 送入真实Ubuntu宿主。它只读共享路径、/proc相关进程和现有UART FD持有者，不打开UART；另查systemd-logind与DBus `CanPowerOff`。`yes/challenge/no/错误`以及不可读/proc范围须如实记录，不能据端口连接失败或TTY安静认定设备已停机。

现有独占UART实现位于Ubuntu `/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py`，封装器 `/home/ghmd/aura-board-ui-autostart-20261009/manage_startup.py`。根代理确认角色窗口结束、没有其它FD持有者、当前实际状态和日志都已保存后，已有 `UART.command('sync', 唯一marker, 20)` 可取得返回码与SHA帧；专门 `UART.poweroff()` 则先恢复console echo并确认 `UART_SHUTDOWN_ECHO_READY` 和prompt，再发正常 `systemctl --no-block poweroff`，最多等待120秒的 `reboot: Power down` 标记。关闭UART仍须保留/恢复宿主termios。只有命令被接收、无SSH回应或无prompt不足以等同Power down。

不要用普通 `run_uart.py` 或 `run_board_check.py` 将poweroff包装成“等下一prompt”的普通脚本。历史 `poweroff_for_coldboot.py` 和 `cold_boot.py` 固定旧boot、uEnv、相机PID及停服务/检查点步骤，不能整份重跑覆盖现役；本次只参考其UART方法。Ubuntu最终poweroff权限、systemctl/logind可用性和Windows正常关机同样由父代理核验并执行，本代理没有执行这些命令。

恢复第一步是先读本轮根README、shutdown_host_audit及父代理最终停机回执，确认两端和板卡实际启动状态。Ubuntu热点地址可能变化，先恢复现有SSH通道及共享目录，核对新boot、实际/proc入口与pending启动器、组件绑定、相机epoch、麦/跟随关闭和机械FAULT/null保护；不要从旧PID、旧boot或旧GUI路径直接接管。旧r3/286pins及13:00前公开样本报告是历史证据，不能替代这次新开机核验。

模型候选仍是独立目录，没有迁成生产；不恢复旧私库或跨端双写。LLM/Ollama权重继续在D盘，不复制共享目录。新启动下重新建立板端身份授权与请求归属，按最新source/handoff核对候选而不是旧压缩包。人物替换是否采用仍按用户确认与实际A/B结果处理，不能借恢复自动换图或启用未过门槛的新捕获/播放链。

**新clock真实ARM未跑。** Date/client报告只证明纯mock；语义记忆ARM使用合成UTC也不等同HTTP-Date/真实clock锚验证。新的board_clock_probe当前仍是未配置模板，启动后应在受控窗口完成真实源/peer/boot/期限/quality-lease验证。恢复factory使用 `wall_clock=timeline.event_time`；后台条件组合 `jobs.idle and controller.idle and timeline.safe_for_compaction`。没有可信时间时保留待处理正文，不以board `time.time`替代并清理记忆。

jobs最新search转发、ASR前preempt/组合idle、root后续policy/clock/Store修复均须跑最终统一回归；最后63项旧阶段通过不能当作当前整套通过。本阶段没有为收尾运行新模型、pytest、网络替代通道或任何UART/设备动作。
