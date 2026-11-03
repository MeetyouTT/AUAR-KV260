# 玩偶素材 Seedance 提示词包（wujing-lite 竖屏 9:16 版）· 技术记录

> 适用对象：**雾镜 Lite 玩偶 Avatar**（`assets/avatar/<素材名>/` 帧序列，9 个 RuntimeState）
> 上游规范：`D:\share\项目开发\实体桌宠\桌宠动作素材生成提示词_20260901\桌宠动作素材生成提示词（Seedance 完整版）.md`（v3）
> 关键帧与核验工具：`wujing-lite/tools/avatar_keyframes.py`
> 记录日期：2026-09-11

---

## 0. 先看这个：与桌宠 v3 的三点差异

| 维度 | 桌宠 v3 | 本包（wujing-lite） | 原因 |
|---|---|---|---|
| 构图 | VTuber **半身**（腰以上） | **竖屏 9:16，头顶到膝上**，脚不入镜 | 玩偶面板显示区是竖屏比例；现役 `idle_normal` 即此构图 |
| 播放策略 | 循环 7 态 + **burst 单次 2 态** | **全部无缝循环** | 播放器只有"无限循环"（`AvatarPanel.frame_at` 取模），没有"播完回 idle" |
| 状态集合 | 9 条提示词（含 emo_happy/emo_angry/act_patted） | **7 条素材**映射 9 个 RuntimeState | 板端状态是 待机/注视/聆听/思考/播报/摄像头丢失/本地模式/已取消/错误 |
| 生成帧率 | 目标 60fps | 源 **24fps 即可** | 入库要抽到 10fps，源 24fps 已足够顺滑 |

### 0.1 构图基准（**实测**现役 `idle_normal` 首帧，非估算）

| 量 | 实测值 | 含义 |
|---|---|---|
| 头顶距画面上边 | **6.7%** | 留一点顶空 |
| 人物高度占画面 | **93%** | 下沿裁在大腿上部，**脚不入镜** |
| 左右安全边距 | **0~2%**（发辫/袖口接近贴边） | 抠像时边缘别被裁掉 |
| 绿幕实测色 | ≈ `#0FE91B`（左下角 `22,229,28`） | AIGC 偏色，`-m adaptive` 可自动估计 |

> 结论：新素材**沿用同一机位与人物大小**。最省事的做法是——**所有素材的首帧都用同一张绿幕参考图**
> （`...\桌宠动作素材生成提示词_20260901\refs\idle_normal_t00.00_f000000.png`），Seedance 会自然继承构图。

---

## 1. 关键帧策略（"细节顺畅"靠这三件事）

1. **首帧锚定**：所有素材的第 1 帧输入 = 同一张绿幕参考图 → 9 态切换时人物大小/位置零跳变；
2. **尾帧锚定**：Seedance 图生视频选 **「首尾帧」模式，首帧与尾帧给同一张图** → 强制画面回到起点；
3. **生成后量化核验**（不靠肉眼，FAIL 即重生成）：

```bash
cd "D:\share\项目开发\FPGA语音助手开发\wujing-lite"
python tools/avatar_keyframes.py ^
    --src "D:\...\idle_listening.mp4" ^
    --out-dir "evidence_shots\keyframes" ^
    --check-loop ^
    --ref "D:\share\项目开发\实体桌宠\桌宠动作素材生成提示词_20260901\refs\idle_normal_t00.00_f000000.png"
```

- `--check-loop`：**首帧 vs 末帧**；判定阈值 主体 mean ≤ 2.0 且 差异像素(>8) ≤ 2% → `PASS`（2 倍内 `WARN`，超出 `FAIL`）
- `--ref`：**新素材首帧 vs 参考图**；阈值 mean ≤ 4.0 且 差异像素 ≤ 5% → `PASS`
- `--find-loop`：扫描全片找"与首帧最接近的帧"（用于挑裁剪点 / 反向验证是否真循环）
- 产物：关键帧原图（绿幕原样）+ `*_loop_check.png`（首帧 \| 末帧 \| 差异热力）+ `*_ref_check.png`

### 1.1 已实测的问题（为什么必须做首尾帧锚定）

| 素材 | 首帧 vs 末帧（主体区） | 判定 | 说明 |
|---|---|---|---|
| `idle_normal.mp4`（现役） | mean=**19.90**、差异像素 **47.3%** | **FAIL** | 扫描全片后发现：**与首帧最接近的帧就是 f0 自己**（mean=0.00）→ 该视频**从未回到起始姿态**，循环播放到接缝处会跳发丝/裙摆 |

> 也就是说：Seedance 默认生成的是"一段 10s 的动作"，**不是**"一个闭环"。首尾同图是把它逼成闭环最直接的手段。
>
> ⚠️ **参考图是"全库同源"的锚点**：若日后重做 `idle_normal`（例如修循环缝），
> 参考图必须同步更新，且**其余 7 态要一起重生成**——否则跨素材一致性核验（`--ref`）会 FAIL。
>
> 🔧 **工具缺陷已修（2026-09-11）**：`avatar_keyframes.py` 的 `read_frame()` 曾漏了 mp4 的 seek，
> 导致 `--count>2` 抽出的**中间关键帧其实全是首帧**；已修复并补 2 条 mp4 回归单测
> （全库 **154 项通过**）。判定结论（FAIL）不受影响。
> 详见 `wujing-lite/docs/关键帧抽帧Seek缺陷修复_技术记录.md`。

