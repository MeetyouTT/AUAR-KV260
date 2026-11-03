import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const root=path.dirname(fileURLToPath(import.meta.url));
const data=JSON.parse(await fs.readFile(path.join(root,'report_data.json'),'utf8'));
const wb=Workbook.create();
const names=['报告材料清单','DPU与视觉','玩偶与语音','大模型与TTS','FPGA与转轴','后续测试','原始数据'];
const sheets=Object.fromEntries(names.map(n=>[n,wb.worksheets.add(n)]));
const navy='#234C6B', pale='#F1F5F8', text='#17212F', amber='#FFF2CC';
const font='Microsoft YaHei';
const formula=s=>({f:s});
const ref=k=>`'原始数据'!$C$${data.metric_rows[k]}`;
const raw=k=>formula('='+ref(k));
const NA='n.a.';

function col(n){let s='';for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;}
function matrix(sheet,row,column,rows){
  const width=rows[0].length;
  const values=rows.map(r=>r.map(v=>v&&typeof v==='object'&&'f'in v?null:v));
  sheet.getRangeByIndexes(row-1,column-1,rows.length,width).values=values;
  rows.forEach((r,i)=>r.forEach((v,j)=>{if(v&&typeof v==='object'&&'f'in v)sheet.getCell(row-1+i,column-1+j).formulas=[[v.f]];}));
}
function setup(sheet,title,last=70,widths=[210,115,115,115,115,100,120,390]){
  sheet.showGridLines=false;
  const end=col(widths.length-1);
  const area=sheet.getRange(`A1:${end}${last}`);
  area.format.font={name:font,size:11,color:text};
  area.format.verticalAlignment='center';
  area.format.rowHeightPx=30;
  widths.forEach((w,i)=>sheet.getRange(`${col(i)}1:${col(i)}${last}`).format.columnWidthPx=w);
  sheet.getRange('A2').values=[[title]];
  sheet.getRange('A2').format.font={name:font,size:16,bold:true,color:text};
  sheet.getRange(`A3:${end}3`).format.borders={bottom:{style:'thin',color:'#CBD5DF'}};
  sheet.tabColor=navy;
}
function note(sheet,row,textValue){sheet.getCell(row-1,0).values=[[textValue]];sheet.getCell(row-1,0).format.font={name:font,size:11,italic:true,color:'#526275'};}
function section(sheet,row,title){sheet.getCell(row-1,0).values=[[title]];sheet.getCell(row-1,0).format.font={name:font,size:12,bold:true,color:text};}
function table(sheet,row,headers,rows,{height=48,numeric=[],noteCol=headers.length-1}={}){
  const n=headers.length,end=col(n-1),last=row+rows.length;
  matrix(sheet,row,1,[headers,...rows]);
  const header=sheet.getRange(`A${row}:${end}${row}`);
  header.format.fill=navy;
  header.format.font={name:font,size:11,bold:true,color:'#FFFFFF'};
  header.format.horizontalAlignment='center';header.format.wrapText=true;header.format.rowHeightPx=38;
  header.format.borders={insideVertical:{style:'thin',color:'#FFFFFF'},bottom:{style:'thin',color:navy}};
  if(rows.length){
    sheet.getRange(`A${row+1}:${end}${last}`).format.rowHeightPx=height;
    sheet.getRange(`A${row+1}:${end}${last}`).format.wrapText=true;
    rows.forEach((_,i)=>{if(i%2===1)sheet.getRange(`A${row+1+i}:${end}${row+1+i}`).format.fill=pale;});
    numeric.forEach(i=>{const r=sheet.getRange(`${col(i)}${row+1}:${col(i)}${last}`);r.format.horizontalAlignment='right';r.setNumberFormat('0.00');});
    if(noteCol>=0)sheet.getRange(`${col(noteCol)}${row+1}:${col(noteCol)}${last}`).format.font={name:font,size:11,color:'#526275'};
  }
  return last;
}
function chart(sheet,range,title,start,end,{line=false,unit='0.00'}={}){
  const c=sheet.charts.add(line?'line':'bar',sheet.getRange(range));
  c.title=title;c.titleTextStyle.typeface=font;c.titleTextStyle.fontSize=14;
  c.setPosition(start,end);
  c.legend={position:'top',textStyle:{typeface:font,fontSize:12}};
  c.xAxis={axisType:'textAxis',textStyle:{typeface:font,fontSize:12}};
  c.yAxis={numberFormatCode:unit,numberFormatSourceLinked:false,textStyle:{typeface:font,fontSize:12}};
  const colors=['#235789','#94B7D4','#5E8B66'];
  c.series.items.forEach((s,i)=>{s.fill=colors[i%colors.length];if(line)s.line={fill:colors[i%colors.length],style:'solid',width:2};});
  return c;
}
function chartSource(sheet,range,numericRange,format='0.00'){
  sheet.getRange(range).format.wrapText=true;
  sheet.getRange(range).format.font={name:font,size:10,color:'#526275'};
  sheet.getRange(range).format.rowHeightPx=32;
  sheet.getRange(numericRange).setNumberFormat(format);
}

