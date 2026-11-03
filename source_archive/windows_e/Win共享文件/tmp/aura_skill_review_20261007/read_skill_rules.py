from pathlib import Path
from pypdf import PdfReader

path = Path(r"E:\项目\参赛资料\全国大学生嵌入式芯片与系统设计竞赛'2026FPGA赛道选题指南-AMD.pdf")
reader = PdfReader(path)
for index in (22, 23, 24):
    content = reader.pages[index].extract_text()
    (Path(__file__).parent / f"guide_page_{index + 1}.txt").write_text(content, encoding="utf-8")
    if index in (23, 24):
        print(content)
