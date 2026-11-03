from pathlib import Path
from html import escape
import json
from PIL import Image, ImageDraw, ImageFont

OUT=Path(r'C:\Users\uuh56\Desktop\项目\output\hardware')
OUT.mkdir(parents=True,exist_ok=True)
W,H=1900,1380
im=Image.new('RGB',(W,H),'#f7f9fc')
d=ImageDraw.Draw(im)
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
     '<title>AURA KV260 单舵机完整接线方案，5V</title>',
     '<desc>逻辑连接示意，非实物针脚位置。12V电池经SVPDB-8S降为5V，供舵机及ADuM1201侧2。KV260的3.3V、地、拟选PWM分别连接VDD1、GND1、VIB。VIB经隔离送到VOB，再经供电板信号1送舵机。两侧地不连接。KV260针号参照B03原理图，尚需确认用户载板及PWM工程。</desc>']
fonts={}

def font(s,b=False):
    k=(s,b)
    if k not in fonts:
        fonts[k]=ImageFont.truetype(r'C:\Windows\Fonts\msyhbd.ttc' if b else r'C:\Windows\Fonts\msyh.ttc',s)
    return fonts[k]

def box(x,y,w,h,fill,stroke=None,r=16,width=2):
    d.rounded_rectangle((x,y,x+w,y+h),radius=r,fill=fill,outline=stroke,width=width)
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke or "none"}" stroke-width="{width}"/>')

def txt(x,y,t,s=30,c='#1c2c44',b=False,center=False):
    f=font(s,b)
    tw=d.textlength(t,font=f)
    left=x-tw/2 if center else x
    bb=d.textbbox((0,0),t,font=f)
    assert 0<=left and left+tw<=W,(t,left,tw)
    d.text((left,y-bb[1]),t,font=f,fill=c)
    by=y-bb[1]+f.getmetrics()[0]
    svg.append(f'<text x="{x}" y="{by}" font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif" font-size="{s}" font-weight="{700 if b else 400}" text-anchor="{"middle" if center else "start"}" fill="{c}">{escape(t)}</text>')
    return tw

def wire(points,c,width=5,arrow=False,dashed=False):
    for a,b in zip(points,points[1:]):
        if dashed:
            x1,y1=a;x2,y2=b
            length=((x2-x1)**2+(y2-y1)**2)**0.5
            if length:
                for t in range(0,int(length),18):
                    t2=min(t+10,length)
                    d.line((x1+(x2-x1)*t/length,y1+(y2-y1)*t/length,x1+(x2-x1)*t2/length,y1+(y2-y1)*t2/length),fill=c,width=width)
        else:
            d.line((a,b),fill=c,width=width)
    pts=' '.join(f'{x},{y}' for x,y in points)
    dash=' stroke-dasharray="10 8"' if dashed else ''
    svg.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="{width}"{dash}/>')
    if arrow:
        (xa,ya),(x,y)=points[-2:]
        if x!=xa:
            sign=1 if x>xa else -1
            tri=[(x,y),(x-15*sign,y-9),(x-15*sign,y+9)]
        else:
            sign=1 if y>ya else -1
            tri=[(x,y),(x-9,y-15*sign),(x+9,y-15*sign)]
        d.polygon(tri,fill=c)
        svg.append(f'<polygon points="{" ".join(f"{a},{b}" for a,b in tri)}" fill="{c}"/>')

red='#c54934';blue='#2268c8';ground='#526071'
box(0,0,W,H,'#f7f9fc',r=0)
txt(66,48,'KV260 + 单舵机 · 完整接线图',55,b=True)
txt(70,134,'12 V 独立电池 → SVPDB-8S → 5 V｜PWM 使用 ADuM1201 的 VIB → VOB 通道',30,c='#50617a')
box(60,196,1780,63,'#fff0d9',r=12)
txt(84,214,'逻辑连接示意，非实物针脚位置。KV260 针号按 B03 原理图；实物版本和 PWM 工程需确认。',27,c='#85471b',b=True)

box(60,287,730,638,'#eaf2ff','#c1d5f2',24)
box(790,287,1050,980,'#fff3e7','#edcfb3',24)
txt(91,307,'KV260 电源域 · 3.3 V',32,c=blue,b=True)
txt(818,307,'舵机电源域 · 5 V',32,c='#9d511e',b=True)

box(100,420,300,450,'#ffffff','#aac5ee',18)
txt(250,446,'KV260 / FPGA',31,b=True,center=True)
txt(250,498,'J2 11 或 12',30,b=True,center=True)
txt(250,542,'3.3 V',27,c=red,center=True)
txt(250,620,'J2 1*：PWM',30,b=True,center=True)
txt(250,664,'拟选封装脚 H12',23,c='#52617a',center=True)
txt(250,750,'J2 9 或 10',30,b=True,center=True)
txt(250,794,'KV260 的 GND',26,c=ground,center=True)

