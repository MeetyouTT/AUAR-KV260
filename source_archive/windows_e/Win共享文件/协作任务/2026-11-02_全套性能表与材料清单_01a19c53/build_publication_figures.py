"""Plot recorded measurements with explicit hardware and scope labels."""
from pathlib import Path
import json
import shutil
from statistics import mean
from reportlab.graphics.shapes import Drawing, String, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderSVG
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parent
FIG=ROOT/'报告配图';FIG.mkdir(exist_ok=True)
DATA=json.loads((ROOT/'report_data.json').read_text(encoding='utf-8'))
VALUES={m['key']:m['value'] for m in DATA['metrics']}
FONT='Microsoft YaHei'
pdfmetrics.registerFont(TTFont(FONT,'C:/Windows/Fonts/msyh.ttc',subfontIndex=0))
BLUE=colors.HexColor('#235789');LIGHT=colors.HexColor('#9DBBD5');INK=colors.HexColor('#17212F');GRID=colors.HexColor('#DFE5EA')


def text(d,x,y,s,size=20,anchor='start'):
    d.add(String(x,y,s,fontName=FONT,fontSize=size,textAnchor=anchor,fillColor=INK))


def canvas(title,subtitle):
    d=Drawing(1000,700);d.add(Rect(0,0,1000,700,fillColor=colors.white,strokeColor=None))
    text(d,500,651,title,29,'middle');text(d,500,607,subtitle,19,'middle');return d


def axes(axis):
    axis.labels.fontName=FONT;axis.labels.fontSize=18;axis.strokeColor=colors.HexColor('#707985')


def bars(d,rows,categories,maximum,step,y=205,height=305,label_format='%.2f'):
    c=VerticalBarChart();c.x=95;c.y=y;c.width=810;c.height=height;c.data=rows
    c.categoryAxis.categoryNames=categories;axes(c.categoryAxis);axes(c.valueAxis)
    c.valueAxis.valueMin=0;c.valueAxis.valueMax=maximum;c.valueAxis.valueStep=step
    c.valueAxis.visibleGrid=True;c.valueAxis.gridStrokeColor=GRID
    c.barLabelFormat=label_format;c.barLabels.fontName=FONT;c.barLabels.fontSize=17;c.barLabels.nudge=9
    for i in range(len(rows)):c.bars[i].fillColor=[BLUE,LIGHT][i];c.bars[i].strokeColor=None
    d.add(c)


def legend(d,left,color,label):
    d.add(Rect(left,553,24,18,fillColor=color,strokeColor=None));text(d,left+37,553,label,19)


def save(d,name):renderSVG.drawToFile(d,str(FIG/(name+'.svg')))


