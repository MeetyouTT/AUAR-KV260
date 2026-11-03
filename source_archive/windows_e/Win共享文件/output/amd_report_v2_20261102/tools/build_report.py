"""Build the AMD PDF and editable HTML from one structured text source."""
from __future__ import annotations

import hashlib
import html
import json
import math
import re
import subprocess
from pathlib import Path

from PIL import Image as PILImage
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, CondPageBreak, Table, TableStyle, Image, KeepTogether
import reportlab.lib.textsplit as textsplit
import reportlab.platypus.paragraph as paragraph_engine

import build_figures
from content_updates import compose, REQUIREMENTS

OUT=Path(__file__).resolve().parents[1]
OLD=Path('E:/Win共享文件/协作任务/2026-11-02_dual_reports')
PDF=OUT/'auar_xuefei_amd_design_report_v2.pdf'
NAVY=colors.HexColor('#243E56')
# ReportLab's Japanese list omits common full-width Chinese punctuation.
for engine in (textsplit,paragraph_engine):
    engine.ALL_CANNOT_START+='，。；：！？）》」』】”’％、'


def save_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')


def blocks(text):
    lines=text.splitlines();result=[];i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line: i+=1;continue
        if line=='<!-- pagebreak -->': result.append(('break',None));i+=1;continue
        if line=='<!-- toc -->': i+=1;continue
        m=re.match(r'^(#{1,4}) (.+)$',line)
        if m: result.append(('heading',(len(m.group(1)),m.group(2))));i+=1;continue
        m=re.match(r'^!\[(.*?)\]\((.*?)\)$',line)
        if m: result.append(('image',(m.group(1),m.group(2))));i+=1;continue
        if line.startswith('```'):
            chunk=[];i+=1
            while i<len(lines) and not lines[i].strip().startswith('```'):
                chunk.append(lines[i]);i+=1
            result.append(('code','\n'.join(chunk)));i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                cells=[x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',c) for c in cells): rows.append(cells)
                i+=1
            assert len({len(r) for r in rows})==1,rows
            result.append(('table',rows));continue
        if line.startswith('>'):
            result.append(('quote',line.lstrip('> ').strip()));i+=1;continue
        if re.match(r'^\d+\. ',line): result.append(('list',line));i+=1;continue
        para=[line];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^(#|\||!\[|```|<!--|>|\d+\. )',lines[i].strip()):
            para.append(lines[i].strip());i+=1
        result.append(('paragraph',''.join(para)))
    return result


def rich(text,links=False):
    text=html.escape(text)
    text=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',text)
    text=text.replace('`','')
    return text


def widths(rows,total):
    scores=[]
    for i in range(len(rows[0])):
        weighted=[sum(.55 if ord(c)<128 else 1 for c in row[i]) for row in rows]
        avg=sum(weighted)/len(weighted)
        scores.append(max(4.0,math.sqrt(avg+min(max(weighted),70)*.5)))
    smallest=min(scores);scores=[min(s,smallest*2.3) for s in scores]
    return [total*s/sum(scores) for s in scores]


class ReportPDF(SimpleDocTemplate):
    def afterFlowable(self,flowable):
        if isinstance(flowable,Paragraph) and getattr(flowable,'report_heading',False):
            key='h'+str(self.heading_count);self.heading_count+=1
            level=flowable.report_level
            if level==1 and not self.top_seen: level=0
            if level==0: self.top_seen=True
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(flowable.getPlainText(),key,level,closed=False)


def render_pdf(content):
    margin=57
    doc=ReportPDF(str(PDF),pagesize=A4,leftMargin=margin,rightMargin=margin,topMargin=57,bottomMargin=47,
                  title='AUAR 雪妃 AMD设计报告 V2',author='',subject='AMD 3.3.5.3七项要求及可追溯证据',pageCompression=1)
    doc.heading_count=0;doc.top_seen=False
    width=doc.width
    base=dict(fontName='YaHei',textColor=colors.black,wordWrap='CJK')
    body=ParagraphStyle('body',fontSize=10.5,leading=16.3,spaceAfter=6,firstLineIndent=21,
                        alignment=TA_JUSTIFY,allowWidows=0,allowOrphans=0,**base)
    plain=ParagraphStyle('plain',parent=body,firstLineIndent=0)
    title=ParagraphStyle('title',parent=plain,fontName='YaHeiBold',fontSize=25,leading=34,alignment=TA_CENTER,spaceBefore=7,spaceAfter=12)
    h1=ParagraphStyle('h1',parent=plain,fontName='YaHeiBold',fontSize=16,leading=23,spaceBefore=12,spaceAfter=8,keepWithNext=True)
    h2=ParagraphStyle('h2',parent=h1,fontSize=12.4,leading=19,spaceBefore=9,spaceAfter=6)
    h3=ParagraphStyle('h3',parent=h2,fontSize=11,leading=17)
    cap=ParagraphStyle('cap',parent=plain,fontSize=9,leading=13,textColor=colors.HexColor('#536576'),alignment=TA_CENTER,spaceBefore=5,spaceAfter=10)
    cell=ParagraphStyle('cell',fontName='YaHei',fontSize=9.2,leading=13.2,textColor=colors.black,wordWrap='CJK')
    head=ParagraphStyle('thead',parent=cell,fontName='YaHeiBold',textColor=colors.white)
    quote=ParagraphStyle('quote',parent=plain,leftIndent=12,rightIndent=8,fontSize=10,leading=15.5,textColor=colors.HexColor('#243E56'))
    code=ParagraphStyle('code',fontName='ReportMono',fontSize=8.1,leading=11.5,leftIndent=8,rightIndent=6,spaceBefore=4,spaceAfter=9,textColor=colors.black)
    story=[];first_break=True;image_count=0
    for kind,value in content:
        if kind=='break':
            story.append(PageBreak() if first_break else CondPageBreak(235));first_break=False
        elif kind=='heading':
            level,text=value
            if text=='参考文献' or text.startswith('附录 '):
                if story and isinstance(story[-1],CondPageBreak): story.pop()
                story.append(CondPageBreak(180))
            p=Paragraph(rich(text),title if level==1 else {2:h1,3:h2,4:h3}[level])
            if level in [2,3]: p.report_heading=True;p.report_level=level-2
            story.append(p)
        elif kind=='table':
            data=[[Paragraph(rich(x).replace('27B LLM 与 OmniVoice','27B LLM 与<br/>OmniVoice'),
                             head if r==0 else cell) for x in row] for r,row in enumerate(value)]
            table=Table(data,colWidths=widths(value,width),repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),NAVY),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F4F6F8')]),
                ('GRID',(0,0),(-1,-1),.4,colors.HexColor('#D9D9D9')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
                ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
            ]))
            th=table.wrap(width,doc.height)[1]
            table.spaceBefore=3
            table.spaceAfter=8
            if th<doc.height*.45:
                table.splitByRow=0
            story.append(table)
        elif kind=='image':
            caption,rel=value;p=OUT/rel
            with PILImage.open(p) as im: iw,ih=im.size
            scale=min(width/iw,300/ih)
            diagram=Image(str(p),iw*scale,ih*scale)
            diagram.spaceBefore=4
            diagram.keepWithNext=True
            story.extend([diagram,Paragraph(rich(caption),cap)])
            image_count+=1
        elif kind=='code':
            story.append(Paragraph('<br/>'.join(html.escape(line).replace(' ','&#160;') for line in value.splitlines()),code))
        else:
            style=quote if kind=='quote' else plain if kind=='list' or value.startswith('[') else body
            story.append(Paragraph(rich(value),style))
    def footer(c,d):
        c.saveState();c.setFont('YaHei',8);c.setFillColor(colors.HexColor('#65717D'))
        c.drawString(margin,A4[1]-31,'AUAR 雪妃  /  AMD 自主选题设计报告')
        c.drawString(margin,25,'V2  2026-11-02')
        c.drawRightString(A4[0]-margin,25,str(d.page));c.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return image_count


