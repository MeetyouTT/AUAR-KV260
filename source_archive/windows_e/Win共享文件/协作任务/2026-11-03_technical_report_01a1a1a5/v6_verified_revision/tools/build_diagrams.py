from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor,white
import math,subprocess,sys
sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parents[1]
pdfmetrics.registerFont(TTFont('CN',r'C:\Windows\Fonts\simsun.ttc',subfontIndex=0))
pdfmetrics.registerFont(TTFont('CNB',r'C:\Windows\Fonts\simsun.ttc',subfontIndex=0))
INK='#243746';PS='#e8f0f8';PL='#fbefdf';HOST='#e6f0e9';GRAY='#f1f3f5';EDGE='#91a4b3'
def text(c,x,y,s,size=11,bold=False,align='center'):
 c.setFillColor(HexColor(INK));c.setFont('CNB' if bold else 'CN',size)
 for i,line in enumerate(s.split('\n')):
  yy=y-i*(size+5)
  getattr(c,{'center':'drawCentredString','left':'drawString','right':'drawRightString'}[align])(x,yy,line)
def box(c,x,y,w,h,s,fill=GRAY,size=11,dashed=False):
 c.setFillColor(HexColor(fill));c.setStrokeColor(HexColor(EDGE));c.setLineWidth(.8)
 c.setDash(4,3) if dashed else c.setDash()
 c.roundRect(x,y,w,h,6,fill=1,stroke=1);c.setDash()
 lines=s.count('\n')+1;text(c,x+w/2,y+h/2+(lines-1)*(size+5)/2-size*.35,s,size)
def arrow(c,pts,label=None,labelxy=None,dashed=False):
 c.setStrokeColor(HexColor(INK));c.setFillColor(HexColor(INK));c.setLineWidth(1.1);c.setDash(4,3) if dashed else c.setDash()
 p=c.beginPath();p.moveTo(*pts[0]);[p.lineTo(*pt) for pt in pts[1:]];c.drawPath(p);c.setDash()
 a,b=pts[-2],pts[-1];ang=math.atan2(b[1]-a[1],b[0]-a[0]);p=c.beginPath();p.moveTo(*b)
 p.lineTo(b[0]-6*math.cos(ang-.45),b[1]-6*math.sin(ang-.45));p.lineTo(b[0]-6*math.cos(ang+.45),b[1]-6*math.sin(ang+.45));p.close();c.drawPath(p,fill=1,stroke=0)
 if label:text(c,*(labelxy or ((a[0]+b[0])/2,(a[1]+b[1])/2+8)),label,9)
def save(stem,w,h,fn):
 p=R/'figures'/(stem+'.pdf');c=canvas.Canvas(str(p),pagesize=(w,h));c.setTitle(stem);fn(c);c.save()
 pop=r'C:\Users\REVO1\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe'
 subprocess.run([pop,'-png','-singlefile','-scale-to','2100',str(p),str(R/'figures'/stem)],check=True,capture_output=True)
def architecture(c):
 text(c,310,321,'AUAR 雪妃运行结构与开发链',16,True)
 box(c,12,170,115,105,'相机与 MCP01\n图像与音频输入\n触控与显示',GRAY)
 box(c,170,170,237,105,'KV260 PS Linux\n采集 预后处理 调度\nASR 声纹 记忆与界面',PS,12)
 box(c,450,170,158,105,'Windows GPU 主机\n27B LLM\nOmniVoice16 TTS',HOST)
 box(c,170,38,237,86,'KV260 PL\n单核 B4096 DPU\n自研执行监督与 PWM',PL,12)
 box(c,450,38,158,86,'单轴执行机构\n有限许可与脉宽\n实际角度另行标定',GRAY)
 box(c,12,38,115,86,'Ubuntu 开发节点\n构建 量化 测试\n证据与绘图',GRAY,10,dashed=True)
 arrow(c,[(127,235),(170,235)])
 arrow(c,[(170,198),(127,198)])
 arrow(c,[(407,240),(450,240)],'请求',(428,253))
 arrow(c,[(450,197),(407,197)],'文本 PCM',(429,182))
 arrow(c,[(253,170),(253,124)],'VART',(226,145))
 arrow(c,[(328,124),(328,170)],'AXI',(352,145))
 arrow(c,[(407,80),(450,80)])
 arrow(c,[(127,80),(170,80)],dashed=True)
 text(c,310,10,'PS 检查业务上下文与帧龄  PL 管理接受后的租约和输出时序',10)