def main():
    d=canvas('两轮真人对话的软件分段耗时','历史实测 n=2，KV260与Windows现有模型链路')
    stages=['asr_ms','context_ms','llm_rpc_ms','tts_rpc_ms','capture_complete_to_observed_speaking_ms']
    rows=[[VALUES['turn'+str(i)+'_'+s] for s in stages] for i in [1,2]]
    bars(d,rows,['ASR','上下文','LLM RPC','TTS RPC','软件起播'],6000,1000,label_format='%.0f')
    legend(d,330,BLUE,'第一轮');legend(d,550,LIGHT,'第二轮');text(d,95,530,'耗时（ms）',19)
    text(d,500,130,'软件起播：录音采集完成至观察到SPEAKING状态，包含其它处理与等待。',18,'middle')
    text(d,500,91,'RPC包含传输与服务等待；各条形不作相加，未测扬声器声学首声。',18,'middle')
    text(d,500,52,'两轮均有完整播放回执；当前发布版仍需联合复验。',18,'middle')
    save(d,'语音交互_两轮分段耗时')

    d=canvas('OmniVoice16暖态公开短句合成','Windows RTX 5090 Laptop GPU，2个未缓存样本，未板端播放')
    times=[VALUES['tts'+str(i)+'_seconds'] for i in [1,2]]
    durations=[VALUES['tts'+str(i)+'_samples']/VALUES['tts'+str(i)+'_rate'] for i in [1,2]]
    rtfs=[a/b for a,b in zip(times,durations)]
    bars(d,[times,durations],['公开短句1','公开短句2'],3.5,.5)
    legend(d,270,BLUE,'合成耗时');legend(d,535,LIGHT,'音频时长');text(d,95,530,'时长（s）',19)
    text(d,500,129,f'RTF分别为{rtfs[0]:.3f}、{rtfs[1]:.3f}；RTF = 合成耗时 ÷ 音频时长。',19,'middle')
    text(d,500,88,'初始化与预热另计。样本较少，不作为长句或完整交互延迟保证。',18,'middle')
    text(d,500,49,'本轮依据历史原始记录整理，未新增GPU推理负载。',18,'middle')
    save(d,'TTS_合成耗时与音频时长')

    d=canvas('正常业务30秒CPU与DPU任务忙时','2026-10-31历史板端观察，原业务播报恢复聆听，跟随关闭')
    series=DATA['sections']['resource_series']
    c=LinePlot();c.x=100;c.y=205;c.width=800;c.height=305
    c.data=[[(r['seconds'],r['cpu_percent']) for r in series],[(r['seconds'],r['dpu_busy_percent']) for r in series]]
    c.xValueAxis.valueMin=0;c.xValueAxis.valueMax=30;c.xValueAxis.valueStep=5
    c.yValueAxis.valueMin=0;c.yValueAxis.valueMax=100;c.yValueAxis.valueStep=20
    for axis in [c.xValueAxis,c.yValueAxis]:axes(axis);axis.visibleGrid=True;axis.gridStrokeColor=GRID
    c.lines[0].strokeColor=BLUE;c.lines[1].strokeColor=LIGHT
    c.lines[0].strokeWidth=2;c.lines[1].strokeWidth=2
    d.add(c);legend(d,220,BLUE,'整板CPU忙时');legend(d,520,LIGHT,'DPU CU任务忙时')
    text(d,100,530,'忙时（%）',19);text(d,500,155,'观察时间（s）',18,'middle')
    text(d,500,113,f'整板CPU平均{VALUES["cpu_mean"]:.2f}%；DPU任务忙时平均{VALUES["dpu_busy_mean"]:.2f}%。',19,'middle')
    text(d,500,75,'CPU四核合计100%；DPU为驱动任务忙时，二者均不表示FPGA静态资源占比。',17,'middle')
    text(d,500,38,'短窗观察不代表长期稳定性，不能替代当前最终版本的同条件后测。',17,'middle')
    save(d,'系统资源_历史30秒CPU与DPU忙时')

    d=canvas('SFace量化前后误接收与误拒绝','独立1000对公开测试；500正对、500负对；INT8为主机量化模拟')
    rows=[[VALUES['sface_'+p+'_false_accepts'],VALUES['sface_'+p+'_false_rejects']] for p in ['FP32','INT8']]
    bars(d,rows,['误接收 / 500负对','误拒绝 / 500正对'],14,2,label_format='%.0f')
    legend(d,330,BLUE,'FP32');legend(d,530,LIGHT,'INT8模拟');text(d,95,530,'错误数（对）',19)
    text(d,500,129,'两者总体准确率均为98.8%，错误类型发生变化。',20,'middle')
    text(d,500,88,'各自在独立训练集选阈值，再在测试集评估；不是1000对实板身份验收。',18,'middle')
    text(d,500,49,'本轮对已有评测记录制图，当前现场身份阈值与公开评测阈值分别记录。',17,'middle')
    save(d,'视觉质量_SFace误接收与误拒绝')

    previous=Path('E:/Win共享文件/协作任务/2026-11-02_作品概述_AMD实跑_01a19c53/report_figures')
    for name in ['03_vivado_block_design','04_vivado_resource_utilization','04_05_historical_model_latency','05_xsim_pwm_from_actual_vcd','06_design_workflow']:
        for suffix in ['.png','.svg']:shutil.copy2(previous/(name+suffix),FIG/(name+suffix))
    shutil.copy2(previous/'05_xsim_native_wave_panel.png',FIG/'05_xsim_native_wave_panel.png')
    architectural=Path('E:/Win共享文件/协作任务/2026-11-02_dual_reports/figures')
    for name in ['system_overview','vision_pipeline','dialogue_memory','motion_protocol','hardware_connections']:
        shutil.copy2(architectural/(name+'.png'),FIG/('设计示意_'+name+'.png'))
    print(json.dumps({'new_publication_svg_figures':4,'existing_figures_reused':11},ensure_ascii=False))


if __name__=='__main__':main()
