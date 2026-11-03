import base64
import html
import json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'source'
CONFIG=json.loads((SOURCE/'media-config.json').read_text(encoding='utf-8'))
BG='#f7fbff'; INK='#25435f'; MUTED='#647c92'; LAV='#a48cbc'; PALE='#efebf7'; BLUE='#419de8'; TEXT='#7879e8'; AMBER='#eab04f'; VISION='#77a7bc'; LINE='#d4e2ef'
im=Image.open(ROOT/'assets'/'wordmark-transparent.png')
alpha=np.asarray(im.getchannel('A'))
rows=np.flatnonzero((alpha>180).sum(axis=1)>30)
cols=np.flatnonzero((alpha>180).sum(axis=0)>15)
crop=[max(0,int(cols[0])-14),max(0,int(rows[0])-14),min(im.width,int(cols[-1])+15),min(im.height,int(rows[-1])+15)]

def esc(s):return html.escape(str(s),quote=True)
def text(s,x,y,size=26,color=INK,weight=400,anchor='start',spacing=None):
    extra=f' letter-spacing="{spacing}"' if spacing is not None else ''
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}"{extra}>{esc(s)}</text>'
def rect(x,y,w,h,fill='none',stroke=None,rx=0,dash=None,sw=1.5):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" rx="{rx}"'+(f' stroke="{stroke}" stroke-width="{sw}"' if stroke else '')+(f' stroke-dasharray="{dash}"' if dash else '')+'/>'
def line(x1,y1,x2,y2,color=LINE,sw=2):return f'<path d="M {x1} {y1} L {x2} {y2}" fill="none" stroke="{color}" stroke-width="{sw}"/>'
def arrow(x1,y1,x2,y2,color=LINE,sw=2):
    return line(x1,y1,x2,y2,color,sw)+f'<path d="M {x2-8} {y2-5} L {x2} {y2} L {x2-8} {y2+5}" fill="none" stroke="{color}" stroke-width="{sw}"/>'
def logo(x,y,w,h):
    x0,y0,x1,y1=crop
    return f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="{x0} {y0} {x1-x0} {y1-y0}" preserveAspectRatio="xMinYMid meet" overflow="hidden"><image href="../assets/wordmark-transparent.png" x="0" y="0" width="{im.width}" height="{im.height}"/></svg>'
def image_slot(x,y,w,h,title,detail,key=None):
    p=CONFIG.get(key) if key else None
    if p:
        return rect(x,y,w,h,'#edf3fa',LINE,18)+f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><image href="{esc(p)}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet"/></svg>'
    result=rect(x,y,w,h,'#f0f5fb','#cbdbea',20,'9 12')
    result+=line(x+30,y+30,x+76,y+30,LAV,3)+line(x+30,y+30,x+30,y+76,LAV,3)
    result+=line(x+w-76,y+h-30,x+w-30,y+h-30,LAV,3)+line(x+w-30,y+h-76,x+w-30,y+h-30,LAV,3)
    result+=text(title,x+w/2,y+h/2-10,36,INK,400,'middle')
    result+=text(detail,x+w/2,y+h/2+40,23,MUTED,400,'middle')
    return result
def svg_start(w,h,title):
    return f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title"><title id="title">{esc(title)}</title><style>text{{font-family:"Microsoft YaHei UI","Microsoft YaHei","Segoe UI",sans-serif;dominant-baseline:auto}}*{{box-sizing:border-box}}</style>'+rect(0,0,w,h,BG)
def cover_base(title,stage=-1):
    s=svg_start(1920,1080,title)
    s+=f'<circle cx="1790" cy="20" r="420" fill="{PALE}" opacity=".52"/>'
    s+=logo(104,54,580,102)+text('AUAR · 雪妃',1810,117,23,MUTED,400,'end')
    s+=line(110,940,1810,940)
    names=['实物照片','原理讲解','实机效果']
    for i,name in enumerate(names):
        x=110+i*600
        s+=line(x,940,x+500,940,LAV if i==stage else LINE,4 if i==stage else 2)
        s+=text(f'0{i+1}',x,993,21,LAV if i==stage else MUTED)
        s+=text(name,x+52,993,28,INK if i==stage else MUTED,500 if i==stage else 400)
    return s

