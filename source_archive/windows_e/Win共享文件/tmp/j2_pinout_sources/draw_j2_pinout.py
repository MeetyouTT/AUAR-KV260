from pathlib import Path
from html import escape
import json
from PIL import Image, ImageDraw, ImageFont

OUT = Path(r'C:\Users\uuh56\Desktop\项目\output\hardware')
OUT.mkdir(parents=True, exist_ok=True)
W, H = 1740, 1160
im = Image.new('RGB', (W, H), '#f5f7fb')
d = ImageDraw.Draw(im)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<title>KV260 J2 全部12针引脚逻辑示意图</title>',
       '<desc>依据Xilinx 038-05058-01 Rev B03第17页。采用载板原理图交错针号，非实物观察方向。9与10接地，11与12为3.3伏。FPGA封装脚来自Xilinx Kria-PYNQ约束。</desc>']
regular = r'C:\Windows\Fonts\msyh.ttc'
bold = r'C:\Windows\Fonts\msyhbd.ttc'
fonts = {}

def font(size, weight=False):
    key = (size, weight)
    if key not in fonts:
        fonts[key] = ImageFont.truetype(bold if weight else regular, size)
    return fonts[key]

def rect(x, y, w, h, fill, stroke=None, radius=0, width=2):
    d.rounded_rectangle((x, y, x+w, y+h), radius=radius, fill=fill, outline=stroke, width=width)
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke or "none"}" stroke-width="{width}"/>')

def text(x, y, value, size=28, color='#14233d', weight=False, anchor='left'):
    f = font(size, weight)
    box = d.textbbox((0,0), value, font=f)
    tw = d.textlength(value, font=f)
    left = x-tw/2 if anchor == 'middle' else x
    assert left >= 0 and left+tw <= W, (value, left, tw)
    assert y >= 0 and y+box[3]-box[1] <= H, value
    d.text((left, y-box[1]), value, font=f, fill=color)
    baseline = y-box[1]+f.getmetrics()[0]
    svg.append(f'<text x="{x}" y="{baseline}" font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif" font-size="{size}" font-weight="{700 if weight else 400}" text-anchor="{anchor if anchor == "middle" else "start"}" fill="{color}">{escape(value)}</text>')
    return tw

rect(0,0,W,H,'#f5f7fb')
text(74,51,'KV260 · J2 引脚示意图',56,weight=True)
text(76,134,'采用 KV260 载板原理图针号｜依据 038-05058-01 Rev B03 第 17 页',28,color='#52617a')
rect(74,188,1592,66,'#fff1dc',radius=12)
text(96,207,'逻辑排列示意，非实物观察方向。接线前请确认载板版本、插口 1 号脚及观察方向。',28,color='#854513',weight=True)

pins = [
    (1,'PMOD_HDA11','H12'), (2,'PMOD_HDA15','B10'),
    (3,'PMOD_HDA12','E10'), (4,'PMOD_HDA16_CC','E12'),
    (5,'PMOD_HDA13','D10'), (6,'PMOD_HDA17','D11'),
    (7,'PMOD_HDA14','C11'), (8,'PMOD_HDA18','B11'),
    (9,'GND',None), (10,'GND',None),
    (11,'PMOD_3V3',None), (12,'PMOD_3V3',None),
]

for number, net, ball in pins:
    row=(number-1)%2
    col=(number-1)//2
    x=74+270*col
    y=292+233*row
    if number<=8:
        bg,border,color='#eaf2ff','#bfd4f6','#195dc4'
    elif number<=10:
        bg,border,color='#edf0f4','#c9d0dc','#475569'
    else:
        bg,border,color='#fff0df','#ebc796','#ac5810'
    rect(x,y,242,211,bg,border,14,2)
    text(x+21,y+18,f'{number}',52,color,True)
    text(x+207,y+32,'信号' if ball else ('地' if number<=10 else '电源'),23,color,anchor='middle')
    if ball:
        s=28
        while d.textlength(net,font=font(s,True)) > 218:
            s-=1
        tw=text(x+121,y+100,net,s,anchor='middle',weight=True)
        assert tw<=220, (net,tw)
        text(x+121,y+153,f'FPGA 封装脚 {ball}',24,color='#52617a',anchor='middle')
    elif number<=10:
        text(x+121,y+96,'GND',35,weight=True,anchor='middle')
        text(x+121,y+153,'KV260 侧地',24,color='#52617a',anchor='middle')
    else:
        text(x+121,y+96,'3.3 V',35,weight=True,anchor='middle')
        text(x+121,y+153,'PMOD_3V3',24,color='#52617a',anchor='middle')

