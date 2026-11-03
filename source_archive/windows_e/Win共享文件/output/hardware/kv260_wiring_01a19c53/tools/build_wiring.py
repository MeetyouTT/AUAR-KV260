from __future__ import annotations

import hashlib
import html
import json
import math
import re
import subprocess
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle
from pypdf import PdfReader


ROOT = Path('E:/Win共享文件')
OUT = Path(__file__).resolve().parents[1]
DATE = '2026-11-02'
PDF_PATH = OUT / 'kv260_wiring_review_v1.pdf'
POPPLER = Path('C:/Users/REVO1/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe')

pdfmetrics.registerFont(TTFont('YaHei', 'C:/Windows/Fonts/msyh.ttc', subfontIndex=0))
pdfmetrics.registerFont(TTFont('YaHeiBold', 'C:/Windows/Fonts/msyhbd.ttc', subfontIndex=0))

INK = '#142638'
MUTED = '#536576'
LINE = '#AAB8C4'
BLUE = '#1464B7'
RED = '#C64D32'
GROUND = '#536170'
AMBER = '#9D671A'
PALE_BLUE = '#F2F7FC'
PALE_ORANGE = '#FFF8F0'


class Figure:
    """One geometry source for editable SVG and vector PDF."""

    def __init__(self, width: int, height: int):
        self.w, self.h = width, height
        self.ops = []
        self.text_bounds = []

    def rect(self, x, y, w, h, fill='white', stroke=LINE, radius=12, sw=2):
        self.ops.append(('rect', x, y, w, h, fill, stroke, radius, sw))

    def path(self, points, color=INK, sw=3, arrow=False, start_arrow=False, dash=None):
        self.ops.append(('path', points, color, sw, arrow, start_arrow, dash))

    def circle(self, x, y, radius=4, fill=INK):
        self.ops.append(('circle', x, y, radius, fill))

    def text(self, x, y, value, size=27, color=INK, bold=False, align='left', maxw=None):
        font = 'YaHeiBold' if bold else 'YaHei'
        width = pdfmetrics.stringWidth(value, font, size)
        if maxw is not None and width > maxw + 0.2:
            raise ValueError(f'Text too wide: {value!r}: {width:.1f} > {maxw:.1f}')
        left = x if align == 'left' else x - width if align == 'right' else x - width / 2
        if left < 0 or left + width > self.w + 0.1 or y < size * 0.8 or y > self.h - 2:
            raise ValueError(f'Text outside figure: {value!r}')
        self.text_bounds.append([left, y - size, left + width, y + size * .25, value])
        self.ops.append(('text', x, y, value, size, color, bold, align))

    def wrap(self, x, y, value, width, size=24, leading=36, color=MUTED, bold=False):
        lines, line = [], ''
        font = 'YaHeiBold' if bold else 'YaHei'
        for ch in value:
            if ch == '\n' or (line and pdfmetrics.stringWidth(line + ch, font, size) > width):
                lines.append(line)
                line = '' if ch == '\n' else ch
            else:
                line += ch
        if line:
            lines.append(line)
        for i, line in enumerate(lines):
            self.text(x, y + leading * i, line, size, color, bold, maxw=width)
        return y + leading * len(lines)

    @staticmethod
    def head(tip, prev, length=13, half_width=6):
        dx, dy = tip[0] - prev[0], tip[1] - prev[1]
        n = math.hypot(dx, dy)
        ux, uy = dx / n, dy / n
        bx, by = tip[0] - ux * length, tip[1] - uy * length
        return [tip, (bx - uy * half_width, by + ux * half_width), (bx + uy * half_width, by - ux * half_width)]

    def to_svg(self, path: Path):
        s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">',
             '<title>KV260 接线资料核对图 V1</title>',
             '<desc>工程约束、B03参考映射与既有5V方案整理；外部接线尚待实物复核。</desc>',
             '<rect width="100%" height="100%" fill="white"/>']
        for op in self.ops:
            if op[0] == 'rect':
                _, x, y, w, h, fill, stroke, radius, sw = op
                s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
            elif op[0] == 'path':
                _, points, col, sw, arrow, start, dash = op
                pts = ' '.join(f'{x},{y}' for x, y in points)
                dashed = f' stroke-dasharray="{dash}"' if dash else ''
                s.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{sw}" stroke-linejoin="round"{dashed}/>')
                for tip, prev in ([(points[-1], points[-2])] if arrow else []) + ([(points[0], points[1])] if start else []):
                    pts = ' '.join(f'{x:.3f},{y:.3f}' for x, y in self.head(tip, prev))
                    s.append(f'<polygon points="{pts}" fill="{col}"/>')
            elif op[0] == 'circle':
                _, x, y, r, col = op
                s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>')
            else:
                _, x, y, value, size, col, bold, align = op
                anchor = {'left': 'start', 'right': 'end', 'center': 'middle'}[align]
                s.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{col}">{html.escape(value)}</text>')
        s.append('</svg>')
        path.write_text('\n'.join(s), encoding='utf8')

    def to_pdf(self, c: canvas.Canvas, page_size):
        pw, ph = page_size
        scale = min(pw / self.w, ph / self.h)
        ox, oy = (pw - self.w * scale) / 2, (ph - self.h * scale) / 2
        c.saveState()
        c.translate(ox, oy)
        c.scale(scale, scale)
        for op in self.ops:
            if op[0] == 'rect':
                _, x, y, w, h, fill, stroke, radius, sw = op
                c.setFillColor(colors.toColor(fill))
                c.setStrokeColor(colors.HexColor(stroke))
                c.setLineWidth(sw)
                c.roundRect(x, self.h-y-h, w, h, radius, fill=1, stroke=1)
            elif op[0] == 'path':
                _, points, col, sw, arrow, start, dash = op
                c.setStrokeColor(colors.HexColor(col))
                c.setLineWidth(sw)
                c.setDash([float(x) for x in dash.split(',')] if dash else [])
                p = c.beginPath()
                p.moveTo(points[0][0], self.h-points[0][1])
                for x, y in points[1:]:
                    p.lineTo(x, self.h-y)
                c.drawPath(p, stroke=1)
                c.setDash([])
                c.setFillColor(colors.HexColor(col))
                for tip, prev in ([(points[-1], points[-2])] if arrow else []) + ([(points[0], points[1])] if start else []):
                    tri = self.head(tip, prev)
                    p = c.beginPath()
                    p.moveTo(tri[0][0], self.h-tri[0][1])
                    for x, y in tri[1:]:
                        p.lineTo(x, self.h-y)
                    p.close()
                    c.drawPath(p, fill=1, stroke=0)
            elif op[0] == 'circle':
                _, x, y, r, col = op
                c.setFillColor(colors.HexColor(col))
                c.circle(x, self.h-y, r, stroke=0, fill=1)
            else:
                _, x, y, value, size, col, bold, align = op
                c.setFont('YaHeiBold' if bold else 'YaHei', size)
                c.setFillColor(colors.HexColor(col))
                getattr(c, {'left': 'drawString', 'right': 'drawRightString', 'center': 'drawCentredString'}[align])(x, self.h-y, value)
        c.restoreState()