def flow_node(x,y,w,h,main,sub,color):
    return rect(x,y,w,h,'#fff',LINE,14)+rect(x,y,5,h,color,rx=2)+text(main,x+w/2,y+35,24,INK,500,'middle')+text(sub,x+w/2,y+65,20,MUTED,400,'middle')

def main_cover():
    s=cover_base('AUAR·雪妃 视频总封面')
    s+=text('AMD KV260 · 多模态交互原型',110,298,28,LAV,500)
    s+=text('AUAR',104,459,154,INK,500,spacing=4)+text('雪妃',110,563,74,INK,500)
    s+=text('视觉 · 语音 · 受监督执行',112,650,36,INK)
    s+=text('在板端组织感知与业务，',113,726,27,MUTED)+text('以局域网连接本地模型推理。',113,769,27,MUTED)
    s+=image_slot(1000,291,810,455.625,'项目实物照片','素材待补充','actual_photo')
    s+=text('KV260 / 相机 / 音频 / 显示 / 单轴机构',1405,806,23,MUTED,400,'middle')
    return s+'</svg>'

def chapter_cover(n):
    names=['实物照片','原理讲解','实机效果']
    subtitles=['从硬件连接，看系统组成','从采集、调用，到输出闭环','从交互过程，看协同表现']
    notes=[['KV260 主控与 FPGA 计算','USB 相机 / MCP01 音频','触控屏 / 单轴随动机构'],['视觉感知与转轴协同','语音触发与模型调用','完整播放确认与声画同步'],['自然对话与角色响应','视觉跟随与转轴动作','声音、口型与字幕同步']]
    s=cover_base(f'AUAR 第{n+1}阶段 {names[n]}',n)
    s+=text(f'0{n+1}',109,348,116,LAV,500)
    s+=text(names[n],110,480,80,INK,500)+text(subtitles[n],113,550,29,MUTED)
    for j,note in enumerate(notes[n]):s+=text(note,115,655+j*45,25,MUTED)
    if n==0:
        s+=image_slot(780,245,1040,585,'实物照片','素材待补充','actual_photo')
    elif n==2:
        s+=image_slot(780,245,1040,585,'实机演示画面','素材待补充','actual_demo_still')
    else:
        s+=rect(780,245,1040,585,'#fff',LINE,22)
        s+=text('对话数据流',825,310,25,LAV,500)
        mains=['语音采集','板端调度','LLM / TTS','板端播放'];subs=['起音与句尾','意图与上下文','两次独立调用','统一播放时钟'];colors=[BLUE,TEXT,LAV,AMBER]
        for j,(main,sub,col)in enumerate(zip(mains,subs,colors)):
            x=825+j*245;s+=flow_node(x,350,190,86,main,sub,col)
            if j<3:s+=arrow(x+190,393,x+238,393,LINE)
        s+=text('视觉与转轴协同',825,535,25,LAV,500)
        for j,(main,sub,col)in enumerate(zip(['相机','DPU / CPU','PL / PWM','单轴跟随'],['采集图像','检测与跟踪','受监督控制','到位后停止'],[VISION,VISION,AMBER,AMBER])):
            x=825+j*245;s+=flow_node(x,575,190,86,main,sub,col)
            if j<3:s+=arrow(x+190,618,x+238,618,LINE)
        s+=text('板端调度 · 模型调用 · 完整播放确认',1300,770,22,MUTED,400,'middle')
    return s+'</svg>'