text(78,763,'1–8：3.3 V 数字信号，由 FPGA 工程分配用途；9、10：地；11、12：3.3 V 电源。',28,color='#33445e')
rect(74,830,1592,197,'#ffffff','#dce3ef',16)
text(98,852,'连接到你的 ADuM1201 隔离模块（KV260 侧）',31,weight=True)
items=[('11 或 12 → VDD1','隔离模块的 3.3 V 供电'),
       ('9 或 10 → GND1','隔离模块的 KV260 侧地'),
       ('选定信号脚 → VIB','从 1–8 中配置一根输出 PWM')]
for i,(a,b) in enumerate(items):
    cx=98+i*518
    text(cx,909,a,30,weight=True)
    text(cx,958,b,24,color='#52617a')
text(78,1053,'注意：这些信号脚不会默认输出 PWM；H12 等是 FPGA 封装脚名称，不是插口针号。',25,color='#33445e')
text(78,1106,'来源：Xilinx 载板原理图 Rev B03；Xilinx Kria-PYNQ base.xdc。图内针号与常见 Pmod 标准编号不同。',21,color='#67758b')

svg.append('</svg>')
base=OUT/'KV260_J2_引脚示意图_B03'
im.save(base.with_suffix('.png'))
base.with_suffix('.svg').write_text('\n'.join(svg),encoding='utf-8')
table='\n'.join(f'| {p} | {n} | {b or "—"} |' for p,n,b in pins)
notes=f'''# KV260 J2 引脚示意图说明

本图采用 **Xilinx 038-05058-01 Rev B03 载板原理图第17页的针号**。它是逻辑排列示意，不能用来直接判断实物插口的左右、上下。用户的载板版本尚未确认。

逻辑排布：第一排为 1、3、5、7、9、11；第二排为 2、4、6、8、10、12。原理图符号可旋转，实物仍需确认针1标记。

| J2 原理图针号 | 网名 | FPGA 封装脚 |
|---|---|---|
{table}

1–8为3.3 V数字信号，具体方向和用途由FPGA工程决定。FPGA封装脚名称H12等供约束文件使用，不是J2针号；官方参考工程的pmod索引也不是J2针号。信号脚不会默认输出舵机PWM。

你的隔离模块可按以下方式连接KV260侧：

- J2 11或12（3.3 V）→ ADuM1201 VDD1。
- J2 9或10（GND）→ ADuM1201 GND1。
- 从J2 1–8中选定并在FPGA工程里配置PWM的信号脚 → ADuM1201 VIB。

舵机由独立电池及供电板供电。隔离器GND1与舵机侧GND2不相连。当前工程未提交最终针脚约束，故本图未将任意信号针标为已经可用的PWM。

## 编号区别

常见Digilent Pmod规范按每排1–6与7–12编号；KV260 B03原理图按奇数排与偶数排编号。两者编号不能混用。例如常见规范的地5/11，对应本图的9/10；电源6/12对应本图的11/12。

## 核对来源

- [Xilinx原始载板原理图038-05058-01 Rev B03（镜像）](https://www.mikrocontroller.net/attachment/573191/038-05058-01-X-MLCC_REVB03_SKIT.pdf)，第17页J2。
- [同一Xilinx原始PDF的可下载镜像](https://hacksterio.s3.amazonaws.com/uploads/attachments/1429052/038-05058-01-x-mlcc_revb03_skit_TqvbkQ3RNn.pdf)。已本地渲染并视觉核对9/10接地、11/12接PMOD_3V3及八根信号连接。
- [Xilinx官方Kria-PYNQ base.xdc](https://github.com/Xilinx/Kria-PYNQ/blob/main/kv260/base/vivado/constraints/base.xdc)，交叉核对八根信号的FPGA封装脚及LVCMOS33标准。
- [AMD官方UG1089 Interfaces](https://docs.amd.com/r/en-US/ug1089-kv260-starter-kit/Interfaces)，区分载板rev1.0/rev2.0；用户实物版本未核对。
- [Digilent官方Pmod规范](https://digilent.com/reference/_media/reference/pmod/digilent-pmod-interface-specification.pdf)，第4页Figure 2，核对常见Pmod编号区别。
'''
base.with_suffix('.md').write_text(notes,encoding='utf-8')
print(json.dumps({'png':str(base.with_suffix('.png')),'svg':str(base.with_suffix('.svg')),'notes':str(base.with_suffix('.md'))},ensure_ascii=False))
