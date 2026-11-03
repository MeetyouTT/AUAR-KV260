from pathlib import Path
import collections
import csv
import datetime as dt
import hashlib
import html
import json
import os
import re
import zipfile
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether

from collect_evidence import OUT, WORK, public_text


def sha(b):return hashlib.sha256(b).hexdigest()


def clean(s):
    s=re.sub(r'\[([^\]]+)\]\([^\n]+?\)',r'\1',s)
    s=s.replace('**','').replace('`','')
    return s


def inlines(s):
    s=html.escape(re.sub(r'\[([^\]]+)\]\([^\n]+?\)',r'\1',s))
    s=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',s)
    s=s.replace('`','')
    return s


def blocks(s):
    lines=s.splitlines();out=[];i=0
    while i<len(lines):
        l=lines[i].rstrip()
        if not l.strip():i+=1;continue
        if l=='<!-- pagebreak -->':out.append(('pagebreak',None));i+=1;continue
        if l.startswith('```'):
            vals=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                vals.append(lines[i]);i+=1
            out.append(('code','\n'.join(vals)));i+=1;continue
        if l.startswith('|') and i+1<len(lines) and re.match(r'^\|[\s:|\-]+\|?$',lines[i+1]):
            rows=[[v.strip() for v in l.strip().strip('|').split('|')]];i+=2
            while i<len(lines) and lines[i].startswith('|'):
                rows.append([v.strip() for v in lines[i].strip().strip('|').split('|')]);i+=1
            out.append(('table',rows));continue
        m=re.match(r'^(#{1,6})\s+(.+)',l)
        if m:out.append(('h'+str(len(m.group(1))),m.group(2)));i+=1;continue
        if l.startswith('>'):
            vals=[]
            while i<len(lines) and lines[i].startswith('>'):
                vals.append(re.sub(r'^> ?', '',lines[i]));i+=1
            for part in re.split(r'\n\s*\n','\n'.join(vals)):
                if part.strip():out.append(('quote',part))
            continue
        if re.match(r'^(?:\d+\.|-)\s+',l):
            out.append(('list',l));i+=1;continue
        vals=[l];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^(?:#|>|\||```|<!--|\d+\.\s|[-]\s)',lines[i]):
            vals.append(lines[i].rstrip());i+=1
        out.append(('p',' '.join(vals)))
    return out


FONT='/usr/share/fonts/truetype/arphic/uming.ttc'
pdfmetrics.registerFont(TTFont('RecordSong',FONT,subfontIndex=0))
pdfmetrics.registerFontFamily('RecordSong',normal='RecordSong',bold='RecordSong',italic='RecordSong',boldItalic='RecordSong')
NAVY=colors.HexColor('#17314f')
MUTED=colors.HexColor('#5d6672')


def widths(n,available):
    ratios={2:[.29,.71],3:[.31,.29,.40],4:[.28,.30,.22,.20]}.get(n,[1/n]*n)
    return [available*x for x in ratios]


def make_pdf(md,path,title,transcript=False):
    body=ParagraphStyle('body',fontName='RecordSong',fontSize=10.5,leading=16.8,spaceAfter=7,wordWrap='CJK',splitLongWords=True)
    styles={
      'p':body,'list':ParagraphStyle('list',parent=body,leftIndent=9,firstLineIndent=-9,spaceAfter=7),
      'quote':ParagraphStyle('quote',parent=body,fontSize=10,leading=15.3,leftIndent=12,rightIndent=3,textColor=colors.HexColor('#303b48'),borderColor=colors.HexColor('#b0bfcc'),borderWidth=.5,borderPadding=5,spaceBefore=4,spaceAfter=8),
      'code':ParagraphStyle('code',parent=body,fontSize=9,leading=13.8,leftIndent=8,backColor=colors.HexColor('#f4f6f8'),borderPadding=5),
      'h1':ParagraphStyle('h1',parent=body,fontSize=23,leading=32,textColor=NAVY,spaceBefore=16,spaceAfter=15,keepWithNext=True),
      'h2':ParagraphStyle('h2',parent=body,fontSize=15,leading=23,textColor=NAVY,spaceBefore=4,spaceAfter=12,keepWithNext=True),
      'h3':ParagraphStyle('h3',parent=body,fontSize=11.5,leading=18,textColor=NAVY,spaceBefore=7,spaceAfter=7,keepWithNext=True),
      'h4':ParagraphStyle('h4',parent=body,fontSize=10.5,leading=17,textColor=NAVY,spaceBefore=8,spaceAfter=5,keepWithNext=True),
    }
    cellstyle=ParagraphStyle('cell',parent=body,fontSize=9,leading=13.4,spaceAfter=0)
    cellhead=ParagraphStyle('cellhead',parent=cellstyle,textColor=NAVY)
    story=[]
    for typ,val in blocks(md):
        if typ=='pagebreak':story.append(PageBreak());continue
        if typ=='table':
            n=len(val[0]);w=widths(n,A4[0]-40*mm)
            table=Table([[Paragraph(inlines(c),cellhead if j==0 else cellstyle) for c in row] for j,row in enumerate(val)],colWidths=w,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9eff5')),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#9aaec0')),('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#d6dce2')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story.extend([table,Spacer(1,8)]);continue
        if typ in ('code','quote'):
            val=inlines(val).replace('\n','<br/>')
        else:val=inlines(val)
        sty=styles.get(typ,styles['h4'] if typ.startswith('h') else body)
        story.append(Paragraph(val,sty))
    doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=20*mm,leftMargin=20*mm,topMargin=21*mm,bottomMargin=19*mm,title=title,author='AUAR project',pageCompression=1)
    def page(c,doc):
        c.saveState();c.setFont('RecordSong',8)
        if doc.page>1:
            c.setFillColor(MUTED);c.drawString(20*mm,A4[1]-12*mm,'AUAR·雪妃  |  '+('原始问答节录' if transcript else 'AI 辅助设计与大模型协作记录'))
            c.setStrokeColor(colors.HexColor('#bcc8d4'));c.setLineWidth(.4);c.line(20*mm,A4[1]-14*mm,A4[0]-20*mm,A4[1]-14*mm)
        c.setFillColor(MUTED);c.drawString(20*mm,11*mm,'V1.0  ·  基于历史原件整理')
        c.drawRightString(A4[0]-20*mm,11*mm,str(doc.page));c.restoreState()
    doc.build(story,onFirstPage=page,onLaterPages=page)