// Sources retain one numeric observation per row. Results link directly to them.
const inputs=sheets['原始数据'];
setup(inputs,'性能原始观测与来源',190,[260,300,140,90,230,410,90]);
note(inputs,3,'每行保留原始数值和单位。来源索引位于右侧I列起。');
table(inputs,4,['记录ID','指标','原始数值','单位','设备或版本','测试范围','来源ID'],data.metrics.map(r=>[r.key,r.label,r.value,r.unit,r.device,r.scope,r.source]),{height:42,numeric:[2],noteCol:5});
const sourceStart=4;
inputs.getRange('I2').values=[['来源文件与适用范围']];
inputs.getRange('I2').format.font={name:font,size:16,bold:true,color:text};
matrix(inputs,sourceStart,9,[['来源ID','名称','原文件','SHA256','适用范围'],...data.sources.map(s=>[s.id,s.name,s.path,s.sha256,s.scope])]);
const sourceRange=inputs.getRange(`I4:M${4+data.sources.length}`);
sourceRange.format.font={name:font,size:11,color:text};sourceRange.format.verticalAlignment='center';sourceRange.format.wrapText=true;
inputs.getRange('I4:M4').format.fill=navy;inputs.getRange('I4:M4').format.font={name:font,size:11,bold:true,color:'#FFFFFF'};
inputs.getRange(`I5:M${4+data.sources.length}`).format.rowHeightPx=90;
[90,260,700,500,420].forEach((w,i)=>inputs.getRange(`${col(8+i)}2:${col(8+i)}22`).format.columnWidthPx=w);
inputs.freezePanes.freezeRows(4);

const checklist=sheets['报告材料清单'];
setup(checklist,'AUAR·雪妃 技术文档材料清单',31,[100,240,180,430,340,230]);
note(checklist,3,'按官方模板列出22项。图片可选与有条件要求分别标注。');
table(checklist,4,['模板位置','材料','模板要求','具体内容','已有资料与缺口','获取位置'],data.checklist,{height:74,noteCol:4});
checklist.freezePanes.freezeRows(4);

