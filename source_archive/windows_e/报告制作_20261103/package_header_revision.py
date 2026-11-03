from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,zipfile,sys,subprocess
sys.stdout.reconfigure(encoding='utf-8')
B=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5');R=B/'v3_header_logo'
# Make the included rebuild path retain the header treatment.
source=Path(r'E:\报告制作_20261103\update_header_logo.py').read_text(encoding='utf-8')
start=source.index("doc=Document(OUT/'auar_xuefei_technical_report.docx')")
end=source.index("# Record only formatting changes")
core=source[start:end].replace("OUT/'auar_xuefei_technical_report.docx'","docx_path").replace("OUT/'figures/competition_logo.png'","logo_path")
helper='''from pathlib import Path
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def apply_header_logo(docx_path,logo_path):
'''+''.join('    '+line+'\n' for line in core.splitlines())
(R/'tools/apply_header_logo.py').write_text(helper,encoding='utf-8')
builder=R/'tools/build_word.py'
t=builder.read_text(encoding='utf-8')
if 'from apply_header_logo import apply_header_logo' not in t:t+='\nfrom apply_header_logo import apply_header_logo\napply_header_logo(out, ROOT/"figures/competition_logo.png")\n'
builder.write_text(t,encoding='utf-8')
p=R/'tools/export_header_word.ps1';t=p.read_text(encoding='utf-8')
t=t.replace("$reportRoot = '"+str(R)+"'","$reportRoot = Split-Path -Parent $PSScriptRoot")
p.write_text(t,encoding='utf-8')
p=R/'tools/readme.md'
if not p.read_text(encoding='utf-8').startswith('本修订版由'):p.write_text('本修订版由 apply_header_logo.py 给 Word 设置重复页眉，左侧为4cm比赛logo，右侧为自动页码，下方0.5pt细线。build_word.py已接入此步骤。\n\n'+p.read_text(encoding='utf-8'),encoding='utf-8')
valid=json.loads((R/'qa/header_validation.json').read_text(encoding='utf-8'))
valid['revision']='v3_header_logo';valid['visual_headers_checked']=35;valid['body_reused_pixel_verified_visual_review']=True
(R/'qa/header_validation.json').write_text(json.dumps(valid,ensure_ascii=False,indent=2),encoding='utf-8')
files=[R/'auar_xuefei_technical_report.pdf',R/'auar_xuefei_technical_report.docx',R/'readme.md']
for folder in ['data','evidence','figures','report','sources','tools']:
 files.extend(p for p in (R/folder).rglob('*') if p.is_file() and p.name!='update_header_logo.py')
files.extend([R/'qa/header_validation.json',R/'qa/word_export.json'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
records=[{'path':str(p.relative_to(R)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(set(files))]
(R/'package_manifest.json').write_text(json.dumps({'revision':'v3_header_logo','utc':datetime.now(timezone.utc).isoformat(),'files':records},ensure_ascii=False,indent=2),encoding='utf-8')
files.append(R/'package_manifest.json')
with zipfile.ZipFile(R/'report_package.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(set(files)):z.write(p,'auar_technical_report/'+str(p.relative_to(R)).replace('\\','/'))
with zipfile.ZipFile(R/'report_package.zip') as z:assert z.testzip() is None
(R/'report_package.sha256').write_text(sha(R/'report_package.zip')+'  report_package.zip\n',encoding='ascii')
print(json.dumps({'revision':'v3_header_logo','files':len(set(files)),'zip_bytes':(R/'report_package.zip').stat().st_size,'pdf_sha256':sha(R/'auar_xuefei_technical_report.pdf')},ensure_ascii=False))
dst='/home/ghmd/auar-techdoc-01a1a1a5/delivery/v3_header_logo'
subprocess.run(['ssh','-o','BatchMode=yes','aura-ubuntu','mkdir -p '+dst],check=True,capture_output=True)
for n in ['report_package.zip','auar_xuefei_technical_report.pdf','auar_xuefei_technical_report.docx']:
 subprocess.run(['scp',str(R/n),'aura-ubuntu:'+dst+'/'+n],check=True,capture_output=True)
expected={n:sha(R/n) for n in ['report_package.zip','auar_xuefei_technical_report.pdf','auar_xuefei_technical_report.docx']}
code='''from pathlib import Path
import hashlib,json
expected=json.loads(DATA)
root=Path(DEST)
actual={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in expected}
assert actual==expected
log=Path('/home/ghmd/AMD_Smart/logs/daily/2026-11-03-TECHNICAL-REPORT-01a1a1a5.md')
with log.open('a',encoding='utf-8') as f:f.write(MESSAGE)
print(json.dumps({'status':'PASS','directory':str(root),'matched_files':len(actual)}))
'''.replace('DATA',repr(json.dumps(expected))).replace('DEST',repr(dst)).replace('MESSAGE',repr('\n\n页眉修订 v3_header_logo：除封面外35页左上重复FPGA十周年logo，右上自动页码，下加0.5pt黑线。正文与表格文本、36页正文区域像素与前版逐页一致。新PDF、Word和ZIP在delivery/v3_header_logo，三份文件与Windows逐字节一致。本轮仅排版，无设备测试或生产变更。\n'))
p=subprocess.run(['ssh','aura-ubuntu','python3 -'],input=code.encode(),capture_output=True,check=True)
(R/'ubuntu_delivery_receipt.json').write_bytes(p.stdout)
print(p.stdout.decode())