def wp(text,style='Normal',pagebreak=False):
    props='<w:pStyle w:val="%s"/>'%style
    if pagebreak:props+='<w:pageBreakBefore/>'
    runs=''.join('<w:r><w:t xml:space="preserve">%s</w:t></w:r>%s'%(escape(x),'<w:r><w:br/></w:r>' if i<len(text.split('\n'))-1 else '') for i,x in enumerate(text.split('\n')))
    return '<w:p><w:pPr>'+props+'</w:pPr>'+runs+'</w:p>'


def make_docx(md,path,title):
    body=[]
    for typ,val in blocks(md):
        if typ=='pagebreak':body.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>');continue
        if typ=='table':
            n=len(val[0]);cols=widths(n,9638)
            tbl='<w:tbl><w:tblPr><w:tblW w:w="9638" w:type="dxa"/><w:tblLayout w:type="fixed"/><w:tblBorders><w:top w:val="single" w:sz="5" w:color="A9B9C8"/><w:bottom w:val="single" w:sz="4" w:color="D6DCE2"/><w:insideH w:val="single" w:sz="4" w:color="D6DCE2"/></w:tblBorders><w:tblCellMar><w:top w:w="80" w:type="dxa"/><w:left w:w="90" w:type="dxa"/><w:bottom w:w="80" w:type="dxa"/><w:right w:w="90" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>'+''.join('<w:gridCol w:w="%d"/>'%x for x in cols)+'</w:tblGrid>'
            for j,row in enumerate(val):
                tbl+='<w:tr><w:trPr><w:cantSplit/>'+('<w:tblHeader/>' if j==0 else '')+'</w:trPr>'
                for i,c in enumerate(row):
                    tbl+='<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/>'%cols[i]+('<w:shd w:fill="E9EFF5"/>' if j==0 else '')+'</w:tcPr>'+wp(clean(c),'TableHeader' if j==0 else 'TableText')+'</w:tc>'
                tbl+='</w:tr>'
            body.append(tbl+'</w:tbl>'+wp(''))
        else:body.append(wp(clean(val),{'h1':'Title','h2':'Heading1','h3':'Heading2','h4':'Heading3','quote':'Quote','code':'Code'}.get(typ,'Normal')))
    ns='xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    sect='<w:sectPr><w:headerReference w:type="default" r:id="rId2"/><w:footerReference w:type="default" r:id="rId3"/><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1191" w:right="1134" w:bottom="1077" w:left="1134" w:header="550" w:footer="550"/></w:sectPr>'
    document='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document '+ns+'><w:body>'+''.join(body)+sect+'</w:body></w:document>'
    defs='<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="SimSun" w:hAnsi="SimSun" w:eastAsia="宋体"/><w:sz w:val="21"/><w:lang w:val="zh-CN" w:eastAsia="zh-CN"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="100" w:line="330" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
    st=[]
    for sid,name,size,color,bold,keep,outline in [('Normal','Normal',21,'202833',False,False,None),('Title','Title',42,'17314F',True,True,0),('Heading1','heading 1',30,'17314F',True,True,0),('Heading2','heading 2',23,'17314F',True,True,1),('Heading3','heading 3',21,'17314F',True,True,2),('TableText','Table Text',18,'202833',False,False,None),('TableHeader','Table Header',18,'17314F',True,False,None),('Quote','Quote',20,'303B48',False,False,None),('Code','Code',18,'303B48',False,False,None)]:
        pp=('<w:keepNext/>' if keep else '')+('<w:outlineLvl w:val="%s"/>'%outline if outline is not None else '')
        if sid in ('TableText','TableHeader'):
            pp+='<w:spacing w:after="0" w:line="280" w:lineRule="auto"/>'
        else:
            pp+='<w:spacing w:before="%d" w:after="%d"/>'%(140 if keep else 0,100 if keep else 80)
        if sid=='Quote':pp+='<w:ind w:left="220" w:right="80"/><w:pBdr><w:left w:val="single" w:sz="5" w:color="B0BFCC" w:space="8"/></w:pBdr>'
        st.append('<w:style w:type="paragraph" w:styleId="%s"><w:name w:val="%s"/>'%(sid,name)+('<w:basedOn w:val="Normal"/>' if sid!='Normal' else '')+'<w:pPr>'+pp+'</w:pPr><w:rPr><w:sz w:val="%d"/><w:color w:val="%s"/>'%(size,color)+('<w:b/>' if bold else '')+'</w:rPr></w:style>')
    styles='<?xml version="1.0" encoding="UTF-8"?><w:styles '+ns+'>'+defs+''.join(st)+'</w:styles>'
    header='<?xml version="1.0" encoding="UTF-8"?><w:hdr '+ns+'>'+wp('AUAR·雪妃 | AI 辅助设计与大模型协作记录','TableText')+'</w:hdr>'
    footer='<?xml version="1.0" encoding="UTF-8"?><w:ftr '+ns+'><w:p><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:t>V1.0 · </w:t></w:r><w:fldSimple w:instr="PAGE"><w:r><w:t>1</w:t></w:r></w:fldSimple></w:p></w:ftr>'
    relns='http://schemas.openxmlformats.org/package/2006/relationships'
    rels='<?xml version="1.0"?><Relationships xmlns="'+relns+'"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/></Relationships>'
    rootrels='<?xml version="1.0"?><Relationships xmlns="'+relns+'"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>'
    content='<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'+''.join('<Override PartName="/word/%s" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.%s+xml"/>'%(f,t) for f,t in [('document.xml','document.main'),('styles.xml','styles'),('header1.xml','header'),('footer1.xml','footer')])+'<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>'
    core='<?xml version="1.0"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>'+escape(title)+'</dc:title><dc:creator>AUAR project</dc:creator></cp:coreProperties>'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for n,s in {'[Content_Types].xml':content,'_rels/.rels':rootrels,'word/document.xml':document,'word/styles.xml':styles,'word/header1.xml':header,'word/footer1.xml':footer,'word/_rels/document.xml.rels':rels,'docProps/core.xml':core}.items():z.writestr(n,s.encode())


