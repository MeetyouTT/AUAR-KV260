from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,json,sys,zipfile,subprocess
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
R=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5\v5_contribution_bjt_simsun')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
now=lambda:datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
if '--compare' in sys.argv:
 before=json.loads((R/'qa/reviewed_pages_before_final_time_check.json').read_text(encoding='utf-8'))
 changed=[int(p.stem.split('-')[1]) for p in sorted((R/'qa').glob('page-*.png')) if sha(p)!=before.get(p.name)]
 geometry=[]
 ns={'s':'http://www.w3.org/2000/svg'}
 for p in (R/'figures').glob('*.svg'):
  a=ET.parse(p).getroot();b=ET.parse(R.parent/'v4_face_mosaic/figures'/p.name).getroot()
  pa=[x.get('d') for x in a.findall('.//s:path',ns)];pb=[x.get('d') for x in b.findall('.//s:path',ns)]
  assert pa==pb,p.name
  geometry.append({'figure':p.name,'paths_unchanged':True,'path_count':len(pa)})
 result={'after_last_calendar_edit_changed_pages':changed,'other_page_pixels_identical_to_reviewed_version':38-len(changed),'chart_data_geometry':geometry,'checked_at_beijing':now()}
 (R/'qa/final_render_comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False,indent=2))
elif '--package' in sys.argv:
 validation=json.loads((R/'qa/revision_validation.json').read_text(encoding='utf-8'))
 assert validation['pages']==38 and not validation['pdf_other_font_characters']
 assert not validation['out_of_body_margin_characters']
 validation['visual_review_completed']=True
 validation['visual_review_physical_pages']=list(range(1,39))
 validation['visual_review_method']='All 38 page PNGs inspected; final changed pages re-inspected after calendar wording update; unchanged pages verified byte-identical.'
 validation['review_completed_beijing']=now()
 validation['final_docx_sha256']=sha(R/'auar_xuefei_technical_report.docx')
 validation['final_pdf_sha256']=sha(R/'auar_xuefei_technical_report.pdf')
 (R/'qa/revision_validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf-8')
 files=[R/'auar_xuefei_technical_report.docx',R/'auar_xuefei_technical_report.pdf',R/'readme.md']
 for folder in ['data','evidence','figures','report','sources','tools']:
  files.extend(p for p in (R/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
 files.extend(R/'qa'/n for n in ['revision_validation.json','word_export.json','editorial_changes.json','chart_font_revision.json','final_render_comparison.json'])
 files=sorted(set(files))
 forbidden={'current_raw.png','face_edit_target.png','capture_metadata_private.json','face_rect.json'}
 assert not any(p.name in forbidden for p in files)
 raw=Path(r'E:\报告制作_20261103\face_redaction\current_raw.png')
 rawsha=sha(raw)
 assert all(sha(p)!=rawsha for p in files)
 records=[{'path':str(p.relative_to(R)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]
 manifest={'revision':R.name,'packaged_at_beijing':now(),'display_timezone':'Asia/Shanghai UTC+08:00','pages':38,'unredacted_face_excluded':True,'files':records}
 (R/'package_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
 files.append(R/'package_manifest.json')
 with zipfile.ZipFile(R/'report_package.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in files:z.write(p,'auar_technical_report/'+str(p.relative_to(R)).replace('\\','/'))
 with zipfile.ZipFile(R/'report_package.zip') as z:
  assert z.testzip() is None
  for rec in records:
   assert hashlib.sha256(z.read('auar_technical_report/'+rec['path'])).hexdigest()==rec['sha256']
 (R/'report_package.sha256').write_text(sha(R/'report_package.zip')+'  report_package.zip\n',encoding='ascii')
 print(json.dumps({'files':len(files),'zip_bytes':(R/'report_package.zip').stat().st_size,'pdf_bytes':(R/'auar_xuefei_technical_report.pdf').stat().st_size,'sha256':sha(R/'report_package.zip')},ensure_ascii=False,indent=2))
elif '--sync' in sys.argv:
 dst='/home/ghmd/auar-techdoc-01a1a1a5/delivery/'+R.name
 names=['auar_xuefei_technical_report.pdf','auar_xuefei_technical_report.docx','report_package.zip','report_package.sha256','readme.md']
 expected={n:sha(R/n) for n in names}
 subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','aura-ubuntu','mkdir -p '+dst],check=True,capture_output=True)
 for n in names:
  subprocess.run(['scp','-o','BatchMode=yes',str(R/n),'aura-ubuntu:'+dst+'/'+n],check=True,capture_output=True)
 message='\n\n## 技术报告 V5 北京时间与宋体修订\n\n完成时间 '+now()+'。报告38页，19幅图、13张表。根据用户批注扩写YuNet卷积子图重构、SFace 27处PReLU及全连接头等价改写、INT8校准/编译/向量验证，添加实际源码SHA；扩充设计优势，重点说明27B LLM、PS业务、DPU感知与PL运动监督的协同。没有把公开网络或权重写为从零原创，也没有新增模型/物理实验。\n\n报告时刻改为北京时间：资源观察2026-11-03 21:52:23至21:53:24，马赛克截图22:47:40；历史资源观察日由UTC核对为北京时间2026-10-31。证据原始时间戳保留。正文、标题、目录、表格、代码、图注、页码全部宋体；八张曲线SVG保持数据路径几何不变更换宋体，七张机制图以宋体重建。实际软件截图和赛事logo保持其原字体。PDF全部可检索文字只使用SimSun。\n\n沿用页眉logo、自动页码和细线；图1-1为用户坐入页面的真实截图，人脸粗马赛克，区域外像素保留。未打码的脸部原图及裁剪均不入包。Word原生导出后以Poppler渲染，38页逐页检查，页码序列通过、无非空字符越界；最后改动页重新查看，其余页像素一致。\n\n新PDF、Word和ZIP等5文件位于 '+dst+'，Windows与Ubuntu逐文件SHA一致，ZIP完整性通过。本轮仅报告编辑、绘图排版和交付留存，没有修改生产代码/固件/服务，没有新板端推理、运动、录音或性能测试。\n'
 code='''from pathlib import Path
import json,hashlib,zipfile
root=Path(DEST)
expected=json.loads(EXPECTED)
actual={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in expected}
assert actual==expected
with zipfile.ZipFile(root/'report_package.zip') as z:assert z.testzip() is None
log=Path('/home/ghmd/AMD_Smart/logs/daily/2026-11-03-TECHNICAL-REPORT-01a1a1a5.md')
with log.open('a',encoding='utf-8') as f:f.write(MESSAGE)
receipt={'status':'PASS','directory':str(root),'matched_files':len(actual),'files_sha256':actual,'verified_beijing':VERIFIED}
(root/'ubuntu_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(receipt,ensure_ascii=False))
'''.replace('DEST',repr(dst)).replace('EXPECTED',repr(json.dumps(expected))).replace('MESSAGE',repr(message)).replace('VERIFIED',repr(now()))
 proc=subprocess.run(['ssh','-o','BatchMode=yes','aura-ubuntu','python3 -'],input=code.encode(),capture_output=True,check=True)
 (R/'ubuntu_delivery_receipt.json').write_bytes(proc.stdout)
 print(proc.stdout.decode())
else:raise SystemExit('Use --compare, --package or --sync')
