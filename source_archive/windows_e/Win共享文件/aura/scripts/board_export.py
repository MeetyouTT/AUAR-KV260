# -*- coding: utf-8 -*-
"""board_export —— 人3 侧「板端输入合同」导出工具

一次产出板端（LVGL / PS 送显 / PL overlay 取图）需要的三样东西：

    1. **无 alpha 帧流** `assets/avatar/<素材名>/frames.rgb565`
       （大端 R5G6B5，按 `ui_tokens.colors.panel_bg` 合成底色；**不入库**，见 .gitignore）
    2. **机器可读资源表** `ui/avatar_board_manifest.json`
    3. **C 头文件** `board/interaction/lvgl/avatar_assets_table.h`（LVGL 侧直接 include）

用法：
    python scripts/board_export.py                 # 打包 + 导出 + 打印预算表
    python scripts/board_export.py --status        # 只看表，不写任何文件
    python scripts/board_export.py --pack --force  # 强制重打包帧流
    python scripts/board_export.py --skip-pack     # 只导出表/头文件

说明：
    - 帧流由**已入库的 PNG** 逐帧转换（复用 `prepare_avatar_frames.qimage_rgb565`，
      与入库工具 `--formats png,rgb565` 同一实现 ⇒ 字节一致），**不需要重新抠像**；
    - 原始 mp4 / 已入库 PNG 均只读；`frames.rgb565` 属可再生产物，不入版本库；
    - 环境标签：PC / SIMULATED —— 本工具产物是"板端输入"，不是板端实测。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from board.interaction import avatar_assets, avatar_board  # noqa: E402
from scripts import prepare_avatar_frames as paf  # noqa: E402

MANIFEST_OUT = _ROOT / "ui" / "avatar_board_manifest.json"
HEADER_OUT = _ROOT / "board" / "interaction" / "lvgl" / "avatar_assets_table.h"


def mib(n_bytes: int) -> float:
    return n_bytes / (1024.0 * 1024.0)


def pack_frames(bg: str, force: bool) -> list:
    """为已入库素材生成 `frames.rgb565`（基于已有 PNG，不重新抠像）。"""
    from PySide6.QtGui import QImage

    bg_rgb = avatar_board.parse_hex_color(bg)
    done = []
    for name in avatar_assets.all_asset_names():
        directory = avatar_assets.asset_dir(name)
        frames = avatar_assets.list_frames(directory)
        if not frames:
            continue
        blob = directory / avatar_board.RGB565_NAME
        if blob.is_file() and not force:
            print("  [跳过] %-16s 已有 %s（%.2f MiB；--force 可重打包）"
                  % (name, blob.name, mib(blob.stat().st_size)))
            done.append((name, blob.stat().st_size, False))
            continue
        with open(blob, "wb") as f:
            for path in frames:
                image = QImage(str(path))
                if image.isNull():
                    raise SystemExit("帧无法读取: %s" % path)
                f.write(paf.qimage_rgb565(image, bg_rgb))
        size = blob.stat().st_size
        print("  [写入] %-16s %s（%d 帧 / %.2f MiB%s）"
              % (name, blob.name, len(frames), mib(size),
                 "，已按底色 %s 合成" % bg if bg_rgb else "，alpha<128 置黑"))
        done.append((name, size, True))
    return done


def write_manifest(table: dict) -> Path:
    MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_OUT, "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return MANIFEST_OUT


def write_header(table: dict) -> Path:
    """生成 C 头文件（LVGL 侧消费；单 TU include，故用 static const）。"""
    box = table["avatar_box"]
    total = table["totals"]
    canvas = table["canvas"]
    lines = [
        "/* 自动生成，请勿手改：python scripts/board_export.py --header",
        " * 源：ui/avatar_board_manifest.json + assets/avatar/<素材名>/frames.rgb565",
        " * 环境标签：PC / SIMULATED（板端实测另行记录）",
        " * 帧流格式：RGB565 **大端 R5G6B5**，逐帧紧密排列；底色已按 %s 合成。"
        % table["panel_bg"],
        " */",
        "#ifndef AVATAR_ASSETS_TABLE_H",
        "#define AVATAR_ASSETS_TABLE_H",
        "",
        "#include <stdint.h>",
        "",
        "#define AVATAR_CANVAS_W        %du" % canvas["w"],
        "#define AVATAR_CANVAS_H        %du" % canvas["h"],
        "#define AVATAR_PANEL_BG_RGB565 0x%04Xu   /* %s */"
        % (table["panel_bg_rgb565"], table["panel_bg"]),
        "#define AVATAR_BOX_X           %du" % box["x"],
        "#define AVATAR_BOX_Y           %du" % box["y"],
        "#define AVATAR_BOX_W           %du" % box["w"],
        "#define AVATAR_BOX_H           %du" % box["h"],
        "#define AVATAR_FRAME_BYTES     %du   /* 单帧最大字节 */" % table["frame_bytes"],
        "#define AVATAR_DOUBLE_BUFFER   %du   /* 双缓冲 = 2 帧 */"
        % table["double_buffer_bytes"],
        "#define AVATAR_CANVAS_RGB565   %du   /* 整屏一帧 1024x600x2 */"
        % (canvas["w"] * canvas["h"] * 2),
        "",
        "typedef struct {",
        "    const char *state;          /* 运行时状态，如 SPEAKING_LOW */",
        "    const char *label;          /* 中文标签（UTF-8），如 播报·低落 */",
        "    const char *asset;          /* **实际加载**的素材目录名（帧流所在） */",
        "    const char *asset_mapped;   /* 该状态**映射**的素材名（未就绪时供诊断） */",
        "    uint16_t    frames;         /* 帧数 */",
        "    uint16_t    width;          /* 素材宽（像素） */",
        "    uint16_t    height;         /* 素材高（像素） */",
        "    uint32_t    fps_milli;      /* 帧率 x1000（9.983 -> 9983） */",
        "    uint32_t    rgb565_bytes;   /* 帧流总字节 = width*height*2*frames */",
        "    uint16_t    dst_x, dst_y;   /* 画布绝对落位（contain + 底部对齐） */",
        "    uint16_t    dst_w, dst_h;   /* 落位尺寸（<= avatar_box） */",
        "    uint8_t     ready;          /* 1=专属素材；0=当前为兜底素材 */",
        "    const char *fallback_from;  /* 非空 = 兜底来源素材名 */",
        "} avatar_asset_t;",
        "",
        "static const avatar_asset_t AVATAR_ASSETS[] = {",
    ]
    for r in table["states"]:
        dst = r["dst"]
        lines.append(
            '    { "%s", "%s", "%s", "%s", %u, %u, %u, %u, %uu, %u, %u, %u, %u, %u, %s },'
            % (r["state"], r["label"], r["asset_resolved"] or r["asset"], r["asset"],
               r["frames"], r["src_w"], r["src_h"],
               int(round(r["fps"] * 1000)), r["rgb565_bytes_expected"],
               dst["x"], dst["y"], dst["w"], dst["h"],
               1 if r["ready"] else 0,
               ('"%s"' % r["fallback_from"]) if r["fallback_from"] else "0"))
    lines += [
        "};",
        "",
        "#define AVATAR_ASSETS_COUNT  (sizeof(AVATAR_ASSETS) / sizeof(AVATAR_ASSETS[0]))",
        "",
        "/* 生成时快照：专属素材 %d 态 / 复用 %d 态 / 兜底 %d 态；已打包帧流素材 %d 个 */"
        % (total["dedicated_states"], len(total["reuse_states"]),
           len(total["fallback_states"]), total["assets_packed"]),
        "",
        "#endif /* AVATAR_ASSETS_TABLE_H */",
        "",
    ]
    HEADER_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(HEADER_OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return HEADER_OUT


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(_ROOT))
    except ValueError:
        return str(path)


def print_status(table: dict) -> None:
    """打印板端输入合同预算表（人3 交付给板端/人1 的速查）。"""
    box = table["avatar_box"]
    canvas = table["canvas"]
    total = table["totals"]
    print("")
    print("=== 板端输入合同（环境：%s）===" % table["environment"])
    print("画布 %d×%d ｜ 玩偶框 %d×%d @ (%d,%d) ｜ 取景 %s"
          % (canvas["w"], canvas["h"], box["w"], box["h"], box["x"], box["y"],
             table["fit"].split("#")[0].strip()))
    print("帧流底色 %s → RGB888 %s / RGB565 0x%04X"
          % (table["panel_bg"], tuple(table["panel_bg_rgb888"]),
             table["panel_bg_rgb565"]))
    print("")
    print("%-14s %-14s %5s %7s %10s %10s %11s %s"
          % ("状态", "素材", "帧", "fps", "素材尺寸", "PNG", "RGB565", "专属?"))
    for r in table["states"]:
        if not r["asset_resolved"]:
            mark = "[无素材]"
        elif r["reuse"]:
            mark = "[复用] %s" % r["asset_resolved"]
        elif r["ready"]:
            mark = "[专属] 就绪"
        else:
            mark = "[兜底] <- %s" % r["fallback_from"]
        print("%-14s %-14s %5d %7.2f %10s %8.2fMiB %9.2fMiB %s"
              % (r["state"], r["asset_resolved"] or r["asset"], r["frames"], r["fps"],
                 "%dx%d" % (r["src_w"], r["src_h"]),
                 mib(r["png_bytes"]),
                 mib(r["rgb565_bytes"] or r["rgb565_bytes_expected"]), mark))
    print("")
    print("合计：专属素材 %d 态 ｜ 复用 %s ｜ 兜底 %s（共 %d 态）"
          % (total["dedicated_states"],
             ",".join(total["reuse_states"]) or "-",
             ",".join(total["fallback_states"]) or "-", total["states"]))
    print("     帧流体积：逐素材去重 %.2f MiB ｜ 逐状态 %.2f MiB ｜ PNG 逐状态 %.2f MiB"
          % (mib(total["rgb565_bytes_unique"]), mib(total["rgb565_bytes_expected"]),
             mib(total["png_bytes"])))
    print("板端 RAM 参考：单帧 %d B（%.2f MiB）｜ 双缓冲 %d B（%.2f MiB）｜ 整屏一帧 %d B（%.2f MiB）"
          % (table["frame_bytes"], mib(table["frame_bytes"]),
             table["double_buffer_bytes"], mib(table["double_buffer_bytes"]),
             canvas["w"] * canvas["h"] * 2, mib(canvas["w"] * canvas["h"] * 2)))
    if total["assets_missing_frames"]:
        print("未打包帧流的素材：%s（跑 --pack 生成）"
              % ", ".join(total["assets_missing_frames"]))


def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description="板端输入合同导出：RGB565 帧流 + avatar_board_manifest.json + C 头文件")
    ap.add_argument("--status", action="store_true", help="只打印预算表，不写文件")
    ap.add_argument("--skip-pack", action="store_true", help="跳过帧流打包")
    ap.add_argument("--force", action="store_true", help="强制重打包已有 frames.rgb565")
    ap.add_argument("--bg", default=None,
                    help="RGB565 合成底色 RRGGBB；默认取 ui_tokens.colors.panel_bg")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    # Windows GBK 控制台下中文/符号（如 U+2714）无法编码 → 统一 UTF-8、不可编码字符替换
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    args = parse_args(argv)
    bg = (args.bg or avatar_board.panel_bg()).lstrip("#")

    if args.status:
        print_status(avatar_board.board_table())
        return 0

    if args.skip_pack:
        print("[1/3] 跳过帧流打包（--skip-pack）")
    else:
        print("[1/3] 打包板端帧流（大端 R5G6B5，底色 #%s）" % bg)
        pack_frames(bg, args.force)

    table = avatar_board.board_table()
    print("[2/3] 资源表 → %s" % _rel(write_manifest(table)))
    print("[3/3] C 头文件 → %s" % _rel(write_header(table)))
    print_status(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


