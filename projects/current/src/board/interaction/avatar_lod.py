# -*- coding: utf-8 -*-
"""avatar_lod —— 玩偶素材**入库规格（LOD）**纯逻辑：降采样尺寸 / 抽帧索引 / 体积预算 / 清单校验。

## 为什么要 LOD
原始 Seedance 绿幕素材为 **720×1280 @24fps**，抠像后单帧 ≈**1.23MB**、单状态 241 帧 ≈**290MB**、
9 态全量 ≈**2.5GB**：PC 原型跑得动，但**板端 LVGL 既放不下也跑不动**。
故约定：**入库素材统一降采样**（等比缩到「长边 ≤ max_side」+ 按「目标帧率」抽帧），
同时记录**原始素材指纹**；**原始素材本体保持原样、从不修改**（生成脚本只读）。

## 入库产物（由 scripts/prepare_avatar_frames.py 写出）
    assets/avatar/<素材名>/000000.png      降采样后的帧（RGBA PNG，按名排序 = 播放顺序）
    assets/avatar/<素材名>/meta.json       fps / size / spec / source（原始素材指纹）
    assets/avatar/<素材名>/manifest.json   每帧 sha256 + 字节数（可校验、可复现）

## 依赖
本模块**纯逻辑**（仅标准库，不依赖 Qt / cv2 / numpy），因此可脱机单测，
也可被板端工具链复用（板端只需读 meta.json 即可得到 fps 与尺寸）。
"""
from __future__ import annotations

import hashlib
import json
import typing
from pathlib import Path

# --------------------------------------------------------------------------- #
# 默认规格（实测标定：见 docs/玩偶帧序列素材接入_技术记录.md 第 5.3/5.4 节）
# --------------------------------------------------------------------------- #
# 长边上限（像素）：320 → 竖屏 9:16 素材 = 180×320；单帧 PNG ≈80KB、RGB565 ≈112KB
# （实测表见 docs/玩偶帧序列素材接入_技术记录.md 第 5.4 节）
DEFAULT_MAX_SIDE: int = 320
# 目标帧率：10fps 对玩偶待机/口播足够，且把 10s 素材压到 ≈100 帧（板端可流畅播）
DEFAULT_FPS: float = 10.0
# 单素材入库体积预算（MiB）：超出即告警，`--fit-budget` 也会据此自动降帧率
# v2 调整（状态系统重设计 §10① 拍板 B）：10.0 → 12.5，目的是**保住 24fps**
# ——39 帧 / 480 宽实测 ≈12.2 MiB，按 10.0 会被 --fit-budget 降到 ~19fps 而失去流畅度。
DEFAULT_BUDGET_MB: float = 12.5
# 板端无 alpha 帧流：每像素 2 字节（R5|G6|B5）
RGB565_BYTES_PER_PIXEL: int = 2
# straight-alpha RGBA PNG 的实测经验系数（字节/像素）：180×320→1.53、216×384→1.43、
# 360×640→1.24、108×192→1.73（素材越小人像占比越高，系数越大）→ 取 1.5 偏保守
PNG_BYTES_PER_PIXEL: float = 1.5
# 预算自适应候选帧率阶梯（高→低；用于 --fit-budget 自动挑选能装进预算的帧率）
FPS_LADDER: typing.Tuple[float, ...] = (24.0, 20.0, 16.0, 15.0, 12.0,
                                        10.0, 8.0, 6.0, 5.0, 4.0)

MANIFEST_NAME: str = "manifest.json"


# --------------------------------------------------------------------------- #
# 1.5) 取景（framing）：板端玩偶只显示「腰部以上」
# --------------------------------------------------------------------------- #
# 背景：板端三区布局的右上玩偶框为 **423×516**（1024×600，见 ui/ui_layout_spec.json）。
# 竖屏 9:16 全身素材 contain 进该框时人物偏小、且下半身白占高度（实测显示仅 290×516）。
# 实测裁掉下部 42%（= 保留上部 58% ≈ 腰部以上）后：
#     720×1280 → 裁切 720×742 → 480 档 466×480 → 框内显示 **423×436**（占宽 100%、放大 0.59×）
# 关键：**裁切只裁纵向、宽度与左上角不变**，且发生在降采样之前 →
#      等比缩放倍率不变（仍是缩小采样），"人物变大"来自可视区变矮而非拉伸。
# 决策与证据：docs/UI三区布局草案渲染_技术记录.md（草案图 docs/ui_draft/）。
FRAMING_PRESETS: typing.Dict[str, float] = {
    "full": 0.0,        # 不裁切（膝上全身，历史口径；现役 idle_normal 即此档）
    "waist-up": 0.42,   # 裁掉下部 42% = 保留上部 58%（腰部以上，板端定稿口径）
}


