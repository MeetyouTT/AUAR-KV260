"""Create report figures from original Vivado, XSim, and archived benchmark data."""
from pathlib import Path
import hashlib
import json
import re
import shutil

from reportlab.graphics.shapes import Drawing, String, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderSVG
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parent
FIG = ROOT / 'report_figures'
FIG.mkdir(exist_ok=True)
PROJECT = Path('E:/Win共享文件')
EVIDENCE = PROJECT / '协作任务/2026-11-02_dual_reports/evidence'
FONT = 'Microsoft YaHei'
pdfmetrics.registerFont(TTFont(FONT, 'C:/Windows/Fonts/msyh.ttc', subfontIndex=0))
BLUE = colors.HexColor('#235789')
LIGHT = colors.HexColor('#9dbbd5')
INK = colors.HexColor('#17212f')
GRID = colors.HexColor('#dce2e8')


def label(drawing, x, y, text, size=20, anchor='start', color=INK):
    drawing.add(String(x, y, text, fontName=FONT, fontSize=size,
                       textAnchor=anchor, fillColor=color))


def canvas(title, height=720):
    d = Drawing(1000, height)
    d.add(Rect(0, 0, 1000, height, fillColor=colors.white, strokeColor=None))
    label(d, 500, height-49, title, 30, 'middle')
    return d


def style_axis(axis, step=None):
    axis.labels.fontName = FONT
    axis.labels.fontSize = 18
    axis.strokeColor = colors.HexColor('#707985')
    axis.strokeWidth = .8
    if step is not None:
        axis.valueStep = step


def save(d, name):
    renderSVG.drawToFile(d, str(FIG / (name+'.svg')))


def parse_vcd(path):
    lines = path.read_text(encoding='utf-8').splitlines()
    scale_match = re.search(r'\$timescale\s+(\d+)\s*(s|ms|us|ns|ps|fs)\s+\$end', '\n'.join(lines))
    factors = {'s': 1e3, 'ms': 1, 'us': 1e-3, 'ns': 1e-6, 'ps': 1e-9, 'fs': 1e-12}
    tick_ms = int(scale_match.group(1)) * factors[scale_match.group(2)]
    scope, names, data = [], {}, {}
    tick, declared = 0, False
    for line in lines:
        p = line.split()
        if not p:
            continue
        if p[0] == '$scope':
            scope.append(p[2])
        elif p[0] == '$upscope':
            scope.pop()
        elif p[0] == '$var':
            name = '/'.join(scope+[p[4]])
            names[p[3]] = name
            data[name] = []
        elif p[0] == '$enddefinitions':
            declared = True
        elif declared and line.startswith('#'):
            tick = int(line[1:])
        elif declared and not line.startswith('$'):
            if line[0] in 'bB':
                bits, code = line[1:].split()
            elif line[0] in '01xzXZ':
                bits, code = line[0], line[1:]
            else:
                continue
            if code in names and not any(c in bits.lower() for c in 'xz'):
                data[names[code]].append((tick*tick_ms, int(bits, 2)))
    return data, tick*tick_ms


def step_points(events, end, start=0):
    value = 0
    for t, v in events:
        if t <= start:
            value = v
    points = [(start, value)]
    for t, v in events:
        if t > start:
            points.extend([(t, value), (t, v)])
            value = v
    points.append((end, value))
    return points


def line_chart(d, data, x, y, width, height, ymin, ymax, ystep):
    c = LinePlot()
    c.x, c.y, c.width, c.height = x, y, width, height
    c.data = [data]
    c.lines[0].strokeColor = BLUE
    c.lines[0].strokeWidth = 2
    c.xValueAxis.valueMin, c.xValueAxis.valueMax = 0, 65
    c.xValueAxis.valueStep = 10
    c.yValueAxis.valueMin, c.yValueAxis.valueMax = ymin, ymax
    c.yValueAxis.valueStep = ystep
    for axis in [c.xValueAxis, c.yValueAxis]:
        style_axis(axis)
        axis.visibleGrid = True
        axis.gridStrokeColor = GRID
        axis.gridStrokeWidth = .5
    d.add(c)