def render_html(content):
    parts=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
           '<title>AUAR 雪妃 AMD设计报告 V2</title>',
           '''<style>body{font:16px/1.8 "Microsoft YaHei",sans-serif;color:#111;max-width:900px;margin:40px auto;padding:0 28px}h1,h2,h3,h4{color:#000;line-height:1.5}h1{text-align:center;font-size:30px}h2{margin-top:32px}p{text-align:justify}table{border-collapse:collapse;width:100%;font-size:14px;margin:18px 0}th,td{border:1px solid #d9d9d9;padding:10px;vertical-align:middle}th{background:#243e56;color:white}tr:nth-child(even){background:#f4f6f8}img{width:100%;height:auto}figure{margin:24px 0}figcaption{text-align:center;color:#536576;font-size:14px}blockquote{margin:12px 20px;color:#243e56}pre{font:13px/1.6 Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;padding:12px;background:#f4f6f8}a{overflow-wrap:anywhere}.printbreak{break-before:page}@media print{body{margin:0;max-width:none;font-size:11pt}a{color:inherit}h2,h3{break-after:avoid}figure,tr{break-inside:avoid}}</style><body>''']
    for kind,value in content:
        if kind=='heading':
            level,text=value;parts.append(f'<h{level}>{rich(text)}</h{level}>')
        elif kind=='break': parts.append('<div class="printbreak"></div>')
        elif kind=='table':
            parts.append('<table>')
            for i,row in enumerate(value):
                tag='th' if i==0 else 'td';parts.append('<tr>'+''.join(f'<{tag}>{rich(x)}</{tag}>' for x in row)+'</tr>')
            parts.append('</table>')
        elif kind=='image':
            caption,rel=value;parts.append(f'<figure><img src="{html.escape(rel)}" alt="{html.escape(caption)}"><figcaption>{rich(caption)}</figcaption></figure>')
        elif kind=='code': parts.append('<pre>'+html.escape(value)+'</pre>')
        elif kind=='quote': parts.append('<blockquote>'+rich(value)+'</blockquote>')
        else: parts.append('<p>'+rich(value)+'</p>')
    parts.append('</body></html>')
    (OUT/'amd_design_report_v2.html').write_text('\n'.join(parts),encoding='utf8')