def header(f: Figure, title, subtitle):
    f.text(65, 75, title, 45, bold=True)
    f.text(65, 124, subtitle, 25, MUTED)


def label(f, x, y, wid, text, col=INK):
    f.text(x, y, wid, 22, col, bold=True, align='center')
    if text:
        f.text(x, y+29, text, 21, col, align='center')


def servo_figure():
    f = Figure(1800, 1250)
    header(f, 'KV260 单舵机电气连接图', '资料核对版 V1  |  工程约束 + B03参考映射 + 既有5V方案  |  2026-11-02')
    f.text(65, 175, '工程确认：servo_pwm → E10 / LVCMOS33；载板版本、模块端子与外部导线仍需现场核对。', 25, AMBER)
    f.text(265, 300, 'KV260 电源域', 29, BLUE, True, 'center')

    # Module outlines. Port coordinates describe electrical topology, not physical pin placement.
    f.rect(65, 340, 400, 445, PALE_BLUE)
    f.text(265, 392, 'KV260 / PL', 34, bold=True, align='center')
    f.text(265, 425, '独立供电；自研逻辑输出 PWM', 23, MUTED, align='center')
    f.rect(650, 340, 510, 445)
    f.text(905, 390, 'ADuM1201', 34, bold=True, align='center')
    f.text(905, 423, '芯片脚号，不等同模块排针编号', 22, MUTED, align='center')
    f.path([(905, 445), (905, 555)], LINE, 2, dash='8,7')
    f.path([(905, 653), (905, 718)], LINE, 2, dash='8,7')
    f.rect(1320, 340, 415, 445, PALE_ORANGE)
    f.text(1527, 393, 'SVPDB-8S', 34, bold=True, align='center')
    f.text(1527, 425, '舵机电源域 / 供电及信号分配', 23, MUTED, align='center')

    # Three left-side connections.
    for y, kv, kv2, pin, col, wid in [
        (475, 'J2.11 / 12', '3.3V（B03参考）', '1  VDD1', RED, 'W01'),
        (585, 'J2.3（B03参考）', 'servo_pwm / 封装 E10', '3  VIB', BLUE, 'W02'),
        (695, 'J2.9 / 10', 'GND（B03参考）', '4  GND1', GROUND, 'W03'),
    ]:
        f.text(92, y-12, kv, 27, col, True, maxw=350)
        f.text(92, y+22, kv2, 23, MUTED, maxw=350)
        f.text(675, y+8, pin, 28, col, True)
        f.path([(465,y),(650,y)], col, 4, arrow=col!=GROUND)
        f.circle(465, y, 4, col)
        label(f, 557, y-24, wid, '', col)
    f.text(265, 760, '针号以 B03 原理图为参考', 22, AMBER, align='center')

    # Isolator cross-domain signal and right-side ports.
    f.text(1137, 483, '8  VDD2', 28, RED, True, 'right')
    f.text(1137, 593, '6  VOB', 28, BLUE, True, 'right')
    f.text(1137, 703, '5  GND2', 28, GROUND, True, 'right')
    f.path([(800,585),(1006,585)], BLUE, 3.5, arrow=True)
    f.text(905, 625, 'B 通道', 22, BLUE, align='center')
    f.text(905, 755, '两侧 GND 按方案分域', 23, MUTED, align='center')
    f.text(1345, 483, 'Vx：5V 方案值', 28, RED, True)
    f.text(1345, 593, '信号输入 1', 28, BLUE, True)
    f.text(1345, 703, 'G：舵机侧地', 28, GROUND, True)
    f.path([(1320,475),(1160,475)], RED, 4, arrow=True)
    f.path([(1160,585),(1320,585)], BLUE, 4, arrow=True)
    f.path([(1320,695),(1160,695)], GROUND, 4)
    label(f, 1240, 451, 'W06', '', RED)
    label(f, 1240, 561, 'W08', '', BLUE)
    label(f, 1240, 671, 'W07', '', GROUND)

    # Battery and two separate connections to the regulator input.
    f.rect(1320, 195, 415, 70)
    f.text(1527, 240, '电池：12V 方案值，极性待核', 25, bold=True, align='center', maxw=390)
    f.path([(1440,265),(1440,340)], RED, 4, arrow=True)
    f.path([(1635,265),(1635,340)], GROUND, 4)
    label(f, 1397, 294, 'W04', '', RED)
    label(f, 1680, 294, 'W05', '', GROUND)
    f.text(1440, 365, 'VBAT', 20, RED, align='center')
    f.text(1635, 365, '输入 G', 20, GROUND, align='center')

    # Explicit outgoing signal, positive and ground nets.
    f.text(1527, 770, '输出第1列（端子位置待核）', 22, MUTED, align='center')
    f.rect(1320, 955, 415, 150)
    f.text(1527, 1035, 'DS3230 舵机', 32, bold=True, align='center')
    f.text(1527, 1075, '最终型号、线序和极性待核', 23, AMBER, align='center')
    for x, name, wid, col in [(1380,'S','W09',BLUE),(1527,'+ / Vx','W10',RED),(1670,'- / G','W11',GROUND)]:
        f.path([(x,785),(x,955)], col, 4, arrow=col!=GROUND)
        f.circle(x,785,4,col)
        label(f, x+43, 860, wid, '', col)
        f.text(x, 986, name, 24, col, True, 'center')

    # Design notes sit in open whitespace, avoiding the wire routing region.
    f.text(65, 850, '图中接线状态', 29, bold=True)
    f.wrap(65, 892, '线号 W01-W11 对应逐线表。蓝色：PWM；红色：电源正端；灰色：地。', 1110, 25, 37)
    f.wrap(65, 990, '未用通道按既有方案：芯片7脚 VIA 接 GND2，2脚 VOA 留空。模块端子、去耦和未用通道的实际处理需按实物核对。', 1110, 24, 36)
    f.wrap(65, 1100, '图中未画跨域共地线；实物是否存在其他共地路径需核对。模块位置和连线为逻辑示意，不表示插针的物理朝向。', 1110, 24, 36)
    f.text(65, 1220, '图1  单轴执行机构接线资料图  |  依据 S1-S5；外部导线尚未现场复核，供电数值不是实测结果。', 22, MUTED)
    return f


