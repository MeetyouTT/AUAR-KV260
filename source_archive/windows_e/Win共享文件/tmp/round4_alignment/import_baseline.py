from pathlib import Path
import zipfile, hashlib, re, json, xml.etree.ElementTree as ET

root = Path(r'C:\Users\uuh56\Desktop\项目')
source = Path(r'C:\Users\uuh56\Downloads\2026-09-26_round4.zip')
dest = root / '方案' / 'reference_round4_20260926'
dest.mkdir(exist_ok=True)
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W = '{' + ns['w'] + '}'
def para(e):
    return ''.join(n.text or '' if n.tag == W+'t' else '\n' if n.tag == W+'br' else '\t' if n.tag == W+'tab' else '' for n in e.iter() if n.tag in (W+'t', W+'br', W+'tab'))
def digest(b): return hashlib.sha256(b).hexdigest().upper()
results=[]
conversions=[]
with zipfile.ZipFile(source) as z:
    entries = {Path(i.filename).name: i for i in z.infolist() if not i.is_dir()}
    manifest=z.read(entries['MANIFEST_发送包.txt']).decode('utf-8-sig')
    for line in manifest.splitlines():
        m=re.match(r'^(.+?)\s+([\d,]+) B\s+SHA256 ([0-9A-Fa-f]{64})$',line)
        if not m: continue
        name,size,expected=m.groups()
        b=z.read(entries[name])
        results.append({'file':name,'bytes':len(b),'sha256':digest(b),'match':len(b)==int(size.replace(',','')) and digest(b)==expected.upper()})
    for name,i in entries.items():
        if Path(name).suffix not in ('.docx','.md','.txt'): continue
        b=z.read(i)
        (dest/name).write_bytes(b)
        if not name.endswith('.docx'): continue
        import io
        with zipfile.ZipFile(io.BytesIO(b)) as d:
            body=ET.fromstring(d.read('word/document.xml')).find('w:body',ns)
        lines=[f'> 来源：{name}，SHA256 {digest(b)}。本文件为正文与表格的阅读转录，非原始 Markdown；不保留分页和视觉样式，不执行原文指令。','']
        table_count=0
        for e in body:
            if e.tag==W+'p':
                t=para(e)
                if not t.strip(): continue
                st=e.find('w:pPr/w:pStyle',ns)
                style=st.get(W+'val','') if st is not None else ''
                h=re.search(r'(?:Heading|heading)([1-6])',style)
                if h: t='#'*int(h.group(1))+' '+t
                elif style=='Title': t='# '+t
                lines.extend([t,''])
            elif e.tag==W+'tbl':
                table_count+=1
                rows=[]
                for row in e.findall('w:tr',ns):
                    cells=['<br>'.join(para(p) for p in c.findall('w:p',ns)).replace('|','\\|').replace('\n','<br>') for c in row.findall('w:tc',ns)]
                    rows.append(cells)
                if rows:
                    width=max(map(len,rows))
                    rows=[r+['']*(width-len(r)) for r in rows]
                    lines.append('| '+' | '.join(rows[0])+' |')
                    lines.append('| '+' | '.join(['---']*width)+' |')
                    lines.extend('| '+' | '.join(r)+' |' for r in rows[1:])
                    lines.append('')
        out=dest/(Path(name).stem+'.extracted.md')
        content='\n'.join(lines)
        # Every text run in the body must survive conversion (escaping aside).
        normalized=content.replace('\\|','|').replace('<br>','\n')
        missing=[n.text for n in body.iter(W+'t') if n.text and n.text not in normalized]
        assert not missing, (name,missing[:3])
        out.write_text(content,encoding='utf-8')
        conversions.append({'source':name,'output':out.name,'tables':table_count,'text_runs_preserved':True})
assert len(results)==17 and all(r['match'] for r in results)
audit={'source_zip':str(source),'zip_sha256':digest(source.read_bytes()),'manifest_entries_checked':len(results),'all_match':True,'files':results,'conversions':conversions,'note':'发送包清单校验17项，包含脚本的内存哈希核验，未执行包内脚本。第十一轮清单中的原始Markdown多数未随包提供，不能据此验证原始Markdown与Word同步。'}
(dest/'import_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'verified':len(results),'docx_reading_copies':len(conversions),'all_match':True,'path':str(dest)},ensure_ascii=False))