const vision=sheets['DPU与视觉'];
setup(vision,'DPU与视觉性能',81,[210,115,115,115,115,180,120,390]);
note(vision,3,'延迟为历史KV260固定输入结果；YuNet/SFace格式在本轮Ubuntu重读。');
table(vision,5,['模型','CPU中位 ms','DPU中位 ms','CPU P95 ms','DPU P95 ms','样本数','中位比值','测试范围'],data.sections.latency_rows.map(r=>[
 r.name,raw(r.name+'_cpu_median_ms'),raw(r.name+'_dpu_median_ms'),raw(r.name+'_cpu_p95_ms'),raw(r.name+'_dpu_p95_ms'),raw(r.name+'_dpu_samples'),formula(`=B${r.name==='YuNet'?6:7}/C${r.name==='YuNet'?6:7}`),r.sample_scope+'。FP32/INT8及硬件同时变化。'
]),{numeric:[1,2,3,4,5,6],height:56});
vision.getRange('G6:G7').setNumberFormat('0.00"×"');
vision.getRange('F6:F7').setNumberFormat('0');
section(vision,10,'编译模型元数据');
const deployedModels=data.sections.models.filter(m=>m.model!=='YOLO官方参考');
table(vision,11,['模型','输入 NHWC','精度','DPU分区','文件 MiB','指纹','来源ID','核对范围'],deployedModels.map(m=>[
 m.model,m.shape,m.dtype,m.partitions,formula(`=${ref(m.model+'_bytes')}/1048576`),'hex: '+m.fingerprint,m.source,m.historical_only?'历史板端同SHA记录；本轮未取回现役字节':'本轮Vitis AI 3.0只读解析，哈希与部署记录一致'
]),{height:62,numeric:[3,4]});
vision.getRange('D12:D14').setNumberFormat('0');
section(vision,17,'公开人脸质量评测');
table(vision,18,['SFace版本','正对数量','负对数量','误接收','误拒绝','准确率','阈值','测试范围'],['FP32','INT8'].map((p,i)=>[
 p,raw('sface_'+p+'_positive_pairs'),raw('sface_'+p+'_negative_pairs'),raw('sface_'+p+'_false_accepts'),raw('sface_'+p+'_false_rejects'),formula(`=1-(D${19+i}+E${19+i})/(B${19+i}+C${19+i})`),raw('sface_'+p+'_threshold'),'独立1000对主机评测；INT8为量化模拟，非1000对上板。'
]),{numeric:[1,2,3,4,5,6],height:60});
vision.getRange('F19:F20').setNumberFormat('0.0%');vision.getRange('G19:G20').setNumberFormat('0.0000');
vision.getRange('B19:E20').setNumberFormat('0');
table(vision,23,['YuNet阈值','图像数','参考脸数','匹配脸数','匹配框IoU','关键点误差 px','指标类型','测试范围'],[[.9,raw('yunet_agreement_images'),raw('yunet_agreement_reference_faces'),raw('yunet_agreement_matched_iou_ge_05'),raw('yunet_matched_box_iou_median'),raw('yunet_landmark_error_pixels_median'),'FP32/INT8一致性','参考框来自浮点模型，不能作为人工真值AP或现场准确率。']],{numeric:[0,1,2,3,4,5],height:62});
section(vision,27,'历史三模型核心调用');
table(vision,28,['模式','YOLO中位 ms','YuNet中位 ms','SFace中位 ms','YOLO调用数','YuNet调用数','SFace调用数','测试范围'],data.sections.mixed.map(r=>[
 r.mode,raw('mixed_'+r.mode+'_yolo'),r.yunet?raw('mixed_'+r.mode+'_yunet'):NA,r.sface?raw('mixed_'+r.mode+'_sface'):NA,r.yolo_calls,r.yunet_calls,r.sface_calls,'预编码固定输入核心网络调用。数值不同于预后处理完整路径。'
]),{numeric:[1,2,3,4,5,6],height:60});
section(vision,34,'当前正式版仍需补测');
table(vision,35,['项目','单模型吞吐','YOLO现场AP','多人识别FAR','三模型有效fps','整帧P95','状态','原因'],[['最终同版结果',NA,NA,NA,NA,NA,'等待维护交接','现有记录不能替代当前版本、同一负载与人工标注测试。']],{height:60});
matrix(vision,40,1,[['模型','ARM FP32中位 ms','DPU INT8中位 ms'],['YuNet',formula('=B6'),formula('=C6')],['SFace',formula('=B7'),formula('=C7')]]);
chart(vision,'A40:C42','历史固定输入路径中位耗时（ms）','A45','H61');
chartSource(vision,'A40:C42','B41:C42');
vision.getRange('A40:C40').format.rowHeightPx=42;
note(vision,64,'图中比较改变了执行硬件和数值精度；不等于整机对话加速比。');

