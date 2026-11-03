# AURA / KV260 本地项目入口

**2026-10-18 最新：实录自动回答已通过。** 板卡5秒新录音→本地模型→板端实际开口约1.61秒，用户确认听到回答，口型和结束待机正常；相机保持运行。[单轮闭环证据与后台启动说明](deliverables/2026-10-18_board_dialogue/README.md)。下方早先“实录待确认”为历史状态。

2026-10-18 最新：[本地模型与板端语音接入](deliverables/2026-10-18_board_dialogue/README.md)。SSH公钥已授权，新录音跨机ASR已通，完整Qwen3 4B＋OmniVoice16服务与板端自动回答客户端已就绪；最后实录播报结果在该目录保存。模型主机8792、纯ASR8791，运行/备份/启动脚本均已整理。

2026-10-18 有线已通：本机 `192.168.50.1/24` → 板卡 `192.168.50.2`，网关/DNS为空，Wi-Fi未改。[连接配置与备份](deliverables/2026-10-18_network_discovery/README.md)。用户随后要求继续模型接入，当前进度以上方新条目为准。

2026-10-18 已将 `E:\Win共享文件\共享文件夹` 的最新工程与交付资料整合到本目录。当前工作根目录：`D:\share、\项目开发\FPGA-amd自主命题赛道`。历史资料中的 E 盘、Ubuntu 和板端路径是原始来源；在当前 Windows 主机执行命令时请使用本地实际路径。

项目已进入**实板整机集成阶段**。真实相机/DPU 人体检测、ByteTrack 跟踪选人、双层板端界面、MCP01 采录与缓存播放均有已保存板测记录；Windows 语音基线已获用户接受。完整身份、跨端问答播报、当前视觉链随动、创新对照、冷启动及整机长稳仍待收口。

## 从这里接手

1. [整体进度核查（2026-10-17）](aura/report/project_status_20261017/REPORT.md)：八个模块、已做范围、缺口及下一步顺序。
2. [本次本地整合记录](deliverables/2026-10-18_project_integration/README.md)：文件差异、备份、验证和移机边界。
3. [已接受语音交接](deliverables/2026-10-11_voice_accepted/HANDOVER.md)：柔亮俏皮参考、OmniVoice 16 步、Qwen3 4B、模型与环境配置。
4. [跨机 ASR 必需文件](deliverables/2026-10-17_board_asr_host_files/FULL_ASR_CHECKLIST.md)及[板端 ASR 操作说明](aura/docs/BOARD_ASR.md)：下一项优先完成板端新录音→Windows 识别→实屏文字。
5. [最新显示启动补丁](aura/report/display_coldboot_20261017/REPORT.md)：已安装的原板版本下次启动生效，实际断电冷启效果仍待验收。

接通 ASR 后，回收各独立服务到匹配的统一运行版本，再接动态回答／TTS→板端实际出声、字幕及口型。`aura/config/runtime.kv260.json` 仍为未收拢全部实板成果的总配置，不能直接当作整机已验收入口。

本机已有 Python 路径、虚拟环境、VerySync 状态和已验收语音归档保留。Linux 原生库与启动服务已作为工件归档，不代表能在 Windows 执行。共享中仍有历史同步冲突版本，正式发布前须复核。更多原始板测证据仍引用 Ubuntu 共享目录之外的绝对路径，本次整合只包含 E 盘实际保存的文件。
