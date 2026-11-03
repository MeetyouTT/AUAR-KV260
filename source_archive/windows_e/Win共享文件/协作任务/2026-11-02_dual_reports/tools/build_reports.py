"""Render two evidence-based report drafts without running engineering tasks.

Uses stdlib OOXML plus ReportLab. PDF and DOCX share Markdown content; PDF is
independently typeset, rather than produced by an installed Word application.
"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
from html import escape
import csv
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
import xml.etree.ElementTree as ET

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak, CondPageBreak,
                              Table, TableStyle, Image, KeepTogether)
import build_figures

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('/home/ghmd')
SHARED = BASE/'Win共享文件'
VOICE = SHARED/'语音共享文件/deliverables'
TEMPLATE = BASE/'下载/技术文档模板.docx'
PYNQ = SHARED/'协作任务/2026-11-02_pynq_skill/skill/pynq-contract-testgen'
VISION = VOICE/'2026-10-21_dpu_vision_start'
REPAIR = VOICE/'2026-10-30_board_owner/integration/dialogue_repair'
WIDE = BASE/'aura-pan-wide-20261028'
NAVY = colors.HexColor('#213c5a')

EVIDENCE = [
    ('V01', BASE/'aura-pan-joint-20261023/implementation/utilization.rpt', 'narrow_utilization.rpt', '10月23日联合窄版资源'),
    ('V02', WIDE/'implementation/utilization.rpt', 'wide_utilization.rpt', '10月28日联合宽版资源'),
    ('V03', WIDE/'INDEPENDENT_AUDIT.json', 'wide_independent_audit.json', '宽版独立路由后审查'),
    ('V04', VISION/'evidence/board-yunet-v2.json', 'yunet_board.json', '固定输入YuNet实板对照'),
    ('V05', VISION/'evidence/board-three-fixed.json', 'sface_three_model_board.json', 'SFace实板及三模型切换'),
    ('V06', VISION/'evidence/sface-evaluation-report.json', 'sface_quality.json', 'SFace公开独立配对评估'),
    ('V07', VISION/'evidence/yunet-evaluation-report.json', 'yunet_quality.json', 'YuNet与FP32参考一致性'),
    ('V08', VOICE/'2026-10-18_compact_reply_fields/paired_profile.json', 'compact_fields_profile.json', '短字段配对阶段耗时'),
    ('V09', SHARED/'协作任务/2026-10-31_板卡资源实测/evidence/resource-samples.json', 'resource_samples.json', '30秒正常业务资源采样'),
    ('V10', REPAIR/'joint_balance_20261101/continued_validation_20261101/RETENTION_RESULT.json', 'retention_result.json', '自然到期存储检查'),
    ('V11', VOICE/'2026-10-30_board_owner/integration/production_business_acceptance/CURRENT_PUBLICATION_STATE.json', 'saved_publication_state.json', '最新保存业务状态，非本轮设备读取'),
    ('V12', PYNQ/'evidence/offline_validation.json', 'skill_offline_validation.json', 'Skill离线测试与示例汇总'),
    ('V13', PYNQ/'case_studies.md', 'skill_case_studies.md', 'Skill失败、修正与边界'),
    ('V14', WIDE/'build_joint.py', 'historical_build_joint.py', '构建输入与绝对路径依赖，仅阅读'),
    ('V15', SHARED/'协作任务/2026-11-02_AI辅助学习记录/ai_learning_record_review.md', 'ai_engineering_record.md', '五项工程协作案例复盘'),
    ('V16', SHARED/'协作任务/2026-11-02_AI辅助学习记录/conversation_excerpts.md', 'visible_conversation_excerpts.md', '可见范围调整问答，非全部历史导出'),
    ('V17', SHARED/'协作任务/2026-11-01_全项目文件复核/README.md', 'saved_project_review.md', '现状、机构异常与发布缺口'),
    ('V18', REPAIR/'animation_thinking_collaboration/public_preview_actual_1793458354293233900/preview_result.json', 'historical_render_result.json', '隔离角色渲染来源及限制'),
    ('V19', SHARED/'协作任务/2026-10-26_DPU模型量化核查/README.md', 'deployed_model_audit.md', '模型精度、形状与部署身份'),
    ('V20', WIDE/'candidate/rtl/visual_servo.sv', 'wide_visual_servo.sv', 'VSRV2宽版寄存器与时序实现'),
    ('V21', WIDE/'prepare.tcl', 'wide_prepare.tcl', '地址窗口及平台参数'),
    ('V22', WIDE/'platform/pin.xdc', 'wide_pin.xdc', '实际引脚约束'),
    ('V23', WIDE/'implementation/clocks.rpt', 'wide_clocks.rpt', '实现时钟报告'),
    ('V24', BASE/'aura-pan-joint-20261023/implementation/timing.rpt', 'narrow_timing.rpt', '窄版静态时序'),
    ('V25', WIDE/'implementation/timing.rpt', 'wide_timing.rpt', '宽版静态时序'),
    ('V26', PYNQ/'evidence/unit_tests.log', 'skill_unit_tests.log', 'Skill历史15项单元测试原始输出'),
    ('V27', SHARED/'协作任务/2026-11-02_pynq_skill/validation/archive_reproduction.json', 'skill_archive_reproduction.json', 'Skill解压复现记录'),
    ('V28', SHARED/'协作任务/2026-11-02_AI辅助学习记录/evidence_index.json', 'ai_source_index.json', 'AI工程案例38项具体来源索引'),
]

EXTERNAL = [
    {'id':'R1','title':'YOLOX: Exceeding YOLO Series in 2021','url':'https://arxiv.org/abs/2107.08430'},
    {'id':'R2','title':'ByteTrack: Multi-Object Tracking by Associating Every Detection Box','url':'https://arxiv.org/abs/2110.06864'},
    {'id':'R3','title':'OpenCV Zoo / YuNet','url':'https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet'},
    {'id':'R4','title':'OpenCV Zoo / SFace','url':'https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface'},
    {'id':'R5','title':'Vitis AI 3.0 tool compatibility','url':'https://xilinx.github.io/Vitis-AI/3.0/html/docs/reference/version_compatibility.html'},
    {'id':'R6','title':'PYNQ 3.1 overlay API','url':'https://pynq.readthedocs.io/en/v3.1/pynq_package/pynq.overlay.html'},
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def snapshot():
    out = ROOT/'evidence'
    out.mkdir(exist_ok=True)
    entries = []
    for ident, source, filename, scope in EVIDENCE:
        data = source.read_bytes()
        dest = out/(ident.lower()+'_'+filename)
        dest.write_bytes(data)
        entries.append({'id':ident, 'scope':scope, 'source_path':str(source),
                        'report_copy':str(dest.relative_to(ROOT)), 'bytes':len(data),
                        'sha256':sha(data), 'source_modified_utc':datetime.fromtimestamp(source.stat().st_mtime, timezone.utc).isoformat()})
    inputs = []
    for p in [TEMPLATE, BASE/'下载/2026FPGA创新设计赛道作品上传要求.pdf',
              BASE/'下载/Write/设计报告/设计报告.pdf', BASE/'下载/项目.zip',
              SHARED/"共享文件夹/Docs/全国大学生嵌入式芯片与系统设计竞赛'2026FPGA赛道选题指南-AMD.pdf",
              BASE/'图片/1212.png']:
        data = p.read_bytes()
        inputs.append({'path':str(p), 'bytes':len(data), 'sha256':sha(data)})
    index = {'schema':'auar-report-evidence-1', 'prepared_utc':datetime.now(timezone.utc).isoformat(),
             'work_title':'AUAR·雪妃', 'status':'REVIEW_DRAFT_NOT_FINAL_RELEASE',
             'engineering_experiments_rerun':False, 'board_accessed':False,
             'inputs':inputs, 'entries':entries, 'external_primary_sources':EXTERNAL,
             'note':'This is a document evidence snapshot, not the full project source or final engineering submission.'}
    (ROOT/'source_index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2)+'\n')
    return index


def blocks(path):
    lines = path.read_text().splitlines()
    result = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line == '<!-- pagebreak -->':
            result.append(('break', None));i += 1;continue
        if line == '<!-- toc -->':
            result.append(('toc', None));i += 1;continue
        m = re.match(r'^(#{1,4}) (.+)$', line)
        if m:
            result.append(('heading', (len(m.group(1)), m.group(2))));i += 1;continue
        m = re.match(r'^!\[(.*?)\]\((.*?)\)$', line)
        if m:
            result.append(('image', (m.group(1), m.group(2))));i += 1;continue
        if line.startswith('```'):
            chunk = [];i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                chunk.append(lines[i]);i += 1
            result.append(('code', '\n'.join(chunk)));i += 1;continue
        if line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', x.strip()) for x in cells):
                    rows.append(cells)
                i += 1
            assert len({len(row) for row in rows}) == 1, rows
            result.append(('table', rows));continue
        if line.startswith('>'):
            result.append(('quote', line.lstrip('> ').strip()));i += 1;continue
        if re.match(r'^\d+\. ', line):
            result.append(('list', line));i += 1;continue
        para = [line];i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#|\||!\[|```|<!--|>|\d+\. )', lines[i].strip()):
            para.append(lines[i].strip());i += 1
        result.append(('paragraph', ''.join(para)))
    return result


def limit_check():
    s = (ROOT/'competition_technical_report.md').read_text()
    checks = []
    for title, limit in [('摘要',800),('1.1 功能与特性',400),('1.2 应用领域',400),
                         ('1.3 主要技术特点',400),('1.4 主要性能指标',200),('1.5 主要创新点',200),
                         ('1.6 设计流程',200),('4.1 可扩展之处',300),('4.2 心得体会',1000)]:
        m = re.search(r'^#{2,4} '+re.escape(title)+r'\n(.*?)(?=^#{1,4} |\Z)', s, re.M|re.S)
        assert m, title
        value = re.sub(r'<!--.*?-->', '', m.group(1), flags=re.S)
        value = re.sub(r'\|\s*---[^\n]*', '', value)
        value = re.sub(r'[\s|*`#]', '', value)
        assert len(value) <= limit, (title, len(value), limit)
        checks.append({'section':title,'non_whitespace_characters_including_latin_and_digits':len(value),
                       'limit':limit,'passed':True})
    return checks


def widths(rows, total):
    n = len(rows[0])
    values = []
    for i in range(n):
        lengths = [len(row[i]) for row in rows]
        avg = sum(lengths)/len(lengths)
        values.append(max(3.2, (avg + min(max(lengths), 80)*0.5)**0.5))
    smallest = min(values)
    values = [min(v, smallest*2.1) for v in values]
    return [total*v/sum(values) for v in values]


def rich(s):
    s = escape(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = s.replace('`', '')
    return s


class ReportPDF(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and getattr(flowable, 'report_heading', False):
            key = 'h'+str(self._heading_count)
            self._heading_count += 1
            self.canv.bookmarkPage(key)
            level = min(flowable.report_level, 1)
            if level == 1 and not self._has_top:
                level = 0
            if level == 0:
                self._has_top = True
            self.canv.addOutlineEntry(flowable.getPlainText(), key, level, closed=False)


def render_pdf(content, dest, competition=False):
    build_figures.register()
    if 'ReportMono' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('ReportMono','/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'))
    pdfmetrics.registerFontFamily('ReportSong', normal='ReportSong', bold='ReportSong', italic='ReportSong', boldItalic='ReportSong')
    margin = 90 if competition else 64
    total = A4[0]-2*margin
    base = dict(fontName='ReportSong', textColor=colors.HexColor('#1f2933'), wordWrap='CJK')
    body = ParagraphStyle('body', fontSize=10.5, leading=16, spaceAfter=5,
                          firstLineIndent=21, alignment=TA_JUSTIFY,
                          allowWidows=0, allowOrphans=0, **base)
    plain = ParagraphStyle('plain', parent=body, firstLineIndent=0)
    h1 = ParagraphStyle('h1', fontSize=16, leading=23, textColor=NAVY, fontName='ReportSong',
                        wordWrap='CJK', spaceBefore=12, spaceAfter=9, keepWithNext=True)
    h2 = ParagraphStyle('h2', parent=h1, fontSize=12.6, leading=19, spaceBefore=9, spaceAfter=6)
    h3 = ParagraphStyle('h3', parent=h2, fontSize=11.4, leading=18, spaceBefore=9)
    title = ParagraphStyle('title', parent=h1, fontSize=29, leading=40, alignment=TA_CENTER, spaceBefore=38, spaceAfter=18)
    caption = ParagraphStyle('caption', parent=plain, fontSize=9, leading=13, textColor=colors.HexColor('#526274'), alignment=TA_CENTER, spaceBefore=5, spaceAfter=11)
    cell = ParagraphStyle('cell', fontName='ReportSong', fontSize=8.8, leading=12.5, wordWrap='CJK')
    header = ParagraphStyle('header', parent=cell, textColor=colors.white)
    quote = ParagraphStyle('quote', parent=plain, leftIndent=14, rightIndent=6, textColor=NAVY, borderColor=colors.HexColor('#c3d5e4'), borderWidth=0.7, borderPadding=8, spaceBefore=4, spaceAfter=10)
    code = ParagraphStyle('code', fontName='ReportMono', fontSize=8.3, leading=12, leftIndent=6, rightIndent=6, backColor=colors.HexColor('#f2f5f7'), borderPadding=7, spaceBefore=5, spaceAfter=10)
    doc = ReportPDF(str(dest), pagesize=A4, leftMargin=margin, rightMargin=margin,
                    topMargin=76, bottomMargin=55, title='AUAR·雪妃｜'+('赛事方技术报告' if competition else 'AMD设计报告'),
                    author='', subject='审阅稿V1；阶段证据与最终验收范围分开', pageCompression=1)
    doc._heading_count = 0
    doc._has_top = False
    story = []
    break_count = 0
    for kind, value in content:
        if kind == 'break':
            if not competition and break_count == 0:
                story.append(PageBreak())
            else:
                story.append(CondPageBreak(260))
            break_count += 1
        elif kind == 'heading':
            level, s = value
            if s == '参考文献' or s.startswith('附录 ') or (competition and s.startswith('第五部分 ')):
                if story and isinstance(story[-1],CondPageBreak):
                    story.pop()
                story.append(PageBreak())
            style = title if level == 1 else {2:h1,3:h2,4:h3}[level]
            p = Paragraph(rich(s), style)
            if level in (2,3):
                p.report_heading = True;p.report_level = level-2
            story.append(p)
        elif kind == 'toc':
            story.append(Spacer(1, 12))
            story.append(Paragraph('阅读目录', h2))
            for k,v in content:
                if k == 'heading' and v[0] == 2 and v[1] != '摘要':
                    story.append(Paragraph(rich(v[1]), plain))
        elif kind == 'table':
            w = widths(value, total)
            data = [[Paragraph(rich(x), header if r == 0 else cell) for x in row] for r,row in enumerate(value)]
            t = Table(data, colWidths=w, repeatRows=1, hAlign='LEFT')
            t.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),NAVY),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f3f6f9')]),
                ('VALIGN',(0,0),(-1,-1),'TOP'),
                ('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#ced7df')),
                ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
                ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
            ]))
            # Keep short tables intact, rather than leaving a few rows alone.
            th = t.wrap(total, doc.height)[1]
            group = [Spacer(1,3),t,Spacer(1,8)]
            prefix=[]
            if story and isinstance(story[-1],Paragraph):
                prefix.insert(0,story.pop())
                while story and isinstance(story[-1],Paragraph) and story[-1].style.name in ('h1','h2','h3'):
                    prefix.insert(0,story.pop())
            ph=sum(p.wrap(total,doc.height)[1]+p.getSpaceBefore()+p.getSpaceAfter() for p in prefix)
            if th+ph < doc.height-45:
                story.append(KeepTogether(prefix+group))
            else:
                story.extend(prefix)
                story.append(KeepTogether(group) if th < doc.height-70 else t)
        elif kind == 'image':
            cap, rel = value
            p = ROOT/rel
            with PILImage.open(p) as im:
                iw, ih = im.size
            scale = min(total/iw, (230 if 'character_' in rel else 345)/ih)
            image = Image(str(p), width=iw*scale, height=ih*scale)
            heads=[]
            while story and isinstance(story[-1],Paragraph) and story[-1].style.name in ('h1','h2','h3'):
                heads.insert(0,story.pop())
            story.append(KeepTogether(heads+[Spacer(1,5),image,Paragraph(rich(cap),caption)]))
        elif kind == 'code':
            lines = [escape(s) for s in value.splitlines()]
            story.append(Paragraph('<br/>'.join(lines),code))
        else:
            style = quote if kind == 'quote' else plain if kind == 'list' or value.startswith('[') else body
            story.append(Paragraph(rich(value), style))
    def page(c, _):
        c.saveState()
        c.setFont('ReportSong', 8)
        c.setFillColor(colors.HexColor('#6b7885'))
        c.drawString(margin,A4[1]-44,'AUAR·雪妃  /  '+('赛事方技术文档' if competition else 'AMD 自主选题设计报告'))
        c.setStrokeColor(colors.HexColor('#cdd7e1'));c.setLineWidth(0.5)
        c.line(margin,A4[1]-52,A4[0]-margin,A4[1]-52)
        c.drawString(margin,31,'审阅稿 V1  ·  2026-11-02')
        c.drawRightString(A4[0]-margin,31,str(doc.page))
        c.restoreState()
    doc.build(story, onFirstPage=page, onLaterPages=page)


W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
WP = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
PIC = 'http://schemas.openxmlformats.org/drawingml/2006/picture'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
for prefix, ns in [('w',W),('r',R),('wp',WP),('a',A),('pic',PIC)]:
    ET.register_namespace(prefix,ns)


def el(tag, attrs=None, text=None):
    e = ET.Element('{'+W+'}'+tag, {'{'+W+'}'+k:str(v) for k,v in (attrs or {}).items()})
    if text is not None:
        e.text = text
    return e


def paragraph(s='', style='RptBody', keep=False):
    p = el('p');pr = el('pPr');pr.append(el('pStyle',{'val':style}))
    if keep:pr.append(el('keepNext'))
    p.append(pr)
    run = el('r');t = el('t',text=s.replace('**','').replace('`',''))
    t.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
    run.append(t);p.append(run)
    return p


def docx_styles():
    values = [
        ('RptBody', '正文',22,False,0,'202933',None),
        ('RptPlain','无缩进正文',22,False,0,'202933',None),
        ('RptTitle','作品名称',48,True,0,'213C5A',None),
        ('RptH1','一级标题',32,True,0,'213C5A',0),
        ('RptH2','二级标题',26,True,0,'213C5A',1),
        ('RptH3','三级标题',23,True,0,'213C5A',2),
        ('RptCell','表格正文',18,False,0,'202933',None),
        ('RptCellHead','表头',19,True,0,'FFFFFF',None),
        ('RptCaption','图题',18,False,0,'526274',None),
        ('RptQuote','问答摘录',21,False,0,'213C5A',None),
        ('RptCode','命令',18,False,0,'202933',None),
    ]
    out = ''
    for sid,name,size,bold,_,color,outline in values:
        heading = sid.startswith('RptH')
        pr = '<w:keepNext/>' if heading else ''
        pr += '<w:spacing w:before="'+('180' if heading else '0')+'" w:after="'+('140' if heading else '100')+'" w:line="310" w:lineRule="auto"/>'
        if sid == 'RptBody':pr += '<w:ind w:firstLine="440"/><w:jc w:val="both"/>'
        if sid in ('RptTitle','RptCaption'):pr += '<w:jc w:val="center"/>'
        if sid in ('RptCell','RptCellHead'):pr += '<w:spacing w:after="0" w:line="270" w:lineRule="auto"/>'
        if outline is not None:pr += '<w:outlineLvl w:val="'+str(outline)+'"/>'
        if sid == 'RptQuote':pr += '<w:ind w:left="260" w:right="100"/>'
        font = '黑体' if heading or sid=='RptTitle' else '宋体'
        latin = 'Consolas' if sid=='RptCode' else 'Times New Roman'
        out += '<w:style w:type="paragraph" w:styleId="'+sid+'"><w:name w:val="'+name+'"/><w:qFormat/><w:pPr>'+pr+'</w:pPr><w:rPr><w:rFonts w:ascii="'+latin+'" w:hAnsi="'+latin+'" w:eastAsia="'+font+'"/><w:sz w:val="'+str(size)+'"/><w:szCs w:val="'+str(size)+'"/><w:color w:val="'+color+'"/>'+('<w:b/>' if bold else '')+'</w:rPr></w:style>'
    return out


def render_docx(content, dest, competition=False):
    with zipfile.ZipFile(TEMPLATE) as z:
        parts = {n:z.read(n) for n in z.namelist() if not n.endswith('/')}
    document = ET.Element('{'+W+'}document')
    body = ET.SubElement(document,'{'+W+'}body')
    original = ET.fromstring(parts['word/document.xml'])
    section = deepcopy(original.find('{'+W+'}body/{'+W+'}sectPr'))
    if not competition:
        mar = section.find('{'+W+'}pgMar')
        mar.set('{'+W+'}left','1280');mar.set('{'+W+'}right','1280')
    # Keep the template's page size, margins, logo header and header relationships.
    available_twips = 11906-(3600 if competition else 2560)
    rels = ET.fromstring(parts['word/_rels/document.xml.rels'])
    image_number = 100
    drawing_id = 100
    break_count = 0
    for kind,value in content:
        if kind == 'heading':
            level,s = value
            if s == '参考文献' or s.startswith('附录 ') or (competition and s.startswith('第五部分 ')):
                p=el('p');run=el('r');run.append(el('br',{'type':'page'}));p.append(run);body.append(p)
            body.append(paragraph(s,{1:'RptTitle',2:'RptH1',3:'RptH2',4:'RptH3'}[level]))
        elif kind == 'break':
            if not competition and break_count == 0:
                p = el('p');run=el('r');run.append(el('br',{'type':'page'}));p.append(run);body.append(p)
            break_count += 1
        elif kind == 'toc':
            body.append(paragraph('阅读目录','RptH2'))
            for k,v in content:
                if k=='heading' and v[0]==2 and v[1]!='摘要':body.append(paragraph(v[1],'RptPlain'))
        elif kind == 'table':
            tbl=el('tbl');pr=el('tblPr');pr.append(el('tblW',{'w':available_twips,'type':'dxa'}))
            borders=el('tblBorders')
            for key in ['top','left','bottom','right','insideH','insideV']:
                borders.append(el(key,{'val':'single','sz':'4','color':'CED7DF'}))
            pr.append(borders);pr.append(el('tblLayout',{'type':'fixed'}))
            margins=el('tblCellMar')
            for k in ['top','left','bottom','right']:margins.append(el(k,{'w':'80','type':'dxa'}))
            pr.append(margins);tbl.append(pr)
            grid=el('tblGrid');ws=widths(value,available_twips)
            ws=[round(x) for x in ws];ws[-1]=available_twips-sum(ws[:-1])
            for width in ws:grid.append(el('gridCol',{'w':width}))
            tbl.append(grid)
            for rn,row in enumerate(value):
                tr=el('tr');rpr=el('trPr');rpr.append(el('cantSplit'))
                if rn==0:rpr.append(el('tblHeader'))
                tr.append(rpr)
                for width,txt in zip(ws,row):
                    tc=el('tc');tcpr=el('tcPr');tcpr.append(el('tcW',{'w':width,'type':'dxa'}))
                    tcpr.append(el('vAlign',{'val':'top'}))
                    if rn==0:tcpr.append(el('shd',{'fill':'213C5A','val':'clear'}))
                    elif rn%2==0:tcpr.append(el('shd',{'fill':'F3F6F9','val':'clear'}))
                    tc.append(tcpr);tc.append(paragraph(txt,'RptCellHead' if rn==0 else 'RptCell'));tr.append(tc)
                tbl.append(tr)
            body.append(tbl);body.append(paragraph('','RptPlain'))
        elif kind == 'image':
            cap,rel=value;p=ROOT/rel
            with PILImage.open(p) as im:iw,ih=im.size
            max_w=available_twips/20
            scale=min(max_w/iw,(230 if 'character_' in rel else 345)/ih)
            cx,cy=round(iw*scale*12700),round(ih*scale*12700)
            media='report_image_'+str(image_number)+'.png';rid='rIdReport'+str(image_number)
            parts['word/media/'+media]=p.read_bytes()
            ET.SubElement(rels,'{'+REL+'}Relationship',{'Id':rid,'Type':R+'/image','Target':'media/'+media})
            node=paragraph('','RptCaption',keep=True)
            run=el('r');drawing=el('drawing')
            xml='<wp:inline xmlns:wp="'+WP+'" xmlns:a="'+A+'" xmlns:pic="'+PIC+'" xmlns:r="'+R+'" distT="0" distB="0" distL="0" distR="0"><wp:extent cx="'+str(cx)+'" cy="'+str(cy)+'"/><wp:docPr id="'+str(drawing_id)+'" name="'+escape(media)+'" descr="'+escape(cap,quote=True)+'"/><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic><a:graphicData uri="'+PIC+'"><pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="'+media+'"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="'+rid+'"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="'+str(cx)+'" cy="'+str(cy)+'"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline>'
            drawing.append(ET.fromstring(xml));run.append(drawing);node.append(run);body.append(node)
            body.append(paragraph(cap,'RptCaption'));image_number+=1;drawing_id+=1
        elif kind=='code':
            for line in value.splitlines():body.append(paragraph(line,'RptCode'))
        else:
            style='RptQuote' if kind=='quote' else 'RptPlain' if kind=='list' or value.startswith('[') else 'RptBody'
            body.append(paragraph(value,style))
    body.append(section)
    parts['word/document.xml']=ET.tostring(document,encoding='utf-8',xml_declaration=True)
    parts['word/_rels/document.xml.rels']=ET.tostring(rels,encoding='utf-8',xml_declaration=True)
    styles=parts['word/styles.xml'].decode('utf-8')
    parts['word/styles.xml']=styles.replace('</w:styles>',docx_styles()+'</w:styles>').encode('utf-8')
    footer='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr xmlns:w="'+W+'"><w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:rFonts w:eastAsia="宋体"/><w:sz w:val="16"/></w:rPr><w:t>AUAR·雪妃  |  审阅稿 V1  |  </w:t></w:r><w:fldSimple w:instr="PAGE"><w:r><w:t>1</w:t></w:r></w:fldSimple></w:p></w:ftr>'
    for n in list(parts):
        if re.fullmatch(r'word/footer\d+\.xml',n):parts[n]=footer.encode('utf-8')
    # Do not inherit the template authors' names or custom personal metadata.
    parts['docProps/core.xml']=('''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>AUAR·雪妃：'''+('赛事方技术报告' if competition else 'AMD设计报告')+'''</dc:title><dc:creator></dc:creator><cp:lastModifiedBy></cp:lastModifiedBy><dc:description>审阅稿V1；对应阶段证据，最终验收待补</dc:description><dcterms:modified xsi:type="dcterms:W3CDTF">'''+datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')+'''</dcterms:modified></cp:coreProperties>''').encode('utf-8')
    if 'docProps/custom.xml' in parts:
        parts['docProps/custom.xml']=b'<?xml version="1.0" encoding="UTF-8"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"/>'
    # Reset stale document statistics inherited from the blank template.
    app=ET.fromstring(parts['docProps/app.xml'])
    for node in app:
        if node.tag.split('}')[-1] in ('Pages','Words','Characters','CharactersWithSpaces','TotalTime'):node.text='0'
    parts['docProps/app.xml']=ET.tostring(app,encoding='utf-8',xml_declaration=True)
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in parts.items():z.writestr(name,data)


def validate(index, limits):
    results={'prepared_utc':datetime.now(timezone.utc).isoformat(), 'engineering_tasks_run':False,
             'template_character_limits':limits,'evidence':[],'documents':[],
             'limitations':['DOCX has not been opened in Windows Word/WPS.',
                            'PDF is independently typeset from the same Markdown, not an Office conversion.',
                            'Physical photos, CAD/wiring originals, historical AI transcripts and final same-release acceptance remain pending.']}
    for row in index['entries']:
        p=ROOT/row['report_copy'];assert sha(p.read_bytes())==row['sha256']
        if p.suffix=='.json':json.loads(p.read_text())
        results['evidence'].append({'id':row['id'],'sha256_match':True})
    for stem in ['auar_xuefei_amd_report','auar_xuefei_competition_report']:
        d=ROOT/(stem+'.docx');p=ROOT/(stem+'.pdf')
        with zipfile.ZipFile(d) as z:
            assert z.testzip() is None
            for name in z.namelist():
                if name.endswith('.xml') or name.endswith('.rels'):ET.fromstring(z.read(name))
            text=''.join(ET.fromstring(z.read('word/document.xml')).itertext())
            assert 'AUAR·雪妃' in text
            assert '平芜春烬' not in z.read('docProps/core.xml').decode()
        assert p.stat().st_size<50_000_000
        extracted=subprocess.check_output(['pdftotext','-layout',str(p),'-']).decode('utf-8')
        assert 'AUAR·雪妃' in extracted
        for marker in ['66,960','61.41','13.56','98.8%']:
            assert marker in extracted,(stem,marker)
        info=subprocess.check_output(['pdfinfo',str(p)]).decode()
        pages=int(re.search(r'^Pages:\s+(\d+)',info,re.M).group(1))
        results['documents'].append({'stem':stem,'pdf_pages':pages,'pdf_bytes':p.stat().st_size,
                                     'docx_bytes':d.stat().st_size,'docx_xml_crc_valid':True,
                                     'pdf_text_and_key_metrics_present':True,'pdf_under_50mb':True})
    results['status']='PASS_DOCUMENT_CHECKS_REVIEW_ITEMS_REMAIN'
    (ROOT/'validation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    return results


def main():
    index=snapshot()
    limits=limit_check()
    build_figures.main()
    for source,stem,competition in [('amd_design_report.md','auar_xuefei_amd_report',False),
                                     ('competition_technical_report.md','auar_xuefei_competition_report',True)]:
        content=blocks(ROOT/source)
        for kind,value in content:
            if kind=='image':assert (ROOT/value[1]).exists(),value
        render_docx(content,ROOT/(stem+'.docx'),competition)
        render_pdf(content,ROOT/(stem+'.pdf'),competition)
    result=validate(index,limits)
    print(json.dumps({'status':result['status'],'documents':result['documents'],
                      'evidence_files':len(index['entries']),'word_limits':len(limits)},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