const avatar=sheets['玩偶与语音'];
setup(avatar,'玩偶界面与语音交互性能',85);
note(avatar,3,'各表属于不同历史版本或负载，保留各自范围，不合并成当前整机成绩。');
table(avatar,5,['界面指标','调整前','调整后','单位','变化量','统计性质','状态','范围'],data.sections.ui_comparisons.map((r,i)=>[
 r.label,raw('ui_'+r.key+'_before'),raw('ui_'+r.key+'_after'),r.unit,formula(`=C${i+6}-B${i+6}`),'历史观察','已归档','主页面，聆听/跟随关闭。GUI重启及场景变化未受控，保留变差指标。'
]),{numeric:[1,2,4],height:56});
section(avatar,17,'两轮真人对话软件计时');
table(avatar,18,['轮次','ASR ms','上下文 ms','LLM RPC ms','TTS RPC ms','首音频入队 ms','软件SPEAKING ms','范围'],[1,2].map(i=>[
 i,...data.sections.dialogue_stages.map(stage=>raw('turn'+i+'_'+stage)),'录音采集完成至软件起播。两轮均完整播放，非外部声学首声。'
]),{numeric:[1,2,3,4,5,6],height:62});
matrix(avatar,21,1,[['两轮平均',...Array.from({length:6},(_,i)=>formula(`=AVERAGE(${col(i+1)}19:${col(i+1)}20)`)),'n=2，旧boot记录；当前版本待复验。']]);
avatar.getRange('B21:G21').setNumberFormat('0.00');avatar.getRange('A21:H21').format.rowHeightPx=48;avatar.getRange('H21').format.wrapText=true;
section(avatar,24,'ASR公开音频描述性对照');
table(avatar,25,['线程数','测量次数','平均解码 ms','中位解码 ms','总体RTF','人工真值','指标类型','范围'],[2,3].map(i=>[
 i,raw('asr_thread'+i+'_samples'),raw('asr_thread'+i+'_mean_decode_wall_ms'),raw('asr_thread'+i+'_median_decode_wall_ms'),raw('asr_thread'+i+'_aggregate_real_time_factor'),'无','历史公开音频','不含构造和预热；背景计数变化，不能据此归因整机提速或给WER。'
]),{numeric:[0,1,2,3,4],height:62});
section(avatar,30,'历史正常业务30秒资源');
table(avatar,31,['指标','数值','单位','统计窗','负载','口径','状态','范围'],[
 ['整板CPU平均',raw('cpu_mean'),'%',raw('resource_duration'),'原正常业务','四核合计100%','历史观察','原业务播报恢复聆听，跟随关闭。'],
 ['DPU任务忙时平均',raw('dpu_busy_mean'),'%',raw('resource_duration'),'同一观察窗','驱动CU任务忙时','历史观察','非FPGA静态LUT/DSP占比。'],
 ['系统内存平均已用',formula(`=${ref('memory_mean_kib')}/1048576`),'GiB',raw('resource_duration'),'同一观察窗','MemTotal - MemAvailable','历史观察','GPU/XRT/CMA不再重复相加。'],
 ['系统内存最低可用',formula(`=${ref('memory_min_available_kib')}/1048576`),'GiB',raw('resource_duration'),'同一观察窗','MemAvailable最低值','历史观察','30秒不代表长期稳定性。']
],{numeric:[1,3],height:52});
matrix(avatar,39,1,[['阶段','两轮均值 ms'],['ASR',formula('=B21')],['上下文',formula('=C21')],['LLM RPC',formula('=D21')],['TTS RPC',formula('=E21')],['软件起播',formula('=G21')]]);
chart(avatar,'A39:B44','两轮真人交互软件计时（ms，历史记录）','A47','H64');
chartSource(avatar,'A39:B44','B40:B44');
note(avatar,67,'阶段耗时与软件起播各有定义，不把条形图相加当作声学首声。');

