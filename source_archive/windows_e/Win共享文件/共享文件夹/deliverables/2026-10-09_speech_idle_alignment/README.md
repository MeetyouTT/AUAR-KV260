# 说话与现有待机动画对齐（2026-10-09）

用户明确要求说话沿用待机的身体运动。此前新增的头肩侧摆／俯仰变形已退出活动代码，历史实验移至 `../2026-10-09_speech_body_motion/archive/`。

默认临时剧本与汐蓝实时演示现在共用现有 `idle_normal` 39 帧底图和正式播放器的待机时序：原 enter、28–35 帧主循环、相邻原帧插值，以及原有整体呼吸。没有新增身体动作、变形或动态素材。

待机和说话共用持续的身体游标；五套独立口型的轮换、静音停顿、自然结束／打断收口均不重置它。暂停冻结视觉时间，重播／明确重置重新起播。嘴型依据现有脸部跟踪矩阵逐帧定位，三档口型先注册到待机脸部，眨眼也使用同一身体帧的脸部位置。

这意味着三档说话的身体姿势统一来自待机，情绪差异保留在独立嘴型中。唤醒、倾听、思考、点头等其他状态继续使用各自原素材。

## 观看与启动

- `index.html`：平静、开心、安慰三档同步动画。左侧原待机，右侧待机身体叠加独立嘴型；无声，口型取真实缓存录音的包络。
- `neutral_idle_speech.webp`、`happy_idle_speech.webp`、`low_idle_speech.webp`：三档动画文件。
- `face_alignment.png`：每档 1／3／5 秒脸部放大抽帧；`contact.png` 是全身抽帧。
- 项目根目录 `aura/tools/run_demo_script.bat`：默认有声临时剧本，使用此次对齐策略。
- 项目根目录 `aura/tools/run_demo_stage.bat`：实时演示，使用此次对齐策略。已打开的窗口需重启加载代码。
- `aura/tools/run_demo_script_accepted.bat`：此前接受版，通过 `idle_body=False` 保留原身体播放方式。

旧缓存网页和移机 ZIP 是历史快照，不会随源码自动更新。本次未重新打包。启动器优先本地 `.venv-live`；任意新台词的 Qwen 环境仍引用旧 D 盘，本次使用既有缓存语音。

## 验证记录

`aura/tests/test_speech_idle_body.py` 九项标准库专项通过：与生产待机逐像素一致、五套口型区域限制及下巴／透明轮廓保护、情绪锚点注册、静音期间继续待机、眨眼位置与统一变换、口型池轮换和停止衔接、暂停／取消、重播，以及已接受版保留。

额外将眼层变换限定到其实际区域，保持原仿射采样：六套眼层各五个姿态与旧全画布采样逐像素一致，避免眨眼时重复处理整张身体图。

三档共 363 个同步对照采样：身体 y>=170 区域改变像素为零，透明通道与待机完全一致，身体游标完全一致。完整 47.27 秒缓存语音剧本共 1420 次采样，五套口型均实际使用，无错误／拒绝，最终 IDLE。源码指纹和离线渲染计时见 `verification.json`。

预加载完整剧本的离线渲染 P95 为 12.63ms、最长 25.96ms；未预热的局部对照最长 197.89ms，包含首次帧序列解码。默认有声入口在开始播放前预加载。上述计时未包含 Qt 显示、音频设备及传输，不能当作实际显示帧率。

已检查全身及脸部放大图，未见嘴型浮在原位置、下巴边缘跳动或眼层错位。本次为 PC 离线验证，尚未作本轮实际窗口／音频设备／板端验收；本机缺 pytest，依赖下载未获批准，未重跑原 550 项完整回归。

重验（项目根目录 PowerShell）：

```powershell
& '.\.venv-live\Scripts\python.exe' -B 'aura\tests\test_speech_idle_body.py' -v
& '.\.venv-live\Scripts\python.exe' -B 'aura\tools\verify_speech_idle_body.py'
& '.\.venv-live\Scripts\python.exe' -B 'aura\tools\realtime_stage.py' --check
```

活动代码入口：`aura/tools/idle_body_compositor.py`、`deliverables/2026-10-06_avatar_reuse/preview_script.py`、`aura/tools/facial_layers.py` 与 `aura/tools/realtime_facials.py`。正式状态合同与正式资源文件未修改。