def wave_figure():
    vcd = ROOT / 'simulations/tb_nominal/actual_wave.vcd'
    data, end = parse_vcd(vcd)
    pwm = data['tb_nominal/pwm']
    rising, widths, high = [], [], None
    previous = 0
    for t, value in pwm:
        if value == 1 and previous == 0:
            rising.append(t)
            high = t
        elif value == 0 and previous == 1 and high is not None:
            widths.append((t-high)*1000)
            high = None
        previous = value
    periods = [(b-a) for a, b in zip(rising, rising[1:])]
    assert [round(x, 5) for x in widths] == [1450, 1454, 1458, 1460]
    assert all(abs(x-20) < 1e-7 for x in periods)
    d = canvas('运动监督IP的XSim实际仿真波形', 760)
    label(d, 500, 669, '源数据：本次XSim导出的VCD；横轴为仿真时间（ms）', 20, 'middle')
    label(d, 110, 613, 'PWM输出', 21)
    line_chart(d, step_points(pwm, end), 110, 430, 800, 160, -.1, 1.25, 1)
    for t, width in zip(rising, widths):
        text = f'{width:.0f} µs'
        label(d, 110+800*(t+2)/65, 596, text, 17)
    label(d, 110, 370, '有效输出阶段的脉宽寄存器（µs）', 21)
    width_data = step_points(data['tb_nominal/dut/width'], end, rising[0])
    line_chart(d, width_data, 110, 185, 800, 160, 1448, 1462, 4)
    label(d, 500, 121, '上升沿间隔20.000 ms；四个脉冲宽度1450、1454、1458、1460 µs。', 19, 'middle')
    label(d, 500, 78, '本图说明RTL仿真行为；板外电气波形和机械运动需另行实测。', 19, 'middle')
    save(d, '05_xsim_pwm_from_actual_vcd')
    result = {'source':str(vcd), 'source_sha256':hashlib.sha256(vcd.read_bytes()).hexdigest(),
              'time_unit':'ms', 'rising_edge_ms':rising, 'pulse_width_us':widths,
              'period_ms':periods, 'simulation_end_ms':end, 'board_measurement':False}
    (ROOT/'wave_measurements.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def resource_figure():
    report = ROOT/'vivado_reports/utilization.rpt'
    rows = {}
    for line in report.read_text().splitlines():
        if line.startswith('|'):
            fields = [x.strip() for x in line.split('|')[1:-1]]
            if len(fields) == 6 and fields[0] in ['CLB LUTs','CLB Registers','Block RAM Tile','URAM','DSPs']:
                rows[fields[0]] = {'used':float(fields[1]),'available':float(fields[-2]),'percent':float(fields[-1])}
    keys = ['CLB LUTs','CLB Registers','Block RAM Tile','URAM','DSPs']
    assert all(k in rows for k in keys)
    d = canvas('联合FPGA平台静态资源占用', 680)
    label(d,500,589,'Vivado 2022.2 本次重新读取最终布线检查点生成',20,'middle')
    c = VerticalBarChart()
    c.x,c.y,c.width,c.height = 95,190,810,325
    c.data = [[rows[k]['percent'] for k in keys]]
    c.categoryAxis.categoryNames = ['LUT','FF','BRAM','URAM','DSP']
    style_axis(c.categoryAxis)
    style_axis(c.valueAxis,20)
    c.valueAxis.valueMin,c.valueAxis.valueMax = 0,100
    c.valueAxis.visibleGrid=True
    c.valueAxis.gridStrokeColor=GRID
    c.bars[0].fillColor=BLUE
    c.bars[0].strokeColor=None
    c.barLabelFormat='%.2f%%'
    c.barLabels.fontName=FONT
    c.barLabels.fontSize=20
    c.barLabels.nudge=12
    d.add(c)
    label(d,95,539,'资源占比（%）',19)
    label(d,500,118,'用量：LUT 66,960；FF 124,192；BRAM 93.5；URAM 56；DSP 710。',19,'middle')
    label(d,500,73,'此为布局布线后的静态资源占用，不是DPU或CPU的运行时利用率。',19,'middle')
    save(d,'04_vivado_resource_utilization')
    (ROOT/'resource_metrics.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')


def benchmark_figure():
    yunet = json.loads((EVIDENCE/'v04_yunet_board.json').read_text())['core']['latencies']
    sface = json.loads((EVIDENCE/'v05_sface_three_model_board.json').read_text())['core']['latencies']
    groups = [('YuNet',yunet['cpu_fp32'],yunet['dpu_int8_with_cpu_postprocess'],180,30),
              ('SFace',sface['arm_cpu_fp32'],sface['dpu_int8_with_input_output_conversion'],700,100)]
    d=canvas('历史实板固定输入耗时对照',760)
    label(d,500,669,'根据原始JSON绘图；本轮没有重跑板端模型性能测试',20,'middle')
    for x,color,text in [(335,BLUE,'中位数'),(535,LIGHT,'P95')]:
        d.add(Rect(x,617,25,18,fillColor=color,strokeColor=None));label(d,x+38,617,text,20)
    for i,(name,cpu,dpu,ymax,step) in enumerate(groups):
        left=85+i*485
        label(d,left+175,581,name,25,'middle')
        c=VerticalBarChart()
        c.x,c.y,c.width,c.height=left,225,350,310
        c.data=[[cpu['median_ms'],dpu['median_ms']],[cpu['p95_ms'],dpu['p95_ms']]]
        c.categoryAxis.categoryNames=['ARM FP32','DPU INT8']
        style_axis(c.categoryAxis);style_axis(c.valueAxis,step)
        c.valueAxis.valueMin,c.valueAxis.valueMax=0,ymax
        c.valueAxis.visibleGrid=True;c.valueAxis.gridStrokeColor=GRID
        c.bars[0].fillColor=BLUE;c.bars[1].fillColor=LIGHT
        c.bars[0].strokeColor=None;c.bars[1].strokeColor=None
        c.barLabelFormat='%.2f';c.barLabels.fontName=FONT;c.barLabels.fontSize=17;c.barLabels.nudge=9
        d.add(c);label(d,left,548,'耗时（ms）',18)
    label(d,500,156,'YuNet：40次固定输入，含预后处理；SFace：8次对齐输入，含转换。',19,'middle')
    label(d,500,112,'硬件与数值精度同时变化；不同模型的纵轴范围不同。',19,'middle')
    label(d,500,70,'本图不代表实时摄像头帧率、当前版本准确率或整机对话延迟。',19,'middle')
    save(d,'04_05_historical_model_latency')


def copy_context():
    history=ROOT/'historical_ui';history.mkdir(exist_ok=True)
    source=PROJECT/'语音共享文件/aura/report/ui_layers_20261016'
    for name in ['main.jpg','vision.jpg','validation.json']:
        shutil.copy2(source/'board'/name,history/name)
    shutil.copy2(source/'README.md',history/'original_source_README.md')
    old=PROJECT/'output/report_overview_01a19c53'
    for ext in ['png','svg']:
        shutil.copy2(old/('overview_design_flow.'+ext),FIG/('06_design_workflow.'+ext))
    archived=ROOT/'historical_benchmarks';archived.mkdir(exist_ok=True)
    for name in ['v04_yunet_board.json','v05_sface_three_model_board.json']:
        shutil.copy2(EVIDENCE/name,archived/name)


if __name__=='__main__':
    status=json.loads((ROOT/'RUN_STATUS.json').read_text())
    simulations=json.loads((ROOT/'SIM_STATUS.json').read_text())
    assert status['stage']=='VIVADO_COMPLETE'
    assert simulations['stage']=='ALL_4_PASSED'
    wave_figure();resource_figure();benchmark_figure();copy_context()
    print(json.dumps({'created_svg_figures':sorted(p.name for p in FIG.glob('*.svg'))},ensure_ascii=False))
