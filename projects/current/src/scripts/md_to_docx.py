"""md_to_docx.py —— 极简 Markdown → Word(.docx) 转换器

用途：遵循「md and word」规则，把项目内 docs/*.md 技术文档同步渲染成同名 .docx。

支持子集（覆盖本项目文档用到的语法）：
  - 标题  # ~ ######
  - 段落 / 软换行
  - 无序列表 - / *（按缩进分级）
  - 有序列表 1. 2. （按缩进分级）
  - 引用  > 
  - 围栏代码块 ```lang ... ```
  - 表格  | a | b |  + 分隔行 |---|---|
  - 分隔线 --- / ***
  - 行内 **加粗** 与 `行内代码`

依赖：python-docx（已在本项目环境安装，1.2.0）。

用法：
    python scripts/md_to_docx.py docs/某某_技术记录.md            # 生成同名 .docx
    python scripts/md_to_docx.py docs/a.md docs/b.md              # 批量
    python scripts/md_to_docx.py docs/a.md -o out/a.docx          # 指定输出

退出码：0 成功；非 0 失败。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

CJK_FONT = "微软雅黑"
MONO_FONT = "Consolas"

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_UL = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_OL = re.compile(r"^(\s*)\d+[.)]\s+(.*)$")
_QUOTE = re.compile(r"^\s*>\s?(.*)$")
_HR = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
_FENCE = re.compile(r"^\s*```(\w*)\s*$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$")
_INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+`)")


def _set_cjk_style(doc: Document) -> None:
    """把 Normal 样式设成中英文字体（东三区字体需单独写 rPr）。"""
    style = doc.styles["Normal"]
    style.font.name = CJK_FONT
    style.font.size = Pt(10.5)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), CJK_FONT)


def _set_run_mono(run, size: float = 9) -> None:
    run.font.name = MONO_FONT
    run.font.size = Pt(size)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), MONO_FONT)


def _add_inline(paragraph, text: str) -> None:
    """把 **加粗** / `代码` 解析成 run 追加到段落。"""
    for token in _INLINE.split(text):
        if not token:
            continue
        if token.startswith("**") and token.endswith("**") and len(token) > 4:
            paragraph.add_run(token[2:-2]).bold = True
        elif token.startswith("`") and token.endswith("`") and len(token) > 2:
            run = paragraph.add_run(token[1:-1])
            _set_run_mono(run, 9.5)
            run.font.color.rgb = RGBColor(0xC7, 0x25, 0x4E)
        else:
            paragraph.add_run(token)


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def _list_level(indent: str) -> int:
    return min(len(indent) // 2, 2)


def _flush_table(doc: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    ncol = max(len(r) for r in rows)
    table = doc.add_table(rows=0, cols=ncol)
    table.style = "Light Grid Accent 1"
    for i, row in enumerate(rows):
        cells = table.add_row().cells
        for j in range(ncol):
            text = row[j] if j < len(row) else ""
            para = cells[j].paragraphs[0]
            _add_inline(para, text)
            if i == 0:
                for run in para.runs:
                    run.bold = True
    doc.add_paragraph()


def _flush_code(doc: Document, lines: list[str]) -> None:
    para = doc.add_paragraph()
    pf = para.paragraph_format
    pf.left_indent = Pt(12)
    pf.space_before = Pt(2)
    pf.space_after = Pt(6)
    if not lines:
        lines = [""]
    for idx, raw in enumerate(lines):
        run = para.add_run(("\n" if idx else "") + raw)
        _set_run_mono(run, 9)


def convert(md_path: Path, out_path: Path) -> None:
    text = md_path.read_text(encoding="utf-8")
    doc = Document()
    _set_cjk_style(doc)

    lines = text.splitlines()
    i = 0
    in_code = False
    code_buf: list[str] = []
    table_buf: list[list[str]] = []

    def flush_table_if_any() -> None:
        nonlocal table_buf
        if table_buf:
            _flush_table(doc, table_buf)
            table_buf = []

    while i < len(lines):
        line = lines[i]

        # 围栏代码块
        m_fence = _FENCE.match(line)
        if in_code:
            if m_fence:
                _flush_code(doc, code_buf)
                code_buf = []
                in_code = False
            else:
                code_buf.append(line)
            i += 1
            continue
        if m_fence:
            flush_table_if_any()
            in_code = True
            i += 1
            continue

        # 表格（连续的 | 行）
        if line.strip().startswith("|"):
            if _TABLE_SEP.match(line):
                i += 1
                continue
            table_buf.append(_split_row(line))
            i += 1
            continue
        flush_table_if_any()

        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        # 分隔线
        if _HR.match(line):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run("─" * 24)
            run.font.color.rgb = RGBColor(0xBB, 0xBB, 0xBB)
            i += 1
            continue

        # 标题
        m_h = _HEADING.match(line)
        if m_h:
            h = doc.add_heading(level=min(len(m_h.group(1)), 4))
            _add_inline(h, m_h.group(2).strip())
            i += 1
            continue

        # 引用
        m_q = _QUOTE.match(line)
        if m_q:
            p = doc.add_paragraph(style="Intense Quote")
            _add_inline(p, m_q.group(1))
            i += 1
            continue

        # 无序列表
        m_ul = _UL.match(line)
        if m_ul:
            lvl = _list_level(m_ul.group(1))
            style = "List Bullet" if lvl == 0 else f"List Bullet {lvl + 1}"
            p = doc.add_paragraph(style=style)
            _add_inline(p, m_ul.group(2))
            i += 1
            continue

        # 有序列表
        m_ol = _OL.match(line)
        if m_ol:
            lvl = _list_level(m_ol.group(1))
            style = "List Number" if lvl == 0 else f"List Number {lvl + 1}"
            p = doc.add_paragraph(style=style)
            _add_inline(p, m_ol.group(2))
            i += 1
            continue

        # 普通段落
        p = doc.add_paragraph()
        _add_inline(p, stripped)
        i += 1

    if in_code:
        _flush_code(doc, code_buf)
    flush_table_if_any()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Markdown → Word(.docx) 极简转换器")
    parser.add_argument("inputs", nargs="+", help="输入的 .md 文件（可多个）")
    parser.add_argument("-o", "--output", help="输出 .docx（仅单个输入时可用）")
    args = parser.parse_args(argv)

    if args.output and len(args.inputs) != 1:
        parser.error("-o/--output 仅在单个输入时可用")

    ok = 0
    for raw in args.inputs:
        src = Path(raw)
        if not src.is_file():
            print(f"[SKIP] 不存在：{src}", file=sys.stderr)
            continue
        dst = Path(args.output) if args.output else src.with_suffix(".docx")
        convert(src, dst)
        print(f"[OK] {src}  ->  {dst}")
        ok += 1
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
