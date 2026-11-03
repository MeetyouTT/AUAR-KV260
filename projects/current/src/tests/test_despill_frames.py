# -*- coding: utf-8 -*-
"""强化去绿单测：scripts/despill_frames.py（A 硬限绿 + D1 蓝发去青）。

覆盖：A 只压绿不改 alpha / D1 只作用于蓝发且把青染比压到上限 / 屏外像素不动 /
      幂等性 / 面积守恒（内容与不透明像素数不变）/ 非 ASCII 路径文件往返。
"""
import sys
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.despill_frames import (analyze, decyan_blue,  # noqa: E402
                                    despill_bgra, despill_file, hard_limit_green)


def _px(b, g, r, a=255):
    """1x1 BGRA 像素。"""
    return np.array([[[b, g, r, a]]], np.uint8)


def test_hard_limit_green_caps_only_green():
    """A：绿为主导的像素被压到 max(r,b)，其余像素与 alpha 不动。"""
    img = np.concatenate([_px(50, 200, 100),      # 绿残留 d=100 → 应压到 100
                          _px(200, 150, 100),     # 蓝主导，d=-50 → 不动
                          _px(50, 40, 200, 128)], axis=0)
    out = hard_limit_green(img)
    assert tuple(out[0, 0]) == (50, 100, 100, 255)
    assert tuple(out[1, 0]) == (200, 150, 100, 255)
    assert tuple(out[2, 0]) == (50, 40, 200, 128)


def test_decyan_blue_caps_q_and_leaves_non_blue():
    """D1：蓝发（b-r>30 且 b>80）且 q>=q_min 时把 q 压到 q_max（只降不升）；非蓝像素不动。"""
    img = np.concatenate([_px(200, 200, 100),     # q=1.00 → 压到 0.5 → g=150
                          _px(200, 160, 100),     # q=0.60 → 压到 0.5 → g=150
                          _px(200, 140, 100),     # q=0.40 → 命中但已低于上限 → 不变
                          _px(200, 120, 100),     # q=0.20 → 不命中
                          _px(50, 200, 40)],      # 非蓝（b-r=10 且 b=50）→ 不命中
                         axis=0)
    out, hit = decyan_blue(img, q_min=0.35, q_max=0.50)
    assert tuple(out[0, 0]) == (200, 150, 100, 255)
    assert tuple(out[1, 0]) == (200, 150, 100, 255)
    assert tuple(out[2, 0]) == (200, 140, 100, 255)
    assert tuple(out[3, 0]) == (200, 120, 100, 255)
    assert tuple(out[4, 0]) == (50, 200, 40, 255)
    assert hit == 3


def test_alpha_and_area_preserved():
    """面积守恒：A+D1 不改 alpha，内容/不透明像素数逐位相同。"""
    rng = np.random.default_rng(0)
    img = rng.integers(0, 256, size=(32, 32, 4), dtype=np.uint8)
    img[..., 3] = np.where(rng.random((32, 32)) > 0.5, 255, rng.integers(0, 256, (32, 32)))
    out = despill_bgra(img)
    assert np.array_equal(out[..., 3], img[..., 3])
    assert analyze(out)["content_px"] == analyze(img)["content_px"]
    assert analyze(out)["opaque_px"] == analyze(img)["opaque_px"]


def test_idempotent():
    """幂等：跑两遍与跑一遍结果一致（链上重复调用安全）。"""
    img = np.concatenate([_px(200, 210, 100), _px(50, 200, 100)], axis=0)
    once = despill_bgra(img)
    twice = despill_bgra(once)
    assert np.array_equal(once, twice)
    m = analyze(once)
    assert m["d_ge3"] == 0 and m["blue_q60"] == 0


def test_despill_file_roundtrip_nonascii_path(tmp_path):
    """文件往返（非 ASCII 路径安全）：就地处理后指标归零。"""
    import cv2
    d = tmp_path / "绿幕素材_测试"
    d.mkdir()
    p = d / "frame_000000.png"
    img = np.concatenate([_px(200, 210, 100), _px(50, 200, 100)], axis=0)
    cv2.imencode(".png", img)[1].tofile(str(p))
    m = despill_file(p)
    assert m["d_ge3"] == 0 and m["content_px"] == 2
    back = cv2.imdecode(np.fromfile(str(p), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    assert tuple(back[0, 0]) == (200, 150, 100, 255)


def test_trim_alpha_ring_optional():
    """可选 C2：去掉最外 1px 圈里 alpha<128 的淡晕，不透明主体不动。"""
    from scripts.despill_frames import trim_alpha_ring
    img = np.zeros((5, 5, 4), np.uint8)
    img[1:4, 1:4] = (10, 20, 30, 255)
    img[0, 0] = (10, 20, 30, 60)          # 最外圈淡晕
    out = trim_alpha_ring(img)
    assert out[0, 0, 3] == 0
    assert out[2, 2, 3] == 255
