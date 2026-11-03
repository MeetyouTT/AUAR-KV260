"""Report-native vectors and a standard ReportLab bar chart from frozen metrics."""
from pathlib import Path
import ast
import importlib.util
import json
import re
import subprocess

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF, renderSVG

OUT=Path(__file__).resolve().parents[1]
POPPLER=Path('C:/Users/REVO1/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')


def register():
    for name,file in [('YaHei','msyh.ttc'),('YaHeiBold','msyhbd.ttc'),('ReportMono','consola.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name,'C:/Windows/Fonts/'+file,subfontIndex=0))
    pdfmetrics.registerFontFamily('YaHei',normal='YaHei',bold='YaHeiBold',italic='YaHei',boldItalic='YaHeiBold')


def figure_type():
    helper=OUT/'tools/figure_core.py'
    if not helper.exists():
        source=Path('E:/Win共享文件/output/hardware/wiring_review_20261102/tools/build_wiring.py').read_text(encoding='utf8')
        node=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='Figure')
        prefix='''import math,html
from pathlib import Path
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
INK='#142638'
MUTED='#536576'
LINE='#AAB8C4'
'''
        helper.write_text(prefix+ast.get_source_segment(source,node)+'\n',encoding='utf8')
    spec=importlib.util.spec_from_file_location('amd_figure_core',helper)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.Figure


def publish(f,name):
    dest=OUT/'figures';dest.mkdir(exist_ok=True)
    qa=OUT/'_qa/figures';qa.mkdir(parents=True,exist_ok=True)
    svg=dest/(name+'.svg');f.to_svg(svg)
    text=svg.read_text(encoding='utf8')
    text=re.sub(r'<title>.*?</title>','<title>AUAR AMD 设计报告配图</title>',text)
    text=re.sub(r'<desc>.*?</desc>','<desc>系统结构、接口和离线验证工作流</desc>',text)
    svg.write_text(text,encoding='utf8')
    p=qa/(name+'.pdf');c=canvas.Canvas(str(p),pagesize=(f.w,f.h))
    f.to_pdf(c,(f.w,f.h));c.showPage();c.save()
    r=subprocess.run([str(POPPLER),'-scale-to','2200','-singlefile','-png',str(p),str(dest/name)],capture_output=True,text=True)
    assert r.returncode==0,r.stderr


def generate():
    register();Figure=figure_type()
    navy='#243E56';blue='#1762A5';muted='#536576';gray='#ABB9C5'
    f=Figure(1200,800)
    f.text(40,55,'AUAR 系统功能框图',36,bold=True)
    for x,y,w,h in [(390,100,420,130),(390,360,420,270),(40,355,270,125),(40,550,270,135),(890,370,270,125),(890,575,270,150)]:
        f.rect(x,y,w,h,fill='#F7F9FB')
    f.text(600,150,'Windows 模型主机',31,bold=True,align='center')
    f.text(600,199,'27B LLM / OmniVoice',27,align='center')
    f.text(600,417,'KV260',36,bold=True,align='center')
    f.text(600,480,'PS：采集 / 预后处理 / 业务',25,align='center')
    f.text(600,529,'音频 / ASR / 记忆 / 显示',25,align='center')
    f.text(600,580,'PL：单 DPU + 运动监督',25,align='center')
    f.text(175,405,'相机',33,bold=True,align='center')
    f.text(175,449,'唯一图像采集源',25,align='center')
    f.text(175,603,'MCP01',33,bold=True,align='center')
    f.text(175,648,'USB 录音与播放',25,align='center')
    f.text(1025,421,'显示链与屏幕',29,bold=True,align='center')
    f.text(1025,465,'字幕与角色界面',25,align='center')
    f.text(1025,626,'单轴执行机构',29,bold=True,align='center')
    f.text(1025,670,'隔离 / 供电 / 舵机',23,align='center')
    f.path([(600,230),(600,360)],blue,4,True,True)
    f.text(630,308,'LAN',25,blue)
    f.path([(310,420),(390,420)],blue,4,True)
    f.path([(310,613),(390,613)],blue,4,True,True)
    f.path([(810,432),(890,432)],blue,4,True)
    f.path([(810,590),(850,590),(850,650),(890,650)],blue,4,True)
    f.text(40,768,'运行链与开发链分开：Ubuntu承担构建、量化和编译；各节点版本及接口需要配套。',24,muted)
    publish(f,'system_overview')

    f=Figure(1200,600)
    f.text(40,55,'运动命令与执行许可',36,bold=True)
    f.text(40,118,'命令字段：session / epoch / seq / target / lease',27,muted)
    xs=[40,340,640,940]
    titles=['PS 检查','提交与许可','帧边界推进','PWM 输出']
    lines=[['目标与源帧时效','形成有限请求'],['上下文 / 序号','脉宽 / 租约'],['目标限速推进','独立帧时序'],['输出到接口电路','机械反馈另验']]
    for x,title,body in zip(xs,titles,lines):
        f.rect(x,220,220,220,fill='#F7F9FB')
        f.text(x+110,274,title,29,bold=True,align='center')
        f.text(x+110,335,body[0],24,align='center')
        f.text(x+110,380,body[1],24,align='center')
    for x in xs[:-1]: f.path([(x+220,330),(x+300,330)],blue,4,True)
    f.text(40,505,'STOP或租约失效关闭许可；源帧绝对时效由PS检查，PL租约从命令接受时起计时。',25,muted)
    f.text(40,555,'数据总线写成功、命令被接受、实际机械到位，分别使用相应证据确认。',25,muted)
    publish(f,'motion_protocol')

    f=Figure(1200,580)
    f.text(40,55,'接口合同到验证结果',36,bold=True)
    titles=['输入资料','静态核对','生成代码','参考比对']
    lines=[['合同 / HWH / 向量','独立模拟与参考'],['地址 / 偏移 / 权限','缺项和冲突显式报错'],['driver / test','运行说明与报告'],['单元和示例执行','保存结果与边界']]
    for x,title,body in zip(xs,titles,lines):
        f.rect(x,190,220,230,fill='#F7F9FB')
        f.text(x+110,246,title,30,bold=True,align='center')
        f.text(x+110,305,body[0],22,align='center')
        f.text(x+110,353,body[1],22,align='center')
    for x in xs[:-1]: f.path([(x+220,300),(x+300,300)],blue,4,True)
    f.text(40,485,'同一生成器用于加法和CRC两类布局；黄金参考与模拟实现独立。',26,muted)
    f.text(40,536,'本次验证层级为离线生成与模拟。真实PYNQ、跨板和整机复现分别记录。',25,muted)
    publish(f,'skill_workflow')

    metrics=json.loads((OUT/'data/metrics.json').read_text(encoding='utf8'))
    d=Drawing(1100,485)
    d.add(Rect(0,0,1100,485,fillColor=colors.white,strokeColor=None))
    d.add(String(40,447,'固定输入路径中位耗时',fontName='YaHeiBold',fontSize=29,fillColor=colors.black))
    for x,row,maxval,step in zip([90,655],metrics['model_paths'],[150,600],[50,200]):
        c=VerticalBarChart()
        c.x=x;c.y=105;c.width=330;c.height=260
        c.data=[(row['cpu_median_ms'],row['dpu_median_ms'])]
        c.categoryAxis.categoryNames=['ARM FP32','DPU INT8']
        c.categoryAxis.labels.fontName='YaHei';c.categoryAxis.labels.fontSize=17
        c.valueAxis.labels.fontName='YaHei';c.valueAxis.labels.fontSize=17
        c.valueAxis.valueMin=0;c.valueAxis.valueMax=maxval;c.valueAxis.valueStep=step
        c.valueAxis.visibleGrid=True;c.valueAxis.gridStrokeColor=colors.HexColor('#E1E6EB')
        c.bars[(0,0)].fillColor=colors.HexColor('#7D8995')
        c.bars[(0,1)].fillColor=colors.HexColor(blue)
        c.bars.strokeColor=None;c.barLabelFormat='%.2f'
        c.barLabels.fontName='YaHei';c.barLabels.fontSize=19;c.barLabels.nudge=10
        c.barWidth=50;c.groupSpacing=15
        d.add(c)
        d.add(String(x+165,396,f'{row["model"]}  N={row["samples"]}  {row["median_ratio"]:.2f}x',textAnchor='middle',fontName='YaHeiBold',fontSize=23))
        d.add(String(x-40,374,'ms',fontName='YaHei',fontSize=17))
    d.add(String(40,38,'两个子图纵轴独立；对照同时改变硬件和数值精度，不代表整机问答加速比。',fontName='YaHei',fontSize=21,fillColor=colors.HexColor(muted)))
    qa=OUT/'_qa/figures/model_latency.pdf'
    renderPDF.drawToFile(d,str(qa))
    svg=OUT/'figures/model_latency.svg';renderSVG.drawToFile(d,str(svg))
    text=svg.read_text(encoding='utf8').replace('font-family: YaHeiBold','font-family: Microsoft YaHei').replace('font-family: YaHei','font-family: Microsoft YaHei')
    svg.write_text(text,encoding='utf8')
    r=subprocess.run([str(POPPLER),'-scale-to','2200','-singlefile','-png',str(qa),str(OUT/'figures/model_latency')],capture_output=True,text=True)
    assert r.returncode==0,r.stderr


if __name__=='__main__':
    generate()
