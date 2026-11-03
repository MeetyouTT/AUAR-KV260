from pathlib import Path
import re
import json
import hashlib
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT

ROOT = Path('E:/项目')
TMP = ROOT / 'tmp/aura_innovation_plan_20261004'
MD = ROOT / 'output/aura_innovation_execution_plan_and_score_20261004.md'
DOCX = MD.with_suffix('.docx')

def font_xml(obj, size=11.5, east='SimSun', color='000000'):
    obj.font.name = 'Calibri'
    obj.font.size = Pt(size)
    obj.font.color.rgb = RGBColor.from_string(color)
    rpr = obj.element.get_or_add_rPr()
    rf = rpr.find(qn('w:rFonts'))
    if rf is None:
        rf = OxmlElement('w:rFonts')
        rpr.insert(0, rf)
    rf.set(qn('w:eastAsia'), east)
    for a in ['asciiTheme', 'hAnsiTheme', 'eastAsiaTheme', 'cstheme']:
        rf.attrib.pop(qn('w:' + a), None)

def add_link(p, label, target, size):
    h = OxmlElement('w:hyperlink')
    h.set(qn('r:id'), p.part.relate_to(target, RT.HYPERLINK, is_external=True))
    r = OxmlElement('w:r')
    rp = OxmlElement('w:rPr')
    rf = OxmlElement('w:rFonts')
    rf.set(qn('w:ascii'), 'Calibri')
    rf.set(qn('w:hAnsi'), 'Calibri')
    rf.set(qn('w:eastAsia'), 'SimSun')
    rp.append(rf)
    co = OxmlElement('w:color'); co.set(qn('w:val'), '24527A'); rp.append(co)
    sz = OxmlElement('w:sz'); sz.set(qn('w:val'), str(round(size * 2))); rp.append(sz)
    under = OxmlElement('w:u'); under.set(qn('w:val'), 'single'); rp.append(under)
    r.append(rp)
    t = OxmlElement('w:t'); t.text = label; r.append(t)
    h.append(r); p._p.append(h)

def inline(p, text, size=11.5):
    rx = r'(\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*)'
    for token in re.split(rx, text):
        if not token:
            continue
        m = re.fullmatch(r'\[([^\]]+)\]\(([^)]+)\)', token)
        if m:
            add_link(p, m[1], m[2], size)
        else:
            r = p.add_run(token[2:-2] if token.startswith('**') else token)
            font_xml(r, size)
            r.bold = token.startswith('**')

doc = Document()
sec = doc.sections[0]
sec.page_width = Inches(8.5); sec.page_height = Inches(11)
sec.left_margin = sec.right_margin = Inches(0.78)
sec.top_margin = Inches(0.72); sec.bottom_margin = Inches(0.7)
sec.footer_distance = Inches(0.3)
for name in ['Normal', 'Title', 'Subtitle', 'Heading 1', 'Heading 2', 'Heading 3', 'List Bullet', 'List Number']:
    s = doc.styles[name]
    font_xml(s, 11.5)
    s.paragraph_format.line_spacing = 1.2
    s.paragraph_format.space_after = Pt(6)
    s.paragraph_format.widow_control = True
    for b in list(s.element.iter(qn('w:pBdr'))):
        b.getparent().remove(b)
for name, size in [('Title', 23), ('Heading 1', 16), ('Heading 2', 13), ('Heading 3', 12)]:
    s = doc.styles[name]
    font_xml(s, size, 'SimHei')
    s.font.bold = name != 'Title'
    s.paragraph_format.space_before = Pt(14 if name != 'Title' else 0)
    s.paragraph_format.space_after = Pt(8)
    s.paragraph_format.keep_with_next = True

fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
for text in ['第 ', 'PAGE', ' 页']:
    if text == 'PAGE':
        r = fp.add_run(); f = OxmlElement('w:fldSimple'); f.set(qn('w:instr'), 'PAGE'); r._r.addnext(f)
    else:
        font_xml(fp.add_run(text), 9)

def widths_for(header):
    n = len(header)
    if n == 5 and header[0] == '工作日':
        return [0.48, 1.55, 1.55, 1.55, 1.81]
    if n == 5:
        return [1.84, 0.46, 0.62, 0.92, 3.1]
    if n == 4 and header[0] == '论文或方法':
        return [1.53, 1.88, 1.48, 2.05]
    if n == 4 and header[0] == '评分项':
        return [2.22, 1.0, 1.7, 2.02]
    if n == 4:
        return [0.6, 2.08, 2.0, 2.26]
    if n == 3 and header[0] == '官方评测项':
        return [2.08, 0.48, 4.38]
    if n == 3 and header[0] == '工作线':
        return [0.9, 1.15, 4.89]
    if n == 3:
        return [1.8, 2.5, 2.64]
    return [1.55, 5.39] if n == 2 else [6.94 / n] * n

