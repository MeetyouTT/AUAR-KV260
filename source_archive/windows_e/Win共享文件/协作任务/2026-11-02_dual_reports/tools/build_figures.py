"""Draw report-native engineering figures; copy the historical render unchanged."""
from pathlib import Path
import math
import shutil
import subprocess
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, white

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / 'figures'
FONT_PATH = '/usr/share/fonts/truetype/arphic/uming.ttc'
NAVY = HexColor('#213c5a')
BLUE = HexColor('#e9f1fa')
MINT = HexColor('#e9f5f1')
GREY = HexColor('#f3f5f7')
INK = HexColor('#263544')


def register():
    if 'ReportSong' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('ReportSong', FONT_PATH, subfontIndex=0))


def text(c, x, y, lines, size=14, color=INK, center=True):
    c.setFont('ReportSong', size)
    c.setFillColor(color)
    if isinstance(lines, str):
        lines = lines.split('\n')
    for i, line in enumerate(lines):
        if center:
            c.drawCentredString(x, y-i*(size+6), line)
        else:
            c.drawString(x, y-i*(size+6), line)


def box(c, x, y, w, h, lines, fill=GREY, size=14):
    c.setFillColor(fill)
    c.setStrokeColor(HexColor('#aec0cf'))
    c.setLineWidth(0.9)
    c.roundRect(x, y, w, h, 8, fill=1, stroke=1)
    lines = lines.split('\n') if isinstance(lines, str) else lines
    y0 = y+h/2+(len(lines)-1)*(size+6)/2-size/3
    text(c, x+w/2, y0, lines, size=size)


def arrow(c, x1, y1, x2, y2, label=None, lx=None, ly=None):
    c.setStrokeColor(NAVY)
    c.setFillColor(NAVY)
    c.setLineWidth(1.5)
    c.line(x1, y1, x2, y2)
    angle = math.atan2(y2-y1, x2-x1)
    a = 7
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(x2-a*math.cos(angle-0.4), y2-a*math.sin(angle-0.4))
    p.lineTo(x2-a*math.cos(angle+0.4), y2-a*math.sin(angle+0.4))
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    if label:
        text(c, (x1+x2)/2 if lx is None else lx,
             (y1+y2)/2+10 if ly is None else ly, label, 12)


def make(name, height, draw):
    FIG.mkdir(parents=True, exist_ok=True)
    p = FIG / (name+'.pdf')
    c = canvas.Canvas(str(p), pagesize=(640, height))
    c.setTitle(name)
    c.setAuthor('')
    c.setFillColor(white)
    c.rect(0, 0, 640, height, fill=1, stroke=0)
    draw(c)
    c.save()
    subprocess.run(['pdftoppm', '-singlefile', '-scale-to', '1600', '-png',
                    str(p), str(FIG/name)], check=True, stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE)


def overview(c):
    text(c, 320, 408, 'AUAR·雪妃：运行节点与数据路径', 19, NAVY)
    box(c, 12, 228, 130, 132, '真实输入输出\n相机 / MCP01\n显示与单轴机构', GREY)
    box(c, 187, 228, 230, 132, 'KV260 PS / Linux\n采集、预后处理与调度\nASR、身份、记忆与界面', BLUE)
    box(c, 465, 228, 163, 132, 'Windows 主机\n27B LLM\nOmniVoice TTS', MINT)
    arrow(c, 142, 310, 187, 310)
    arrow(c, 187, 268, 142, 268)
    arrow(c, 417, 318, 465, 318)
    text(c, 441, 339, '请求', 12)
    arrow(c, 465, 264, 417, 264)
    text(c, 441, 242, '回答/PCM', 12)
    box(c, 187, 99, 230, 76, 'KV260 PL\n单 B4096 DPU ＋ 自研监督 IP', BLUE)
    box(c, 465, 99, 163, 76, '执行输出\n受限 PWM → 单轴', GREY)
    arrow(c, 260, 228, 260, 175)
    arrow(c, 345, 175, 345, 228)
    text(c, 302, 196, 'VART / AXI', 12)
    arrow(c, 417, 137, 465, 137)
    text(c, 320, 40, 'Ubuntu 开发链：构建、量化、编译、部署材料与证据归档', 14, NAVY)


def vision(c):
    text(c, 320, 394, '同源视觉与身份处理', 19, NAVY)
    box(c, 185, 302, 270, 55, '唯一相机采集：图像、序号、时间', GREY)
    box(c, 25, 186, 175, 61, 'YOLOX-Nano\nINT8 / DPU', BLUE)
    box(c, 232, 186, 175, 61, 'YuNet\nINT8 / DPU', BLUE)
    box(c, 438, 186, 175, 61, '可选任务准入\nPS / 单 DPU 共享', MINT)
    arrow(c, 235, 302, 112, 247)
    arrow(c, 320, 302, 320, 247)
    arrow(c, 455, 329, 526, 247)
    box(c, 25, 65, 175, 66, 'PS 解码与轨迹更新\n目标与运动候选', GREY)
    box(c, 232, 65, 175, 66, 'PS 解码、NMS\n关键点与人脸对齐', GREY)
    box(c, 438, 65, 175, 66, 'SFace / DPU\nPS 归一化与匹配', BLUE)
    arrow(c, 112, 186, 112, 131)
    arrow(c, 320, 186, 320, 131)
    arrow(c, 407, 99, 438, 99)
    text(c, 320, 23, '身份模板按模型版本隔离；时效与上下文在业务接受处检查', 13, NAVY)