CASES=[
 ('C01','平台工件一致性与DFX修复','q01 q02 q03','E02-0 E03','工件生成不等于可部署；加入复位/同图/冷启验证','历史平台验收，不代替整机'),
 ('C02','运动监督与真实源码重建','q12 q22','E04 E05 E06 E07 E33','位宽与上下游一致；余量实验未成功则保留基线','新候选没有新增板验'),
 ('C03','DPU模型适配及量化质量','q04 q05','E08 E09 E10 E11','结构可行、编译、执行、质量分层验证','公开模拟/固定输入不代替现场身份验收'),
 ('C04','共享DPU调度及独立AI审查','q06 q07 q08 q09','E12 E13 E14','第三次故障推翻早期判断；反例拒绝错误补丁','罕见长尾唯一根因仍未确认'),
 ('C05','人脸随动连续性','q10 q11','E15 E16 E25','否决简单降频；感知与PL执行频率分开','当轮主观反馈，不代替机械精度'),
 ('C06','LLM/TTS输出路由及GPU资源','q13 q14 q15','E17 E18 E19 E20 E21 E22','阶段测量、运行加载核对；纠正只能Windows/GPU的绝对判断','Windows完整原问答未回收；旧平台数据'),
 ('C07','板端记忆与来源一致性','q16','E23 E24 E25','有效摘要与源回收、实际召回分开验收','自然回收案例仍RECALL_PENDING'),
 ('C08','显示动画及启动','q19 q20','E25 E26 E27 E28 E32','软件状态不替代实屏；候选无新冷启不报节省秒数','自动冷启及同版长稳未证明'),
 ('C09','通用PYNQ Skill提炼','q17','E29 E30','合同/HWH/驱动/测试生成与跨示例复用','仅离线，真实PYNQ/跨板待验'),
 ('C10','源码复现布局纠错','q18 q21 q22','E05 E06 E31 E33','保留真实运行根；历史PASS不能作新测试输入','包体积/离线构建与全系统独立部署分别证明'),
]