def table_block(rows):
    vals = [[v.strip() for v in line.strip().strip('|').split('|')] for line in rows]
    header = vals[0]
    vals = [header] + [row for row in vals[1:] if not all(re.fullmatch(r':?-+:?', v) for v in row)]
    table = doc.add_table(rows=0, cols=len(header))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    widths = widths_for(header)
    for col, width in zip(table.columns, widths):
        col.width = Inches(width)
    pr = table._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for side in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        x = OxmlElement('w:' + side)
        for k, v in [('val', 'single'), ('sz', '4'), ('color', 'D9D9D9')]:
            x.set(qn('w:' + k), v)
        borders.append(x)
    pr.append(borders)
    margins = OxmlElement('w:tblCellMar')
    for side, val in [('top', '95'), ('bottom', '95'), ('left', '105'), ('right', '105')]:
        x = OxmlElement('w:' + side); x.set(qn('w:w'), val); x.set(qn('w:type'), 'dxa'); margins.append(x)
    pr.append(margins)
    for row_index, vals_row in enumerate(vals):
        row = table.add_row()
        trp = row._tr.get_or_add_trPr()
        trp.append(OxmlElement('w:cantSplit'))
        if row_index == 0:
            trp.append(OxmlElement('w:tblHeader'))
        for idx, (cell, text) in enumerate(zip(row.cells, vals_row)):
            cell.width = Inches(widths[idx])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cpr = cell._tc.get_or_add_tcPr()
            sh = OxmlElement('w:shd')
            sh.set(qn('w:fill'), '24445A' if row_index == 0 else ('F3F6F8' if row_index % 2 == 0 else 'FFFFFF'))
            cpr.append(sh)
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.keep_with_next = False
            if row_index == 0 or widths[idx] < 1.2 or re.fullmatch(r'\d+(?:至\d+)?', text):
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            inline(p, text, 10.5)
            if row_index == 0:
                for r in p.runs:
                    r.bold = True; r.font.color.rgb = RGBColor(255, 255, 255)
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(2)
    spacer.paragraph_format.line_spacing = 0.6

lines = MD.read_text(encoding='utf-8').splitlines()
numbering = doc.part.numbering_part.element
list_num_id = None
def restart_numbered_list():
    base_id = doc.styles['List Number'].element.xpath('./w:pPr/w:numPr/w:numId')[0].get(qn('w:val'))
    base = numbering.xpath('./w:num[@w:numId="' + base_id + '"]')[0]
    abstract_id = base.xpath('./w:abstractNumId')[0].get(qn('w:val'))
    new_id = max(int(x.get(qn('w:numId'))) for x in numbering.xpath('./w:num')) + 1
    num = OxmlElement('w:num'); num.set(qn('w:numId'), str(new_id))
    abstract = OxmlElement('w:abstractNumId'); abstract.set(qn('w:val'), abstract_id); num.append(abstract)
    override = OxmlElement('w:lvlOverride'); override.set(qn('w:ilvl'), '0')
    start = OxmlElement('w:startOverride'); start.set(qn('w:val'), '1'); override.append(start)
    num.append(override); numbering.append(num)
    return new_id

i = 0
while i < len(lines):
    s = lines[i].strip()
    if not s:
        i += 1; continue
    if s.startswith('|'):
        group = []
        while i < len(lines) and lines[i].strip().startswith('|'):
            group.append(lines[i]); i += 1
        table_block(group)
        continue
    if s.startswith('# '):
        p = doc.add_paragraph(s[2:], 'Title')
    elif s.startswith('## '):
        p = doc.add_paragraph(s[3:], 'Heading 1')
    elif s.startswith('### '):
        p = doc.add_paragraph(re.sub(r'^\d+\.\d+\s+', '', s[4:]), 'Heading 2')
    elif s.startswith('- '):
        p = doc.add_paragraph(style='List Bullet'); inline(p, s[2:], 10.5)
    elif re.match(r'^\d+\. ', s):
        if s.startswith('1. ') or list_num_id is None:
            list_num_id = restart_numbered_list()
        p = doc.add_paragraph(style='List Number')
        np = p._p.get_or_add_pPr().get_or_add_numPr()
        np.get_or_add_ilvl().val = 0
        np.get_or_add_numId().val = list_num_id
        inline(p, re.sub(r'^\d+\. ', '', s))
    else:
        p = doc.add_paragraph(); inline(p, s)
    i += 1

doc.core_properties.title = 'AURA 论文方法融合实施计划与初级组评分评估'
doc.core_properties.subject = '三人20个工作日实施计划与当前证据评分'
doc.core_properties.author = 'AURA'
doc.core_properties.keywords = 'KV260, FPGA, DPU, 20个工作日, 自主选题初级组'
doc.save(DOCX)

links = re.findall(r'\[[^\]]+\]\((E:/[^)]+)\)', MD.read_text(encoding='utf-8'))
evidence = []
for raw in sorted(set(links)):
    path = Path(raw)
    evidence.append({'path': raw, 'exists': path.exists(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None})
assert all(e['exists'] for e in evidence), 'A cited local source is missing'
summary = {
    'date': '2026-10-04', 'workdays': 20, 'current_score': 39,
    'current_range': [28, 50], 'baseline_complete_scenario': 72,
    'optimized_complete_scenario': 84, 'optimized_range': [77, 90],
    'fixture_tests_rerun': {'count': 35, 'result': 'OK', 'hardware_test': False},
    'evidence_files': evidence,
    'markdown_chars': len(MD.read_text(encoding='utf-8')),
    'docx_paragraphs': len(doc.paragraphs), 'tables': len(doc.tables),
}
(TMP / 'evidence_and_build.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in summary.items() if k != 'evidence_files'}, ensure_ascii=False))