box(500,420,580,450,'#ffffff','#bcc9da',18)
txt(790,446,'ADuM1201 信号隔离模块',32,b=True,center=True)
wire([(790,496),(790,847)],'#adbacb',3,dashed=True)
txt(645,497,'KV260 侧',25,c=blue,center=True)
txt(935,497,'舵机侧',25,c='#9d511e',center=True)
for x,y,t in [(640,538,'VDD1'),(640,620,'VIB'),(640,750,'GND1'),(940,538,'VDD2'),(940,620,'VOB'),(940,750,'GND2')]:
    txt(x,y,t,32,b=True,center=True)
wire([(400,554),(500,554)],red,5,True)
wire([(400,643),(500,643)],blue,5,True)
wire([(400,773),(500,773)],ground,5)
wire([(702,643),(878,643)],blue,4,True)
txt(790,684,'磁隔离',24,c='#647389',center=True)
txt(645,821,'VOA：留空',25,c='#52617a',center=True)
txt(935,821,'VIA → GND2',25,c='#52617a',center=True)

box(1390,293,400,100,'#ffffff','#e6b589',14)
txt(1590,308,'12 V 电池 + DC 接头',29,b=True,center=True)
txt(1590,353,'红黑线的正负极先实测',24,c='#52617a',center=True)
wire([(1470,393),(1470,470)],red,5,True)
wire([(1700,393),(1700,470)],ground,5)
box(1390,470,400,400,'#ffffff','#e6b589',18)
txt(1432,487,'VBAT',25,c=red,b=True)
txt(1645,487,'输入 G',25,c=ground,b=True)
txt(1590,588,'SVPDB-8S',34,b=True,center=True)
txt(1590,638,'12 V → 5 V 降压',27,c='#9d511e',center=True)
txt(1430,540,'Vx：5 V',29,c=red,b=True)
txt(1430,696,'信号输入 1',29,c=blue,b=True)
txt(1430,754,'G：电池侧地',28,c=ground,b=True)
txt(1590,819,'舵机输出端：第 1 列',25,c='#52617a',center=True)

# The three horizontal connections are independently routed to labelled pads.
wire([(1390,554),(1080,554)],red,5,True)
txt(1235,516,'5 V 供电',26,c=red,center=True)
wire([(1080,643),(1210,643),(1210,711),(1390,711)],blue,5,True)
txt(1260,674,'PWM',26,c=blue,center=True)
wire([(1390,773),(1080,773)],ground,5)
txt(1235,786,'同一舵机侧地',25,c=ground,center=True)

# The output-side first column has signal, positive and ground pins.
for x,c,lab in [(1470,blue,'信号 1'),(1590,red,'Vx 5 V'),(1710,ground,'G')]:
    wire([(x,870),(x,1044)],c,5,True)
    txt(x+13,925,lab,24,c=c,b=True)
box(1390,1044,400,184,'#ffffff','#e6b589',18)
txt(1470,1061,'信号 S',24,c=blue,b=True,center=True)
txt(1590,1061,'正极 +',24,c=red,b=True,center=True)
txt(1710,1061,'负极 −',24,c=ground,b=True,center=True)
txt(1590,1116,'DS3230 舵机',33,b=True,center=True)
txt(1590,1173,'三线按标识插第 1 列',25,c='#52617a',center=True)

box(60,953,1270,314,'#ffffff','#dae2ed',18)
txt(88,976,'接线前确认',33,b=True)
for i,t in enumerate([
    '*J2 1 号 / H12 是拟选 PWM 脚，须先在 FPGA 工程中配置。',
    '供电板“6V”和“7.2V”两组焊桥均开路，输出设为 5 V。',
    'GND1 与 GND2 不连接；12 V 只接供电板 VBAT / 输入 G。',
    '先空载测 Vx 对 G 约为 5 V；确认 PWM 后再接舵机测试。',
    '停机先断舵机电池；线色以实物标识与测量为准。',
]):
    txt(88,1032+42*i,t,27,c='#334861')
txt(65,1304,'依据：Xilinx B03 载板原理图与官方 XDC、ADI ADuM1201 数据手册、MATEKSYS SVPDB-8S 资料。',23,c='#627189')
txt(65,1346,'SVPDB 编号 1 是供电板的信号通道，和 KV260 J2 的针号不是同一套编号。',23,c='#627189')
svg.append('</svg>')
base=OUT/'AURA_单舵机完整接线_5V'
im.save(base.with_suffix('.png'))
base.with_suffix('.svg').write_text('\n'.join(svg),encoding='utf-8')