save('system_architecture',620,345,architecture)
def sequence(c):
 text(c,300,307,'PS 与 PL 的命令事务',16,True)
 box(c,32,255,170,28,'PS 软件与 MMIO',PS,11);box(c,380,255,180,28,'PL 监督状态与寄存器',PL,11)
 c.setDash(3,3);c.setStrokeColor(HexColor(EDGE));c.line(117,38,117,255);c.line(470,38,470,255);c.setDash()
 events=[(231,'session epoch → BIND',False),(197,'reference → REFERENCE',False),(163,'ARM',False),(129,'session epoch seq width lease → COMMIT',False),(91,'reason flags ack_seq width lease_left',True),(51,'STOP 或 QUIESCE',False)]
 for y,label,rev in events:
  arrow(c,[(470,y),(117,y)] if rev else [(117,y),(470,y)])
  text(c,294,y+8,label,10)
 text(c,300,15,'总线写成功之后仍需检查 reason 与 ack_seq  到期或停止使绑定失效',10)
save('command_sequence',600,325,sequence)
def scheduler(c):
 text(c,300,315,'单 DPU 任务组织与结果接受',16,True)
 box(c,185,245,230,40,'同源帧 序号 时间与当前任务',GRAY)
 box(c,22,157,155,52,'主视觉任务\n维持优先级',PS)
 box(c,227,157,160,52,'YuNet 与 SFace\n预算 状态与时效准入',PS,10)
 box(c,438,157,140,52,'不满足条件\n退让或丢弃',GRAY)
 arrow(c,[(250,245),(100,209)])
 arrow(c,[(307,245),(307,209)])
 arrow(c,[(387,183),(438,183)])
 box(c,185,77,230,46,'原生运行层单一所有权\n执行 DPU 子图并释放',PL)
 arrow(c,[(100,157),(100,100),(185,100)])
 arrow(c,[(307,157),(307,123)])
 box(c,185,8,230,38,'核对上下文与新鲜度后更新业务',PS,10)
 arrow(c,[(300,77),(300,46)])
 text(c,520,85,'不把调用次数\n等同有效结果',10)
save('scheduler_flow',600,335,scheduler)
def dialogue(c):
 text(c,300,395,'交互状态与回答交付',16,True)
 states=['空闲','采集','识别','生成','播放','收尾']
 for j,state in enumerate(states):
  box(c,10+98*j,340,90,32,state,GRAY,11)
  if j<5:arrow(c,[(100+98*j,356),(108+98*j,356)])
 text(c,300,317,'取消或失败使当前代次失效  收尾后返回空闲',10)
 text(c,300,285,'完整播放确认与记忆提交分别管理',12)

 boxes=[(15,211,155,48,'板端音频与 ASR\n会话和请求代次',PS),(222,211,155,48,'Windows LLM TTS\n回答与 PCM',HOST),(428,211,155,48,'有效性与取消检查\n接受当前结果',PS),
        (428,111,155,48,'播放 字幕与角色\n依据真实交付推进',PS),(222,111,155,48,'完整播放确认\n提交已交付历史',PS),(15,111,155,48,'摘要生成与校验\n成功落库后回收原文',PS)]
 for x,y,w,h,s,col in boxes:box(c,x,y,w,h,s,col,10)
 arrow(c,[(170,235),(222,235)]);arrow(c,[(377,235),(428,235)]);arrow(c,[(505,211),(505,159)])
 arrow(c,[(428,135),(377,135)]);arrow(c,[(222,135),(170,135)])
 box(c,191,20,235,41,'取消 过期或失败\n不作为完整已播回答提交',GRAY,10)
 arrow(c,[(505,111),(505,41),(426,41)],dashed=True)
 text(c,300,79,'模型生成完成  音频入队  软件起播  声学首声分别计量',10)
