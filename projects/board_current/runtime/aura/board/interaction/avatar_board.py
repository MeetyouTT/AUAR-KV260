# -*- coding: utf-8 -*-
"""avatar_board —— 板端帧流与资源表（人3：板端 UI 的**输入合同**，纯逻辑、无 Qt）

职责：把「运行时状态（10 态情绪节点）→ 素材 → 帧流 / 几何 / 体积」整理成板端
（**LVGL 显示**、PS 送显、PL overlay 取图）可直接消费的一张表。

输入（只读，全部为已入库产物或权威合同）：
    assets/avatar/<素材名>/meta.json       帧率 / 尺寸 / 帧数 / 源指纹
    assets/avatar/<素材名>/manifest.json   逐帧 sha256 与字节（PNG 实际体积）
    assets/avatar/<素材名>/frames.rgb565   板端无 alpha 帧流（大端 R5G6B5，**不入库**）
    ui/ui_layout_spec.json            画布与三区几何（唯一权威数值）
    ui/ui_tokens.json                 颜色令牌（底色 = colors.panel_bg = #FCFCF3）

输出：`board_table()` → 纯 JSON 兼容 dict，供
    - `scripts/board_export.py` 导出 `ui/avatar_board_manifest.json` 与 C 头文件；
    - 板端 LVGL：按 `state` 查 `asset` 与目标矩形；`ready=0` 时按 `fallback_chain` 走兜底。

设计约束：
    1. **不新增状态、不改映射**：状态清单取自 `avatar_fsm.all_states()`，素材名取自
       `avatar_assets.STATE_ASSET` / `fallback_chain()` —— 板端表永远是它们的**投影**；
    2. **几何按合同算**，不硬编码像素：玩偶框 = 右区内（扣 pad 与状态标签）；素材在框内
       **contain 缩放 + 水平居中 + 底部对齐**（与 `qt_widgets._draw_sprite_frame` 同一约定）；
    3. 帧流缺失（`frames.rgb565` 未打包）时给出 `rgb565_bytes_expected`，`rgb565_packed=False`。
"""
from __future__ import annotations

import json
import typing
from pathlib import Path

from . import avatar_assets, avatar_fsm, avatar_timing

_ROOT = Path(__file__).resolve().parents[2]
LAYOUT_SPEC = _ROOT / "ui" / "ui_layout_spec.json"
TOKENS_SPEC = _ROOT / "ui" / "ui_tokens.json"

# 板端帧流文件名（与 scripts/prepare_avatar_frames.py 的 --formats rgb565 一致）
RGB565_NAME = "frames.rgb565"
# 底色兜底（ui_tokens.colors.panel_bg 读不到时用）
PANEL_BG_FALLBACK = "#FCFCF3"


# --------------------------------------------------------------------------- #
# 合同读取
# --------------------------------------------------------------------------- #
def _load_json(path: typing.Union[str, Path]) -> typing.Dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def load_layout(path: typing.Optional[typing.Union[str, Path]] = None) -> typing.Dict:
    """读取布局合同（`ui/ui_layout_spec.json`）。"""
    return _load_json(path or LAYOUT_SPEC)


def load_tokens(path: typing.Optional[typing.Union[str, Path]] = None) -> typing.Dict:
    """读取样式令牌（`ui/ui_tokens.json`）。"""
    return _load_json(path or TOKENS_SPEC)


def panel_bg() -> str:
    """板端面板底色（帧流合成底色，必须与 `ui_tokens.colors.panel_bg` 一致）。"""
    try:
        colors = load_tokens().get("colors", {})
        value = colors.get("panel_bg")
        if parse_hex_color(value):
            return str(value)
    except OSError:
        pass
    return PANEL_BG_FALLBACK