connections=[
    ('电池正极，经DC接头已确认的正极线','SVPDB-8S VBAT','12V电池只进降压板输入'),
    ('电池负极，经DC接头已确认的负极线','SVPDB-8S 输入 G','先量极性，断电后焊接'),
    ('KV260 J2 原理图11或12（3.3V）','ADuM1201 VDD1','KV260侧供电'),
    ('KV260 J2 原理图9或10（GND）','ADuM1201 GND1','KV260侧地'),
    ('KV260 J2 原理图1（拟选PWM；封装脚H12）','ADuM1201 VIB','需配置FPGA并确认载板版本/针1方向'),
    ('SVPDB-8S 输出 Vx（5V）','ADuM1201 VDD2','舵机侧供电，禁止直接接12V或6V'),
    ('SVPDB-8S 输出 G','ADuM1201 GND2','与电池负极同一电源域'),
    ('ADuM1201 VOB','SVPDB-8S 单排输入编号1','PWM经隔离后送入供电板信号1'),
    ('SVPDB-8S 输出第1列 信号1','舵机信号线S','供电板只是信号直通，不生成PWM'),
    ('SVPDB-8S 输出第1列 Vx','舵机正极','通常红线，以舵机标识为准'),
    ('SVPDB-8S 输出第1列 G','舵机负极','通常黑/棕线，以舵机标识为准'),
    ('ADuM1201 VIA','ADuM1201 GND2','固定未使用输入为低电平'),
    ('ADuM1201 VOA','留空，不连接','未使用输出'),
]
table='\n'.join(f'|{a}|{b}|{c}|' for a,b,c in connections)
notes=f'''# AURA 单舵机完整接线方案（5 V）

电气结构可行；接线图仅表示逻辑连接，不表示实物针脚位置。用户KV260载板版本尚未确认，现有项目platform_manifest仍为design_only_not_board_verified、pin_map_verified=false。J2针号参照Xilinx 038-05058-01 Rev B03原理图，不能与常见Pmod标准编号混用。

## 器件与电压

- KV260沿用自己的独立供电。
- 舵机电池：用户提供12 V、1800 mAh、持续放电6 A；接头线极性、尺寸及额定电流仍需实测或查规格。
- SVPDB-8S输入5.5–36 V，默认输出5 V，全板合计持续4 A、短时7 A；输入没有反接保护。保持“6V”和“7.2V”焊桥均开路，先量Vx/G输出。
- 舵机：DS3230，一只；本方案先用5 V。实际负载、起动时压降、线缆与接头承载能力需实测。
- ADuM1201ARZ：VDD1=3.3 V、VDD2=5 V；PWM走VIB→VOB。正常供电2.7–5.5 V。

## 逐线连接

|从哪里来|接到哪里|说明|
|---|---|---|
{table}

GND1和GND2不连接。不要通过其他USB模块、调试线或电源线把两侧地再次连通。

## 供电板插排位置

以用户上传的元件面朝上、VBAT单排在上方的照片为参考，输入单排为VBAT、G、1、2、3、4、5、6；输出六列三行从靠电感到板边依次为信号1–6、Vx、G。同一列三根针组成一个舵机口。接线时以实物丝印为准，翻面会改变左右关系。

## FPGA 输出选择

本图拟选J2原理图1号（PMOD_HDA11，FPGA封装脚H12）作为PWM输出。官方参考约束可核对其封装脚，但不代表用户现有工程已输出PWM。需确认对应端口未被当前平台其他功能占用，再将PWM输出约束到H12，使用LVCMOS33。

## 首次上电

1. 断电设置焊桥、焊接并绝缘；先不接舵机及VDD2。
2. 先确认电源接头正负极，再只给供电板接电池，量Vx对G约5 V。
3. 断开电池，按表接线；先配置KV260 PWM，在舵机断开的情况下确认隔离后的信号。
4. 断电接上舵机，先无负载、小角度测试，检查5 V轨是否明显掉压以及接头、板子是否发热。
5. 停机先断舵机电池。ADuM1201在VDD1掉电而VDD2仍上电时，VOB为高电平；不能将FPGA掉电视为可靠停机。

## 来源

- [MATEKSYS SVPDB-8S](https://www.mateksys.com/?portfolio=svpdb-8s)，规格结合用户上传电压焊桥及插排图核对。
- [ADI ADuM1200/ADuM1201数据手册](https://www.analog.com/media/en/technical-documentation/data-sheets/ADuM1200_1201.pdf)，表16/18及供电范围。
- [Xilinx官方Kria-PYNQ base.xdc](https://github.com/Xilinx/Kria-PYNQ/blob/main/kv260/base/vivado/constraints/base.xdc)，H12/pmod[0]/LVCMOS33参考映射。
- [Xilinx原始B03载板原理图镜像](https://hacksterio.s3.amazonaws.com/uploads/attachments/1429052/038-05058-01-x-mlcc_revb03_skit_TqvbkQ3RNn.pdf)，第17页J2。
- 项目aura_fpga/contracts/platform_manifest.json：载板版本未填、针脚映射未验证。
'''
base.with_suffix('.md').write_text(notes,encoding='utf-8')
print(json.dumps({'png':str(base.with_suffix('.png')),'svg':str(base.with_suffix('.svg')),'guide':str(base.with_suffix('.md'))},ensure_ascii=True))