def system_figure():
    f = Figure(1800, 1150)
    header(f, 'KV260 整机外设连接关系', '报告配图 V1  |  记录设备之间的接口，单舵机逐线连接详见图1  |  2026-11-02')
    f.text(65, 177, '按现有报告与项目资料整理；相机、显示链、接口位置和电源型号仍需按实物补全。', 26, AMBER)
    f.rect(650, 450, 480, 250, PALE_BLUE)
    f.text(890, 510, 'KV260', 39, bold=True, align='center')
    f.text(890, 563, 'PS：采集、ASR、业务、记忆与播放', 25, align='center', maxw=445)
    f.text(890, 615, 'PL：DPU + 自研运动监督逻辑', 25, align='center', maxw=445)
    f.text(890, 665, '接口与运行版本应配套记录', 23, MUTED, align='center')
    f.rect(650, 220, 480, 140)
    f.text(890, 273, 'Windows 模型主机', 32, bold=True, align='center')
    f.text(890, 320, '语言模型 / TTS 服务', 27, align='center')
    f.path([(890,360),(890,450)], BLUE, 4, arrow=True, start_arrow=True)
    f.text(918, 415, '以太网 / LAN', 24, BLUE)
    f.rect(65, 400, 370, 155)
    f.text(250, 457, '相机', 34, bold=True, align='center')
    f.text(250, 508, '最终型号与接口待录', 25, MUTED, align='center')
    f.path([(435,478),(650,478)], BLUE, 4, arrow=True)
    f.text(541, 445, '图像输入', 24, BLUE, align='center')
    f.rect(65, 650, 370, 170)
    f.text(250, 710, 'MCP01 USB 音频', 31, bold=True, align='center')
    f.text(250, 760, '录音与播放', 27, align='center')
    f.path([(435,735),(540,735),(540,640),(650,640)], BLUE, 4, arrow=True, start_arrow=True)
    f.text(541, 777, 'USB 音频', 24, BLUE, align='center')
    f.rect(1340, 420, 395, 170)
    f.text(1537, 480, '显示转换链与屏幕', 31, bold=True, align='center')
    f.text(1537, 529, '接口与转换器型号待录', 25, MUTED, align='center')
    f.path([(1130,510),(1340,510)], BLUE, 4, arrow=True)
    f.text(1235, 476, '显示信号', 24, BLUE, align='center')
    f.rect(1340, 760, 395, 200, PALE_ORANGE)
    f.text(1537, 816, '单轴执行机构', 31, bold=True, align='center')
    f.text(1537, 862, '隔离器 / 供电板 / 舵机', 25, align='center')
    f.text(1537, 911, '独立动力供电；详见图1', 24, MUTED, align='center')
    f.path([(1130,640),(1235,640),(1235,860),(1340,860)], BLUE, 4, arrow=True)
    f.text(1262, 720, 'PWM / E10', 24, BLUE)
    f.rect(650, 870, 480, 120)
    f.text(890, 922, 'KV260 独立电源', 31, bold=True, align='center')
    f.text(890, 964, '原配电源或已确认供电，规格待录', 23, MUTED, align='center')
    f.path([(890,870),(890,700)], RED, 4, arrow=True)
    f.text(925, 800, '板卡供电', 24, RED)
    f.text(65, 1060, '图2  整机接口关系图。蓝线为数据或控制连接，红线为板卡供电；接口所在位置不代表实物端口位置。', 23, MUTED)
    f.text(65, 1110, '依据 S6 与既有接线方案。图1和图2描述设计连接，不构成全部功能已完成验收的声明。', 23, MUTED)
    return f


