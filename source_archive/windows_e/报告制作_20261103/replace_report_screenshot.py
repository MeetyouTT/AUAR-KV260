from pathlib import Path
from datetime import datetime,timezone
from docx import Document
from docx.oxml.ns import qn
import json,zipfile,shutil,hashlib,sys
sys.stdout.reconfigure(encoding='utf-8')
B=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5')
SRC=B/'v3_header_logo';R=B/'v4_face_mosaic';R.mkdir(exist_ok=True)
W=Path(r'E:\报告制作_20261103\face_redaction')
with zipfile.ZipFile(SRC/'report_package.zip') as arc:
 for z in arc.infolist():
  parts=Path(z.filename).parts[1:]
  if not parts:continue
  out=R.joinpath(*parts)
  assert R.resolve() in out.resolve().parents
  out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(arc.read(z))
edited=(W/'board_x11_mosaic.png').read_bytes()
(R/'figures/board_x11_live.png').write_bytes(edited)
(R/'figures/board_x11_mosaic.png').write_bytes(edited)
oldcap='图 1-1 当前板端视觉页面 2026年11月3日采集 此时聆听和人脸跟随关闭'
newcap='图 1-1 板端视觉页面 人脸已作马赛克处理 2026年11月3日采集'
oldphrase='图中的人物来自实际摄像头，界面像素没有重绘。'
newphrase='图中的人物来自实际摄像头，已对人脸作马赛克处理，其余截图像素保留。'
oldnote='本次截图显示“未识别”，说明页面保留了拒识状态，不能据此计算识别准确率。'
newnote='界面中的轨迹编号和身份标签用于显示业务状态，不能据此计算识别准确率。'
replacements=[(oldcap,newcap),(oldphrase,newphrase),(oldnote,newnote)]
doc=Document(R/'auar_xuefei_technical_report.docx')
matched=[]
for p in doc.paragraphs:
 before=p.text;after=before
 for a,b in replacements:after=after.replace(a,b)
 if after!=before:
  p.clear();p.add_run(after);matched.append((before,after))
assert len(matched)==3,len(matched)
changed_image=0
for s in doc.inline_shapes:
 if s._inline.docPr.get('descr','').startswith('图 1-1 '):
  blip=s._inline.xpath('.//a:blip')[0];rid=blip.get(qn('r:embed'))
  doc.part.related_parts[rid]._blob=edited;s._inline.docPr.set('descr',newcap);changed_image+=1
assert changed_image==1
doc.save(R/'auar_xuefei_technical_report.docx')
md=R/'report/technical_report.md';t=md.read_text(encoding='utf-8')
for a,b in replacements:
 assert a in t,a;t=t.replace(a,b)
md.write_text(t,encoding='utf-8')
idx=R/'sources/figure_index.json';items=json.loads(idx.read_text(encoding='utf-8'))
for f in items:
 if f['caption']==oldcap:f['caption']=newcap
idx.write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
meta=json.loads((W/'capture_metadata_private.json').read_text(encoding='utf-8'))
verify=json.loads((W/'redaction_verification.json').read_text(encoding='utf-8'))
evidence={'capture_host_utc':meta['host_capture_utc'],'board_boot_id':meta['boot_id'],'ui_page':meta['gui']['ui_page'],
 'people_count':meta['camera']['people_count'],'raw_screenshot_sha256':hashlib.sha256((W/'current_raw.png').read_bytes()).hexdigest(),
 'public_redacted_screenshot_sha256':hashlib.sha256(edited).hexdigest(),'privacy':verify,
 'raw_image_in_report_or_package':False,'new_motion_commands':0,'production_changes':False,'scope':'Screenshot replacement only; no new performance or recognition-accuracy test'}
(R/'evidence/screenshot_replacement.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
readme=R/'readme.md';readme.write_text('''# 第5页截图与人脸隐私修订

图1-1已换为用户坐在当前视觉画面中的真实截图。仅人脸矩形区域覆盖粗马赛克，区域外的全部像素与原始截图逐点一致。未打码的人脸原图及脸部裁剪不包含在报告或资料包中。原页眉logo、页码和其余图表保留；同步修改图注与相关身份说明。本轮没有新性能测试、运动命令或生产变更。

'''+readme.read_text(encoding='utf-8'),encoding='utf-8')
export=(SRC/'tools/export_header_word.ps1').read_text(encoding='utf-8')
(R/'tools/export_word.ps1').write_text(export,encoding='utf-8')
print(json.dumps({'output':str(R),'image_replaced':changed_image,'text_paragraphs_adjusted':len(matched),'public_capture_utc':meta['host_capture_utc'],'redaction_outside_pixels_changed':verify['changed_pixels_outside']},ensure_ascii=False))