```bash
# 复现上面这条结论（现役素材）：
python tools/avatar_keyframes.py --src "D:\share\项目开发\桌面AI桌宠\assets\videos\idle_normal.mp4" ^
    --out-dir "D:\share\项目开发\实体桌宠\桌宠动作素材生成提示词_20260901\refs" ^
    --name idle_normal --count 3 --check-loop
```

---

## 2. 六段式骨架（竖屏版 · 所有状态共用）

```
[视角与构图] + [主体引用] + [核心动作细节] + [循环/时序控制] + [背景与色彩隔离] + [画质与边缘控制]
```

与桌宠 v3 的差别**只在第一段**（半身 → 竖屏全身）与第四段（burst 模板不再使用）。

### 2.1 [视角与构图]（替换 v3 的 `VTuber half-body shot …`）

```text
Vertical 9:16 portrait shot of @character.png: the entire character is framed from the top of the head down to the upper thighs, feet out of frame, perfectly centered horizontally with safe margin on both sides, the figure occupies about 93% of the frame height with the top of the head about 7% below the upper edge, fixed tripod camera at eye level, identical framing, camera distance and character scale in every frame and in every material.
```

### 2.2 [循环/时序控制]（所有 7 态统一，**不再使用 burst 模板**）

```text
All movement is slow, tiny in amplitude and evenly paced; the last frame returns to exactly the same pose as the first frame so the animation loops seamlessly, seamless loop, continuous micro-movement, seamless looping animation, the character never changes position or scale and stays inside the frame.
```

> ⚠️ **循环素材里不要放"一次性动作"**（挥手、被吓一跳、点头问好）。素材每 10s 循环一次，
> 一次性动作会变成"每 10 秒挥手一次"的机械感。7 条素材都只描述**持续状态 + 微动**。

### 2.3 [背景与色彩隔离]

```text
Background is a completely flat, plain, pure solid uniform green screen (#00FF00), crisp edge contrast between character and background, no green color bleeding, no green ambient glow on character edges, no shadows, no props, no reflections, no background objects, no text, no watermark, no UI elements.
```

### 2.4 [画质与边缘控制]

```text
Clean 2D anime live2d illustration style, high detail, ultra-sharp vector clean edges, zero motion blur, no camera shake, no 3D render, no photorealistic elements, hairstyle, hair color, eye color, outfit and body proportions strictly identical to @character.png.
```

### 2.5 通用负向提示词（7 态全部使用）

```text
green spill, green rim light, green reflection, green ambient lighting, green halo, green outline tint, green shadow, soft edges, 3d render, realistic photo, photorealistic, live action, real human face, deformed hands, extra fingers, missing fingers, broken limbs, dislocated joints, motion blur, camera shake, shaky camera, panning, zooming, zoom in, zoom out, dolly, dutch angle, fisheye lens, character size drift, cropping change, walking out of frame, transparent background, white background, black background, background objects, props, floor shadows, text, watermark, logo, signature, low quality, blurry, pixelated, jitter, flickering, morphing, shape distortion, inconsistent character design, color bleeding, outline blur
```

> 相比桌宠 v3 新增：`zooming / zoom in / zoom out / dolly / character size drift / cropping change / walking out of frame`
> —— 专治"生成时悄悄推近或把人物放大"，这是 10 态切换跳大小的**主因**。

### 2.6 锚点图继承效应（**7 态必读** · 2026-09-11 看锚点图实物后补充）

锚点图（`idle_normal_t00.00_f000000.png`）不只是"构图基准"，它同时把**姿态与表情的初始值**带进了每一帧。
实测该图有 3 个特征会**被模型继承**，因此下面 3 件事必须在动作段里显式写清：

| 锚点图特征（实测） | 会被继承成什么 | 处理方式（已写回 §4.x） |
|---|---|---|
| 嘴角已微微上扬、带腮红 | 情绪态全都"笑着"，沮丧/困惑/离线态**表达失效** | §4.5 / §4.6 / §4.7 显式写 `the slight smile fades away …` |
| 双手藏在宽大和服振袖内（画面看不见手） | 模型不知道手在哪，"托腮 / 交握"会变成袖口乱飘 | §4.3 / §4.7 显式写 `hand emerges from the wide kimono sleeve` |
| 右侧长辫甩出画面、袖口贴左右两边 | 往**画面右侧**歪头 / 抬手会把辫子袖口推出框 | §4.2 歪头**锁死画面左侧**；§4.5 抬手改为"**只抬到胸口高度**" |

> 另外：锚点图 f0 本身已"正视镜头 + 微扬嘴角"，所以 §4.1 `idle_present` 与 IDLE 的差异会很小。
> 该态的辨识度主要靠**前倾**体现，生成后务必用 `make_asset_gallery.py` 与 `idle_normal` **并排目检**。



---

## 3. 状态 ↔ 素材 ↔ 提示词 对照表

> **口径（2026-09-12 拆分，依据见 §12）**：运行时状态共 **10 个**，按用途分两组 ——
> **① 表达性节点（6 个，需专门生成素材与提示词）**：待机 / 探头·注视 / 倾听 / 思考 / 说话·高涨 / 说话·低落；
> **② 系统·故障态（4 个）**：CAMERA_LOST / NETWORK_LOST / CANCELLED / ERROR
> （由系统事件驱动，素材上或复用、或降级表演，**不作"情绪"评审**）。

### 3.1 表达性节点（6 个）