def parse_framing(framing: str,
                  crop_bottom_ratio: typing.Optional[float] = None) -> float:
    """取景名（或显式比例）→ 底部裁切比例。

    - `crop_bottom_ratio` 给出时**优先**（支持自定义比例，如 0.46 = 保留上部 54%）；
    - 否则查 `FRAMING_PRESETS`；**未知取景名直接抛 ValueError**，不静默按 full 入库；
    - 结果必须落在 [0, 1)，否则抛 ValueError。
    """
    if crop_bottom_ratio is not None:
        ratio = float(crop_bottom_ratio)
    else:
        key = str(framing or "full")
        if key not in FRAMING_PRESETS:
            raise ValueError("未知取景 %r（可选: %s）"
                             % (key, ", ".join(sorted(FRAMING_PRESETS))))
        ratio = FRAMING_PRESETS[key]
    if not (0.0 <= ratio < 1.0):
        raise ValueError("底部裁切比例必须落在 [0, 1)：%r" % (ratio,))
    return ratio


def crop_box(width: int, height: int,
             bottom_ratio: float = 0.0) -> typing.Tuple[int, int, int, int]:
    """裁掉下部 `bottom_ratio` 后返回 `(x, y, w, h)`（供 `QImage.copy` / 尺寸规划用）。

    - **只裁纵向**：`x/y` 恒为 0、`w` 不变，只缩小 `h` → 缩放倍率不受裁切影响；
    - `h = round(height × (1 - bottom_ratio))`（不做奇偶规整，最终偶数由 `target_size` 负责，
      保持与草案渲染器 `scripts/ui_mock_draft.py::crop_bottom` 完全一致：1280×0.58 = 742）；
    - 比例须落在 [0, 1)、尺寸须为正，否则抛 ValueError；
    - `bottom_ratio = 0` → 原尺寸矩形。
    """
    if width <= 0 or height <= 0:
        raise ValueError("原始尺寸必须为正: %rx%r" % (width, height))
    ratio = parse_framing("full", bottom_ratio)
    keep_h = int(round(height * (1.0 - ratio)))
    return 0, 0, int(width), max(2, keep_h)


# --------------------------------------------------------------------------- #
# 1) 目标尺寸
# --------------------------------------------------------------------------- #
def target_size(width: int, height: int,
                max_side: int = DEFAULT_MAX_SIDE) -> typing.Tuple[int, int]:
    """等比缩放到「长边 ≤ max_side」，宽度规整为偶数（≥2）。

    - **不放大**（素材本身小于规格时保持原尺寸，仅规整宽度奇偶）；
    - `max_side <= 0` 表示「不缩放」（同样只规整宽度）；
    - 原始尺寸非法（<=0）抛 ValueError。

    宽度取偶数是为了板端 RGB565 / 行对齐不出现半像素。
    """
    if width <= 0 or height <= 0:
        raise ValueError("原始尺寸必须为正: %rx%r" % (width, height))
    if max_side <= 0 or max(width, height) <= max_side:
        tw, th = width, height
    else:
        scale = max_side / float(max(width, height))
        tw, th = int(round(width * scale)), int(round(height * scale))
    tw = max(2, tw - tw % 2)
    th = max(2, th - th % 2)
    return tw, th


# --------------------------------------------------------------------------- #
# 2) 抽帧（时间均匀，不插帧）
# --------------------------------------------------------------------------- #
def select_indices(count: int, src_fps: float,
                   dst_fps: float) -> typing.List[int]:
    """按时间**均匀抽取**帧索引（升序、去重、非空）。

    - `src_fps <= dst_fps`（目标帧率不低于源）→ 全部帧保留（不做插帧、不重复帧）；
    - 否则按 `step = src_fps / dst_fps` 取 `round(i * step)`，越界剔除；
    - `count <= 0` → 空表；fps 非法（<=0）→ 安全回退为「全部帧」。
    """
    if count <= 0:
        return []
    if src_fps <= 0 or dst_fps <= 0 or src_fps <= dst_fps:
        return list(range(count))
    step = src_fps / dst_fps
    indices: typing.List[int] = []
    seen: typing.Set[int] = set()
    i = 0
    while True:
        k = int(round(i * step))
        if k >= count:
            break
        if k not in seen:
            seen.add(k)
            indices.append(k)
        i += 1
    return indices or [0]