const llm=sheets['大模型与TTS'];
setup(llm,'大语言模型与语音合成性能',66);
note(llm,3,'Windows是实际推理主机；Ubuntu整理统计不能替代该主机上的性能测量。');
table(llm,5,['项目','当前或已记录值','单位','采集性质','设备','状态','来源','范围'],[
 ['GPU','RTX 5090 Laptop GPU','设备','本轮只读核对','Windows','已确认','环境记录','与桌面版RTX 5090分开标注。'],
 ['显存总量',raw('gpu_total_mib'),'MiB','本轮只读核对','Windows','已确认','环境记录','总容量，非运行时占用或峰值。'],
 ['显卡驱动','621.01','版本','本轮只读核对','Windows','已确认','环境记录','本轮未增加推理负载。'],
 ['Ollama','0.40.13','版本','本轮只读核对','Windows','模型已驻留','环境记录','原27B IQ4_XS。'],
 ['语言模型','27B IQ4_XS','模型','已记录配置','Windows','现有模型','校准记录','实际生成仍需当前版专项测速。'],
 ['上下文长度',raw('llm_context_tokens'),'token','已记录配置','Windows','现有配置','校准记录','原模型探针与现役配置记录。'],
 ['语音合成','OmniVoice','模型','历史公开校准','Windows','已有2条暖态记录','校准记录','16步，同音色、缓存未命中、未板端播放。']
],{height:52});
llm.getRange('B6:B12').format.columnWidthPx=210;
llm.getRange('B7').setNumberFormat('#,##0');llm.getRange('B11').setNumberFormat('#,##0');
section(llm,13,'LLM短探针原始计时');
table(llm,14,['性质','输出token数','生成耗时 ms','总耗时 ms','折算token/s','样本条数','稳定吞吐','范围'],[[
 '单独准入探针',raw('llm_eval_count'),formula(`=${ref('llm_eval_duration')}/1000000`),formula(`=${ref('llm_total_duration')}/1000000`),formula('=B15/(C15/1000)'),1,NA,'仅4个token，不能据此报告稳态tokens/s或首token延迟。'
]],{numeric:[1,2,3,4,5],height:65});
llm.getRange('G15:H15').format.fill=amber;
section(llm,18,'OmniVoice暖态公开短句合成');
table(llm,19,['样本','合成耗时 s','PCM样本数','采样率 Hz','音频时长 s','RTF','缓存','范围'],[1,2].map((i,j)=>[
 i,raw('tts'+i+'_seconds'),raw('tts'+i+'_samples'),raw('tts'+i+'_rate'),formula(`=C${20+j}/D${20+j}`),formula(`=B${20+j}/E${20+j}`),'未命中','历史暖态合成，不含初始化；未实际播放，不代替音质评价。'
]),{numeric:[0,1,2,3,4,5],height:65});
llm.getRange('C20:D21').setNumberFormat('#,##0');llm.getRange('F20:F21').setNumberFormat('0.000');
section(llm,24,'待补的正式指标');
table(llm,25,['指标','TTFT P50','TTFT P95','稳定token/s','联合显存峰值','真人首声','状态','原因'],[['最终同版',NA,NA,NA,NA,NA,'等待专项测量','公开固定提示、足够输出token、冷暖态分组；当前维护结束后采集。']],{height:65});
matrix(llm,30,1,[['样本','合成耗时 s','音频时长 s'],['短句1',formula('=B20'),formula('=E20')],['短句2',formula('=B21'),formula('=E21')]]);
chart(llm,'A30:C32','历史暖态TTS合成与音频时长（s）','A35','H51');
chartSource(llm,'A30:C32','B31:C32','0.000');
note(llm,54,'RTF = 合成耗时 ÷ 音频时长。LLM token/s使用末包真实token计数。');

const hardware=sheets['FPGA与转轴'];
setup(hardware,'FPGA平台与运动监督结果',67);
note(hardware,3,'本次Vivado重读既有最终DCP；四套XSim仿真新跑，原工程输入哈希保持。');
const resourceKeys=['CLB LUTs','CLB Registers','Block RAM Tile','URAM','DSPs'];
table(hardware,5,['资源','已用','可用','占比','统计性质','工具','状态','范围'],resourceKeys.map((k,i)=>[
 k,raw('fpga_'+k+'_used'),raw('fpga_'+k+'_available'),formula(`=B${i+6}/C${i+6}`),'静态资源','Vivado 2022.2','本次重算','2026-10-28最终布线检查点；非本轮完整重建或实板利用率。'
]),{numeric:[1,2,3],height:54});
hardware.getRange('D6:D10').setNumberFormat('0.00%');
hardware.getRange('B6:C10').setNumberFormat('#,##0.##');
section(hardware,13,'时序、路由与检查项');
const hardwareRows=[
 ['WNS',raw('setup_worst_slack_ns'),'ns','已约束路径'],['WHS',raw('hold_worst_slack_ns'),'ns','已约束路径'],
 ['建立时间失败端点',raw('setup_failing_endpoints'),'个','本次报告'],['保持时间失败端点',raw('hold_failing_endpoints'),'个','本次报告'],
 ['可布线网络',raw('routable_nets'),'条','本次报告'],['完成布线网络',raw('fully_routed_nets'),'条','本次报告'],['路由错误',raw('routing_error_nets'),'条','本次报告'],
 ['DRC Warning',raw('drc_warning_total'),'项','保留原报告告警'],['CDC Critical',raw('cdc_critical_total'),'项','保留原报告告警'],['缺输入延迟约束端口',raw('unconstrained_input_ports'),'个','需结合外部接口分析'],['缺输出延迟约束端口',raw('unconstrained_output_ports'),'个','需结合外部接口分析']
];
table(hardware,14,['指标','数值','单位','适用范围'],hardwareRows,{numeric:[1],height:38,noteCol:3});
hardware.getRange('B15:B16').setNumberFormat('0.000');
hardware.getRange('B17:B25').setNumberFormat('#,##0');
section(hardware,28,'本次RTL仿真与现场功能状态');
table(hardware,29,['项目','结果','单位','证据类型','测试环境','状态','物理量实测','范围'],[
 ['通过的RTL测试台',raw('xsim_passed'),'套','本次XSim','Vivado 2022.2','4套通过','无','含授权、越界、租约、停止及PWM行为。'],
 ['PWM周期',raw('pwm_period'),'ms','本次VCD','100MHz nominal','通过','无','周期20ms，即50Hz。'],
 ['转轴实物跟随','用户已确认','定性','既有现场反馈','保留现有实现','功能验收收口',NA,'不重复调参；角度、角速度若声明数值需另测。'],
 ['长时记忆','存储半段通过','状态','历史元数据','自然摘要窗口','召回待验',NA,'摘要保存和真实召回分别验证。']
],{height:64});
matrix(hardware,37,1,[['资源','占比'],...resourceKeys.map((k,i)=>[k,formula(`=D${i+6}`)])]);
chart(hardware,'A37:B42','最终布线平台静态资源占用','A45','H61',{unit:'0%'});
chartSource(hardware,'A37:B42','B38:B42','0.00%');

