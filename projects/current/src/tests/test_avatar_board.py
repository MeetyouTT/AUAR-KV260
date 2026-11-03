# -*- coding: utf-8 -*-
"""avatar_board 单测：板端输入合同（几何、资源表、兜底解析、帧流口径、导出产物）。

不依赖 pytest-qt：几何/表为纯逻辑；帧流口径用 QImage 直接构造（offscreen 即可）。
"""
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from board.interaction import avatar_assets, avatar_board, avatar_fsm
from scripts import board_export

ALL_COUNT = len(avatar_fsm.all_states())


def _mkasset(root, name, count=3, size=(8, 8)):
    """在 root/<name>/ 造 count 张纯色 PNG + meta.json（不依赖被造素材的内容）。"""
    from PySide6.QtGui import QColor, QImage

    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        img = QImage(size[0], size[1], QImage.Format_ARGB32)
        img.fill(QColor(0, 255, 0, 255))
        assert img.save(str(d / ("%06d.png" % i)), "PNG")
    (d / "meta.json").write_text(
        json.dumps({"fps": 10, "size": list(size), "frames": count}),
        encoding="utf-8")
    return d


# --------------------------------------------------------------------------- #
# 合同读取 / 几何
# --------------------------------------------------------------------------- #
def test_parse_hex_color():
    assert avatar_board.parse_hex_color("#16202B") == (0x16, 0x20, 0x2B)
    assert avatar_board.parse_hex_color("16202B") == (0x16, 0x20, 0x2B)
    assert avatar_board.parse_hex_color("  #0FE91B ") == (0x0F, 0xE9, 0x1B)
    assert avatar_board.parse_hex_color("#16202") is None
    assert avatar_board.parse_hex_color(None) is None
    assert avatar_board.parse_hex_color("zzzzzz") is None


def test_panel_bg_from_tokens():
    """底色必须取合同令牌（板端合成底色不能写死）。"""
    assert avatar_board.panel_bg() == "#FCFCF3"
    assert avatar_board.parse_hex_color(avatar_board.panel_bg()) == (252, 252, 243)


def test_avatar_box_matches_layout_contract():
    """玩偶框：右区 x0=585 + pad 8、label 24 之后，423×516。"""
    box = avatar_board.avatar_box()
    assert (box["x"], box["y"], box["w"], box["h"]) == (593, 32, 423, 516)
    assert (box["canvas_w"], box["canvas_h"]) == (1024, 600)


def test_contain_rect_contain_and_bottom():
    """466×480 进 423×516：缩放 0.9077 → 423×436，贴框底（y=80），水平居中（x=0）。"""
    rel = avatar_board.contain_rect(466, 480, 423, 516, align="bottom")
    assert (rel["w"], rel["h"]) == (423, 436)
    assert rel["x"] == 0
    assert rel["y"] == 80
    assert abs(rel["scale"] - 423 / 466.0) < 1e-6
    # 顶部对齐 / 居中
    assert avatar_board.contain_rect(466, 480, 423, 516, "top")["y"] == 0
    assert avatar_board.contain_rect(466, 480, 423, 516, "center")["y"] == 40


def test_contain_rect_degenerate():
    assert avatar_board.contain_rect(0, 480, 423, 516)["w"] == 0


# --------------------------------------------------------------------------- #
# 资源表（10 态投影 + 兜底解析）
# --------------------------------------------------------------------------- #
def test_state_rows_project_all_states(tmp_path):
    """只有 idle_normal 时：10 态全部落 Table，专属仅 IDLE，其余兜底←idle_normal。"""
    _mkasset(tmp_path, "idle_normal")
    rows = avatar_board.state_rows(root=tmp_path)
    assert len(rows) == ALL_COUNT
    assert [r["state"] for r in rows] == avatar_fsm.all_states()
    for r in rows:
        assert r["asset_resolved"] == "idle_normal"
        assert r["frames"] == 3
        assert r["fps"] == 10.0
        assert r["src_w"] == 8 and r["src_h"] == 8
        assert r["rgb565_bytes_expected"] == 8 * 8 * 2 * 3
    assert [r["state"] for r in rows if r["ready"]] == ["IDLE", "CANCELLED"]
    # 兜底来源与映射表一致
    by_state = {r["state"]: r for r in rows}
    assert by_state["SPEAKING_LOW"]["asset"] == "talking_low"
    assert by_state["SPEAKING_LOW"]["fallback_chain"] == \
        ["talking_low", "talking_normal", "idle_normal"]
    assert by_state["SPEAKING_LOW"]["fallback_from"] == "idle_normal"
    assert by_state["CAMERA_LOST"]["asset"] == "idle_offline"
    # 「复用」与「专属」必须区分：CANCELLED 按设计复用 idle_normal，不算专属素材
    assert by_state["CANCELLED"]["reuse"] is True
    assert by_state["IDLE"]["reuse"] is False
    assert by_state["CAMERA_LOST"]["reuse"] is False


def test_state_rows_prefers_own_asset(tmp_path):
    """专属素材存在时 ready=True、无兜底来源；帧流打包标记按文件而定。"""
    _mkasset(tmp_path, "idle_normal")
    _mkasset(tmp_path, "talking_low", count=2, size=(16, 32))
    (tmp_path / "talking_low" / avatar_board.RGB565_NAME).write_bytes(
        b"\x00" * (16 * 32 * 2 * 2))
    rows = {r["state"]: r for r in avatar_board.state_rows(root=tmp_path)}
    low = rows["SPEAKING_LOW"]
    assert low["ready"] is True
    assert low["fallback_from"] is None
    assert low["asset_resolved"] == "talking_low"
    assert low["rgb565_packed"] is True
    assert low["rgb565_bytes"] == 16 * 32 * 2 * 2
    assert low["rgb565_bytes_expected"] == 16 * 32 * 2 * 2
    assert low["frames_file"] == "talking_low/frames.rgb565"
    assert low["dst"]["w"] <= avatar_board.avatar_box()["w"]


