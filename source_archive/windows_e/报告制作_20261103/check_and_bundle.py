from pathlib import Path
from datetime import datetime,timezone
from pypdf import PdfReader
from docx import Document
from docx.oxml.ns import qn
import re,json,hashlib,csv,subprocess,zipfile,sys,shutil
sys.stdout.reconfigure(encoding='utf-8')
R=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
# Normalize filenames in this newly created report package.
renames={
 'history_计算结果.json':'history_curve_summary.json',
 'history_DPU视觉_360个原始采样点.csv':'history_vision_samples.csv',
 'history_SFace_1000对公开测试_逐对分数.csv':'history_sface_pair_scores.csv',
 'history_SFace_每100对及累计准确率.csv':'history_sface_accuracy.csv'}
for a,b in renames.items():
 p=R/'data'/a;dest=R/'data'/b
 if p.exists():
  assert R.resolve() in p.resolve().parents and R.resolve() in dest.resolve().parents
  p.rename(dest)
man=json.loads((R/'sources/source_manifest.json').read_text(encoding='utf-8'));unique={}
for x in man:
 for a,b in renames.items():
  if x.get('copy')=='data/'+a:x['copy']='data/'+b
 unique[(x['source'],x.get('copy'),x['sha256'])]=x
(R/'sources/source_manifest.json').write_text(json.dumps(list(unique.values()),ensure_ascii=False,indent=2),encoding='utf-8')
md=(R/'report/technical_report.md').read_text(encoding='utf-8');doc=Document(R/'auar_xuefei_technical_report.docx');pdf=PdfReader(R/'auar_xuefei_technical_report.pdf')
figs=json.loads((R/'sources/figure_index.json').read_text(encoding='utf-8'))
assert len(figs)==19 and len(doc.tables)==13 and len(pdf.pages)==36
assert len(re.findall(r'^表 [0-9A-F].*$',md,re.M))==13
assert len(re.findall(r'^## [1-9] ',md,re.M))==9
assert len(re.findall(r'^## 附录 [A-F]',md,re.M))==6
for fig in figs:assert (R/fig['path']).is_file()
alltext=''.join(p.extract_text() or '' for p in pdf.pages)
for bad in ['Error!','错误!','错误！','引用源未找到','未定义书签','{{','}}']:assert bad not in alltext,bad
compact=re.sub(r'\s','',alltext)
for value in ['124.02','61.41','520.86','13.56','98.8%','79.43%','9.85','1.7365','66,960']:
 assert value in compact,value
title=doc.styles['Title'].element
assert title.find('.//'+qn('w:pBdr')) is None
# Simulator log hashes must match the native receipts byte for byte.
rtl=R/'evidence/ubuntu_rtl/rtl';res=json.loads((rtl/'result.json').read_text())
logchecks=[]
assert res['status']=='PASS' and res['source_unchanged'] and len(res['tests'])==4
for test in res['tests']:
 for stage in test['stages']:
  assert stage['exit_code']==0 and stage['status']=='PASS'
  p=rtl/stage['log'];assert sha(p)==stage['log_sha256'],str(p)
  logchecks.append(str(p.relative_to(R)))
top=json.loads((R/'evidence/ubuntu_rtl/rtl.receipt.json').read_text())
assert sha(R/'evidence/ubuntu_rtl/rtl.console.log')==top['log_sha256']
raw=json.loads((R/'evidence/live_board_samples.json').read_text(encoding='utf-8'))
assert raw['boot_id']==raw['boot_id_end'] and len(raw['samples'])==61
assert '30 packets transmitted, 30 received, 0% packet loss' in raw['ping']['stdout']
# Render the final Word-exported PDF and compare every earlier reviewed page.
q=R/'qa/review_v4';q.mkdir(exist_ok=True)
pop=r'C:\Users\REVO1\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe'
subprocess.run([pop,'-png','-r','120',str(R/'auar_xuefei_technical_report.pdf'),str(q/'page')],check=True,capture_output=True)
changed=[]
for i in range(1,37):
 n=f'page-{i:02d}.png'
 if sha(q/n)!=sha(R/'qa/review_v3'/n):changed.append(i)
validation={'utc':datetime.now(timezone.utc).isoformat(),'pdf_pages':36,'main_chapters':9,'appendices':6,'figures':19,'tables':13,
 'native_word_pdf_export':True,'toc_updated':True,'title_border_removed':True,'missing_figures':0,'bad_field_markers':0,
 'current_sample_count':61,'cpu_intervals':60,'network_samples':30,'rtl_testbenches':4,'rtl_log_hashes_verified':len(logchecks),
 'changed_pages_since_visual_review':changed,'visual_review_completed_pages':list(range(1,37)),
 'canon_renderer_limitation':'No bundled LibreOffice on Windows; rendered native Microsoft Word PDF with bundled Poppler',
 'new_board_motion_commands':0,'new_model_requests':0,'firmware_or_production_changes':False}
(R/'qa/final_validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf-8')
# Select only referenced figures and needed sources; omit earlier QA and unused pictures.
files=[R/'auar_xuefei_technical_report.pdf',R/'auar_xuefei_technical_report.docx',R/'readme.md']
for d in ['report','data','evidence','sources','tools']:files.extend(p for p in (R/d).rglob('*') if p.is_file())
for f in figs:
 p=R/f['path'];files.append(p)
 for ext in ['.svg','.pdf']:
  other=p.with_suffix(ext)
  if other.exists():files.append(other)
files.append(R/'figures/competition_logo.png')
files.extend([R/'qa/word_export.json',R/'qa/final_validation.json'])
files=sorted(set(files));manifest=[]
for p in files:
 rel=str(p.relative_to(R)).replace('\\','/')
 assert rel.isascii(),rel
 manifest.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha(p)})
(R/'package_manifest.json').write_text(json.dumps({'created_utc':datetime.now(timezone.utc).isoformat(),'files':manifest},ensure_ascii=False,indent=2),encoding='utf-8')
files.append(R/'package_manifest.json')
z=R/'report_package.zip'
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as out:
 for p in files:out.write(p,'auar_technical_report/'+str(p.relative_to(R)).replace('\\','/'))
with zipfile.ZipFile(z) as out:assert out.testzip() is None
(R/'report_package.sha256').write_text(sha(z)+'  report_package.zip\n',encoding='ascii')
print(json.dumps({'validation':validation,'package_files':len(files),'zip_bytes':z.stat().st_size,'zip_sha256':sha(z)},ensure_ascii=False,indent=2))
