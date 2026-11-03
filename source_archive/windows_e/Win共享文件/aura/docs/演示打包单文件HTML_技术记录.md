# 演示打包单文件 HTML · 技术记录

> 日期：2026-09-12（第 5 轮）　环境标签：**PC / SIMULATED**（PC 侧离屏渲染，非板端实测）
> 触发：演示素材散落在 `evidence_shots/demo24/`（313 张 PNG + GIF + MP4），
> 需要「**一个点击即可查看的演示文件**」。
> 结论：交付 `evidence_shots/demo24_viewer.html` —— **自包含单文件（0.91 MiB），双击即看、可单独转发**；
> 由新工具 `tools/make_demo_viewer.py` 一键复现。

---

## 一、背景与目标

- 现状三个不顺：① 帧目录要点开 313 个文件；② `demo_scenario.gif` 6.13 MiB 且被 PIL 合并成 135 帧、256 色；
  ③ `demo_scenario.mp4` 是 cv2 写的 **`mp4v`（MPEG-4 Part 2）**，浏览器 `<video>` 基本不能播。
- 目标：**双击一个文件就能看完整 13 秒演示**，不依赖同目录任何文件（能单独发给别人），
  并顺手把「校验结论」写进页面，避免口头说明。

## 二、产物清单（本轮新增）

| 产物 | 体积 | 说明 |
|---|---|---|
| `evidence_shots/demo24_viewer.html` | **0.91 MiB** | **主交付**：自包含单文件（视频 + 9 张缩略图全 base64 内嵌） |
| `evidence_shots/demo24/demo_scenario_h264.mp4` | 0.38 MiB | H.264 / avc1 / yuv420p / +faststart（原 1.10 MiB 的 mp4v 转来） |
| `evidence_shots/demo24/demo_scenario_vp9.webm` | 0.20 MiB | VP9 / WebM（**开放编码**，无专有解码器依赖） |
| `tools/make_demo_viewer.py` | — | 打包工具（可复跑、参数化） |

- 原 `demo_scenario.mp4` / `demo_scenario.gif` / `demo_frames/*.png` **一个字节都没动**（转码产物是新文件）。
- 用法：

```powershell
$w = "D:\share\项目开发\FPGA语音助手开发\wujing-lite"
cd $w
python tools\make_demo_viewer.py                    # 默认打包 evidence_shots\demo24
python tools\make_demo_viewer.py --thumbs 9 --thumb-width 320 --embed auto
python tools\make_demo_viewer.py --embed gif        # 只嵌 GIF（不转码）
python tools\make_demo_viewer.py --embed both       # 视频 + GIF 都嵌
```

## 三、关键决策与技术细节

### 3.1 为什么不能直接内嵌现有 mp4

- 实测本机 MP4 的容器 tag：`mp4v` @ offset 1156815 → **MPEG-4 Part 2**；
  `tag_avc1 = -1`、`tag_hvc1 = -1`。
- 本机 **cv2 写不出 H.264**（`writer_open`: `avc1=false / H264=false / X264=false / mp4v=true`），
  原因在 stderr：`Failed to load OpenH264 library: openh264-2.5.0-win64.dll`（缺 Cisco openh264 动态库）。
- ⇒ 必须借道 ffmpeg。本机可用的是 **`imageio-ffmpeg 0.6.0` 自带 ffmpeg 7.1**（`ffmpeg-win-x86_64-v7.1.exe`），
  `PATH` 上**没有**第二个 ffmpeg（已全盘搜索常见目录确认）；
  它的 `-encoders` 含 **libx264 / libvpx-vp9 / libaom-av1 / libx265** ✓。

### 3.2 双源自动兜底 + **codecs 限定**（本轮最大的坑）

- 先只嵌 H.264 → 用 QtWebEngine（Chromium）无头探测，**黑屏**：
  `error: "4:DEMUXER_ERROR_NO_SUPPORTED_STREAMS: FFmpegDemuxer: no supported streams"`
  —— 该 PySide6 QtWebEngine 构建**没有编译 H.264 专有解码器**。
- 对策一：同一个 `<video>` 里放**多个 `<source>`**（H.264/MP4 → VP9/WebM），浏览器自己挑能播的；
  VP9/VP8/AV1 是**开放编码**，所有 Chromium 构建都能解。
- 对策二（**关键**）：`<source>` 的 `type` 必须**带 codecs 限定**：
  `type='video/mp4; codecs="avc1.64001e"'`、`type='video/webm; codecs="vp9"'`。
  只写 `type="video/mp4"` 时，Chromium 的 `canPlayType()` 返回「可能可以」→ 选中 mp4 →
  解码失败后**不会**再回退到下一个 `<source>`（实测 `networkState=3` + 全源耗尽）。
  带上 codecs 后 `canPlayType()` 会如实返回 `""` → 自动跳到 WebM。
- 为了让 `avc1.64001e` 与实际编码一致，`libx264` 额外显式加 `-profile:v high -level 3.0`。
- 尺寸/元数据：`512×300 / 24.0000 fps / 313 帧 / 13.042 s`（与 `_verify_fps.py` 结论一致）。

### 3.3 页面内容全部自动推导（不手写）

- **剧本时间轴**：按帧文件名里的状态变化切段（`demo_<idx>_t<秒>_<状态>.png`），
  自动得出 **6 段**：`IDLE → PRESENT → LISTENING → THINKING → SPEAKING → IDLE`，含时刻/帧号范围/帧数。
