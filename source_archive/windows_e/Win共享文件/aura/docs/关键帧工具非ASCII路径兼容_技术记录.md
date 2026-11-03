# 关键帧核验工具非 ASCII（中文）路径兼容 技术记录

> 日期：2026-09-12 ｜ 环境标签：PC / SIMULATED（素材质检工具链，非板端）
> 关联：`docs/玩偶素材Seedance提示词包_技术记录.md` §1.1/§5（核验命令示例）、
> `docs/素材排队应对方案.md` §四（增量入库 SOP）、`docs/聆听素材入库与一致性核验_技术记录.md`

## 一、背景与目标

在准备 `idle_present` 素材前做锚点核对时，按提示词包 §5 的原样示例、把 `--ref` 指向**上游中文路径**的锚点图，工具直接报"无法读取参考图"：

```text
[ WARN:0@0.537] global loadsave.cpp:278 cv::findDecoder imread_('D:\share\椤圭洰寮€鍙慭...'): can't open/read file: check file path/integrity
无法读取参考图: D:\share\项目开发\实体桌宠\桌宠动作素材生成提示词_20260901\refs\idle_normal_t00.00_f000000.png
```

**目标**：让核验工具对非 ASCII 路径（中文目录/文件名）可用，去掉"必须记得用 ASCII 副本"的隐性依赖。

## 二、根因

1. `cv2.imread / cv2.imwrite` 在 Windows 上走 **ANSI 文件 API**：路径含中文时内部被转成 GBK 乱码 → 直接返回 `None`（日志里的 `椤圭洰寮€鍙慭` 就是 UTF-8 路径被 GBK 解码的乱码）。
2. `tools/avatar_keyframes.py` 中 **4 处读图 + 1 处写图回退**都用了 imread/imwrite：
   `probe_source`（帧目录探测）、`read_frame`（帧目录取帧）、`find_best_loop`（扫描最佳循环点）、`_load_ref`（参考图）、`save_rgb`（Pillow 缺失时的回退）。
3. 之前一直没暴露，是因为所有既有调用**碰巧**都是 ASCII 路径：`--ref` 一律用工程内 `evidence_shots\avatar_ref_idle_normal_f000000.png`，输出目录也都是 ASCII；`tools/ui_mock_draft.py` 甚至显式"先把中文路径的源帧拷到 ASCII 临时路径再读"来绕过同一问题（见该文件第 21、77 行注释）。

## 三、方案对比与选型

| 维度 | 方案 A：不改代码，只用 ASCII 副本 | **方案 B：改工具（`imdecode`/`fromfile`）← 采用** |
| --- | --- | --- |
| 改动量 | 0 行 | **1 个文件、2 个新 helper、5 处替换（≤20 行）** |
| 一次性成本 | 0 | 约 20 分钟（含 3 条单测） |
| 稳定性 | 低：靠"人记得"与约定 | **高：根治，任意路径可用** |
| 最坏失败模式 | **静默用旧锚点图判 PASS（假绿）**——锚点图换代时副本忘记同步，跨素材一致性核验失真，且不报错 | 读失败即报错，不会静默 |
| 对"锚点图换代"（必然发生） | 需人工同步副本 + 记录 sha256 | 无需副本，天然正确 |
| 跨人 / 跨机 | 约定易漏（新同事、另一台机器） | 与路径无关 |
| 覆盖范围 | 只覆盖 `--ref` 一个入口 | 同时覆盖 `--src` 帧目录、输出对比图等全部入口 |
| 回归风险 | 无 | 低：`imdecode` 与 `imread(IMREAD_UNCHANGED)` 语义一致，原有 192 项单测兜底 |

**结论：选方案 B。** 方案 A"成本为 0"是假象——它把**一致性核验的正确性**绑在人的记忆上，而失败模式是**静默假绿**（比报错危险得多）；方案 B 的增量成本是一次性的、可被单测锁死，因此边际成本更低、稳定性高一个量级。

## 四、做了什么（改动清单）

