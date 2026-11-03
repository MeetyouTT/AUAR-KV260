from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,hashlib,sys
sys.stdout.reconfigure(encoding='utf-8')
R=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5')
dst='/home/ghmd/auar-techdoc-01a1a1a5/delivery'
subprocess.run(['ssh','aura-ubuntu','mkdir -p '+dst],check=True,capture_output=True)
files=['report_package.zip','report_package.sha256','auar_xuefei_technical_report.pdf','auar_xuefei_technical_report.docx','readme.md']
hashes={name:hashlib.sha256((R/name).read_bytes()).hexdigest() for name in files}
for name in files:subprocess.run(['scp',str(R/name),'aura-ubuntu:'+dst+'/'+name],check=True,capture_output=True)
payload={'hashes':hashes,'dst':dst}
code='''from pathlib import Path
import json,hashlib,zipfile
data=json.loads(PAYLOAD)
root=Path(data['dst']);actual={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in data['hashes']}
assert actual==data['hashes']
with zipfile.ZipFile(root/'report_package.zip') as z:
 assert z.testzip() is None
 count=len(z.infolist())
receipt={'status':'PASS','location':str(root),'files_sha256':actual,'zip_entries':count,'windows_source_bytes_match':True}
(root/'ubuntu_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
entry=Path('/home/ghmd/AMD_Smart/logs/daily/2026-11-03-TECHNICAL-REPORT-01a1a1a5.md')
entry.write_text('''+repr('''# AUAR 雪妃技术报告完成记录

日期 2026年11月3日 America/Los_Angeles

按用户指定 writing_sample.md 完成九章正文与六个附录。交付 PDF/Word 共36页，含19幅图及13张表，使用用户提供10周年PSD合成图。报告源和资料在 Windows E:/Win共享文件/协作任务/2026-11-03_technical_report_01a1a1a5。Ubuntu核验副本位于 /home/ghmd/auar-techdoc-01a1a1a5/delivery，逐字节SHA与Windows一致，ZIP校验通过。

本次实际工作：SSH读取当前KV260页面和过滤健康状态；59.988313秒自然负载、61样本/60个CPU区间；板端到Windows30次ICMP均收到回复。CPU加权79.43%，主检测9.885Hz、YuNet9.852Hz、SFace8次完成，主超周期无新增。聆听和人脸跟随均关闭，未发新模型或运动指令，没有修改生产源码、固件、服务或设置。

Ubuntu独立目录 /home/ghmd/auar-techdoc-01a1a1a5/verification 重跑四套RTL，12阶段全通过，源未变。相应日志已逐一核对SHA。Matplotlib3.4.3在已有VitisAI CPU容器中从实采CSV生成三组新图，没有模型推理。其他模型质量、资源、语音及Skill数据保留历史范围。

Word原生导出PDF，打包Poppler渲染36页逐页检查。封面标题边线、目录、表格编号和长SHA排版已修正。完整工程未重新综合实现或部署，本报告包不替代方案A工程。

现场整机照片、最终供电与机械图、PWM电气波形、机械/声学端到端数据、同版全功能长稳及更完整AI原问答仍需补齐。较新用户已接受的跟随与记忆使用反馈按其范围保留，没有把旧故障当作当前状态或把短测提升为最终整机验收。
''')+''',encoding='utf-8')
print(json.dumps(receipt,ensure_ascii=False))
'''
code=code.replace('PAYLOAD',repr(json.dumps(payload)))
p=subprocess.run(['ssh','aura-ubuntu','python3 -'],input=code.encode(),capture_output=True,check=True)
d=json.loads(p.stdout);d['host_verified_utc']=datetime.now(timezone.utc).isoformat()
(R/'ubuntu_delivery_receipt.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(d,ensure_ascii=False,indent=2))