- **关键帧缩略图**：等间隔抽 N 张（默认 9，**必含首末帧**），PIL 缩到宽 320 + JPEG q80 → base64 内嵌（合计 0.09 MiB）。
- **校验结论表**：帧序列（命名序 == 帧号序）、内嵌视频元数据（fps/帧数/时长）、
  内嵌编码（`avc1 ＋ vp9`）、GIF 兜底（总时长与 24 fps 时间轴偏差）、内嵌体积。
- **自身体积自指**：页面要显示自己的体积 → 渲染后测长、回填、再渲染，**迭代到收敛**（2 次内）。
- 播放器属性：`controls autoplay loop muted playsinline preload="auto" poster=<首帧缩略图>`，
  muted 才允许浏览器自动播放；另有 JS 监听 `error` 事件显示「改用 GIF / 用播放器打开」的兜底提示。

### 3.4 体积账（为什么是 0.91 MiB 而不是 9 MiB）

| 方案 | 视频内嵌 | HTML 体积 |
|---|---|---|
| 只嵌 GIF | 6.13 MiB → base64 8.5 MiB | ≈ 8.6 MiB |
| 只嵌 mp4v 原片 | 1.10 MiB（**且浏览器多不能播**） | 不可用 |
| **本方案：H.264 + VP9 双源** | 0.38 + 0.20 MiB → base64 0.79 MiB | **0.91 MiB** |

> H.264 转码顺带把 1.10 MiB 压到 0.38 MiB（CRF 20，`-preset slow`），VP9 只要 0.20 MiB（CRF 34）。

---

## 四、验证方式与结果

### 4.1 工具自检（`make_demo_viewer.py` 输出）

```
[1] 帧序列：313 张（demo_000_t00.00_IDLE.png ~ demo_312_t13.00_IDLE.png）；文件名序 == 帧号序：是
[2] ffmpeg：…imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe
     H.264 libx264: OK → evidence_shots/demo24/demo_scenario_h264.mp4 (0.38 MiB)
     WebM  libvpx-vp9: OK → evidence_shots/demo24/demo_scenario_vp9.webm (0.20 MiB)
[3] 内嵌视频：512×300 / fps=24.0000 / 313 帧 / 13.042 s / 0.38 MiB
[4] GIF：135 帧 / 总时长 13040 ms / 6.13 MiB
[5] 关键帧缩略图：9 张（JPEG 合计 0.09 MiB）
[6] 剧本时间轴：自动推导 6 段（IDLE、PRESENT、LISTENING、THINKING、SPEAKING、IDLE）
[7] 产物：evidence_shots/demo24_viewer.html（0.91 MiB）
结论: PASS
```

### 4.2 浏览器内核实测（**关键证据**）

用 `PySide6.QtWebEngine`（Chromium）**无头加载真实 HTML** 并执行 JS 探查
（临时脚本 `evidence_shots/_check_viewer.py`，可删）：

| 探针项 | 只嵌 H.264（修复前） | **双源 + codecs（修复后）** |
|---|---|---|
| `loadOk` / `placeholders` | true / 0 | true / **0**（无残留占位符） |
| 缩略图 / 表格 | 9 / 2 | 9 / 2 |
| `error` | **`DEMUXER_ERROR_NO_SUPPORTED_STREAMS`** | **null** |
| `readyState` | 0 | **4（HAVE_ENOUGH_DATA）** |
| `videoWidth × videoHeight` | 0 × 0 | **512 × 300** |
| `duration` | null | **13.042 s** |
| 实际选中源 | mp4（解不了） | **`data:video/webm;…`（自动回退成功）** |

⇒ 该 Chromium 构建**无 H.264 解码器**却仍能播放页面里的视频，证明「双源 + codecs 限定」兜底生效；
真实 Edge / Chrome（自带 H.264）会优先走更省体积的 MP4 源。

> 说明：无头环境下 `autoplay` 被策略拦截（探针里 `paused=true`），但 `readyState=4` 已证明**可完整解码**，
> 页面带 `controls`，真实浏览器双击打开时 muted 自动播放正常、也可手动点播。

### 4.3 回归

`python -m pytest -q` → **tests=217 / failures=0 / errors=0**（新增 `tools/make_demo_viewer.py`，未改动运行时代码）。

---

## 五、涉及文件清单

- 新增：`tools/make_demo_viewer.py`（打包工具）、`docs/演示打包单文件HTML_技术记录.md`（本文档 + 同名 `.docx`）
- 新增产物：`evidence_shots/demo24_viewer.html`、`evidence_shots/demo24/demo_scenario_h264.mp4`、
  `evidence_shots/demo24/demo_scenario_vp9.webm`
- 临时探针（可删）：`evidence_shots/_check_viewer.py`、`_probe_pack.py`、`_viewer_probe.json`、`_viewer_shot.png`
- 未改动：`examples/run_demo_scenario.py`、`evidence_shots/demo24/demo_scenario.mp4|.gif`、`demo_frames/*.png`

## 六、已知边界与下一步

1. **`autoplay`**：muted + loop 才允许自动播放；若浏览器策略更严，用户点一下播放键即可。
2. **截图**：无头 `QWebEngineView.grab()` 拿不到 WebEngine 合成层（得到的是空画面），
   故本页「能播」的证据是 **JS 探针数值**，不是截图。
3. **素材帧率上限不变**：素材本体 9.983 fps，24 fps 只是采样/播放帧率（页面里已写明）。
4. 可选下一步：
   - 把 `_check_viewer.py` 转正为 `tools/verify_demo_viewer.py`，纳入「出演示证据」SOP；
   - 让 `examples/run_demo_scenario.py --mp4` 直接写 H.264（避免先写 mp4v 再转码，省一次 IO）；
   - 演示页加入控件：播放速度（0.5×/1×）、逐段跳转（按时间轴分段 seek）。