| RuntimeState | 中文 | 素材名 | 表情/动作基调 | 提示词 | 状态 |
|---|---|---|---|---|---|
| IDLE | 待机 | `idle_normal` | 平静呼吸、偶尔眨眼 | 沿用桌宠 v3 §3.1（改构图段） | ⚠️ 已入库但**取景口径落后**（full/180×320，待重生成） |
| PRESENT | 探头·注视 | `idle_present` | 好奇注视、微微前倾 | 本包 §4.1 | ✅ 已入库（waist-up，2026-09-12） |
| LISTENING | 倾听 | `idle_listening` | 侧头聆听、眼神专注 | 本包 §4.2 | ✅ 已入库（waist-up，2026-09-12） |
| THINKING | 思考 | `idle_thinking` | 托腮、视线左上 | 本包 §4.3 | ✅ 已入库（waist-up，2026-09-12） |
| SPEAKING | 说话·**情绪高涨** | `talking_normal` | 口型开合 + 胸口手势 + 微笑 | 本包 §4.4 | ✅ 已入库（waist-up，2026-09-12） |
| **SPEAKING_LOW** | 说话·**情绪低落** | **`talking_low`** | 小幅口型开合 + 嘴角下垂 | **本包 §4.8** | ✅ **已入库**（waist-up，2026-09-12，24.8 MiB） |

### 3.2 系统 · 故障态（4 个）

| RuntimeState | 中文 | 素材名 | 表情/动作基调 | 提示词 | 状态 |
|---|---|---|---|---|---|
| CAMERA_LOST | 摄像头丢失 | `emo_puzzled` | 困惑、左右张望（降级表演） | 本包 §4.5 | ⏳ 待生成 |
| NETWORK_LOST | 网络丢失（本地模式） | `idle_offline` | 安静离线待机（降级表演） | 本包 §4.6 | ⏳ 待生成 |
| CANCELLED | 已取消 | `idle_normal`（复用兜底） | —（瞬时态，回迁用） | — | ✅ 复用 |
| ERROR | 错误 | `emo_sad` | 垂头沮丧（降级表演） | 本包 §4.7 | ⏳ 待生成 |

> 缺任何一个素材都不会白屏：渲染层按「**状态素材 → 状态专属中间兜底 → `idle_normal` → B2V 矢量**」
> 逐级回退（见 `board/ui/avatar_assets.py` 的 `fallback_chain()`）。中间兜底目前只有一条：
> `SPEAKING_LOW` 未入库时先放 **`talking_normal`**（观感上"仍在说话"），而不是直接退成待机。

---

## 4. 八条完整提示词（可直接复制）

> 每条 = §2.1 构图段 + **§4.x 动作段** + §2.2 循环段 + §2.3 背景段 + §2.4 画质段；
> 粘贴时整段拷贝，负向词单独用 §2.5。**只有动作段随状态变化**。

### 4.1 `idle_present` —— 注视（PRESENT，好奇型持续态）

**动作段（中文意图）**：察觉到有人在看它，抬起视线盯住镜头、眼睛睁大、嘴唇微张成小"o"，
上身微微前倾，双手自然垂在身体两侧、藏在和服振袖里；全程只有呼吸、发丝与偶尔眨眼的微动。

```text
Noticing the viewer and holding eye contact: head lifted and turned slightly toward the camera, eyes wide open and focused directly on the viewer with a bright curious look, lips slightly parted in a small curious "o" shape, upper body leaning forward by a very small amount, arms relaxed at the sides of the body with the hands inside the wide kimono sleeves, gentle breathing motion in the chest, and a slow natural blink every few seconds.
```

**质检要点**：视线必须锁死镜头（不能左右飘）；前倾幅度极小（≤3°）；唇型是"微张"不是说话。

### 4.2 `idle_listening` —— 聆听（LISTENING，专注型持续态）

**动作段（中文意图）**：头轻轻偏向**画面左侧**（她的右肩侧，避开出框的长辫）、眼神专注柔和地看着镜头，上身略前倾像在认真听；
双手静止垂在身侧、藏在和服振袖里（画面看不到手）；只有呼吸与偶尔眨眼，发丝有极轻微晃动；**歪头方向整段锁死左侧，绝不换边**。

```text
Listening attentively to the viewer: head tilted gently toward the viewer's left side (her right shoulder) and the tilt direction never changes to the other side, eyes calmly focused on the viewer with an engaged, attentive expression, upper body leaning in slightly, arms hanging still at the sides of the body with the hands hidden inside the wide kimono sleeves, subtle continuous breathing, occasional soft blinking, and only the tiniest sway of hair strands.
```

**质检要点**：歪头方向**整段锁死画面左侧**（不能中途换边，也不能偏向右侧——右侧长辫会甩出画框）；不能出现点头/摇头等一次性动作；
**首尾帧同图 ⇒ 头会从中线缓慢歪出、再缓慢回正**，所以"整段同侧"指的是中段不翻面，末帧回正属正常（这正是闭环所需）。

### 4.3 `idle_thinking` —— 思考（THINKING，检索中）

**动作段（中文意图）**：一只手从振袖里伸出、抬起到下巴，指尖轻触（托腮），**袖子自然垂落、不遮脸**，视线向上偏左、微微眯眼，
头略偏、眉毛轻抬、嘴唇轻抿；另一只手自然垂放；呼吸幅度很小。

```text
Thinking quietly: one hand emerges from the wide kimono sleeve and is raised so the fingertips rest lightly against the chin, the sleeve draping down naturally without covering the face, eyes looking up toward the upper left with a thoughtful slight squint, head tilted a little, eyebrows gently raised, lips softly pursed, the other arm relaxed at the side of the body, with only small slow breathing movement.
```

**质检要点**：托腮手不能与脸粘连/穿模；视线方向固定"左上"不漂移；手不能抖动。

### 4.4 `talking_normal` —— 播报（SPEAKING，口型循环）

