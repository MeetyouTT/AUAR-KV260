from pathlib import Path
import subprocess,json,sys
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parents[1]
pdfmetrics.registerFont(TTFont('Song',r'C:\Windows\Fonts\simsun.ttc',subfontIndex=0))
c=canvas.Canvas(str(R/'figures/history_model_latency.pdf'),pagesize=(660,440))
c.setTitle('Fixed input latency median comparison')
def text(x,y,s,sz=11):
 c.setFont('Song',sz);c.setFillColor(HexColor('#1d2734'));c.drawCentredString(x,y,s)
text(330,414,'固定输入路径耗时对照',18)
text(330,388,'历史实板数据  硬件与精度同时变化',11)
for x,title,n,vals,top in [(60,'YuNet',40,[124.02,61.41],150),(380,'SFace',8,[520.86,13.56],600)]:
 text(x+110,355,title+'  n='+str(n),15)
 c.setLineWidth(.6);c.setStrokeColor(HexColor('#a5afbb'))
 c.line(x,120,x+245,120);c.line(x,120,x,330)
 for tick in range(0,4):
  value=top*tick/3;y=120+210*value/top
  c.setStrokeColor(HexColor('#e4e7eb'));c.line(x,y,x+245,y)
  c.setFont('Song',9);c.setFillColor(HexColor('#1d2734'));c.drawRightString(x-6,y-3,str(round(value)))
 for j,v in enumerate(vals):
  bx=x+35+110*j;h=210*v/top
  c.setFillColor(HexColor('#285c89' if j==0 else '#7199b8'));c.rect(bx,120,60,h,fill=1,stroke=0)
  text(bx+30,120+h+9,format(v,'.2f'),12)
  text(bx+30,100,'ARM FP32' if j==0 else 'DPU INT8',10)
 text(x+110,77,'中位数  单位 ms',10)
text(330,48,'YuNet含预后处理  SFace为已对齐输入且含输入输出转换',11)
text(330,26,'n=8 不报告尾部分位数  统计数据见 data/history_latency_summary.csv',10)
c.save()
pop=r'C:\Users\REVO1\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe'
subprocess.run([pop,'-png','-singlefile','-scale-to','2200',str(R/'figures/history_model_latency.pdf'),str(R/'figures/history_model_latency')],check=True,capture_output=True)
# The revised PDF is the vector master; the previous SVG contains removed P95 bars.
old=R/'figures/history_model_latency.svg'
if old.exists():old.unlink()
print('Updated Figure 5-1; SFace P95 bars removed; no performance test run.')