def main():
    # Use UTC for PDF metadata; this host's local-time/ReportLab combination
    # otherwise writes local wall time with a +00 offset.
    os.environ['SOURCE_DATE_EPOCH']=str(int(dt.datetime.now(dt.timezone.utc).timestamp()))
    original=[json.loads(l) for l in (WORK/'selected_conversations.jsonl').open()]
    rs=[]
    for r in original:
        r=dict(r);r['text']=public_text(r['text'])
        if r['selection_id']=='q21':
            r['text']=re.sub(r'34BZNXC|JoneNik\S*','[设备名已脱敏]',r['text'])
        r['export_text_sha256']=sha(r['text'].encode());r['redacted']=r['source_text_sha256']!=r['export_text_sha256']
        rs.append(r)
    (OUT/'conversations_full.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rs))
    stats=json.loads((WORK/'history_stats.json').read_text())
    (OUT/'history_audit.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2))
    cols=['selection_id','topic','role','created_utc','created_bjt','thread_id','turn_id','item_id','rollout_ordinal','source_item_json_sha256','source_text_sha256','export_text_sha256','redacted','model_last_recorded','cli_version_last_recorded']
    with (OUT/'conversation_index.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(rs)
    with (OUT/'case_matrix.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['case_id','engineering_topic','conversation_ids','evidence_ids','correction_and_decision','validation_boundary']);w.writerows(CASES)
    transcript=['# AUAR·雪妃｜大模型协作原文节录','',
      '本附件从本地 Codex 历史数据库导出，包含 22 个片段、67 条消息。顺序按工程主题编排，每条保留原始事件时间。只列可见用户消息及最终回复；同一轮内的多条消息保持原次序，不人为拼接为一问一答。','',
      '长篇转贴审查意见在阅读版仅显示开头连续节录；完整入选消息保存于 conversations_full.jsonl。节录本身不改写原句；局域网地址、明确凭据及部分标识按需脱敏。消息原文与导出指纹、数据库定位见 conversation_index.csv。辅助模型字段仅为线程表最后记录，逐轮精确版本未确认。','',
      '历史回答只代表当时判断；后续证据可能已经更新。Q07—Q09 为明确的纠错序列，Q22 的旧DCP来源由正文较新源码重建证据更新。','']
    for qid in sorted(set(r['selection_id'] for r in rs)):
        items=[r for r in rs if r['selection_id']==qid]
        transcript+=['## '+qid.upper()+'｜'+items[0]['topic'],'',
          '北京时间：'+items[0]['created_bjt'][:19].replace('T',' ')+' 至 '+items[-1]['created_bjt'][:19].replace('T',' ')+'。','',
          '线程：`'+items[0]['thread_id']+'`。轮次：`'+items[0]['turn_id']+'`。','']
        for index,r in enumerate(items,1):
            label='用户原文' if r['role']=='user' else 'AI 最终回复原文'
            transcript+=['### '+str(index)+'. '+label+'｜'+r['created_bjt'][11:19],'', '消息定位：`'+r['item_id']+'`；序号 '+str(r['rollout_ordinal'])+'。','']
            text=r['text'];limit=1500 if r['role']=='user' else 5000
            if len(text)>limit:
                end=text.rfind('\n',0,limit)
                end=end if end>limit//2 else limit
                excerpt=text[:end]
                transcript+=['本条原文共 '+str(len(text))+' 字符，以下为开头 '+str(len(excerpt))+' 字符连续节录；余文见完整 JSONL。','']
            else:excerpt=text
            transcript+=['\n'.join('> '+l for l in excerpt.splitlines()),'']
        transcript+=['']
    transcript_md='\n'.join(transcript)
    (OUT/'conversation_records.md').write_text(transcript_md)
    main_md=(OUT/'ai_collaboration_record.md').read_text()
    make_pdf(main_md,OUT/'ai_collaboration_record.pdf','AUAR·雪妃 AI辅助设计与大模型协作记录')
    make_docx(main_md,OUT/'ai_collaboration_record.docx','AUAR·雪妃 AI辅助设计与大模型协作记录')
    make_pdf(transcript_md,OUT/'conversation_records.pdf','AUAR·雪妃 大模型协作原文节录',True)
    print(json.dumps({'messages':len(rs),'selections':len(set(r['selection_id'] for r in rs)),'cases':len(CASES),'main_md_chars':len(main_md),'transcript_md_chars':len(transcript_md),'documents':[p.name for p in OUT.glob('*.pdf')]},ensure_ascii=False))


if __name__=='__main__':main()