**动作段（中文意图）**：对着镜头说话，口型自然开合，胸口附近有小的手势辅助，
头随语气轻微点头、上身小幅律动，眼睛带笑、偶尔眨眼。

```text
Talking cheerfully to the viewer: lively lip-sync with the mouth opening and closing naturally, small cheerful hand gestures kept near the chest, gentle head bobbing and a rhythmic small sway of the upper body that matches a speech cadence, bright smiling eyes, occasional blinking, gaze toward the viewer.
```

**质检要点**：口型幅度适中（不要变成"张嘴大笑"）；手势留在胸口小范围不越界；
**首尾帧的嘴型与手位必须一致**（否则循环时嘴会"咔"一下）。

### 4.5 `emo_puzzled` —— 困惑（CAMERA_LOST，左右张望）

**动作段（中文意图）**：眉毛轻蹙、眼神左右游移像在找刚消失的东西，
头缓慢左右转（振袖宽大 ⇒ 手只能抬到胸口高度、绝不能遮脸），一只手抬到头侧做"疑惑"的小手势，嘴唇抿成一条不确定的线，
偶尔小幅耸肩（**微笑必须先淡掉**，否则不像困惑）；**不与镜头对视**。

```text
Puzzled and searching: the slight smile fades away and the mouth corners turn flat, eyebrows slightly drawn together in a small uncertain frown, eyes darting left and right as if looking for something that just disappeared, head turning slowly from side to side, one hand raised only to chest height beside the face in a small puzzled gesture, the wide sleeve draping straight down and never covering the face, lips pressed into a wavering line, a small slow shrug of the shoulders, no eye contact with the viewer.
```

**质检要点**：左右转头幅度小（≤15°）、不遮挡脸；禁止"挠头"这类一次性夸张动作；
**首尾帧转头方向必须回到同一侧**。

### 4.6 `idle_offline` —— 本地模式待机（NETWORK_LOST，安静离线）

**动作段（中文意图）**：安静地站着等，表情平静（**嘴角微笑淡掉**）、眼皮略垂，头微微低一点、肩放松，
双手静止垂放，呼吸幅度是 7 态里最小的，偶尔一次缓慢眨眼，偶尔在姿态内轻轻点一下头；
不说话、不做手势，整体安静克制。

```text
Standing by quietly in local offline mode: the slight smile fades into a calm neutral expression with soft half-lidded eyes, head lowered slightly, shoulders relaxed, hands hanging still at the sides of the body, minimal breathing motion, one slow quiet blink, and an occasional small sleepy nod kept inside the same pose, no speech and no gesture toward the viewer, subdued and tranquil mood.
```

**质检要点**：动作幅度应为全库最小；视线平视偏下，不要与镜头强对视；
**不要闭眼太久/不要睡着**（板端看着像"死机"）。

### 4.7 `emo_sad` —— 沮丧（ERROR，道歉/出错）

**动作段（中文意图）**：垂着头、眼神向下（**微笑完全消失、嘴角向下**），眉尾上挑呈担心的八字眉，肩膀微微垮下来，
双手从振袖里伸出、在身前轻轻交握，嘴唇抿成细细的抖线，偶尔轻轻抽一下鼻子，呼吸带着无力的起伏。

```text
Sad and apologetic, the slight smile gone and the mouth corners turned down: head hanging low, gaze cast downward with sad half-lidded eyes, eyebrows tilted upward in a worried frown, shoulders slumping slightly, hands emerging from the wide kimono sleeves and loosely clasped together in front of the body, lips pressed into a small trembling line, occasional quiet sniffle, and a subtle resigned breathing sway.
```

**质检要点**：垂头角度不能遮住五官；交握的手不要顶到画面下沿被裁；
节奏是全库最慢的（错误态停留时间较长，动作快了会显得躁）。

### 4.8 `talking_low` —— 播报·情绪低落（SPEAKING_LOW，低沉说话）

**动作段（中文意图）**：对着镜头**小声、低落**地说话——口型仍在开合，但幅度比 §4.4 **小一档**、节奏更慢；
**嘴角全程下垂、微笑完全消失**（锚点图的浅笑会被继承，必须显式压掉，见 §2.6 第 1 条），
眉尾上挑呈担心的八字眉，**视线偏下、不与镜头对视**；肩微微垮下、上身几乎不动，只有很轻的呼吸起伏，
偶尔一次缓慢眨眼；**手势几乎为零**（双手留在振袖里），只有说话时袖口布料极轻微晃动；情绪低落但不哭不闹。

```text
Talking in a soft, subdued and low-spirited way to the viewer: the slight smile is completely gone and the mouth corners stay turned down while the lips still open and close in small slow lip-sync movements, gaze lowered and avoiding direct eye contact, eyebrows tilted upward in a worried frown, shoulders slightly slumped, the upper body almost still with only a faint breathing motion, hands kept still inside the wide kimono sleeves with just a tiny tremble of the fabric sleeve, occasional slow blinking, slow and quiet speaking rhythm, sad and downhearted mood.
```

**质检要点**：① 口型幅度**比 §4.4 小一档**（"低落"不是"大哭"，也不是"闭着嘴"——嘴必须还在动）；
② **嘴角必须下垂**，否则继承锚点图微笑后与 `talking_normal` 观感无差别；
③ 视线偏下、不与镜头强对视；④ 手势为零、袖口不遮脸；
⑤ 首尾帧的嘴型与手位一致（循环缝判据同 §4.4）。

