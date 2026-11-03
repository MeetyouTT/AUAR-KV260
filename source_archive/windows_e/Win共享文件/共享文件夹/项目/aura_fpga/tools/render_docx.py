# -*- coding: utf-8 -*-
"""极简 md → docx 渲染器（python-docx 版，替代不可用的 pandoc）。

支持：# 标题（1—4 级）、- / 1. 列表、| 表格 |、``` 代码块、**粗体**、`行内代码`、普通段落。
用法：python render_docx.py <in.md> [out.docx]（默认同名 .docx，UTF-8 无 BOM 读取）
"""
from __future__ import annotations

import io
import os
import re
import sys

from docx import Document
from docx.shared import Pt

CODE_FONT = "Consolas"
BOLD_RE = re.compile(r"(\*\*.+?\*\*|`[^`]+`)")


def _add_runs(par, text: str) -> None:
    """把 **粗体** 与 `行内代码` 渲染成不同 run，其余原样。"""
    for piece in BOLD_RE.split(text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**"):
            par.add_run(piece[2:-2]).bold = True
        elif piece.startswith("`") and piece.endswith("`"):
            run = par.add_run(piece[1:-1])
            run.font.name = CODE_FONT
            run.font.size = Pt(9)
        else:
            par.add_run(piece)


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_sep(line: str) -> bool:
    return bool(re.fullmatch(r"\|[\s:|-]+\|", line.strip()))


def render(md_path: str, docx_path: str) -> tuple[int, int]:
    lines = io.open(md_path, encoding="utf-8").read().splitlines()
    doc = Document()
    doc.styles["Normal"].font.name = "微软雅黑"
    doc.styles["Normal"].font.size = Pt(10.5)
    n_par = n_tab = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            par = doc.add_paragraph()
            run = par.add_run("\n".join(buf))
            run.font.name = CODE_FONT
            run.font.size = Pt(9)
            n_par += 1
            continue
        if stripped.startswith("|") and i + 1 < len(lines) and _is_sep(lines[i + 1]):
            head = _cells(stripped)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_cells(lines[i]))
                i += 1
            table = doc.add_table(rows=1, cols=len(head))
            table.style = "Table Grid"
            for c, txt in enumerate(head):
                cell = table.rows[0].cells[c]
                cell.paragraphs[0].text = ""
                _add_runs(cell.paragraphs[0], txt)
                for run in cell.paragraphs[0].runs:
                    run.bold = True
            for row in rows:
                cells = table.add_row().cells
                for c in range(min(len(head), len(row))):
                    cells[c].paragraphs[0].text = ""
                    _add_runs(cells[c].paragraphs[0], row[c])
            n_tab += 1
            doc.add_paragraph()
            continue
        if not stripped:
            i += 1
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            doc.add_heading(m.group(2), level=len(m.group(1)))
            n_par += 1
        elif re.match(r"^([-*]|\d+\.)\s+", stripped):
            text = re.sub(r"^([-*]|\d+\.)\s+", "", stripped)
            par = doc.add_paragraph(style="List Bullet")
            _add_runs(par, text)
            n_par += 1
        else:
            par = doc.add_paragraph()
            _add_runs(par, stripped)
            n_par += 1
        i += 1
    doc.save(docx_path)
    return n_par, n_tab


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python render_docx.py <in.md> [out.docx]")
        return 2
    md = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(md)[0] + ".docx"
    n_par, n_tab = render(md, out)
    print("rendered: %s | paragraphs=%d tables=%d size=%d" % (out, n_par, n_tab, os.path.getsize(out)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