def parse_hex_color(text: typing.Any) -> typing.Optional[typing.Tuple[int, int, int]]:
    """`#FCFCF3` / `FCFCF3` → (252, 252, 243)；非法返回 None。"""
    if not isinstance(text, str):
        return None
    body = text.strip().lstrip("#")
    if len(body) != 6:
        return None
    try:
        return (int(body[0:2], 16), int(body[2:4], 16), int(body[4:6], 16))
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# 几何：玩偶框 + contain 落位（与 PySide6 原型同约定）
# --------------------------------------------------------------------------- #
def avatar_box(layout: typing.Optional[typing.Dict] = None) -> typing.Dict:
    """板端玩偶框（画布绝对坐标，整数）。

    来源：`right_panel`（x0/x1/y0/y1/padding）+ `right_inner.label_h` +
    `right_inner.avatar_box`（423×516 由合同直接给宽高）。
    """
    lay = layout or load_layout()
    panel = lay.get("right_panel", {})
    inner = lay.get("right_inner", {})
    pad = int(panel.get("padding", 8))
    label_h = int(inner.get("label_h", 24))
    box = inner.get("avatar_box", {})
    w = int(box.get("width", 423))
    h = int(box.get("height", 516))
    px0 = int(panel.get("x0", 0))
    px1 = int(panel.get("x1", px0))
    x = px0 + pad + max(0, (px1 - px0 - 2 * pad - w) // 2)
    y = int(panel.get("y0", 0)) + pad + label_h
    canvas = lay.get("canvas", {})
    return {
        "x": x, "y": y, "w": w, "h": h,
        "panel_x0": px0, "panel_y0": int(panel.get("y0", 0)),
        "canvas_w": int(canvas.get("width", 1024)),
        "canvas_h": int(canvas.get("height", 600)),
    }


def contain_rect(src_w: int, src_h: int, box_w: int, box_h: int,
                 align: str = "bottom") -> typing.Dict:
    """素材在目标框内 **contain（不拉伸）+ 水平居中 + 垂直 align** 的落位矩形。

    与 `qt_widgets._draw_sprite_frame`（Qt.KeepAspectRatio + 底部对齐）同一几何约定：
    `scale = min(box_w / src_w, box_h / src_h)`，落位尺寸四舍五入取整。
    """
    if src_w <= 0 or src_h <= 0 or box_w <= 0 or box_h <= 0:
        return {"x": 0, "y": 0, "w": 0, "h": 0, "scale": 0.0}
    scale = min(box_w / float(src_w), box_h / float(src_h))
    w = min(int(round(src_w * scale)), box_w)
    h = min(int(round(src_h * scale)), box_h)
    x = int(round((box_w - w) / 2.0))
    if align == "top":
        y = 0
    elif align == "center":
        y = int(round((box_h - h) / 2.0))
    else:  # bottom：板端取景为"腰部以上"，腰部切线贴框底 + 渐隐收边
        y = box_h - h
    return {"x": x, "y": y, "w": w, "h": h, "scale": round(scale, 6)}


# --------------------------------------------------------------------------- #
# 素材读取（只读文件，不加载像素）
# --------------------------------------------------------------------------- #
def _png_size(path: Path) -> typing.Optional[typing.Tuple[int, int]]:
    """从 PNG 头读尺寸（无 Qt 依赖）：IHDR 的宽高。"""
    try:
        with open(path, "rb") as f:
            head = f.read(26)
    except OSError:
        return None
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return (int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big"))


def _png_bytes(directory: Path) -> int:
    """PNG 实际体积：优先 `manifest.json` 逐帧字节合计，否则目录实测。"""
    for candidate in (avatar_lod_manifest(directory), avatar_assets.read_meta(directory)):
        entries = candidate.get("entries") if isinstance(candidate, dict) else None
        if isinstance(entries, list) and entries:
            try:
                return sum(int(e.get("bytes", 0)) for e in entries)
            except (AttributeError, TypeError, ValueError):
                continue
    try:
        return sum(p.stat().st_size for p in avatar_assets.list_frames(directory))
    except OSError:
        return 0


def avatar_lod_manifest(directory: Path) -> typing.Dict:
    """读 `manifest.json`（不存在/非法 → 空 dict）。"""
    path = Path(directory) / "manifest.json"
    if not path.is_file():
        return {}
    try:
        return _load_json(path)
    except (OSError, ValueError):
        return {}


def _primary_owner(asset: str) -> str:
    """素材名的"主状态" = `all_states()` 顺序里第一个把它作为专属素材引用的状态。

    用于区分"**专属**"与"**按设计复用**"（如 `CANCELLED` 复用 `IDLE` 的 `idle_normal`）。
    """
    for s in avatar_fsm.all_states():
        if avatar_assets.asset_name(s) == asset:
            return s
    return ""


def asset_info(state: str,
               root: typing.Optional[typing.Union[str, Path]] = None) -> typing.Dict:
    """单个运行时状态的板端素材信息（含兜底链解析结果，**不加载像素**）。"""
    chain = avatar_assets.fallback_chain(state)
    own = avatar_assets.asset_name(state)
    directory = avatar_assets.frames_dir(state, root=root)
    info: typing.Dict = {
        "state": state,
        "label": avatar_fsm.avatar_spec(state).label,
        "animation": avatar_fsm.avatar_spec(state).animation,
        "asset": own,
        "asset_resolved": None,
        "ready": False,          # True = 该状态映射的素材（asset）已就绪
        "reuse": _primary_owner(own) != state,   # True = 按设计复用别的状态的素材名
        "fallback_chain": list(chain),
        "fallback_from": None,   # 非空 = 当前实际用的是**兜底链**里的素材（观感降级）
        "frames": 0, "fps": 0.0, "src_w": 0, "src_h": 0,
        "png_bytes": 0,
        "rgb565_bytes": 0, "rgb565_bytes_expected": 0,
        "rgb565_packed": False, "frames_file": None,
    }
    if directory is None:
        return info

    frames = avatar_assets.list_frames(directory)
    size = avatar_assets.read_meta(directory).get("size")
    if not (isinstance(size, (list, tuple)) and len(size) == 2):
        size = _png_size(frames[0]) if frames else None
    w = int(size[0]) if size else 0
    h = int(size[1]) if size else 0

    info.update({
        "asset_resolved": directory.name,
        "ready": directory.name == own,
        "fallback_from": None if directory.name == own else directory.name,
        "frames": len(frames),
        "fps": avatar_assets.frames_fps(directory),
        "src_w": w, "src_h": h,
        "png_bytes": _png_bytes(directory),
        "rgb565_bytes_expected": w * h * 2 * len(frames),
    })
    blob = directory / RGB565_NAME
    if blob.is_file():
        try:
            info["rgb565_bytes"] = blob.stat().st_size
        except OSError:
            info["rgb565_bytes"] = 0
        info["rgb565_packed"] = info["rgb565_bytes"] == info["rgb565_bytes_expected"] > 0
        info["frames_file"] = "%s/%s" % (directory.name, RGB565_NAME)
    return info


def state_rows(root: typing.Optional[typing.Union[str, Path]] = None,
               layout: typing.Optional[typing.Dict] = None) -> typing.List[typing.Dict]:
    """10 态 → 板端素材行（含目标矩形），顺序取自 `avatar_fsm.AVATAR_MAP`。"""
    box = avatar_box(layout)
    rows: typing.List[typing.Dict] = []
    for state in avatar_fsm.all_states():
        info = asset_info(state, root=root)
        rel = contain_rect(info["src_w"], info["src_h"], box["w"], box["h"],
                           align="bottom")
        info["dst_rel"] = dict(rel)
        info["dst"] = {"x": box["x"] + rel["x"], "y": box["y"] + rel["y"],
                       "w": rel["w"], "h": rel["h"]}
        info['asset_pool'] = list(avatar_assets.pool_assets(state, root=root))
        info['burst'] = state in avatar_assets.BURST_STATES
        rows.append(info)
    return rows


def resource_rows(root=None, layout=None) -> typing.List[typing.Dict]:
    """All distinct primary and pooled resources, including stage/window contracts."""
    box = avatar_box(layout)
    out = []
    for name in avatar_assets.all_asset_names():
        directory = avatar_assets.asset_dir(name, root=root)
        frames = avatar_assets.list_frames(directory)
        if not frames:
            continue
        meta = avatar_assets.read_meta(directory)
        w, h = meta.get('size') or _png_size(frames[0])
        expected = int(w) * int(h) * 2 * len(frames)
        blob = directory / RGB565_NAME
        actual = blob.stat().st_size if blob.is_file() else 0
        rel = contain_rect(int(w), int(h), box['w'], box['h'])
        burst = avatar_assets.is_burst_asset(name)
        out.append({'asset': name, 'frames': len(frames),
            'fps': avatar_assets.frames_fps(directory), 'src_w': int(w), 'src_h': int(h),
            'frames_file': name + '/' + RGB565_NAME, 'rgb565_bytes': actual,
            'rgb565_bytes_expected': expected, 'rgb565_packed': actual == expected,
            'dst': {'x': box['x'] + rel['x'], 'y': box['y'] + rel['y'],
                    'w': rel['w'], 'h': rel['h']}, 'burst': burst,
            'segments': None if burst else avatar_assets.read_segments(directory),
            'loop_slowdown': 3.0})
    return out


def board_table(root: typing.Optional[typing.Union[str, Path]] = None,
                layout: typing.Optional[typing.Dict] = None) -> typing.Dict:
    """板端输入合同总表（可直接 `json.dump`）。"""
    lay = layout or load_layout()
    box = avatar_box(lay)
    rows = state_rows(root=root, layout=lay)
    resources = resource_rows(root=root, layout=lay)
    bg = panel_bg()
    bg_rgb = parse_hex_color(bg) or (252, 252, 243)
    bg565 = ((bg_rgb[0] >> 3) << 11) | ((bg_rgb[1] >> 2) << 5) | (bg_rgb[2] >> 3)

    frame_max = max((r["src_w"] * r["src_h"] * 2 for r in rows), default=0)
    packed = sorted(r['asset'] for r in resources if r['rgb565_packed'])
    missing = sorted(r['asset'] for r in resources if not r['rgb565_packed'])
    unique_bytes = 0
    seen: typing.Dict[str, int] = {}
    for r in rows:                      # 逐素材**去重**合计（板端真正要存盘/打包的量）
        name = r["asset_resolved"]
        if name and name not in seen:
            seen[name] = int(r["rgb565_bytes"]) or int(r["rgb565_bytes_expected"])
    unique_bytes = sum(r['rgb565_bytes_expected'] for r in resources)
    return {
        "schema_version": "1.2",
        "generated_by": "scripts/board_export.py",
        "environment": "PC / SIMULATED",
        "note": "板端帧流与资源表；不含任何板端实测数据（环境标签红线）",
        "canvas": {"w": box["canvas_w"], "h": box["canvas_h"]},
        "panel_bg": bg,
        "panel_bg_rgb888": list(bg_rgb),
        "panel_bg_rgb565": bg565,
        "fit": "contain+bottom   # 与 qt_widgets._draw_sprite_frame 同约定",
        "avatar_box": {k: box[k] for k in ("x", "y", "w", "h")},
        "frame_bytes": frame_max,
        "double_buffer_bytes": frame_max * 2,
        "states": rows,
        'resources': resources,
        'playback': {'stages': ['enter', 'loop', 'blend', 'exit'],
                     'blend_ms': avatar_timing.SEGMENT_BLEND_MS,
                     'pool_switch_seconds': 6.0, 'loop_slowdown': 3.0,
                     'algorithm': 'continuous_cursor_v1',
                     'loop_window_policy': 'primary_only',
                     'loop_curve': 'cosine_round_trip_no_random_phase',
                     'blend_meaning': 'velocity_ramp_not_pose_crossfade',
                     'exit_policy': 'nearest_clip_endpoint_on_stop; last_endpoint_on_pool_rotation',
                     'interpolation': 'adjacent_source_frames_only',
                     'reference_header': 'board/interaction/lvgl/avatar_playback.h',
                     'hardware_verified': False,
                     'burst_completion': 'AWAKE -> AUDIO_PLAYBACK_STOP; active speech -> AUDIO_PLAYBACK_START'},
        "totals": {
            "states": len(rows),
            # ready = 该状态映射的素材已就绪（含按设计的复用）；dedicated = 专属素材（非复用）
            "ready_states": sum(1 for r in rows if r["ready"]),
            "dedicated_states": sum(1 for r in rows if r["ready"] and not r["reuse"]),
            "reuse_states": [r["state"] for r in rows if r["reuse"]],
            "fallback_states": [r["state"] for r in rows
                                if r["asset_resolved"] and not r["ready"]],
            "assets_packed": len(packed),
            "packed_assets": packed,
            "assets_missing_frames": missing,
            "png_bytes": sum(r["png_bytes"] for r in rows),
            # 逐状态合计（含同一素材被多状态引用时的重复计入）
            "rgb565_bytes": sum(r["rgb565_bytes"] for r in rows),
            "rgb565_bytes_expected": sum(r["rgb565_bytes_expected"] for r in rows),
            # 逐素材去重合计（板端存储/打包的真实总量）
            "rgb565_bytes_unique": unique_bytes,
            "double_buffer_bytes": frame_max * 2,
        },
    }


