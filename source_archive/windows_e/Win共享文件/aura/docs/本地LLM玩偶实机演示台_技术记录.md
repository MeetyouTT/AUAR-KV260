# 本地 LLM 玩偶实机演示台_技术记录

> 项目：AURA（`D:\share、\项目开发\FPGA-amd自主命题赛道\aura`）
> 目标：用**本机 Ollama** 充当对话主机，跑通「文本 → LLM → emotion/avatar_action → 玩偶播放」
> 的实机联动，用来实验长句去重复（P0-2）、情绪分档、动作路由的实际观感。
> 日期：2026-10-04　状态：**已完成**（四段链路验证全绿；GUI 已在桌面打开）

## 一、本机现状核查（实测，不是假设）

| 项 | 结论 | 依据 |
|---|---|---|
| Ollama | ✅ **已在跑**（v0.35.0） | `ollama.exe` PID 17908；`/api/tags`、`/api/version` 正常 |
| 已有模型 | `huihui_ai/qwen3-abliterated:14b`（14.8B Q4_K_M，ctx 40960，completion+tools+thinking）；`goonsai/qwen2.5-3B-...`（3.1B F16） | `/api/tags` |
| 单次耗时 | 14B 结构化输出 **10.2s**（含加载）；已加载后 **1.0s** | `ollama_probe.py` / E2E |
| PySide6 | ❌ 缺失 | 便携 Python `find_spec`：`PySide6:MISS`（`numpy/PIL/requests:OK`） |
| tkinter | ✅ 9.0 + PIL.ImageTk 可用 | 「TK_OK python 3.14.7」 |
| 对话主机 8765 | ❌ 原本无服务（`ws_adapter` 默认 `127.0.0.1:8765 /dialogue`） | `Test-NetConnection` |

结论：**LLM 这一环已经具备，缺的是"主机服务 + 渲染壳"**。板端 `qt_app.py` 因缺 PySide6 跑不了，
故选「零依赖演示台」路线（用户拍板）。

## 二、做了什么（3 个交付物）

1. **`tools/dialogue_host_ollama.py`** —— LAN 主机侧服务（**零第三方依赖 WebSocket 服务端**）
   - 自写 RFC6455：握手（`Sec-WebSocket-Accept`）、文本帧、ping/pong、close；**服务端不加掩码**，
     帧口径与项目自研客户端 `ws_client.py` 严格对应（其 `_recv_frame` 已容忍带/不带掩码）；
   - 合同不变：收 `DialogueRequest` → 回 `DialogueResponse`；
   - 后端可切换：`--backend ollama`（默认）/ `--backend mock`（不依赖 LLM，用于先验 WS 链路）；
   - `--once`（处理一条即退）、`--selftest`（不开端口，直接跑一条请求）。
2. **`tools/demo_stage.py`** —— 演示台（**Tk + PIL 渲染层**，逻辑层全是生产代码）
   - 复用：`fsm.RuntimeFSM`（真状态机）、`avatar_assets`（真素材/回退链/burst 名单）、
     `avatar_timing`（**P0-2 真时序**）、`dialogue_client`（真合同 + Mock/WS 适配器）；
   - 播放回路与 `qt_widgets.AvatarPanel` 同口径：状态内相对时间（状态一变归零）→
     相位（loop 抽一次）→ `frame_time` → `frame_index`；HUD 实时显示 asset/帧号/相位/speed；
   - 交互：文本输入 +「发给 LLM」（后台线程，不卡 UI）、三档快捷句长、五个事件按钮
     （来访者进入/唤醒 KWS/说完 VAD/播报结束/重来）、事件日志（含"被拒/自环"标记）；
   - `--selftest`：无窗口跑剧本 → 导出拼图 + 指标。
3. **`tools/run_demo_stage.bat`** —— 一键启动（**纯 ASCII + CRLF**）：先起主机，再开演示台。

## 三、关键决策与踩坑

1. **（最重要）Cline 终端的进程模型**：新命令会**掐掉**仍在跑的上一条前台命令 ——
   长时间任务（模型加载）必须 `start /b` 后台跑，或用 `subprocess` 把生命周期管在**同一个进程内**
   （本轮 E2E 就改成"一体化脚本"：起主机 → 轮询端口 → 请求 → 收尾）。
2. **零依赖的边界**：本机 `websockets` 缺失，但项目本就有自研 `ws_client.py`，于是服务端也自写，
   口径一一对应；这样板端 C++ 移植时不用猜库行为。
