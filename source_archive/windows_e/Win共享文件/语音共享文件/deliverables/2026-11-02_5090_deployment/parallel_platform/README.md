# KV260 平台只读审查交付

本目录由平台只读子代理准备。没有执行板端文件写入、创建锁/检查点、服务操作、平台切换、MMIO、音频、数据库打开或运动。用户已告知转轴通电且可观察；这不构成本 boot 的 ARM、参考建立或短测授权。

- 本 boot 的具体恢复顺序、每阶段条件、命令和停止点：[RECOVERY_REVIEW.md](RECOVERY_REVIEW.md)。这是供唯一设备操作者审阅的人工分阶段入口，**没有宣称写入执行器已就绪**。
- 后续默认启动选择与依赖修订：[PERSISTENT_BOOT_REVIEW.md](PERSISTENT_BOOT_REVIEW.md)。未安装，未做冷启动验收。
- 源码/RTL/驱动依据与来源 SHA：[SOURCE_AUDIT.json](SOURCE_AUDIT.json)。真实 launcher 的 `--preflight` 分支已静态审阅，未执行。
- 本机分阶段事务控制器及明确缺口：[TRANSACTION_DRAFT_REVIEW.md](TRANSACTION_DRAFT_REVIEW.md)、`platform_transaction_draft.py`；真实backend硬拒执行，状态 `EXECUTION_NOT_READY`，25项隔离fake测试通过。真实只读事实输入是 `TRANSACTION_REVIEW_CONTEXT.json`，没有批准或未来seed/PID。
- 最新正常停止前只读实证：[preflight_readonly_03.json](preflight_readonly_03.json)，主机 UTC 2026-11-02 02:28:11.335100–02:28:14.268051。
- 盘上旧 checkpoint 与本 boot 新计数域的区别：[native_context_readonly_01.json](native_context_readonly_01.json)。盘上旧 `5b26714b…` 不是当前相机的最终检查点。

可以复用的只读脚本：

1. `collect_preflight_readonly.py`：绑定 boot 903c、当前 startup 07c5 和真实相机 1333/birth2359；核对 380 业务组件、14 读回来源、222 原 Native Python 文件、7 operator 文件、4 wide 固件和 3 driver，检查 GUI 无 owner、保存监听 false、真实相机推进及 DPU/原始内存 owner 清单。通过只表示具备进入“正常停相机”的前提，输出始终 `platform_switch_permitted=false`。
2. `collect_final_checkpoint_readonly.py`：为主操作者正常停止当前相机之后准备；本子代理**没有执行**。它只读真实最终文件，拒绝旧 SHA、活着的前驱、当前 boot/PID/birth 不符、低于实测累计下界、非静止辅助状态和已消费文件，并验证前驱内核归档链接。它不替代原 `load_business_checkpoint` 的完整校验，也不创建封存文件或 marker。
3. `collect_platform_readonly.py`、`collect_startup_sources_readonly.py`、`collect_native_context_readonly.py`、`collect_wide_contract_readonly.py`：本轮详细只读发现的可审查来源。

本机运行入口采用已审阅的 `board_ssh.py`，仅把源码经 stdin 发给 `python3 -B -`；不上传板端脚本。示例应给全新的本机输出文件名，既有证据不覆盖：

```powershell
python -B 'E:\Win共享文件\语音共享文件\deliverables\2026-11-02_5090_deployment\parallel_platform\run_readonly_probe.py' 'E:\Win共享文件\语音共享文件\deliverables\2026-11-02_5090_deployment\parallel_platform\collect_preflight_readonly.py' --output 'E:\Win共享文件\语音共享文件\deliverables\2026-11-02_5090_deployment\parallel_platform\preflight_readonly_next.json'
```

脚本失败必须按实际上下文重新审阅；不能通过改 boot/PID、清 marker、降低阈值或补造 seed 获得通过。两次准备期只读探针失败保存在 `PROBE_ATTEMPTS.json` 的说明中：不可读的 sysfs `firmware` 属性，及字体大于初始 2 MiB 读上限。后续读取改为正确来源/有界 64 MiB 源文件核验；没有因此触碰设备或写板。
