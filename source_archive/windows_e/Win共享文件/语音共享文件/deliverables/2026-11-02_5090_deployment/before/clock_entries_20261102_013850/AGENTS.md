<!-- 5090-local-deployment-20261102 -->
5090 本机部署接续更新（洛杉矶 2026-11-01）：RTX 5090 Laptop / 24463 MiB；独立 Python 环境的 104 项依赖、真实 CUDA 和原 OmniVoice 三个文件 SHA 已验证；完整回归 101 项及 5 子用例通过，原 OmniVoice16 已生成新 PCM 并测量显存。原 27B 仍在项目外 D:/AIModels 续传，须完整 SHA 通过再加载。动态阶段见语音共享文件/deliverables/2026-11-02_5090_deployment/STATUS.json，下载见 llm_download_progress.json，接续见 HANDOFF.txt。只有 complete=true 且阶段为 READY_LOCAL_ONLY_BOARD_INTEGRATION_PENDING 才表示本机模型验证完成。板卡已接有线网，主机 192.168.50.1/24；可信 SSH 与新公钥登录已验证。新 boot 903cfade-b93c-48fa-804e-379be1967313：当前 benchmark 固件，相机 1333 运行，GUI failed，保存聆听 false，板端时钟 2021 年不可作为当前实时时钟；详见 board_baseline.json 及主机时间锚定的 board_baseline_observation.json。本机正式模型服务验证目标暂为 127.0.0.1:8797。勿重复安装/下载、启动旧 8792 业务、沿用旧 READY/PID/GPU 校准或重放旧运动请求；转轴平台与实体动作尚未恢复。
<!-- /5090-local-deployment-20261102 -->

<!-- 5090-migration-current-20261101 -->
2026-11-01最新接续：后续工作与Windows模型服务迁往5090 Laptop主机，旧机可能不再启用。先读[5090换机入口](E:/Win共享文件/5090主机迁移包_20261101/00_先读.md)与[新主机Codex提示词](E:/Win共享文件/5090主机迁移包_20261101/01_给新主机Codex的提示词.txt)。完整载荷是整个Win共享文件目录。

转轴接入优先、记忆验收后置。最新设备状态以axis_priority_20261101/HANDOFF_5090.txt为准：只完成一次两秒初始化及STOP，实物未观察清楚；重复/方向/本boot跟随未完成。迁移末次SSH未连通，当前在线/boot/输出不能新鲜确认。ec12文件已应用但GUI因MCP01尚未READY；重启回benchmark的持久接入仍待处理。以下旧READY、PID、时间窗和性能段落按历史理解，不代替新机核验。

LLM权重/Ollama仍按原约定在共享目录外，下载/恢复记录随包；登录凭证、SSH私钥、不可移植venv不复制。已补存的普通资源、环境清单、配置、会话导出及校验报告见迁移包清单。
<!-- /5090-migration-current-20261101 -->

# 共享目录的模型与分析存储约定

- 用户明确要求：大语言模型权重、权重副本、下载分段及Ollama模型数据不得放在 `E:\Win共享文件` 或其任何子目录中。不得用指向外部权重的目录联接等方式让共享目录再次包含模型数据入口。
- 当前27B权重和下载缓存位于 `D:\AIModels\qwen3.8-27b-abliterated`，对应Ollama模型库位于 `D:\AIModels\Ollama-AURA`。后续新增大语言模型继续使用项目外本地模型目录，实际路径在语音项目的 `aura/config/model_storage.local.json` 中配置。
- 语言模型分析、设计规划、测试报告、运行证据和路径配置允许保存在 `E:\Win共享文件`，统一分析入口为 `E:\Win共享文件\语言模型分析\README.md`。
- 当前语音业务源码仍在 `E:\Win共享文件\语音共享文件`，保留原运行证据和源码引用；统一分析目录可归档小型报告副本，不复制模型权重或虚拟环境。
- ASR、TTS资源按现有明确授权的运行配置处理；用户本条约束针对大语言模型。存储路径变更不得顺带删除历史归档或无关资源。