def write_companions(text,requirements):
    coverage=[]
    evidence_status=['DOCUMENTED','DOCUMENTED','DOCUMENTED_WITH_PHYSICAL_WIRING_PENDING',
                     'HISTORICAL_COMPARISONS_WITH_DEFINED_LIMITS','VERBATIM_EXCERPTS_AND_LABELLED_HISTORICAL_REVIEWS',
                     'OFFLINE_SKILL_PASSED_NOT_BOARD_VALIDATED','OFFLINE_REPRODUCIBLE_FULL_SYSTEM_PENDING']
    for (rid,title,chapter,detail),status in zip(requirements,evidence_status):
        coverage.append({'id':rid,'requirement':title,'chapter':chapter,'content':detail,'chapter_present':True,'evidence_status':status})
    save_json(OUT/'requirements/coverage.json',{'schema':'amd-seven-requirements-coverage-1','requirements':coverage,
              'all_seven_chapters_present':True,'all_full_system_acceptance_claimed':False})
    (OUT/'README.txt').write_text('''AUAR 雪妃 AMD设计报告 V2

主报告：auar_xuefei_amd_design_report_v2.pdf
可编辑正文：amd_design_report_v2.html（与figures目录保持相对位置）
七项映射：requirements/coverage.json
来源索引：source_index.json；数值来源：data/metrics.json

附件
attachments/evidence：阶段原始报告、JSON、少量源码和新保存状态摘录。
attachments/ai_collaboration：历史工程复盘、可见问答及文档生成纠错实录。
attachments/validation：本次Windows离线原始日志和输出。
attachments/wiring：资料核对版接线PDF、PNG、SVG和逐线表。
skill/pynq-contract-testgen：既有离线Skill原字节副本、两个示例和说明。
reproduction：从新目录核对证据与复跑Skill的入口。

从零执行包内离线部分
准备Python 3.8或更高版本。在本目录运行：
python -B reproduction/reproduce_offline.py --out ../auar_verify_01
输出目录必须是新目录。预期summary.json为PASS；15项单元、加法36例和CRC37例通过。
board_verified和full_system_reproduced保持false。

交付范围
这是AMD七项设计报告及附件，不是全部工程源码RAR或已完成实机复现的发布包。
完整重建仍需参考DCP/IP仓库和最终配套release；操作步骤、输入与待验事项见第7章。
准确历史AI模型版本、核心开发逐轮问答和个人分工按真实留存继续归档。
人脸与声纹独立工作；已取消的跨模态关联不作为新增任务。
图纸保留实物待核标签，阶段性能不代替新版联合性能。
''',encoding='utf-8-sig')
    save_json(OUT/'reproduction/full_system_inputs.json',{
        'status':'INPUTS_NOT_COMPLETE_IN_REPORT_PACKAGE',
        'reference_dcp':{'filename':'source_routed.dcp','bytes':125094047,
                         'sha256':'ac5f85a14eee133b56e06a514f37e3e8db30b2ae4d16a5490b79b926a07bb77e','included':False},
        'tool_versions':{'vivado':'2022.2','vitis':'2022.2','petalinux':'2022.2','vitis_ai':'3.0'},
        'dpu_target_fingerprint':'0x101000056010407',
        'other_required_inputs':['complete IP repositories and repos.txt','same-build BIT/XSA/DTBO/XCLBIN',
                                 'fixed model sources and arch.json','unified application/camera/controller/native manifests',
                                 'external Windows LLM/TTS weights and configured runtimes','documented physical peripherals'],
        'llm_weights_copied':False,'full_system_reproduction_verified':False})