def connection_rows():
    return [
        ('W01','KV260 J2.11 / 12（B03）','ADuM1201 VDD1（芯片1脚）','3.3V 方案','B03参考映射；载板版本和模块端子待核'),
        ('W02','servo_pwm / E10；B03映射J2.3','ADuM1201 VIB（芯片3脚）','PWM / LVCMOS33','E10由宽版XDC确认；J2.3和实物接线待核。旧H12拟选标注不用于此宽版图'),
        ('W03','KV260 J2.9 / 10（B03）','ADuM1201 GND1（芯片4脚）','KV260侧地','B03参考映射；与模块GND1的实物对应待核'),
        ('W04','电池正极','SVPDB-8S VBAT','12V 方案','电池规格、接头正负极与实际导线待核'),
        ('W05','电池负极','SVPDB-8S 输入G','舵机侧地','电池与供电板端子极性待核'),
        ('W06','SVPDB-8S 输出Vx','ADuM1201 VDD2（芯片8脚）','5V 方案','模块设置与输出电压需实测；不是已测5V'),
        ('W07','SVPDB-8S G','ADuM1201 GND2（芯片5脚）','舵机侧地','按方案与舵机负极同域；实物共地路径待核'),
        ('W08','ADuM1201 VOB（芯片6脚）','SVPDB-8S 信号输入1','隔离后的PWM','芯片B通道3→6由数据手册核对；模块端子及通道待核'),
        ('W09','SVPDB-8S 输出第1列信号1','舵机信号S','PWM','第1列的物理方向与舵机线序待核'),
        ('W10','SVPDB-8S 输出第1列Vx','舵机电源正极','5V 方案','舵机准确型号、允许电压与极性待核'),
        ('W11','SVPDB-8S 输出第1列G','舵机电源负极','舵机侧地','按实物端子核对，不仅凭线色判断'),
        ('U01','ADuM1201 VIA（芯片7脚）','GND2（芯片5脚）','未用输入处理','既有方案；核对模块是否已有固定处理'),
        ('U02','ADuM1201 VOA（芯片2脚）','不连接','未用输出处理','既有方案；核对模块实际布线'),
    ]


