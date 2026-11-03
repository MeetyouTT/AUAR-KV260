# 2026-10-12 最新语音与对话文件复核

用户要求“看看最新的语言文件”，随后要求“重新开始”。结合前文按最新语音/对话交付重新定位文件。查阅 ZIP README、已读项目范围和当前规则，检查共享交接入口、配置、启动源码与验证记录。本地可见最新已接受基线为 2026-10-11；本轮未发现更新的语音交付，不推断远端没有新工作。

## 文件与结论

- 最新交接：`/home/ghmd/Win共享文件/共享文件夹/deliverables/2026-10-11_voice_accepted/HANDOVER.md`、`acceptance.json`。
- 当前入口：同级 `2026-10-11_omnivoice_dialogue/README.md`、`launch.py`、`stage_config.json`。
- 冻结源码、配置、参考和证据：`accepted_source.zip`；模型清单为 `model_files.json`，参考/ASR/冻结包清单为 `baseline_files.json`。
- 链路是浏览器按键录音→CPU Paraformer 中文识别→Qwen3 4B Instruct Q4_K_M 多轮对话→OmniVoice 16 步→Windows Qt 实际音频设备/口型。最新源码默认 4B，14B 保留可切换；本轮不连接 Windows，不能确认当前在线进程使用哪个模型。
- 用户已接受汐蓝“柔亮俏皮”声音。现有 `chain_verification.json` 记录录音夹具完整链 1.250/1.094 秒；`warm_turns_verification.json` 记录两轮无缓存文字对话开口 1.594/1.031 秒；`regression_fast.log` 记录历史 26 项相关回归通过。不是本轮重跑或板端性能，也不是物理麦克风自动验收。

## 本轮实际验证

1. 执行交付自带 `verify_saved.py` 时，Ubuntu Python 3.8.10 缺少 `Path.is_relative_to`，退出码 1。问题限于校验脚本与解释器版本，不是模型缺失或哈希错误。
2. 使用只读标准库检查，采用 `relative_to` 验证路径边界并按原清单检查全部文件大小与 SHA256：31/31 通过，共 6,009,374,183 字节，退出码 0。没有修改冻结脚本或业务源码。
3. 冻结 ZIP 127 个条目，`zipfile.testzip()` 返回 None，CRC 通过。

这证明当前 Ubuntu 副本的清单模型、ASR、参考和冻结包已完整到达并与清单一致；不证明其他接手机器同步完成或 GPU/模型服务环境就绪。

## 尚缺与后续

- 板端 MCP01 真实采录→LAN→Windows→KV260 动态播放/字幕/口型仍未验收。
- 这是文本对话链，没有据此确认 VLM 看图问答或 Light-ASD 接入。
- 按键半双工尚无自动 VAD 或全双工；对话事实质量仍有已记录问题。
- 原环境路径仍为 Windows 本机示例，换机必须重建环境并覆盖 Python 路径；本轮未启动服务、录放音或修改运行配置。

本轮仅新增此日志，未修改语音项目文件。本轮未重新执行历史 26 项回归；其通过范围不能用来消除跟踪报告中另一范围的 7 项旧语音 API 错误。