> **闭环提示**：与 §4.4 同源（同一锚点图、同一构图段、同一机位），所以 `--ref` 核验**优先与
> `talking_normal` 首帧互比**（同代同姿态，判据 mean ≤4.0 / 差异像素 ≤5%）；
> 不要拿旧锚点图当基准（那会读出 ~26 的"代差"数字，见 §11 与 `docs/TALKING素材入库与同代一致性核验_技术记录.md`）。

**整段可复制**（§2.1 + §4.8 + §2.2 + §2.3 + §2.4 + 内联负向**精简档 A**；共 **2291** 字符，
不会被提示词框截断 —— 措辞与上表逐字一致，仅为免手工拼接）：

```text
Vertical 9:16 portrait shot of @character.png: the entire character is framed from the top of the head down to the upper thighs, feet out of frame, perfectly centered horizontally with safe margin on both sides, the figure occupies about 93% of the frame height with the top of the head about 7% below the upper edge, fixed tripod camera at eye level, identical framing, camera distance and character scale in every frame and in every material. Talking in a soft, subdued and low-spirited way to the viewer: the slight smile is completely gone and the mouth corners stay turned down while the lips still open and close in small slow lip-sync movements, gaze lowered and avoiding direct eye contact, eyebrows tilted upward in a worried frown, shoulders slightly slumped, the upper body almost still with only a faint breathing motion, hands kept still inside the wide kimono sleeves with just a tiny tremble of the fabric sleeve, occasional slow blinking, slow and quiet speaking rhythm, sad and downhearted mood. All movement is slow, tiny in amplitude and evenly paced; the last frame returns to exactly the same pose as the first frame so the animation loops seamlessly, seamless loop, continuous micro-movement, seamless looping animation, the character never changes position or scale and stays inside the frame. Background is a completely flat, plain, pure solid uniform green screen (#00FF00), crisp edge contrast between character and background, no green color bleeding, no green ambient glow on character edges, no shadows, no props, no reflections, no background objects, no text, no watermark, no UI elements. Clean 2D anime live2d illustration style, high detail, ultra-sharp vector clean edges, zero motion blur, no camera shake, no 3D render, no photorealistic elements, hairstyle, hair color, eye color, outfit and body proportions strictly identical to @character.png. Negative prompt: green spill, green rim light, soft edges, 3d render, photorealistic, real human face, deformed hands, extra fingers, motion blur, camera shake, zoom in, zoom out, dolly, character size drift, cropping change, walking out of frame, transparent background, background objects, floor shadows, text, watermark, low quality, blurry, pixelated, flickering, morphing, color bleeding, outline blur
```

> 若提示词框上限 ≥2700，可把尾巴换成 §2.5 **全量负向**（共 2635 字符）；
> 否则**必须**用上面的档 A —— 全量负向的尾部正是 `zoom in / zoom out / character size drift / cropping change`
> 这串"防缩放"词，被截掉就会 10 态切换跳大小（§5.1.1）。

---

## 5. Seedance 生成操作步骤（逐态照做）

1. **准备参考图**（只需一次，已生成）：
   `D:\share\项目开发\实体桌宠\桌宠动作素材生成提示词_20260901\refs\idle_normal_t00.00_f000000.png`
   —— 这是现役 `idle_normal` 的绿幕首帧，**构图/角色/绿色都是基准**。
2. 生成方式选 **图生视频**，并开启 **首尾帧**：**首帧与尾帧都给同一张参考图**（这是"闭环"的关键）。
3. 粘贴 §4.x 的**整条正向提示词** + §2.5 负向词。
4. 参数：
   - 比例 **9:16 竖屏**；分辨率 **1080×1920** 优先（720×1280 也可，现役素材就是 720×1280）
   - 时长 **10s**（平台只给 5s 也可接受；此时把"动作幅度"再压小一档）
   - 若有"运动幅度 / 动态强度"档位 → 选**低档**
5. 同状态出 **2~3 个候选**，按 §6 清单打分，只留 1 个（省额度，别反复重抽）。
6. 下载命名 `<素材名>.mp4`（如 `idle_listening.mp4`），**与原始素材放一起，不要直接拷进 `assets/avatar/`**。
7. 跑关键帧核验（FAIL 就换候选/重生成）：

```bash
cd "D:\share\项目开发\FPGA语音助手开发\wujing-lite"
python tools/avatar_keyframes.py --src "D:\...\<素材名>.mp4" ^
    --out-dir "evidence_shots\keyframes" --check-loop ^
    --ref "D:\share\项目开发\实体桌宠\桌宠动作素材生成提示词_20260901\refs\idle_normal_t00.00_f000000.png"
```