const plan=sheets['后续测试'];
setup(plan,'性能指标获取位置与补测安排',21,[210,240,470,290,410,390]);
note(plan,3,'样本数为建议方案，不是模板强制数量。当前不触发设备、模型或机械操作。');
table(plan,4,['测试项','实际执行位置','操作与统计方法','建议样本','保存的表格或图像','前提与当前限制'],data.tests,{height:110,noteCol:5});
plan.freezePanes.freezeRows(4);

wb.recalculate();
// A positive-input recalculation check verifies that calculations remain live.
const firstTtsRaw=data.metric_rows['tts1_seconds'];
const original=inputs.getRange(`C${firstTtsRaw}`).values[0][0];
const initial=llm.getRange('F20').values[0][0];
inputs.getRange(`C${firstTtsRaw}`).values=[[original*2]];wb.recalculate();
const changed=llm.getRange('F20').values[0][0];
if(Math.abs(changed-initial*2)>1e-9)throw new Error('RTF formula did not recalculate');
inputs.getRange(`C${firstTtsRaw}`).values=[[original]];wb.recalculate();
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},maxChars:2500});
await fs.writeFile(path.join(root,'formula_error_scan.json'),errors.ndjson);
const qa=path.join(root,'qa');await fs.mkdir(qa,{recursive:true});
const views=[
 ['报告材料清单','A1:F26','01_materials'],['DPU与视觉','A1:H36','02_vision_tables'],['DPU与视觉','A39:H64','02_vision_chart'],
 ['玩偶与语音','A1:H35','03_avatar_tables'],['玩偶与语音','A38:H67','03_dialogue_chart'],
 ['大模型与TTS','A1:H26','04_llm_tables'],['大模型与TTS','A29:H54','04_tts_chart'],
 ['FPGA与转轴','A1:H34','05_fpga_tables'],['FPGA与转轴','A36:H62','05_fpga_chart'],
 ['后续测试','A1:F16','06_test_plan'],['原始数据','A1:G18','07_raw'],['原始数据',`I2:M${sourceStart+data.sources.length}`,'07_sources']
];
for(const [name,range,file] of views){
 const preview=await wb.render({sheetName:name,range,scale:1.4,format:'png'});
 await fs.writeFile(path.join(qa,file+'.png'),new Uint8Array(await preview.arrayBuffer()));
}
const output=await SpreadsheetFile.exportXlsx(wb);
const file=path.join(root,'技术文档材料清单与性能表.xlsx');await output.save(file);
const sample=await wb.inspect({kind:'region',sheetId:'DPU与视觉',range:'A5:H7',maxChars:2500,tableMaxRows:4,tableMaxCols:8});
await fs.writeFile(path.join(root,'workbook_key_results.json'),JSON.stringify({sample:sample.ndjson,rtf_initial:initial,rtf_recalculation_verified:Math.abs(changed-initial*2)<1e-9,sheet_count:names.length,previews:views.length},null,2));
console.log(JSON.stringify({output:file,sheets:names.length,numeric_observations:data.metrics.length,preview_count:views.length,rtf_recalculated:true}));
