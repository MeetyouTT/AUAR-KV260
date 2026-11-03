from pathlib import Path
import re,csv,json,hashlib,sys
sys.stdout.reconfigure(encoding='utf-8')
R=Path(r'E:\Win共享文件\协作任务\2026-11-03_technical_report_01a1a1a5\v6_verified_revision')
p=R/'report/technical_report.md';t=p.read_text(encoding='utf-8')
assert '表 G-4' not in t
old='外部 I/O 的 no_input_delay、no_output_delay 与已约束内部路径分开审阅，新增外设或修改采样关系时须补齐相应约束。'
assert t.count(old)==1
t=t.replace(old,old+' 新报告的无输入延迟端口为 iic_scl_io、iic_sda_io 及 mipi_phy_if_data_p[0] 至 [3]，共 6 个；无输出延迟端口为 iic_scl_io、iic_sda_io，共 2 个。原工具将两类均标为 HIGH，故内部时序通过的范围不包含这些外部接口假设。[E31]')
s=(R/'evidence/implementation/source_rebuild_timing.rpt').read_text(errors='replace');rows=[]
for b in s.split('Slack (')[1:]:
 head=b[:2200]
 if not re.search(r'Path Type:\s+Setup',head):continue
 m=re.match(r'(?:MET|VIOLATED)\)\s*:\s*([-0-9.]+)ns',head)
 if not m:continue
 def val(k):return re.search(r'^\s*'+k+r':\s*(.+)',head,re.M).group(1).strip()
 rows.append({'slack_ns':float(m.group(1)),'source':val('Source'),'destination':val('Destination'),'group':val('Path Group')})
