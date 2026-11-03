# 接续：r11 已部署，实际身份摘要网络验收待授权

先读本目录 README.md、PROGRESS.json、verification.json、approval_pending.json 和适用 AGENTS.md。四个用户授权子代理均已冻结，父代理已集成，不重复派工或创建聊天。

## 当前实际版本

- Windows `voice-identity-gpu-20261030-r11`，指纹 `38544d0413af52c73c5d030271834b352bf3e1e25fc258be04b456989760368d`，46 份源码/配置通过。
- 实际板根 `/home/root/aura-identity-bridge-20261030/063ae6c47d2048d5a8e78111fc9484a9/runtime`，同级 startup/config.json，286 项绑定。最后 UI PID 525685、相机 1333，PID 仅证据，操作前重新核对。
- Voice/Hub 所属见 service_processes.json；项目 Ollama 所属见 ../2026-10-18_board_dialogue/project_ollama_process.json。默认 11434/其他模型保持，不按旧项目 PID 24812 操作。
- final_ready_fixed.json=READY；旧 final_ready.json 为已修正时间戳失败证据。
- GPU adaptive/enforcing，项目 11435 子进程 fit-target4096；最终三组非缓存最低空闲 1656 MiB，不保证外部未来分配或整体延迟。
- 637 合并回归、实际 ARM public-only 通道、真实原 DB 来源严格比较均通过。真实脸库摘要网络验收未运行，不填通过。

## 自动审批阻断

verify_arm_bridge.py 会在板卡读取私有人脸身份 ID、模板 SHA256，向用户 Windows 192.168.50.1:8792 传送，经本机 Hub 核对关联与旧模板失效。没有图片、向量或姓名，但摘要仍属敏感生物识别元数据。自动审批认为缺少具体载荷/目的地授权，在执行前拒绝。

**用户明确批准该载荷和目的地前，不得运行此脚本、间接调用另一进程、换接口传同类真实数据，或开启会自动提交该数据的真人验收。** safe alternative verify_arm_transport.py 不读脸库/不带脸元数据，已 PASS，但不代表关联传输通过。

用户批准后核对授权范围与实际状态，再运行原可审阅脚本。若再次拒绝如实报告，继续无关工作；不能通过改名或脱敏字眼绕过。合成状态机验证不需真实数据。

## 下一步

1. 可用 verify_final.py 作只读现状核对。UI/相机/pending unit/pins 有变化先调查，不套旧目录覆盖。
2. 获得具体授权后运行 verify_arm_bridge.py，只将 model/revision/count 和网络结果写报告，不输出 ID/模板 SHA 列表、向量、姓名或图片。
3. 通过独立隐藏 WMI 比较真实库，备份留 AppData，不恢复旧库。start_private_verifier.ps1 仅当前进程执行策略，不改全局；留存严格比较，过期缓存例外须逐行证明。
4. 真人验收见 README。保持 speaker_calibrated=false，除非有真实标定；不降低阈值、不把单人入镜当发声证明、不把姓名候选当记忆授权。
5. 重启/相机更新使静态读库配置失败关闭。核对实际来源后才能刷新，自动安全刷新未实现，不能放宽 boot/PID/源码/模型检查。

## 操作保护

部署前两次确认 IDLE/IDLE_READY、监听/麦克风/跟随关闭、无运动，重新读 /proc 实际入口及 pending unit。保持机械 FAULT/null、boot/FDT/固件/VART 与并行启动优化，不 MMIO/复机/运动；相机本轮没有重启。

LLM 权重/缓存/Ollama 库仅 D:/AIModels，共享目录不得放模型数据或联接。保持其他模型；冷启动保护不能自动卸载，端口关闭或 /api/ps 空都不证明没有请求。

不要重跑 prepare/merge/install 脚手架，它们包含历史原始 hash 和部署事务。正常接续不需重载服务。若确需重载项目 Voice/Hub，重新核对精确 PID/创建时间/命令/监听所属、备份真实库和保留原时限。27B/2048、OmniVoice16、声线/种子/精度与取消交接保持。

旧 r10 observe、r9 和板端279pins是历史。manifest 的 STAGED 为冻结记录，实际看 final_installation.json、board_deployment.json、verification.json。