3. **LLM 输出必须被约束成合同 JSON**（否则板端 `policy_validator` 会拒整条响应）：
   三层保险 = ① Ollama `format="json"`；② 提示词里**直接注入白名单**（动作白名单取自
   **P0-4 的单一来源** `board/runtime/avatar_actions.ALLOWED_AVATAR_ACTIONS`）；
   ③ 返回后 `normalize_reply()` **归一化 + 兜底**（未知 emotion → neutral；白名单外/未落地动作 → 空串）。
   配合 `think: false` 关闭 qwen3 的思考（实测 `thinking` 长度 0，输出干净）。
4. **`visual_claims` 默认空数组**：grounding 校验是最严的一环，演示阶段不编造视觉声明最安全。
5. **踩坑·相位重抽不能依赖"中间状态被渲染过"**：`_phase_key` 原本在"状态内 tick 后才比较"，
   若某状态（LISTENING/THINKING）没被渲染就直接换状态，相位会**沿用上一次** →
   自检里两次入场相位竟然相同。修法：**状态一变就把 `_phase_key` 置 None**，强制重抽。
6. **踩坑·GBK 控制台**：重定向到文件时 stdout 走 GBK，`✓/✗`（U+2713/2717）直接
   `UnicodeEncodeError`；已统一 `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`。
7. **踩坑·入口位置**：两次"同锚点插入"把 `if __name__ == "__main__"` 挤到 `selftest` **之前** →
   `NameError: selftest is not defined`；入口已移到文件末尾，并留注释警示。
8. **为什么 Tk 而非 PySide6**：本机无 PySide6 且装它要联网下 200MB+，而演示台的价值在**逻辑层联动**，
   渲染层只是替代实现；真机渲染复核仍留作可选下一步。

## 四、验证方式与结果

| 段 | 命令 / 方式 | 结果 |
|---|---|---|
| ① 模型结构化输出 | `ollama_probe.py <model>` | 14B **10.2s**；`format=json` 生效 → 单个 JSON；`thinking` 长度 0 |
| ② 主机合同组装 | `dialogue_host_ollama.py --selftest --backend mock` | `SELFTEST OK`（request_id / 协议 1.0 / 白名单全对） |
| ③ WS 端到端（mock） | `host_e2e_all.py mock 8766` | `E2E OK`：握手通过、`last_latency 0.8ms`、`stale_dropped=0` |
| ④ WS 端到端（真 LLM） | `host_e2e_all.py ollama 8767` | `E2E OK`：**1.0s**、`emotion=friendly`、`avatar_action=ack_nod`（白名单内） |
| ⑤ 演示台逻辑自检 | `demo_stage.py --selftest` | `SELFTEST OK`；拼图 20 格 `docs\demo_stage\stage_selftest.png`（920×1438） |
| ⑥ 演示台 GUI | 后台 `start /b` 启动 | 窗口已在桌面打开（进程存活）；日志 `docs\demo_stage\stage_selftest.log` |

自检关键读数（`stage_selftest.log`）：

- 四态素材与语义全对：`PRESENT→idle_present(loop)`、`AWAKE→emo_surprised(burst, phase=0)`、
  `LISTENING→idle_listening`、`THINKING→idle_thinking`；
- 长句播报 `speed=0.850`（92 字 → 最慢档，P0-2 变速生效）；
- **两次入场相位 `1.345` vs `0.206` → DIFFERENT [P0-2 OK]**（"入场一致"已消除）。

## 五、涉及文件清单

| 文件 | 类型 |
|---|---|
| `tools/dialogue_host_ollama.py` | 新增（零依赖 WS 主机 + Ollama 后端） |
| `tools/demo_stage.py` | 新增（Tk 演示台；复用生产逻辑层） |
| `tools/run_demo_stage.bat` | 新增（一键启动；纯 ASCII + CRLF） |
| `docs/demo_stage/stage_selftest.png` / `.log` | 新增（自检取证） |
| `%TEMP%\ollama_probe.py`、`host_e2e.py`、`host_e2e_all.py` | 临时验收脚本（非交付物） |

## 六、下一步

1. **真机渲染复核（可选）**：装 PySide6 后跑 `qt_app.py`，对比 Tk 演示台与真机观感；
2. **对齐正式主机**：任务书里主机是 Open-LLM-VTuber，本主机是"本地实验替身"（协议相同）；
   若走正式路线，需在其侧实现同一 `DialogueRequest/Response`；
3. **补语音闭环**：接 ASR/TTS（`board/runtime/audio/`）后，`transcript` 与 `AUDIO_PLAYBACK_STOP`
   由真实语音驱动，演示台即成为"真·对话"；
4. **让 LLM 更懂玩偶**：`ack_nod / emo_surprised / emo_puzzled` 的触发目前靠提示词，
   可升级为 few-shot 或 tools 调用，并在提示词里补"句长 → 期望动作"的说明；
5. **顺手验证 P0-1**：本主机可直接用来验"`ack_nod` 后接 `SPEAKING_*` 续播"的观感（方案 §4.1 P0-1）。
