# 实时演示台 · 本机 Ollama 对话实时演示打通 · 技术记录

- 日期：2026-10-07
- 关联交付：`deliverables/2026-10-06_xilan_live`（浏览器 8773）
- 目标：把移机交接里"预留但未启用"的对话链路，改用**本机大模型**真正跑通（原文只写"对话模型将在另一台电脑接入"）

## 1. 本机现状（勘察结论）

- **对话大脑可用**：本机 Ollama 在跑（11434 监听，安装于 `C:\Users\35870\AppData\Local\Programs\Ollama`），
  已下载 `huihui_ai/qwen3-abliterated:14b`（9GB, Q4_K_M）与 `goonsai/qwen2.5-3B-goonsai-nsfw-100k`；
  其中 14B 正是 `aura/tools/dialogue_host_ollama.py` 的默认模型。
- **GPU**：RTX 5060 Ti 16GB（空闲约 14.8GB）。
- **语音合成仍不可用**：候选路径（`D:\share、\项目开发\tmp`、`<项目根>\tmp`、`<项目根>\models`）均无
  `qwen-voice-audition-venv` 与 `Qwen3-TTS-12Hz-1.7B-Base`；本机只有 ComfyUI 便携版 Python **3.14.7**，
  而项目原设计是 3.12（`qwen_tts` / `torchaudio` 在 3.14 上无把握）。

## 2. 做了什么

1. 用 `.venv-live\Scripts\python.exe`（3.14.7；该脚本**零第三方依赖**）跑自检：
   `dialogue_host_ollama.py --selftest --backend ollama --model huihui_ai/qwen3-abliterated:14b` → **SELFTEST OK**
2. 常驻启动对话主机：`--host 127.0.0.1 --port 8765 --path /dialogue`（WMI 脱离终端，日志落 `%TEMP%\zz_dlg_host.log`）
3. 备份并启用 `stage_config.json` 的 `dialogue.enabled=true`（备份 `stage_config.json.bak_20261007_before_dialogue`）
4. 重启演示台（旧实例的两个 pythonw 一起结束 → 新实例），使新配置生效

## 3. 关键细节 / 踩坑

- **配置只在启动时读**：改 `stage_config.json` 后**必须重启**演示台；`/api/state` 的 `dialogue_enabled` 才会变 true，
  前端"对话服务"输入框与按钮才由 `player.js` 第 26-27 行启用。
- **POST /api/command 会被 403**：`realtime_bridge.py` 第 38 行要求同时带
  `Origin: http://127.0.0.1:8773` 与 `Host: 127.0.0.1:8773`，否则回 403「请通过本机演示页面操作」。
  用 PowerShell 复现时必须手动补 Origin 头（浏览器自动带）。
- **合同永不违约**：主机把请求侧白名单注入提示词，返回后再归一化兜底（未知 emotion→首项、白名单外动作→空串），
  Ollama 不可用时回落 mock（`build_response` 第 296-308 行）。
- **语音失败可见**：本机无 Qwen 运行时 → `/api/state` 的 `error=Qwen Python runtime is unavailable`，
  页面显式提示，**不会**静默换成系统音色；本轮的 LLM 文本仍写入 `reply`，页面能看到汐蓝的文字回复。
- **进程拓扑（承接上轮）**：venv 的 `pythonw.exe` 是 redirector ⇒ 同一实例有两个 pythonw；
  **重启实例时要两个一起结束**（"勿去重"指的是不要单独杀其中一个）。
- 前台命令会互相掐断：长任务仍走 WMI 脱离终端 + 日志落盘轮询；含中文的 `-Command` 内层引号用 `[char]34` 拼，避免 cmd 双引号冲突。

## 4. 验证证据

- 自检输出：`{"reply_text":"看到了！你在这儿，我当然能看见你啦。","emotion":"friendly","avatar_action":"ack_nod","visual_claims":[]}` + `SELFTEST OK`
- 主机日志：`[host] client 127.0.0.1:59063 connected`；
  `req=xilan-0297… emotion=friendly action=ack_nod 1286ms | 你好呀，我是汐蓝，一个喜欢和你聊天的桌面玩偶。`
- 演示台：`POST /api/command {"type":"dialogue","text":"你好呀汐蓝，请用一句话介绍你自己。"}` → `{"ok": true}`
- `/api/state`：`dialogue_enabled=True`、`reply=你好呀,我是汐蓝,一个喜欢和你聊天的桌面玩偶。`、
  `error=Qwen Python runtime is unavailable`、`phase=IDLE`；事件日志含 `voice_requested`（文本/情绪/动作齐全）
- 端口：8773 监听、8765 监听

## 5. 涉及文件

- 改动：`deliverables/2026-10-06_xilan_live/stage_config.json`（仅 `dialogue.enabled: false→true`）
- 新增：`stage_config.json.bak_20261007_before_dialogue`（项目根，回滚用）
- 未改动：`aura/` 全部代码、交付目录内其他文件

## 6. 下一步（待定）

- **要让对话"出声 + 带表情动作"**，需补齐语音合成环境（本机缺）：Python 3.12 + `qwen_tts==0.1.1` + torch(cu12x)
  + `Qwen3-TTS-12Hz-1.7B-Base`（固定 revision），下载量约 7GB，且本机 Python 3.14.7 与项目 3.12 口径不符；
  或继续在持有该模型的机器上生成音频。
- 若暂不补：本机可长期演示"本机大模型文字对话"（回复文本实时出现在页面），语音仍用四段缓存。