def effective_fps(src_fps: float, src_count: int, kept_count: int) -> float:
    """抽帧后应写入 `meta.json` 的帧率：**保持播放时长与原始一致**。

    时长 = `src_count / src_fps`；抽帧后 `kept_count` 帧要在相同时长内播完，
    故 `fps = kept_count / 时长`。这样动作**不变慢也不变快**，只是采样变稀。
    例：24.06fps/241 帧 → 目标 12fps 抽帧保留 121 帧 → 写入 12.08fps（时长仍 10.02s）。
    """
    if src_fps <= 0 or src_count <= 0 or kept_count <= 0:
        return DEFAULT_FPS
    duration = src_count / float(src_fps)
    if duration <= 0:
        return DEFAULT_FPS
    return round(kept_count / duration, 3)


# --------------------------------------------------------------------------- #
# 3) 体积预算
# --------------------------------------------------------------------------- #
def estimate_bytes(frame_count: int, size: typing.Tuple[int, int],
                   formats: typing.Sequence[str] = ("png",)) -> typing.Dict[str, int]:
    """按格式估算入库字节数（png 用实测经验系数，rgb565 为精确值）。"""
    w, h = int(size[0]), int(size[1])
    pixels = max(0, w * h)
    frames = max(0, int(frame_count))
    out: typing.Dict[str, int] = {}
    for fmt in formats:
        key = str(fmt).lower()
        if key == "png":
            out["png"] = int(frames * pixels * PNG_BYTES_PER_PIXEL)
        elif key.startswith("rgb565"):
            out["rgb565"] = frames * pixels * RGB565_BYTES_PER_PIXEL
        else:
            raise ValueError("未知输出格式: %r（可选 png / rgb565）" % (fmt,))
    return out


def budget_report(frame_count: int, size: typing.Tuple[int, int],
                  formats: typing.Sequence[str] = ("png",),
                  budget_mb: float = DEFAULT_BUDGET_MB
                  ) -> typing.Dict[str, typing.Any]:
    """体积预算评估：逐格式估算 + 总量 + 是否超预算。"""
    per_fmt = estimate_bytes(frame_count, size, formats)
    total = sum(per_fmt.values())
    budget = max(0.0, float(budget_mb))
    mb = total / (1024.0 * 1024.0)
    return {
        "frames": int(frame_count),
        "size": [int(size[0]), int(size[1])],
        "per_format_bytes": per_fmt,
        "total_bytes": total,
        "total_mb": round(mb, 2),
        "budget_mb": budget,
        "over_budget": bool(budget > 0 and mb > budget),
    }


def mib(num_bytes: int) -> float:
    """字节 → MiB（保留 2 位，仅用于打印）。"""
    return round(int(num_bytes) / (1024.0 * 1024.0), 2)


def fit_to_budget(src_fps: float, src_count: int, size: typing.Tuple[int, int],
                  formats: typing.Sequence[str] = ("png",),
                  budget_mb: float = DEFAULT_BUDGET_MB,
                  ladder: typing.Sequence[float] = FPS_LADDER
                  ) -> typing.Dict[str, typing.Any]:
    """给定尺寸下，从帧率阶梯里挑**能装进预算的最高帧率**（`--fit-budget` 用）。

    返回 `{"fps":…, "frames":…, "report":…, "fits": bool}`：
    - 阶梯中第一个满足预算的帧率即选中（阶梯已按高→低排序，故天然取"最高可行帧率"）；
    - 全都不满足时取阶梯最低值并置 `fits=False`（提示还需调小 `--max-side`）。

    例：241 帧/10s 源素材、入库 180×320、全 PNG（≈86KB/帧）、预算 8MiB 时，
    12fps≈9.89MiB、10fps≈8.24MiB 均超预算 → 自动选 **8fps（80 帧 ≈6.59MiB）**。
    若全阶梯都超，则返回最低帧率并置 `fits=False`，让调用方明确报"存储仍不够"。
    """
    cap = src_fps if src_fps > 0 else float("inf")
    candidates = [float(f) for f in ladder if 0 < float(f) <= cap]
    if not candidates:
        candidates = [DEFAULT_FPS if DEFAULT_FPS <= cap else min(ladder)]
    last: typing.Optional[typing.Dict[str, typing.Any]] = None
    for fps in candidates:
        indices = select_indices(src_count, src_fps, fps)
        report = budget_report(len(indices), size, formats, budget_mb)
        entry: typing.Dict[str, typing.Any] = {
            "fps": fps, "frames": len(indices), "report": report,
            "fits": not report["over_budget"],
        }
        if entry["fits"]:
            return entry
        last = entry
    return last or {"fps": candidates[-1], "frames": 0, "fits": False,
                    "report": budget_report(0, size, formats, budget_mb)}