| 位置 | 变更 |
| --- | --- |
| `tools/avatar_keyframes.py` 新增 `_imread()` | `np.fromfile(path, dtype=uint8)`（Python 层，Unicode 安全）+ `cv2.imdecode(data, IMREAD_UNCHANGED)`，语义等价于原 `cv2.imread`；文件不存在/空文件返回 `None`（保持原调用点的判空逻辑） |
| `tools/avatar_keyframes.py` 新增 `_imwrite()` | `cv2.imencode(后缀, arr)` + `buf.tofile(path)` |
| 4 处读图 | `probe_source` / `read_frame` / `find_best_loop` / `_load_ref` 的 `cv2.imread(...)` → `_imread(...)` |
| 1 处写图 | `save_rgb` 的 cv2 回退 → `_imwrite(path, arr)`（顺带删掉该分支里已无用的 `cv2 = _cv2()`） |
| `tests/test_avatar_keyframes.py` | 新增 3 条回归单测：`test_imread_handles_non_ascii_path`（读写往返）、`test_probe_source_on_non_ascii_frames_dir`（中文帧目录探测）、`test_cli_ref_check_accepts_non_ascii_ref_path`（CLI 端到端 `--ref` 中文路径必须 PASS） |
| `docs/玩偶素材Seedance提示词包_技术记录.md` §5 步骤 7 | 补一条说明：`--ref` 现已支持中文路径，示例可直接执行 |

> **未改动**：`cv2.VideoCapture`（mp4 分支）—— 它本身支持 Unicode 路径（实测中文路径 `idle_normal.mp4` 读取正常：720×1280 / 24.06 fps / 241 帧），无需处理；判定阈值、CLI 参数、输出文件名与"原始素材只读"约定均未变。

## 五、验证方式与结果

1. **复现场景验收（修复前报错那条命令，一字未改）**：

```powershell
python tools\avatar_keyframes.py --src "D:\share\项目开发\桌面AI桌宠\assets\videos\idle_normal.mp4" `
    --out-dir "%TEMP%\chk_anchor" --name chk_cn_path --count 1 `
    --ref "D:\share\项目开发\实体桌宠\桌宠动作素材生成提示词_20260901\refs\idle_normal_t00.00_f000000.png"
```

结果：`[一致性核验] … -> PASS`，全图 `mean=0.00`、主体 `mean=0.00`、差异像素 `0.00%`，`EXIT=0`。

> 附带确认（同一现象的两面）：**锚点图 == 现役 `idle_normal.mp4` 的首帧**（像素级 mean 0.00）；两支锚点图（上游 `refs\` 原图 与 工程内 `evidence_shots\avatar_ref_idle_normal_f000000.png`）sha256 相同（`5B4084CD…4C4BBD8`）；源 mp4 sha256 `ce007253…59ECDF` 与 `idle_normal/meta.json` 记录一致。

2. **回归**：`python -m pytest -q` → **195 passed**（原 192 + 新增 3），无改动其他测试。
3. **未回归项**：mp4 分支未动（`VideoCapture`），原先通过的 mp4 相关单测继续通过。

## 六、涉及文件

| 文件 | 变更 |
| --- | --- |
| `tools/avatar_keyframes.py` | 新增 `_imread` / `_imwrite`；4 处读图 + 1 处写图替换 |
| `tests/test_avatar_keyframes.py` | 新增 3 条非 ASCII 路径回归单测；补 `import shutil` |
| `docs/玩偶素材Seedance提示词包_技术记录.md` | §5 步骤 7 补"支持中文路径"说明 |
| `docs/关键帧工具非ASCII路径兼容_技术记录.md` | 本文档（md + docx） |

## 七、下一步 / 备注

- 提示词包 §5 步骤 7 里那条**中文路径示例现在可直接执行**，无需再先拷 ASCII 副本。
- `tools/ui_mock_draft.py` 的"拷到 ASCII 临时路径再读"绕过逻辑已被本修复覆盖，可在板端 UI 验收后随该草案文件一并删除（已列入清理项）。
- 与本修复无关、仍挂起的事项：`idle_normal` 按 waist-up 口径重生成；素材 alpha 包围盒归一化（可选项）。