def draw_table(c, rows, sources):
    pw, ph = landscape(A3)
    c.setPageSize((pw, ph))
    c.setFillColor(colors.HexColor(INK))
    c.setFont('YaHeiBold', 25)
    c.drawString(40, ph-55, '逐线接线表与现场核对记录')
    c.setFont('YaHei', 11)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawString(40, ph-82, 'V1 资料核对版  |  W01-W11 对应图1；U01-U02 为未用通道  |  2026-11-02')
    style = ParagraphStyle('cell', fontName='YaHei', fontSize=10.4, leading=15.5, textColor=colors.HexColor(INK), wordWrap='CJK')
    hs = ParagraphStyle('header', parent=style, fontName='YaHeiBold', textColor=colors.white)
    data = [[Paragraph(x,hs) for x in ['编号','起点','终点','信号或方案值','确认范围与待核事项']]]
    data += [[Paragraph(html.escape(x), style) for x in row] for row in rows]
    width = pw-80
    cols = [43, 225, 235, 135, width-638]
    table = Table(data, colWidths=cols, repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#243E56')),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor('#F3F6F9')]),
        ('GRID',(0,0),(-1,-1),.5,colors.HexColor('#D9D9D9')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
    ]))
    _, th = table.wrapOn(c,width,ph)
    top = ph-105
    if th>ph-300:
        raise ValueError(f'Connection table leaves insufficient note space: {th}')
    table.drawOn(c,40,top-th)
    y = top-th-27
    c.setFillColor(colors.HexColor(INK))
    c.setFont('YaHeiBold',11)
    c.drawString(40,y,'现场核对：载板版本 __________  实际PWM端子 __________  模块端子对应 __________  供电实测 __________V')
    y-=24
    c.setFont('YaHei',10.5)
    c.drawString(40,y,'舵机型号/线序 __________  其他共地路径 __________  照片编号 __________  核对人及日期 __________________')
    y-=28
    c.setFont('YaHeiBold',11)
    c.drawString(40,y,'来源与使用范围')
    y-=21
    for line in [
        'S1 宽版 v22_wide_pin.xdc；S2 KV260 J2 B03针号说明；S3 既有单舵机5V方案。完整路径和SHA256见 sources.json。',
        'S4 ADI ADuM1200/1201 Rev.L 表16（芯片脚号）；S5 MATEKSYS SVPDB-8S 官方规格；S6 现有赛事报告架构。',
        '本图保留KV260独立供电与舵机独立动力的方案。实际隔离、上电/停机行为及PWM波形仍须分别验证。',
    ]:
        c.setFont('YaHei',10)
        c.setFillColor(colors.HexColor(MUTED))
        c.drawString(40,y,line)
        y-=18
    c.setFont('YaHei',9)
    c.drawRightString(pw-40,25,'KV260 wiring review V1  |  3 / 3')
    return th


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources_and_checks():
    local = [
        ('S1', ROOT/'协作任务/2026-11-02_dual_reports/evidence/v22_wide_pin.xdc', '宽版servo_pwm封装脚和IO标准'),
        ('S2', ROOT/'output/hardware/KV260_J2_引脚示意图_B03.md', 'B03参考针号；用户载板版本未确认'),
        ('S3', ROOT/'output/hardware/AURA_单舵机完整接线_5V.md', '既有供电、隔离与线序方案；旧H12拟选不沿用'),
        ('S6', ROOT/'协作任务/2026-11-02_dual_reports/competition_technical_report.md', '现有整机接口和PS/PL/Windows分工'),
    ]
    result=[]
    for sid,p,scope in local:
        result.append({'id':sid,'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'scope':scope})
    xdc=local[0][1].read_text(encoding='utf8')
    assert re.search(r'PACKAGE_PIN\s+E10\s+\[get_ports\s+servo_pwm\]',xdc)
    assert re.search(r'IOSTANDARD\s+LVCMOS33\s+\[get_ports\s+servo_pwm\]',xdc)
    b03=local[1][1].read_text(encoding='utf8')
    assert '| 3 | PMOD_HDA12 | E10 |' in b03
    assert '| 9 | GND |' in b03 and '| 11 | PMOD_3V3 |' in b03
    result += [
        {'id':'S4','url':'https://www.analog.com/media/en/technical-documentation/data-sheets/ADuM1200_1201.pdf','scope':'Rev.L，表16和表18；引脚3 VIB→6 VOB，供电与地脚号；未验证模块排针','checked_date':DATE},
        {'id':'S5','url':'https://www.mateksys.com/?portfolio=svpdb-8s','scope':'SVPDB-8S默认5V且可调；未据此声称实物输出已测','checked_date':DATE},
    ]
    return result


def write_text_materials():
    (OUT/'report_caption.txt').write_text('''建议图题与说明\n\n图X KV260单轴执行机构电气连接图\n控制路径由KV260的PL侧servo_pwm输出，经ADuM1201隔离器B通道及供电板信号通道传至舵机。KV260与舵机使用各自供电，既有方案分别为3.3V信号侧和5V舵机侧。宽版XDC确认servo_pwm约束到封装脚E10；B03参考原理图将E10映射为J2.3。图中W01至W11与逐线接线表对应。\n\n使用条件\n本版依据工程文件与既有方案整理，尚未完成实物核线。载板版本、J2物理朝向、模块端子与芯片脚号的对应、供电实测值及最终舵机线序核对后，方可将本图作为最终实物接线记录。图1适合放入报告2.2.3；图2辅助整体介绍；实物照片和波形测量应放入成果与验证部分。\n\n文件用法\nPNG用于插入Word；SVG保留可编辑矢量文字和连线；PDF包含两张图与逐线表。原有旧接线图没有被覆盖。\n''',encoding='utf-8-sig')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'qa').mkdir(exist_ok=True)
    sources=sources_and_checks()
    rows=connection_rows()
    (OUT/'sources.json').write_text(json.dumps({'date':DATE,'status':'SOURCE_CHECKED_PHYSICAL_WIRING_PENDING','sources':sources},ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'connections.json').write_text(json.dumps({'status':'REFERENCE_DESIGN_NOT_AS_BUILT','columns':['id','from','to','signal_or_design_value','evidence_and_pending_check'],'rows':rows},ensure_ascii=False,indent=2),encoding='utf8')
    first,second=servo_figure(),system_figure()
    first.to_svg(OUT/'kv260_servo_wiring_v1.svg')
    second.to_svg(OUT/'kv260_system_connections_v1.svg')
    page_size=landscape(A3)
    c=canvas.Canvas(str(PDF_PATH),pagesize=page_size,pageCompression=1)
    c.setTitle('KV260接线图与逐线表 资料核对版V1')
    c.setAuthor('')
    c.setSubject('Source-checked wiring documentation; physical verification pending')
    first.to_pdf(c,page_size); c.showPage()
    second.to_pdf(c,page_size); c.showPage()
    table_height=draw_table(c,rows,sources); c.showPage(); c.save()
    write_text_materials()
    render=subprocess.run([str(POPPLER),'-scale-to','3200','-png',str(PDF_PATH),str(OUT/'qa/page')],capture_output=True,text=True,encoding='utf8',errors='replace')
    if render.returncode:
        raise RuntimeError(render.stderr)
    images=sorted((OUT/'qa').glob('page-*.png'))
    assert len(images)==3,images
    from shutil import copyfile
    copyfile(images[0],OUT/'kv260_servo_wiring_v1.png')
    copyfile(images[1],OUT/'kv260_system_connections_v1.png')
    reader=PdfReader(PDF_PATH)
    text='\n'.join(p.extract_text() or '' for p in reader.pages)
    checks={
        'pages':len(reader.pages),'rows':len(rows),'table_height_pt':table_height,
        'source_pin_verified':'E10','stale_pwm_h12_used_in_diagram':False,
        'pending_physical_checks_visible':'现场核对' in text and '实物' in text,
        'all_wire_ids_in_pdf':all(row[0] in text for row in rows),
        'svg_count':2,'pdf_text_length':len(text),'figure_text_bounds_checked':True,
        'first_figure_text_count':len(first.text_bounds),'second_figure_text_count':len(second.text_bounds),
        'visual_qa':'PENDING_IMAGE_REVIEW','device_commands_sent':False,
    }
    assert checks['all_wire_ids_in_pdf'] and checks['pending_physical_checks_visible']
    (OUT/'validation.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(checks,ensure_ascii=False,indent=2))
    print('OUTPUT',PDF_PATH)


if __name__=='__main__':
    main()