# --------------------------------------------------------------------------- #
# 4) meta.json / manifest.json
# --------------------------------------------------------------------------- #
def build_meta(name: str, fps: float, size: typing.Tuple[int, int],
               frame_count: int,
               spec: typing.Optional[typing.Dict] = None,
               source: typing.Optional[typing.Dict] = None) -> typing.Dict:
    """组装入库 `meta.json`（`avatar_assets.frames_fps` 只关心其中的 `fps`）。

    刻意**不写时间戳**，保证同样的输入产出逐字节一致的 meta/manifest（便于 git diff 与复现）。
    """
    return {
        "name": name,
        "fps": float(fps),
        "size": [int(size[0]), int(size[1])],
        "frames": int(frame_count),
        "spec": dict(spec or {}),
        "source": dict(source or {}),
    }


def sha256_file(path: typing.Union[str, Path]) -> str:
    """文件 sha256（分块读，避免大文件占用内存）。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_entries(paths: typing.Sequence[typing.Union[str, Path]]
                     ) -> typing.List[typing.Dict]:
    """逐帧生成清单项：文件名 / 字节数 / sha256。"""
    items: typing.List[typing.Dict] = []
    for p in paths:
        path = Path(p)
        items.append({
            "file": path.name,
            "bytes": int(path.stat().st_size),
            "sha256": sha256_file(path),
        })
    return items


def build_manifest(name: str,
                   entries: typing.Sequence[typing.Dict]) -> typing.Dict:
    """组装 `manifest.json`（含总字节数，便于板端/CI 快速核对）。"""
    items = [dict(e) for e in entries]
    return {
        "name": name,
        "count": len(items),
        "total_bytes": sum(int(e.get("bytes", 0)) for e in items),
        "entries": items,
    }


def read_manifest(directory: typing.Union[str, Path]
                  ) -> typing.Optional[typing.Dict]:
    """读取目录内 manifest.json（缺失/非法 → None）。"""
    path = Path(directory) / MANIFEST_NAME
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def verify_manifest(directory: typing.Union[str, Path],
                    frame_paths: typing.Sequence[typing.Union[str, Path]]
                    ) -> typing.Dict:
    """校验目录内帧与 manifest.json 是否一致（数量 + 字节数 + sha256）。

    返回 `{"ok": bool, "checked": n, "issues": [...]}`；**不抛异常**，便于 CLI/CI 直接判定。
    """
    root = Path(directory)
    issues: typing.List[str] = []
    manifest = read_manifest(root)
    if manifest is None:
        return {"ok": False, "checked": 0,
                "issues": ["%s 缺失或非法" % MANIFEST_NAME]}

    entries = manifest.get("entries") or []
    by_name = {str(e.get("file")): e for e in entries if isinstance(e, dict)}
    paths = [Path(p) for p in frame_paths]

    if int(manifest.get("count", len(entries))) != len(paths):
        issues.append("manifest 帧数 %s ≠ 实际帧数 %d"
                      % (manifest.get("count"), len(paths)))

    checked = 0
    for path in paths:
        entry = by_name.get(path.name)
        if entry is None:
            issues.append("manifest 缺少条目: %s" % path.name)
            continue
        checked += 1
        if int(entry.get("bytes", -1)) != path.stat().st_size:
            issues.append("字节数不符: %s" % path.name)
        if str(entry.get("sha256")) != sha256_file(path):
            issues.append("sha256 不符: %s" % path.name)

    actual_names = {p.name for p in paths}
    for name in by_name:
        if name not in actual_names:
            issues.append("manifest 多出条目: %s" % name)

    total = sum(p.stat().st_size for p in paths)
    if entries and int(manifest.get("total_bytes", -1)) != total:
        issues.append("total_bytes %s ≠ 实际 %d"
                      % (manifest.get("total_bytes"), total))

    return {"ok": not issues, "checked": checked, "issues": issues}