save('dialogue_lifecycle',600,420,dialogue)
def workflow(c):
 text(c,300,240,'人工与 AI 的证据工作流',16,True)
 specs=[(15,'真实任务与证据',GRAY),(215,'AI 形成候选',PS),(415,'人工检查约束',GRAY)]
 for x,s,col in specs:box(c,x,155,170,45,s,col)
 arrow(c,[(185,178),(215,178)]);arrow(c,[(385,178),(415,178)])
 box(c,415,60,170,50,'工具实际验证\n测试 仿真或设备观察',PL,10)
 box(c,215,60,170,50,'人工接受或纠错\n失败保留具体反例',GRAY,10)
 box(c,15,60,170,50,'冻结产物与证据\n源码 输入 SHA 回执',HOST,10)
 arrow(c,[(500,155),(500,110)]);arrow(c,[(415,85),(385,85)]);arrow(c,[(215,85),(185,85)])
 arrow(c,[(300,110),(300,155)],'修正',(332,128),dashed=True)
 text(c,300,17,'图示为实际采用的人工与 AI 工作流  不是多智能体运行证明',10)
save('ai_workflow',600,265,workflow)
def hardware(c):
 text(c,310,424,'硬件信号关系 非最终电气原理图',16,True)
 for args in [(12,280,170,68,'相机 / USB\n唯一采集源',GRAY),(225,280,170,68,'KV260 PS / Linux\n外设与业务',PS),(438,280,170,68,'MCP01 / USB\n录音与播放',GRAY),(225,160,170,68,'PL 监督 IP\nAXI4-Lite → servo_pwm',PS),(12,42,170,68,'显示转换链\n显示接口 → HDMI 屏',GRAY),(225,42,170,68,'J2.3 / E10\nLVCMOS33 → ADuM1201',HOST),(438,42,170,68,'独立动力单轴\n舵机与相机支架',GRAY)]:
  box(c,*args,size=11)
 arrow(c,[(182,314),(225,314)])
 arrow(c,[(438,314),(395,314)])
 arrow(c,[(310,280),(310,228)])
 arrow(c,[(225,292),(208,292),(208,128),(96,128),(96,110)])
 arrow(c,[(310,160),(310,110)])
 arrow(c,[(395,76),(438,76)])
 text(c,310,13,'最终原理图须补供电 地 端子与保护 实际隔离及机械范围另验',10)
save('old_hardware_connections',620,446,hardware)

def vision(c):
 text(c,310,382,'同源视觉与身份处理',16,True)
 box(c,180,285,260,54,'唯一相机采集 图像 序号 时间',GRAY,12)
 for args in [(12,173,170,60,'YOLOX-Nano\nINT8 / DPU',PS),(225,173,170,60,'YuNet\nINT8 / DPU',PS),(438,173,170,60,'可选任务准入\nPS / 单 DPU 共享',HOST),(12,55,170,64,'PS 解码与轨迹更新\n目标与运动候选',GRAY),(225,55,170,64,'PS 解码 NMS\n关键点与人脸对齐',GRAY),(438,55,170,64,'SFace / DPU\nPS 归一化与匹配',PS)]:
  box(c,*args,size=11)
 arrow(c,[(228,285),(97,233)])
 arrow(c,[(310,285),(310,233)])
 arrow(c,[(440,311),(523,233)])
 arrow(c,[(97,173),(97,119)])
 arrow(c,[(310,173),(310,119)])
 arrow(c,[(395,87),(438,87)])
 text(c,310,16,'身份模板按模型版本隔离 时效与上下文在业务接受处检查',11)
save('old_vision_pipeline',620,407,vision)
print('generated 7 diagrams PDF and PNG in SimSun')