def dialogue(c):
    text(c, 320, 440, '语音、播放确认与来源记忆', 19, NAVY)
    box(c, 30, 335, 250, 62, 'KV260：MCP01 → 前端 / ASR\n输出转写与会话上下文', BLUE)
    box(c, 360, 335, 250, 62, 'Windows：LLM → OmniVoice\n输出回答与 PCM', MINT)
    arrow(c, 280, 367, 360, 367, '请求')
    box(c, 360, 206, 250, 66, 'KV260：结果接受与播放\n字幕、角色状态、完整播放确认', BLUE)
    arrow(c, 485, 335, 485, 272)
    box(c, 30, 206, 250, 66, '取消 / 会话改变 / 结果过期\n检查请求上下文并丢弃迟到结果', GREY)
    arrow(c, 280, 238, 360, 238)
    box(c, 360, 76, 250, 66, '来源记忆与摘要任务\n提交校验通过的摘要', BLUE)
    box(c, 30, 76, 250, 66, '原文回收\n摘要存储与真实召回分别验证', GREY)
    arrow(c, 485, 206, 485, 142)
    arrow(c, 360, 109, 280, 109)
    text(c, 320, 27, '已保存结果：自然到期存储检查通过；同会话召回仍待验收', 13, NAVY)


def motion(c):
    text(c, 320, 440, '运动事务与 PL 独立输出许可', 19, NAVY)
    box(c, 35, 335, 245, 66, 'PS：有效目标与源数据时效\n检查上下文、单写入者及范围', GREY)
    box(c, 360, 335, 245, 66, '建立 PL 执行上下文\nBIND → REFERENCE → ARM', BLUE, 13)
    arrow(c, 280, 368, 360, 368)
    box(c, 360, 210, 245, 66, '写影子字段并 COMMIT\n校验会话、代次、序号、范围与租约', BLUE, 13)
    arrow(c, 482, 335, 482, 276)
    box(c, 360, 78, 245, 70, 'PWM：20 ms 周期\n500–2500 µs；每帧最多 4 µs', BLUE)
    arrow(c, 482, 210, 482, 148)
    box(c, 35, 210, 245, 66, '独立停止条件\nSTOP / 租约失效 / QUIESCE完成', MINT)
    box(c, 35, 78, 245, 70, '输出许可关闭\n旧绑定失效，重新建立参考', MINT)
    arrow(c, 157, 210, 157, 148)
    arrow(c, 360, 110, 280, 110)
    text(c, 320, 27, '当前 PL 不校验源帧绝对截止；PWM 指令值不等于实测角度', 13, NAVY)


def hardware(c):
    text(c, 320, 434, '硬件信号关系（非最终电气原理图）', 19, NAVY)
    box(c, 25, 306, 175, 70, '相机 / USB\n唯一采集源', GREY)
    box(c, 232, 306, 175, 70, 'KV260 PS / Linux\n外设与业务', BLUE)
    box(c, 438, 306, 175, 70, 'MCP01 / USB\n录音与播放', GREY)
    arrow(c, 200, 341, 232, 341)
    arrow(c, 438, 341, 407, 341)
    box(c, 232, 185, 175, 70, 'PL 监督 IP\nAXI4-Lite → servo_pwm', BLUE, 13)
    arrow(c, 320, 306, 320, 255)
    box(c, 25, 63, 175, 70, '显示转换链\n显示接口 → HDMI 屏', GREY)
    box(c, 232, 63, 175, 70, 'J2.3 / E10\nLVCMOS33 → ADuM1201', MINT, 13)
    box(c, 438, 63, 175, 70, '独立动力单轴\n舵机与相机支架', GREY)
    arrow(c, 320, 185, 320, 133)
    arrow(c, 407, 98, 438, 98)
    c.setStrokeColor(NAVY)
    c.setLineWidth(1.5)
    c.lines([(232,319,215,319),(215,319,215,151),(215,151,112,151)])
    arrow(c,112,151,112,133)
    text(c, 320, 24, '最终原理图须补供电、地、端子与保护；实际隔离及机械范围另验', 13, NAVY)


def placeholder(title, details):
    def draw(c):
        c.setStrokeColor(HexColor('#b2bdc7'))
        c.setFillColor(HexColor('#f7f8fa'))
        c.setDash(5, 4)
        c.roundRect(10, 10, 620, 160, 8, fill=1, stroke=1)
        c.setDash()
        text(c, 320, 110, title, 20, NAVY)
        text(c, 320, 70, details, 14)
        text(c, 320, 32, '此图位为审阅占位，不代表已提供对应实物证据', 12)
    return draw


def main():
    register()
    make('system_overview', 440, overview)
    make('vision_pipeline', 420, vision)
    make('dialogue_memory', 470, dialogue)
    make('motion_protocol', 470, motion)
    make('hardware_connections', 460, hardware)
    make('mechanical_pending', 180, placeholder('待补：最终机械设计与装配图', '总装、支架、转轴、关键尺寸、零点与限位'))
    make('front_photo_pending', 180, placeholder('待补：整机正面实物照片', '整机、开发板、外设与单轴机构同框'))
    make('angle_photo_pending', 180, placeholder('待补：整机 45° 实物照片', '结构层次、线束与工作状态清晰可辨'))
    make('board_photo_pending', 180, placeholder('待补：开发板高清特写', '型号、J2.3、供电端子与信号路径可辨认'))
    source = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-30_board_owner/integration/dialogue_repair/animation_thinking_collaboration/public_preview_actual_1793458354293233900/answer.png')
    shutil.copyfile(str(source), str(FIG/'character_render_historical.png'))


if __name__ == '__main__':
    main()
