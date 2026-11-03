# 固定轨迹寄存器适配与PWM锁存复核

最新：主终端v1有限实板试验在第31个ACK被entry/core的 `UNEXPECTED_PWM_WIDTH` 误停。ACK30、31都为目标1415/实际寄存器width1416，两个采样相隔13.816ms，flags15、lease100、session/epoch一致；最终STOP的width仍1416、target1415，未完成往返。本子任务只读其本地数值回执，无板卡访问。错误来自core遗漏preflight已核验的旧width，不是此次放宽范围或生产r15控制修改。

已新增PWM相位反例：首COMMIT+5ms、第30COMMIT+9ms，使589ms才提交1415，而600ms下一次hold仍在605ms PWM边界之前，合法width仍1416。旧二值校验可复现误停；主终端修复post允许 `{preflight已知width, 上一目标, 本次目标}` 后，模型98个ACK完整返回1420/STOP。preflight检查不变，另测范围内但未知的1418仍被拒绝。现在18项通过，见 `PWM_HOLD_REPLAY.json` 与更新的 `VALIDATION.json`；实际修复后实体结果由主终端另验，不把模型PASS当实板PASS。adapter运行文件SHA未改。

`FixedBenchDriver(registers, build_id, boot_id, *, minimum_us, maximum_us, clock=..., sleep=...)` 位于 `fixed_bench_adapter.py`。它继承现役固定SHA的BatchDriver/VSRVDriver；只接受外部已验证且持独占锁的BatchRegisters，不自行开设备、读取相机或重启服务。当前boot现场参考、用户许可及STOP收据由主终端的 `fixed_motion_board_entry_20261026/board_fixed_cli.py` 核验；本模块不能替代这些证据，旧1420及复位默认1500都不能自动当当前物理位置。

新增 `submit_bench` 直接写既有VSRV/2命令寄存器，不调用face submit、不生成脸帧。每次保持同一绝对2秒截止，租约最多100ms，20ms余量外保留3ms提交准备；首次租约至少23ms。仅批准窄窗口、参考±5µs、单步≤1µs；逐次核对session/epoch/seq/reference/target/width/lease。错误STOP时保留原异常，STOP失败另存 `last_failure`/异常的 `bench_cleanup`。`finish`最多等待25ms，并裁剪到原绝对截止。

真实批读没有逐寄存器时间戳，因此ACK同时返回采样起止区间：结束时刻配lease是到期上界，开始+(lease−1)ms是仍有效下界。依据现役RTL，lease是每毫秒递减的计数器，续租不重置毫秒相位；不能用后来的Python时钟去解释旧剩余值。新版entry core已验证该下界，25ms批读暂停后再90ms返回暂停会拒绝旧ACK。记录始末不是外部仪器测量。

初版16项主机测试通过：真实驱动+寄存器模型的98提交/1415往返/STOP，旧1500拒绝、23ms首PWM、原截止不可更改、窗口/步长、过期、错ACK上下文及width/reference、异常优先、批读时间界限、毫秒相位、finish截止，以及禁止face submit。`REGISTER_MODEL_RESULT.json`保留初版完整模型命令；不代表实板波形或机械平滑验收。

**Q09未解决：** 若线程暂停在native最终COMMIT内部，当前相对租约硬件仍可能迟到启动。`KNOWN_LIMITATION_REPLAY.json`明确复现2.1秒native暂停、截止后COMMIT、随后软件STOP，不能宣称2秒硬件绝对保证。真实BatchRegisters时延、PWM/机构手感、供电和完整随动仍待用户在场验证。

验证命令：`python3 -B -m unittest discover -s /home/ghmd/aura-pan-follow-shadow-20261024/fixed_motion_board_adapter_20261026 -p 'test_*.py' -v`。无板卡、UART或MMIO访问；原r15和原离线25项core均未修改。
