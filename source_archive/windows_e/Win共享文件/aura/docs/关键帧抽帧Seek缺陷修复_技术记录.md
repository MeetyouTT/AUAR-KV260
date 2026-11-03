# 关键帧抽帧 Seek 缺陷修复 · 技术记录

> 模块：`wujing-lite/tools/avatar_keyframes.py`
> 单测：`wujing-lite/tests/test_avatar_keyframes.py`
> 记录日期：2026-09-11

## 1. 背景与目标

`avatar_keyframes.py` 是玩偶素材质检第一关：抽关键帧 + 核验「首尾帧自循环 / 跨素材一致性」。
在核对「Seedance 首尾帧锚点图」时发现：抽出的**中间关键帧**与首帧**字节完全相同**，
顺藤摸瓜定位到一处**随机定位（seek）缺失**的缺陷。本文记录根因、影响面、修复与验证。

## 2. 现象（怎么发现的）

对现役 `idle_normal.mp4`（720×1280 @24.06fps，241 帧，10.02s）执行 `--count 3`，三张关键帧里：

| 文件 | sha256(前16) | 判断 |
|---|---|---|
| `idle_normal_t00.00_f000000.png` | `5B4084CD282A8FB8` | ✅ f0 |
| `idle_normal_t05.03_f000121.png` | `5B4084CD282A8FB8` | ❌ 与 f0 完全相同（异常） |
| `idle_normal_t09.98_f000240.png` | `3B1D082DD9196F80` | ✅ f240 |

随后用 OpenCV **逐帧直读**源视频交叉验证：

```text
f0 vs f121 : mean=11.7812  diff>8 = 30.562%   ← 本来就不同
f0 vs f120 : mean=12.5473  diff>8 = 31.679%
f0 vs f240 : mean=17.0506  diff>8 = 40.463%
```

即 **f0 ≠ f121**，但抽帧结果却一样 → 问题出在抽帧环节。

## 3. 根因

`read_frame()`（mp4 分支）只对「末帧」做了定位，**普通帧完全没有 `cap.set(POS_FRAMES, target)`**：

```python
# 修复前（有缺陷）
target = ...
if total and target >= total - 1:      # 只有末帧 seek
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(total - 2, 0))
    cap.read()
ok, frame = cap.read()                 # ← 中间帧从未 seek，永远读到「首帧」
```

`cv2.VideoCapture` 打开后默认停在**第 0 帧**，不 seek 就一直读首帧。
因此任何 `0 < index < total-1` 的抽帧都返回 f0。
（末帧走了「退回一格再连读两帧」分支，恰好读对，所以只有**中间帧**出错。）

## 4. 影响面

| 用法 | 是否受影响 | 说明 |
|---|---|---|
| `--count 1`（只抽首帧当参考图） | ❌ 无影响 | f0 本来就是对的 |
| `--count N`（N>2）的**中间关键帧 PNG** | ✅ 受影响 | 全被写成 f0，证据图失真 |
| `--check-loop`（首帧 vs 末帧） | ⚠️ 基本无影响 | 首、末帧都对 → 判定结论有效 |
| `--find-loop` 的**扫描** | ❌ 无影响 | 走顺序 `cap.read()`，不经过 `read_frame` |
| `--find-loop` 落盘的 `loop_best_f*.png` | ✅ 受影响 | 最佳帧非 0 时会存成 f0 |

> 关键结论：**结论层（PASS/FAIL）没有被推翻**，受影响的是**中间关键帧证据图**。
> 单测此前全绿，是因为端到端用例全部用「**帧目录**」当源，绕开了 mp4 分支。

## 5. 修复

```python
# 修复后：先 seek 到目标帧；末帧退回一格再连读两帧
start = max(target - 1, 0) if (total and target >= total - 1) else target
cap.set(cv2.CAP_PROP_POS_FRAMES, start)
ok, frame = cap.read()
if ok and start != target:             # 末帧：补读一帧到目标
    ok2, frame2 = cap.read()
    if ok2:
        ok, frame = True, frame2
```

## 6. 验证

1. **新增回归单测**（此前无 mp4 用例，正是漏网原因）：
   - `test_read_frame_seeks_to_middle_and_last`：用 `cv2.VideoWriter` 造「每帧前景色不同」的 mp4，
     断言 `read_frame(0) ≠ read_frame(mid) ≠ read_frame(last)`；
   - `test_cli_count_middle_keyframes_are_not_first_frame`：`--count 3` 抽出的三张 PNG 字节互不相同。
2. **全库测试**：`python -m pytest tests -q` → **154 项全通过**（原 152 + 新增 2）。
3. **真实素材回归**（重跑 `idle_normal.mp4`）：
   - `t05.03_f000121.png` 哈希由 `5B4084CD…` → `D5F3045C…`（**已变成真的 f121**）；
   - `t00.00_f000000.png` 哈希不变（`5B4084CD…`，**锚点图未受影响**）；
   - 循环核验结果不变：首帧 f0 vs 末帧 f240 → **FAIL**，主体 mean=19.90、差异像素 47.28%。

## 7. 涉及文件

| 文件 | 改动 |
|---|---|
| `wujing-lite/tools/avatar_keyframes.py` | 修 `read_frame()`：补 seek（含末帧补读） |
| `wujing-lite/tests/test_avatar_keyframes.py` | 新增 2 项 mp4 回归单测（27 → 29） |
| `实体桌宠\...\refs\idle_normal_t05.03_f000121.png` 等 | 用修复后工具重跑，中间关键帧已修正 |

## 8. 下一步

- 每个新素材抽帧后，**看一眼中间关键帧是否互不相同**（或直接依赖新增的两条回归单测）；
- `--find-loop` 的**扫描**本身可信（顺序读帧），其「裁剪建议」可用于后续素材。