def main():
    build_figures.generate()
    text,requirements=compose(OUT,OLD)
    # Confirm the displayed model medians and resource figures agree with the numeric source.
    metrics=json.loads((OUT/'data/metrics.json').read_text(encoding='utf8'))
    for row in metrics['model_paths']:
        for key in ['cpu_median_ms','cpu_p95_ms','dpu_median_ms','dpu_p95_ms']:
            assert f'{row[key]:.2f}' in text,(row['model'],key)
    assert all(re.search(r'^## '+str(i)+r' ',text,re.M) for i in range(1,8))
    assert 'ec12 文件已应用、production_ready=false' not in text
    save_json(OUT/'report_source.json',{'format':'structured_markdown_input','title':'AUAR 雪妃 AMD设计报告 V2','text':text})
    content=blocks(text)
    render_html(content)
    images=render_pdf(content)
    write_companions(text,requirements)
    qa=OUT/'_qa/pages_r3';qa.mkdir(parents=True,exist_ok=True)
    r=subprocess.run([str(build_figures.POPPLER),'-scale-to','1600','-png',str(PDF),str(qa/'page')],capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    reader=PdfReader(PDF)
    page_text=[p.extract_text() or '' for p in reader.pages]
    extracted='\n'.join(page_text)
    checks={'schema':'amd-report-v2-document-validation-1','pages':len(reader.pages),'pdf_bytes':PDF.stat().st_size,
            'below_50mb':PDF.stat().st_size<50_000_000,'seven_chapters_present':all(f'{i} ' in extracted for i in range(1,8)),
            'figure_count':images,'text_length':len(extracted),'per_page_text_length':[len(x) for x in page_text],
            'all_sources_sha_verified_before_copy':True,'new_skill_validation':'PASS_OFFLINE_ONLY',
            'full_system_reproduction_verified':False,'visual_review':'PENDING_ALL_PAGE_INSPECTION'}
    save_json(OUT/'_qa/document_validation.json',checks)
    print(json.dumps(checks,ensure_ascii=False,indent=2))
    print('PDF',PDF)


if __name__=='__main__':
    main()