def test_board_table_totals(tmp_path):
    _mkasset(tmp_path, "idle_normal")
    table = avatar_board.board_table(root=tmp_path)
    assert table["environment"] == "PC / SIMULATED"
    assert table["panel_bg"] == "#FCFCF3"
    assert table["panel_bg_rgb565"] == ((0xFC >> 3) << 11) | ((0xFC >> 2) << 5) | (0xF3 >> 3)
    assert table["totals"]["states"] == ALL_COUNT
    assert table["totals"]["ready_states"] == 2          # IDLE + CANCELLED（复用）
    assert table["totals"]["dedicated_states"] == 1      # 只有 IDLE 是专属素材
    assert table["totals"]["reuse_states"] == ["NETWORK_LOST", "CANCELLED"]
    assert table["frame_bytes"] == 8 * 8 * 2
    assert table["totals"]["rgb565_bytes_expected"] == 8 * 8 * 2 * 3 * ALL_COUNT
    assert table["totals"]["rgb565_bytes_unique"] == 8 * 8 * 2 * 3   # 去重后只剩一个素材
    assert table["avatar_box"] == {"x": 593, "y": 32, "w": 423, "h": 516}
    # 空目录（root 指向空）→ 全部无素材，不抛异常
    empty = avatar_board.board_table(root=tmp_path / "nope")
    assert empty["totals"]["assets_packed"] == 0
    assert all(r["asset_resolved"] is None for r in empty["states"])


# --------------------------------------------------------------------------- #
# 帧流打包（口径必须与入库工具一致）
# --------------------------------------------------------------------------- #
def test_pack_frames_matches_tool_encoding(tmp_path, monkeypatch):
    from PySide6.QtGui import QImage

    from scripts import prepare_avatar_frames as paf

    d = _mkasset(tmp_path, "idle_normal", count=2)
    monkeypatch.setattr(avatar_assets, "AVATAR_DIR", tmp_path)

    done = board_export.pack_frames("16202B", force=False)
    assert len(done) == 1
    name, size, written = done[0]
    assert (name, size, written) == ("idle_normal", 2 * 8 * 8 * 2, True)

    blob = (d / avatar_board.RGB565_NAME).read_bytes()
    expect = b"".join(
        paf.qimage_rgb565(QImage(str(d / ("%06d.png" % i))),
                          avatar_board.parse_hex_color("16202B"))
        for i in range(2))
    assert blob == expect          # 与 prepare_avatar_frames 同一实现 ⇒ 字节一致

    again = board_export.pack_frames("16202B", force=False)
    assert again[0][2] is False    # 已有文件 → 跳过（不重写）


# --------------------------------------------------------------------------- #
# 导出产物（JSON 合同 / C 头文件）
# --------------------------------------------------------------------------- #
def test_export_manifest_and_header(tmp_path, monkeypatch):
    _mkasset(tmp_path, "idle_normal")
    table = avatar_board.board_table(root=tmp_path)
    monkeypatch.setattr(board_export, "MANIFEST_OUT",
                        tmp_path / "avatar_board_manifest.json")
    monkeypatch.setattr(board_export, "HEADER_OUT",
                        tmp_path / "avatar_assets_table.h")

    man = board_export.write_manifest(table)
    hdr = board_export.write_header(table)

    data = json.loads(man.read_text(encoding="utf-8"))
    assert data["canvas"] == {"w": 1024, "h": 600}
    assert data["avatar_box"] == {"x": 593, "y": 32, "w": 423, "h": 516}
    assert len(data["states"]) == ALL_COUNT

    text = hdr.read_text(encoding="utf-8")
    for token in ("#ifndef AVATAR_ASSETS_TABLE_H",
                  "#define AVATAR_ASSETS_COUNT",
                  "} avatar_asset_t;",
                  "asset_mapped",
                  "#define AVATAR_CANVAS_W        1024u",
                  "#define AVATAR_BOX_W           423u",
                  "#define AVATAR_BOX_X           593u",
                  '"SPEAKING_LOW"', '"talking_low"', '"idle_normal"', '"播报·低落"',
                  "#endif /* AVATAR_ASSETS_TABLE_H */"):
        assert token in text, token
    assert text.count('    { "') == ALL_COUNT      # 每态一行


def test_main_writes_both_artifacts(tmp_path, monkeypatch):
    _mkasset(tmp_path, "idle_normal")
    monkeypatch.setattr(avatar_assets, "AVATAR_DIR", tmp_path)
    monkeypatch.setattr(board_export, "MANIFEST_OUT", tmp_path / "m.json")
    monkeypatch.setattr(board_export, "HEADER_OUT", tmp_path / "t.h")
    assert board_export.main(["--skip-pack"]) == 0
    assert (tmp_path / "m.json").is_file() and (tmp_path / "t.h").is_file()


# --------------------------------------------------------------------------- #
# 真实仓库一致性（帧流未打包时跳过）
# --------------------------------------------------------------------------- #
_REAL = avatar_assets.AVATAR_DIR


@pytest.mark.skipif(not (_REAL / "idle_normal" / avatar_board.RGB565_NAME).is_file(),
                    reason="尚未打包 frames.rgb565（跑 python scripts/board_export.py）")
def test_real_rgb565_size_matches_meta():
    d = _REAL / "idle_normal"
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    n = (d / avatar_board.RGB565_NAME).stat().st_size
    assert n == int(meta["size"][0]) * int(meta["size"][1]) * 2 * int(meta["frames"])