def poster():
    s=svg_start(1400,1980,'AUAR·雪妃 项目海报')
    s+=f'<circle cx="1300" cy="10" r="370" fill="{PALE}" opacity=".6"/>'
    s+=logo(84,42,650,113)+text('AMD KV260 · FPGA',1316,111,22,MUTED,400,'end')
    s+=text('AUAR·雪妃',80,266,88,INK,500)
    s+=text('多模型视觉、语音交互与执行监督系统',84,327,34,INK)
    s+=text('板端组织感知与业务，局域网调用语言模型和语音合成',86,375,23,MUTED)
    s+=image_slot(84,418,1232,365,'项目实物照片','KV260 / 相机 / 触控显示 / 音频 / 单轴机构 · 素材待补充','actual_photo')
    s+=text('01  系统如何协同',84,862,32,INK,500)
    s+=text('视觉感知与跟随',84,912,22,LAV,500)
    for j,main in enumerate(['相机采集','DPU 检测','CPU 跟踪','PL / PWM','单轴跟随']):
        x=84+j*260;s+=rect(x,936,190,70,'#fff',LINE,12)+text(main,x+95,979,23,INK,500,'middle')
        if j<4:s+=arrow(x+190,971,x+249,971,AMBER if j>1 else VISION)
    s+=text('语音对话与同步输出',84,1062,22,LAV,500)
    for j,main in enumerate(['麦克风','VAD / ASR','板端调度','LLM / TTS','板端声画同步']):
        x=84+j*260;s+=rect(x,1086,190,70,PALE if j==3 else '#fff',LINE,12)+text(main,x+95,1129,23,INK,500,'middle')
        if j<4:s+=arrow(x+190,1121,x+249,1121,TEXT if j in [1,2] else BLUE)
    s+=text('业务、记录与播放由板端组织；Windows 主机负责模型推理。',84,1203,22,MUTED)
    s+=text('02  设计重点',84,1286,32,INK,500)
    features=[('感知与跟随',['单 DPU 共享多模型','PS 跟踪决策，PL 监督执行']),('对话与记忆',['板端转写与上下文管理','播放确认后提交已播记录']),('异构协同',['板端调度与声画同步','27B + OmniVoice 本地推理'])]
    for j,(head,lines)in enumerate(features):
        x=84+j*424;s+=line(x,1315,x+384,1315,LAV,4)+text(head,x,1361,27,INK,500)
        for k,st in enumerate(lines):s+=text(st,x,1406+k*37,21,MUTED)
    s+=text('03  实机效果',84,1510,32,INK,500)
    s+=image_slot(84,1545,600,337.5,'实机演示画面','素材待补充','actual_demo_still')
    s+=text('关键技术',760,1555,27,INK,500)
    tech=['YOLOX-Nano / YuNet / SFace','GTCRN / Silero VAD / Paraformer','27B / OmniVoice16','AXI4-Lite 监督与 PWM 输出','完整播放 ACK 与来源记忆']
    for j,t in enumerate(tech):s+=text(t,760,1607+j*42,21,MUTED)
    s+=line(84,1905,1316,1905,LINE,1.4)
    s+=text('工程原型展示',84,1930,17,MUTED)
    s+=text('资料依据：项目技术文档与工程交付说明',1316,1930,17,MUTED,400,'end')
    return s+'</svg>'

files={'cover-main.svg':main_cover(),'cover-01-photo.svg':chapter_cover(0),'cover-02-principle.svg':chapter_cover(1),'cover-03-demo.svg':chapter_cover(2),'poster-a3.svg':poster()}
for name,content in files.items():(SOURCE/name).write_text(content,encoding='utf-8')
(ROOT/'.build'/'design-manifest.json').write_text(json.dumps({'logo_canvas':im.size,'logo_visible_layout_box':crop,'covers':list(files)[:4],'poster':'poster-a3.svg','pending_materials':CONFIG['pending_materials'],'source_documents':[r'E:\AUAR_工程交付_20261102\aura\readme.md',r'E:\AUAR_工程交付_20261102\aura\report\competition_report_review.pdf',r'E:\AUAR_工程交付_20261102\aura\report\release_status.md'],'claims_omitted':'No unqualified latency, accuracy, end-to-end acceptance or invented hardware images.'},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'generated':list(files),'logo_visible_layout_box':crop},ensure_ascii=True))