> ✅ **2026-09-12：`--ref` 已支持非 ASCII（中文）路径** —— 上面这条指向 `实体桌宠\…\refs\` 的示例可直接执行。
> 此前 Windows 下 `cv2.imread` 读不了中文路径（报"无法读取参考图"），只能改用工程内 ASCII 副本
> `evidence_shots\avatar_ref_idle_normal_f000000.png`（与原图 sha256 相同、可互换）。
> 根因与修复记录见 `docs/关键帧工具非ASCII路径兼容_技术记录.md`。

8. 通过后入库（原始素材只读，工具自动抠像 + 降采样 + 落清单）：

```bash
python tools/prepare_avatar_frames.py --src "D:\...\<素材名>.mp4"
python tools/prepare_avatar_frames.py --verify
python tools/make_asset_gallery.py --name <素材名> --panel-at 0,1.5,3
```

> 批量：把 7 条 mp4 放同一目录（`<素材名>.mp4`）→ `prepare_avatar_frames.py --src "<目录>"` 一次入库。

### 5.1 即梦界面实况：没有「负面提示词」输入框，怎么办

> **实测（2026-09 即梦网页版）**：视频生成面板**只有 1 个提示词框**，**没有独立的 negative prompt 输入框**
> （负面词框只在**图片生成**里偶有）。所以 §2.5 的负向词**不能单独填**，
> 必须**内联追加到正向提示词末尾**。

**做法**：把 §2.5 那串词以一个引导词接在正向提示词后面即可，例如：

```text
...（§4.x 整条正向提示词）... strictly identical to @character.png. Negative prompt: green spill, green rim light, ... outline blur
```

> 提示词框左侧的 **「首帧 / 尾帧」两个 `+` 框都要上传同一张参考图**（见上面步骤 2）；
> 底部最右的 `🪄` 是"提示词优化"、`✦ 25` 是本次消耗的积分 —— **都不是负面词入口**。

#### 5.1.1 提示词框字数上限（粘贴前先看计数器）

本包单条完整提示词（整段正向 + 内联负向）实测字符数：

| 素材 | 正向 | + 负向(733) | 合计 |
|---|---|---|---|
| §4.1 `idle_present` | 1738 | 733 | **2489** |
| §4.2 `idle_listening` | 1665 | 733 | **2416** |
| §4.3 `idle_thinking` | 1620 | 733 | **2371** |
| §4.4 `talking_normal` | 1619 | 733 | **2370** |
| §4.5 `emo_puzzled` | 1678 | 733 | **2429** |
| §4.6 `idle_offline` | 1676 | 733 | **2427** |
| §4.7 `emo_sad` | 1627 | 733 | **2378** |
| §4.8 `talking_low` | 567 | 733 | **1300** |

> §4.8 是本包**最短**一条（1300），任何上限档位都不会被截断，负向词直接用 §2.5 全量即可。
> 粘贴前**先看提示词框的 `x / N` 计数器**。若上限 < 2400 会被**从尾部截断**，
> 而尾部恰好是负向词里的"防缩放"串 —— 一旦丢掉，10 态切换就会跳大小。
> 因此超限时按下表替换 §2.5（**务必保留 `zoom in / zoom out / character size drift / cropping change` 四项**）。

**负向词精简档 A（389 字符，保留全部视觉质量项）**：

```text
green spill, green rim light, soft edges, 3d render, photorealistic, real human face, deformed hands, extra fingers, motion blur, camera shake, zoom in, zoom out, dolly, character size drift, cropping change, walking out of frame, transparent background, background objects, floor shadows, text, watermark, low quality, blurry, pixelated, flickering, morphing, color bleeding, outline blur
```

**负向词精简档 B（233 字符，只留防缩放/防走位核心）**：

```text
3d render, photorealistic, deformed hands, extra fingers, motion blur, camera shake, zoom in, zoom out, dolly, character size drift, cropping change, walking out of frame, text, watermark, low quality, blurry, green spill, soft edges
```

> 用 A 档单条总长约 **2020~2140**，用 B 档约 **1870~1990**。
> 若仍超限，再删 §2.4 画质段（263 字符，其内容与负向词大量重复）。

### 5.2 模型选哪个（即梦 Seedance）

| 档位 | 推荐度 | 理由 |
|---|---|---|
| **即梦 Seedance 2.0（标准版，非 Fast）** | ✅ **首选** | 细节与提示词遵循度更好；同样支持「首尾帧」，构图不漂 |
| 即梦 视频 3.0 Pro | ⭕ 备选 | 老一代但运动更稳、首尾帧控制成熟；细节略逊 |
| 即梦 Seedance 2.0 **Fast** | ❌ **不推荐** | 速度换质量：快档更容易丢细节 / 私自推近镜头 → 10 态切换会跳大小 |

- **同一批 7 条素材用同一个模型档**生成，避免风格 / 清晰度不一致；
- 时长尽量选 **10s**（若该模型档只有 5s，按上面步骤 4 把动作幅度再压一档）；
- 分辨率 **720P 起**（现役素材即 720×1280）；若要 1080×1920 需模型档支持。

---

## 6. 验收清单（数字判据，逐素材打勾）

| 检查项 | 判据 | 手段 |
|---|---|---|
| 首尾帧自循环 | 主体区 mean ≤ 2.0 **且** 差异像素(>8) ≤ 2% | `avatar_keyframes --check-loop` |
| 跨素材一致性 | 首帧 vs 参考图 mean ≤ 4.0、差异像素 ≤ 5% | `avatar_keyframes --ref` |
| 构图无缩放 | 人物高度占比 93%±3%、头顶距上边 7%±3%；差异热力只亮在发丝/褶皱 | `--ref` 的 `*_ref_check.png` |
| 绿幕均匀无溢色 | 角色边缘无绿光/绿边、无阴影渐变 | `*_loop_check.png` 目检 + 抠像边缘 |
| 提示词未被截断 | 生成前看即梦提示词框 `x / N` 计数器；末尾负向词完整保留 | 人眼（见 §5.1.1） |
| 无一次性动作 | 完整播一遍没有"招手/点头/耸肩"式异动或回弹 | `make_asset_gallery` 的循环 GIF |
| 无残影/穿模 | 手部无多指、发丝无 ghosting、托腮不粘连 | GIF 慢放目检 |
| 入库规格 | 长边 ≤320、10fps、≤10 MiB | `prepare_avatar_frames.py --verify` |
| 面板观感 | 180×320 下表情仍可辨识 | `make_asset_gallery --panel-at 0,1.5,3` |

---

## 7. 入库规格与"播放时长不变"提醒

- 源 10s@24fps → 入库 **100 帧 @9.983fps**：帧率不是整数 10 是因为
  **保持播放时长不变**（`avatar_lod.effective_fps`），动作不会变慢。
- 默认：长边 ≤320（→180×320）+ 10fps + PNG，单素材预算 10 MiB（超了用 `--fit-budget` 降帧）。
- 素材体积档位表见 `assets/avatar/README.md` 第 4.1 节。
- ⚠️ **板端已定档（1024×600，人物区占右侧 3/7 ≈ 439 px 宽）**：9:16 素材在板端显示 **337.5×600**，
  320 档会被放大 **×1.88**（偏糊）；建议入库改用 **480 档**（×1.25，17.75 MiB/状态）或
  **600 档**（1:1，25.68 MiB/状态，需 `--budget-mb 27`）。
  **提示词与素材本身不用改**（构图仍是竖屏 9:16，只改降采样档位这一步），推导见
  `docs/板端显示定档与玩偶素材LOD复核_技术记录.md`。

---

## 8. 涉及文件

| 文件 | 作用 |
|---|---|
| `wujing-lite/tools/avatar_keyframes.py` | **本次新增**：抽关键帧 + 首尾帧循环/跨素材一致性核验（`--check-loop/--ref/--find-loop`） |
| `wujing-lite/tests/test_avatar_keyframes.py` | **本次新增**：27 项单测（全库 152 项通过） |
| `实体桌宠\桌宠动作素材生成提示词_20260901\refs\idle_normal_t00.00_f000000.png` | 参考图（所有素材的首帧/尾帧锚点，**本次实测产出**） |
| `wujing-lite/docs/玩偶素材Seedance提示词包_技术记录.md` | 本文档 |
| `wujing-lite/assets/avatar/README.md` | 入库规范（本次补关键帧核验小节） |
| `wujing-lite/docs/玩偶帧序列素材接入_技术记录.md` | 入库流水线记录（本次补关键帧核验小节） |

---

## 9. 下一步

1. 用户在 Seedance 逐态生成 → 每态跑 §5 第 7~8 步，**先做 `idle_listening` 试产**（与 IDLE 差异最小、最容易判断一致性）；
2. 9 条素材全部入库后：`--verify` → `pytest tests -q` → `make_asset_gallery.py` 出 10 态证据图；
3. 板端显示分辨率已定档（**1024×600，人物区占右侧 3/7**）→ 入库档位建议由 320 上调到
   **480（×1.25）或 600（1:1）**，7 态齐了后一次性重跑：
   `prepare_avatar_frames.py --src "<目录>" --max-side 600 --budget-mb 27 --force`；
   详见 `docs/板端显示定档与玩偶素材LOD复核_技术记录.md`（含实测体积与 RGB565 底色坑）。

> 原始素材（`*.mp4`）始终**只读**：工具仅读取并记录 sha256，不修改、不移动、不入库。

---

## 10. 复核记录（2026-09-11 · 看锚点图实物后）

**触发**：准备开跑 `idle_listening` 之前，把锚点图 `evidence_shots/avatar_ref_idle_normal_f000000.png`
调出来逐项核对提示词，确认"情绪节点"与"提示词效果"是否还成立。

**核对结论**

| 项 | 结论 |
|---|---|
| 9 个情绪节点 | 与 `board/runtime/fsm.py` 的 `RuntimeState` **逐字一致**：IDLE / PRESENT / LISTENING / THINKING / SPEAKING / CAMERA_LOST / NETWORK_LOST / CANCELLED / ERROR |
| 状态 → 素材映射 | 与 `board/ui/avatar_assets.py` 的 `STATE_ASSET` **逐条一致**（`CANCELLED` 复用 `idle_normal`；`FALLBACK_ASSET = idle_normal`） |
| 提示词长度 | 单条 **2370 ~ 2489** 字符（正向 1619~1738 + 负向 733），见 §5.1.1 |
| 核验阈值 | 未变：`--check-loop` 主体 mean ≤2.0 且差异像素(>8) ≤2%；`--ref` mean ≤4.0、差异像素 ≤5% |

**发现与处理（3 条，均已写回 §4.x）**

1. **微笑会被继承**：锚点图嘴角已上扬、带腮红 ⇒ 情绪态不显式覆盖就会一直"笑着"，沮丧/困惑/离线态**表达失效**。
   → §4.5 / §4.6 / §4.7 动作段增补 `the slight smile fades away …` / `mouth corners turned down`。
2. **画面里看不见手**：锚点图双手藏在宽大和服振袖内 ⇒ "托腮 / 交握"没有落点，模型会乱飘袖口。
   → §4.3 / §4.7 增补 `hand emerges from the wide kimono sleeve`，并约束"袖子自然垂落、不遮脸"；
   §4.1 / §4.2 改为 `hands inside the wide kimono sleeves`（与原图一致，不再描述看不见的手指）。
3. **右侧长辫甩出画面、袖口贴左右两边**：往画面右侧歪头 / 抬手会把辫子与袖口推出画框。
   → §4.2 歪头**锁死画面左侧**（她的右肩侧）；§4.5 抬手改为"**只抬到胸口高度**，袖子垂直下垂不遮脸"。

**连带澄清（重要）**：首尾帧同图 ⇒ 聆听态必然是"头从中线缓慢歪出、末帧缓慢回正"，
所以 §4.2 "整段同侧"指的是**中段不翻面**，末帧回正属闭环所需，不是缺陷。

**未改动**：六段式骨架（§2.1~§2.5）、9 态映射、核验阈值与所有命令行示例均保持原样；
本次新增 §2.6（继承效应总表）、§5.1.1（字数上限与两档负向词降级）、§6 增一行"提示词未被截断"。

---

## 11. 2026-09-12 情绪分档扩展：播报拆「高涨 / 低落」两档（**情绪节点 9 → 10**）

**触发**：`talking_normal` 入库后目检确认其演绎为**情绪高涨**（前段双拳举起张嘴、中段右手张开说话、后段握拳，
手势丰富）；需求是在既有情绪节点上再增加一个**情绪低落**的说话状态。

**改动清单**

| 项 | 内容 |
|---|---|
| 新节点 | **`SPEAKING_LOW`**（播报·情绪低落），与 `SPEAKING`（播报·情绪高涨）并列 |
| 新素材名 | **`talking_low`** —— 提示词见本文 **§4.8**（正向 567 字符） |
| 触发来源 | `schemas/dialogue_response.schema.json` 的 `emotion` 字段：命中 `fsm.LOW_EMOTIONS` → 走低落档 |
| 状态机 | `board/runtime/fsm.py`：新增枚举 + `_route_emotion()` **目标后置路由**（事件合同零改动）+ 播报结束/取消/故障转换 |
| 数据合同 | `ui_spec/ui_state.schema.json` 的 `runtime_state.enum` 增补 `SPEAKING_LOW`（`schema_version` 仍为 `1.0`，**加性变更**） |
| 表现映射 | `board/ui/avatar_fsm.py`：`SPEAKING_LOW = AvatarSpec("speak", "sad", "播报·低落", "accent")` |
| 素材回退 | `board/ui/avatar_assets.py`：`FALLBACK_BY_STATE["SPEAKING_LOW"] = ("talking_normal",)` → 未入库时先退**高涨播报**，再退 `idle_normal`，最后 B2V 矢量 |
| 验证 | `pytest` **205 passed / 0 failed**（5.5 s）；`run_ui.py --all-states` 出 **10 张**板图（新增 `evidence_shots/ui_board_speaking_low.png`） |

**未改动**：六段式骨架（§2.1~§2.5）、既有 7 条提示词原文、核验阈值（`--check-loop` 主体 mean ≤2.0 / 差异 ≤2%；
`--ref` mean ≤4.0 / 差异 ≤5%）、既有素材与既有状态映射（`SPEAKING` 仍指 `talking_normal`）。

**执行结果（2026-09-12 当天闭环）**：`talking_low.mp4`（源 `jimeng-2026-09-12-3869-…mp4`，11,061,593 B，
sha256 `1663ecc4…adc7`）已按 §4.8 生成并入库 —— 关键帧核验 **循环缝 WARN（主体 mean 2.63 / 差异 2.77%）**、
**vs `talking_normal` 首帧 PASS（主体 mean 2.13 / 差异 1.16%）**；入库规格
**466×480 / waist-up / 100 帧 / 24.8 MiB**，`--verify` **6/6 [OK]**、`--status` **6/9**。
完整技术记录见 `docs/TALKING_LOW素材入库与同代一致性核验_技术记录.md`
（分档设计与决策见 `docs/情绪分档扩展_播报高低落两档SPEAKING_LOW_技术记录.md`）。

---

## 12. 情绪节点口径拆分（2026-09-12）：**表达性 6 + 系统·故障 4**

**背景**：此前文档把「情绪节点」直接等同于 `RuntimeState` 的**全量**成员（§10 即"9 个情绪节点 = 9 态"），
于是「摄像头丢失 / 网络丢失 / 已取消 / 错误」也被当成"情绪"来讨论与评审。实际它们**不是情绪**，
而是**系统/故障态** —— 由系统事件驱动，素材上或复用、或只是"降级表演"。

**新口径（本包与 `assets/avatar/README.md`、`docs/ui_consistency_checklist.md` 统一）**：

| 组 | 数量 | 节点 | 特征 |
|---|---|---|---|
| ① **表达性节点** | **6** | IDLE 待机 / PRESENT 探头·注视 / LISTENING 倾听 / THINKING 思考 / **SPEAKING 说话·情绪高涨** / **SPEAKING_LOW 说话·情绪低落** | 需**专门生成**素材与提示词；演出设计（动作段）以此为准 |
| ② **系统·故障态** | **4** | CAMERA_LOST 摄像头丢失 / NETWORK_LOST 网络丢失（本地模式） / CANCELLED 已取消 / ERROR 错误 | 由**系统事件**驱动；`CANCELLED` 复用 `idle_normal`，其余为降级表演 |

**红线（本次零改动）**：`board/runtime/fsm.py` 的 `RuntimeState` 成员、`ui_spec/ui_state.schema.json` 枚举、
`avatar_assets.STATE_ASSET` 映射、`avatar_fsm.AVATAR_MAP` **全部保持 10 态原样** ——
本次**只是文档口径分组**，板上逻辑与单测**零改动**（`pytest` 仍 205 passed）。

**为什么要拆**：把故障态混在"情绪"里会让素材评审含糊（例如把 `emo_puzzled` 当成"困惑**情绪**"，
而它的真实身份是 `CAMERA_LOST` 的**降级表现**），也让"情绪节点齐了没有"这种问法**无法回答**。
拆分后：
- **表达性 6 个** = 可枚举、可逐条验收的清单（对应 `--all-states` 里的 6 张"有专门素材"的板图）；
- **系统·故障 4 个** = 按事件驱动，允许复用/降级，验收标准是"**不白屏、语义正确**"。

**§10 复核记录怎么读**：该节写于 2026-09-11，当时"9 个情绪节点 = `RuntimeState` 9 态"的表述
**按当时口径成立**；自本节起改为两组口径理解：**表达性 6 + 系统·故障 4 = 10 态**（9/12 分档后）。