rows=sorted(rows,key=lambda x:x['slack_ns'])[:10];assert len(rows)==10 and rows[0]['slack_ns']==.002
with (R/'data/worst_setup_paths.csv').open('w',encoding='utf-8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
g='表 G-4 已保存报告中最差十条 Setup 路径\n\n| 序号 | 余量 ns | 时钟组简写 | 终点简写 |\n| --- | --- | --- | --- |\n'
for i,x in enumerate(rows):
 group=x['group'].split('_kv260')[0]
 end='/'.join(x['destination'].split('/')[-2:])
 g+=f"| {i+1} | {x['slack_ns']:.3f} | {group} | {end} |\n"
g+='\n时钟组与终点为排版简写，完整起点、终点、时钟组及余量见 data/worst_setup_paths.csv。表格从同一 timing.rpt 已保存的 Setup 路径排序提取，不是新一轮时序运行。\n\n'
t=t.replace('## 附录 H 外置输入 来源与提交对应',g+'## 附录 H 外置输入 来源与提交对应')
maptable='''表 8-2 指南八个入口与本包位置

| 指南入口 | 本包位置 | 内容与范围 |
| --- | --- | --- |
| README.md | 根README.md | 简介与复现入口 |
| src/ | src/fpga board host native等 | 按原运行相对位置保留源码 |
| sim/ | sim/rtl src/tests skill内tests | 硬件测试与软件测试分别定位 |
| build/ | build/ 及report/evidence | 构建脚本与本轮摘要 原生报告摘要另见附录G |
| board/ | board/ | 离线部署定义及上板流程 |
| data/ | data/metrics.csv | 投稿指标 src/data是运行数据 互不替代 |
| skill/ | skill/pynq-contract-testgen | 28件原包及README |
| report/ | report/及独立PDF | 取数回执与本技术报告分别提供 |

该结构为指南推荐，非强制；本包按原运行根组织，并在表中定位软件测试、投稿指标与运行数据。[R6]

'''
needle='### 8.2 获取工程与准备输入';assert t.count(needle)==1;t=t.replace(needle,maptable+needle)
old='| E19–E25 | evidence/history/v19 至 v25 | 模型身份 RTL 地址 引脚 时钟与时序 |'
assert t.count(old)==1
new='\n'.join(['| E19 | evidence/history/v19_deployed_model_audit.md | 模型精度 指纹与分区 |','| E20 | evidence/history/v20_wide_visual_servo.sv | RTL及寄存器真实语义 |','| E21 | evidence/history/v21_wide_prepare.tcl | BD连接 地址和构建参数 |','| E22 | evidence/history/v22_wide_pin.xdc | PWM引脚及电平约束 |','| E23 | evidence/history/v23_wide_clocks.rpt | 历史联合平台时钟 |','| E24 | evidence/history/v24_narrow_timing.rpt | 历史窄版完整时序 |','| E25 | evidence/history/v25_wide_timing.rpt | 历史宽版完整时序 |'])
t=t.replace(old,new)
t=t.replace('WNS 为 0.002 ns、WHS 为 0.010 ns','WNS（建立时序最差余量）为 0.002 ns、WHS（保持时序最差余量）为 0.010 ns',1)
t=t.replace('AMD 官方兼容表列出了 2022.2、DPUCZDX8G 4.1 与 Vitis AI 3.0 的对应关系。[R4]','AMD 官方兼容表列出了 2022.2、DPUCZDX8G 4.1 与 Vitis AI 3.0 的对应关系。[R4] 最新源码包已在 Ubuntu 20.04.4 LTS 与该版本组合下完成 Tcl、综合实现和解包复跑；2025.2、2026.1 未列为本工程已验证环境。[E30]')
p.write_text(t,encoding='utf-8')
# Lock the public vector to the actual historical model, not the new candidate.
p=R/'evidence/public_vectors/yunet_zero_vector.json';v=json.loads(p.read_text(encoding='utf-8'))
model=Path(r'E:\Win共享文件\语音共享文件\deliverables\2026-10-21_dpu_vision_start\artifacts\yunet\yunet_public_int8.xmodel')
v['historical_model_sha256']=hashlib.sha256(model.read_bytes()).hexdigest();assert v['historical_model_sha256'].startswith('54d348')
v['does_not_validate_new_model_sha256']='1219f824929437728eb5c4d702b251740df3dbcb7596dbca46c1a30ce55cf4ad'
p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
# Separate caption styles let Word generate native figure and table lists.
p=R/'tools/build_word.py';s=p.read_text(encoding='utf-8')
needle="font(doc.styles['Header'],'宋体',9)"
assert s.count(needle)==1
addition="""for caption_name in ['Figure Caption','Table Caption']:
 if caption_name not in doc.styles:doc.styles.add_style(caption_name,WD_STYLE_TYPE.PARAGRAPH)
 doc.styles[caption_name].base_style=doc.styles['Caption']
 font(doc.styles[caption_name],'宋体',9.5)
 doc.styles[caption_name].paragraph_format.first_line_indent=Pt(0)
"""
s=s.replace(needle,addition+needle)
s=s.replace("pcap=doc.add_paragraph(cap,'Caption')","pcap=doc.add_paragraph(cap,'Figure Caption')")
s=s.replace("p=doc.add_paragraph(line,'Caption')","p=doc.add_paragraph(line,'Table Caption')")
needle="  i+=1;continue\n if line.startswith('## '):"
assert s.count(needle)==1
replacement=r'''  for list_title,caption_style in [('图目录','Figure Caption'),('表目录','Table Caption')]:
   doc.add_page_break();cp(list_title,size=16,bold=True,after=12)
   listp=doc.add_paragraph();listp.paragraph_format.first_line_indent=Pt(0)
   listfield=OxmlElement('w:fldSimple');listfield.set(qn('w:instr'),'TOC \\h \\z \\t "'+caption_style+',1"');listp._p.append(listfield)
  i+=1;continue
 if line.startswith('## '):'''
s=s.replace(needle,replacement)
p.write_text(s,encoding='utf-8')
# Add the abstract business-state chain to the existing lifecycle diagram.
p=R/'tools/build_diagrams.py';s=p.read_text(encoding='utf-8')
needle=" text(c,300,300,'回答交付与记忆的一致性',16,True)"
assert s.count(needle)==1
new=""" text(c,300,395,'交互状态与回答交付',16,True)
 states=['空闲','采集','识别','生成','播放','收尾']
 for j,state in enumerate(states):
  box(c,10+98*j,340,90,32,state,GRAY,11)
  if j<5:arrow(c,[(100+98*j,356),(108+98*j,356)])
 text(c,300,317,'取消或失败使当前代次失效  收尾后返回空闲',10)
 text(c,300,285,'完整播放确认与记忆提交分别管理',12)
"""
s=s.replace(needle,new).replace("save('dialogue_lifecycle',600,320,dialogue)","save('dialogue_lifecycle',600,420,dialogue)")
p.write_text(s,encoding='utf-8')
print(json.dumps({'worst_setup_paths':10,'new_appendices':['G','H'],'native_lists':['figures','tables'],'public_vector_historical_model':v['historical_model_sha256']},ensure_ascii=False))
