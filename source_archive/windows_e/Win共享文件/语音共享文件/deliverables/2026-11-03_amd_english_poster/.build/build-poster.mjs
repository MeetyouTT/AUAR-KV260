import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { FileBlob, PresentationFile } from '@oai/artifact-tool';

const here = path.dirname(fileURLToPath(import.meta.url));
const workspaceDir = path.dirname(here);
const skillDir = 'C:/Users/REVO1/.codex/plugins/cache/openai-primary-runtime/presentations/26.1026.10807/skills/presentations';
const python = 'C:/Users/REVO1/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const template = path.join(here, 'template-original.pptx');
const revision = process.argv[2] ?? 'v1';
const C = { ink:'#20262E', grey:'#2F2F2F', muted:'#5B6470', line:'#D6DCE5', blue:'#3E789F', blueFill:'#EEF7FC', purple:'#87719C', purpleFill:'#F5F0FA', amber:'#96712D', amberFill:'#FFF7E7' };
const fontPolicy = {
  basis:'reference', families:['Times New Roman','Calibri','Aharoni','Arial','微软雅黑'],
  scriptFonts:{ea:'微软雅黑'}, referencePath:template,
  referenceSha256:createHash('sha256').update(await fs.readFile(template)).digest('hex'),
};
const p = await PresentationFile.importPptx(await FileBlob.load(template));
p.view.hideGridlines();
p.view.hideGuides();
p.view.hidePlaceholders();
const en = p.resolve('sl/y90nupkv');
const localized = new Map();
const B = 14.6667;
const pos = (left,top,width,height)=>({left,top,width,height});
function style(shape, {size=B,bold=false,color=C.ink,font='Calibri',align='left',vertical='top',insets=0}={}) {
  shape.text.style = {fontSize:size,typeface:font,bold,color,alignment:align,verticalAlignment:vertical,wrap:'square',autoFit:'none',insets,lineSpacing:1.08};
}
function localize(shape, name, english, chinese, opts={}) {
  shape.name=name;
  shape.text=name==='project-overview'?english:english.split('\n').map(run=>({runs:[run],spaceBefore:0,spaceAfter:0}));
  style(shape,opts);
  localized.set(name,{english,chinese,opts});
  return shape;
}
function text(name, english, chinese, frame, opts={}) {
  const s=en.shapes.add({geometry:'textbox',name,position:frame,fill:'none',line:{fill:'none',width:0}});
  return localize(s,name,english,chinese,opts);
}
function box(name, english, chinese, frame, fill, color, opts={}) {
  const s=en.shapes.add({geometry:'roundRect',name,position:frame,fill,line:{fill:color,width:1},borderRadius:6});
  return localize(s,name,english,chinese,{align:'center',vertical:'middle',insets:5,...opts});
}
function arrow(a,b,color=C.muted,both=false) {
  const s=en.shapes.connect(a,b,{kind:'straight',fromSide:'right',toSide:'left',line:{fill:color,width:1.3},tail:{type:'triangle',width:'sm',length:'sm'},...(both?{head:{type:'triangle',width:'sm',length:'sm'}}:{})});
  s.name=`flow-${a.name}-${b.name}`;
  return s;
}

// Reuse the supplied slide, its theme, master, three-column structure and AMD marks.
// The samples and yellow editing instructions belong to the source template only.
p.delete([
  'im/43elgf2p','im/21c3e5kj','im/gzulcv2d','im/felkjq1s',
  'sh/buh0nqtg','sh/at8zelcb','sh/8zqx4vq9','sh/t0jyd0ru','sh/6x8f2583',
  'sh/7yhgbq9o','sh/kvqx0vqd','sh/lwzy90ry','sh/yt8fyl87',
]);

const title=p.resolve('sh/utg3698n');
title.position=pos(28,32,590,78);
localize(title,'project-title','AUAR\nFPGA Multimodal Companion','AUAR·雪妃\nFPGA 多模态交互系统',{size:32,font:'Times New Roman',bold:true});

const intro=p.resolve('sh/fu94fe98');
localize(intro,'introduction-header','INTRODUCTION','项目简介',{font:'Aharoni',size:24,bold:true,color:'#FFFFFF',align:'center',vertical:'middle'});

// The two identity text boxes are deliberately empty and remain editable.
for (const [id,name] of [['sh/432dwn6l','team-members-blank'],['sh/vyp0je1s','school-and-adviser-blank']]) {
  const s=p.resolve(id); s.name=name; s.text=''; style(s,{size:16,font:'Times New Roman'});
}

const body=p.resolve('sh/sryl4zqx');
body.position=pos(28,177,360,96);
localize(body,'project-overview',
  'AUAR is a multimodal companion built on AMD KV260. It combines on-board visual perception and speech interaction with local Windows language-model and voice services.',
  'AUAR·雪妃基于 AMD KV260，将板端视觉感知、语音交互与局域网 Windows 大语言模型及语音合成服务协同，完成感知、理解和表达。');

const see=box('application-sense','See + hear','视觉 + 语音',pos(28,285,108,53),C.blueFill,C.blue);
const understand=box('application-reason','Understand','理解与决策',pos(153,285,108,53),C.purpleFill,C.purple);
const respond=box('application-express','Speak + move','表达 + 随动',pos(278,285,108,53),C.amberFill,C.amber);
arrow(see,understand); arrow(understand,respond);
const application=p.resolve('sh/hofulsf2');
application.position=pos(28,349,360,30);
localize(application,'application-caption','One board owns the interaction','由板端统一编排交互流程',{bold:true,align:'center'});

text('goals-heading','Key engineering goals','关键设计目标',pos(28,397,360,25),{bold:true,size:16});
text('goals-body',
  'Share one DPU across detection and face identity.\nTrigger speech without a wake word.\nKeep dialogue, memory and playback on board.\nConstrain actuation with custom RTL.',
  '单个 DPU 共享执行目标检测与人脸识别。\n无需唤醒词，语音活动触发对话。\n对话、记忆和播放由板端统一管理。\n自研 RTL 约束转轴命令与输出。',
  pos(28,431,360,104));
text('implementation-heading','Ubuntu + Windows implementation','Ubuntu 与本地实现',pos(28,559,360,25),{bold:true,size:16});
text('implementation-body',
  'Vivado / Vitis 2022.2 on Ubuntu.\nBoard-side ASR, GUI and orchestration.\nWindows: 27B LLM + OmniVoice16 inference.\nThree reusable validation / optimization workflows.',
  'Ubuntu：Vivado / Vitis 2022.2 工程与验证。\n板端：ASR、界面、上下文与任务编排。\nWindows：27B LLM 与 OmniVoice16 推理。\n沉淀三套可复用验证及优化工作流。',
  pos(28,593,360,97));

// Repaint the source divider strokes explicitly after import.
for (const id of ['sh/ul4vaxgb','sh/vmdcj2xw','sh/4r6dg7et']) {
  p.resolve(id).line={fill:'#000000',width:1.3333,style:'solid'};
}
// Correct the spelling in the supplied DESIGN strip.
p.resolve('sh/dgzetcfa').text='G';
p.resolve('sh/1cvuxc7e').text='N';

text('architecture-heading','System architecture','系统架构',pos(443,119,350,27),{bold:true,size:16,align:'center'});
const board=en.shapes.add({geometry:'roundRect',name:'kv260-boundary',position:pos(443,154,218,187),fill:'#FFFFFF',line:{fill:C.blue,width:1.3},borderRadius:7});
text('board-title','AMD KV260 · PS + PL','AMD KV260 · PS + PL',pos(452,163,200,24),{bold:true,align:'center',color:C.blue});
box('board-input','Camera + microphone','相机 + 麦克风',pos(453,194,198,29),C.blueFill,C.blue);
const processing=box('board-process','PL: vision | PS: VAD + ASR\nPS context + tracking','PL: 视觉 | PS: VAD + ASR\nPS 上下文与目标跟踪',pos(453,233,198,45),C.purpleFill,C.purple);
const output=box('board-output','Speaker + avatar | RTL/PWM\nSingle-axis target following','扬声器 + 形象 | RTL/PWM\n单轴目标跟随',pos(453,288,198,42),C.amberFill,C.amber);
for(const y of [224,279]) en.shapes.add({geometry:'downArrow',name:`board-flow-${y}`,position:pos(548,y,8,8),fill:C.muted,line:{fill:'none',width:0}});
en.shapes.add({geometry:'roundRect',name:'windows-boundary',position:pos(693,154,105,187),fill:'#FFFFFF',line:{fill:C.purple,width:1.3},borderRadius:7});
text('windows-title','Windows','Windows',pos(697,164,97,21),{bold:true,align:'center',color:C.purple});
text('windows-scope','Inference only','仅负责推理',pos(697,187,97,28),{align:'center'});
const llm=box('windows-llm','27B LLM','27B LLM',pos(701,226,89,37),C.purpleFill,C.purple);
const tts=box('windows-tts','OmniVoice\nTTS','OmniVoice\nTTS',pos(701,280,89,48),C.blueFill,C.blue);
// Independent request/return links: the board, not Windows, calls LLM and TTS.
for(const [name,y,color] of [['llm',245,C.purple],['tts',305,C.blue]]) en.shapes.add({geometry:'connector',kind:'straight',name:`independent-${name}-rpc`,position:pos(663,y,28,0),line:{fill:color,width:1.3},head:{type:'triangle',width:'sm',length:'sm'},tail:{type:'triangle',width:'sm',length:'sm'}});
text('lan-label','LAN','LAN',pos(660,197,34,25),{size:12,align:'center',color:C.muted});

const archCaption=p.resolve('sh/036h8but');
archCaption.position=pos(443,361,350,30);
localize(archCaption,'dialogue-heading','Dialogue is orchestrated on KV260','KV260 编排对话与播放闭环',{bold:true,align:'center'});
const dialogue=p.resolve('sh/9sfylgbq');
dialogue.position=pos(443,403,344,165);
dialogue.fill='#FFFFFF'; dialogue.line={fill:'#000000',width:1.3333}; dialogue.borderRadius=24;
localize(dialogue,'dialogue-sequence',
  '1  VAD triggers Paraformer ASR on KV260.\n2  Text + context are sent to the Windows LLM.\n3  Validate reply_text, emotion and avatar_action; then request TTS.\n4  Speech + avatar playback → full ACK → history commit.',
  '1  VAD 触发板端 Paraformer ASR。\n2  文本和上下文 → Windows LLM。\n3  板端校验回复文本、情绪和形象动作，再单独调用 TTS。\n4  同步播放；收到完整回执后提交历史。',
  {insets:{left:14,right:14,top:14,bottom:10}});
const motion=p.resolve('sh/mpozalcz');
motion.position=pos(443,584,344,107);
motion.fill='#FFFFFF'; motion.line={fill:'#000000',width:1.3333}; motion.borderRadius=18;
localize(motion,'motion-design',
  'Perception + bounded motion\nOne B4096 DPU shares 3 vision models.\nPS tracking → RTL checks → PWM.\nSession / sequence / rate / lease checks.',
  '视觉感知与受约束的运动控制\n一个 B4096 DPU 共享三个视觉模型。\nPS 跟踪 → RTL 校验 → PWM 输出。\n校验会话、序号、速率及命令租约。',
  {insets:{left:14,right:14,top:11,bottom:8}});

// Replace the sample product photograph with an editable reserved area.
const photo=en.shapes.add({geometry:'rect',name:'prototype-photo-reserved',position:pos(1087,14,168,141),fill:'#F8F9FB',line:{fill:'#A8ADB6',width:1,style:'dashed'}});
localize(photo,'prototype-photo-reserved','PROTOTYPE PHOTO\nReserved','实物照片\n待补充',{align:'center',vertical:'middle',color:C.muted});
const platform=p.resolve('sh/uxgjq907');
platform.position=pos(1055,171,208,23);
localize(platform,'hardware-platform','AMD KV260 + local Windows','AMD KV260 + 本地 Windows',{font:'Times New Roman',size:13.3333,bold:true,align:'center'});

text('performance-heading','Measured performance','实测性能',pos(947,220,308,26),{size:16,bold:true});
const valuesEN=[['Metric','Observed'],['YOLOX service rate','9.907 /s'],['YuNet service rate','9.862 /s'],['SFace service rate','0.740 /s'],['LLM full RPC','1.837 s'],['TTS full RPC','0.718 s']];
const valuesCN=[['测量项','观测结果'],['YOLOX 服务计数频率','9.907 /s'],['YuNet 服务计数频率','9.862 /s'],['SFace 服务计数频率','0.740 /s'],['LLM 完整 RPC','1.837 s'],['TTS 完整 RPC','0.718 s']];
const table=en.tables.add({rows:6,columns:2,left:947,top:253,width:308,height:192,columnWidths:[211,97],values:valuesEN});
table.name='performance-table';
table.styleOptions={headerRow:false,bandedRows:false};
table.borders.assign({fill:C.line,width:0.8,style:'solid'});
for(let r=0;r<6;r++) {
  table.rows[r].height=32;
  for(let c=0;c<2;c++) {
    const cell=table.getCell(r,c);
    cell.fill=r===0?C.grey:(r%2===0?'#F6F7F9':'#FFFFFF');
    cell.text.style={fontSize:B,typeface:'Calibri',bold:r===0||c===1,color:r===0?'#FFFFFF':C.ink,verticalAlignment:'middle',alignment:c===1?'center':'left',insets:{left:8,right:6,top:4,bottom:4},autoFit:'none',wrap:'square'};
  }
}
text('measurement-scope',
  'Vision: 179.77 s observation; service counts, not peak FPS.\nLLM/TTS: medians of 5 warm RPCs; excludes speech capture and playback.',
  '视觉：179.77 秒服务计数观测，非峰值 FPS。\nLLM/TTS：各 5 次暖态 RPC 的中位数；不含语音采集及播放。',
  pos(947,460,308,79),{color:C.muted});
text('verification-heading','Reproducible engineering','可复现的工程验证',pos(912,558,343,26),{size:16,bold:true});
const evidence=p.resolve('sh/e1oz61c3');
evidence.position=pos(912,594,343,98);
localize(evidence,'verification-body',
  'Ubuntu 20.04.4 / Python 3.8.10:\n9/9 offline checks on one CPU core.\n4 RTL/XSim testbenches passed.\n4 firmware files matched byte-for-byte.\nExport used routed DCP, not fresh P&R.',
  'Ubuntu 20.04.4 / Python 3.8.10：\n单 CPU 核心离线复核，9/9 项通过。\n4 套 RTL/XSim 测试台通过。\n4 个固件文件与原部署逐字节一致。\n基于 routed DCP 导出，未重跑综合布线。');

// Remove the inherited copyright-year editing placeholder, while retaining
// inherited AMD branding and the source page-number treatment.
for (const surface of [...p.masters.items,...p.layouts.items]) {
  for (const shape of surface.shapes.items) {
    if (String(shape.text).includes('Copyright') || String(shape.text).includes('<Year>')) shape.text='';
    // Source master connectors are nonprinting author guides. The importer
    // exposes their fallback strokes, so restore their nonprinting appearance.
    if(['line','connector'].includes(shape.geometry) && /^Straight Connector /u.test(shape.name ?? '')) {
      shape.fill='none'; shape.line={fill:'none',width:0};
    }
  }
}

const sources=[
  'Content sources (local project evidence; no new device actions were performed):',
  'E:/AUAR_工程交付_20261102/aura/readme.md',
  'E:/AUAR_工程交付_20261102/aura/report/release_status.md',
  'E:/AUAR_工程交付_20261102/aura/report/performance_metrics.csv',
  'E:/AUAR_工程交付_20261102/aura/report/performance_addendum.txt',
  'E:/AUAR_工程交付_20261102/先读_交付与核验.txt',
  'E:/AUAR_工程交付_20261102/verification/extracted_single_core.txt',
  'E:/AUAR_工程交付_20261102/verification/vivado_prepare.json',
  'E:/AUAR_工程交付_20261102/verification/vivado_export.json',
  'Template: C:/Users/REVO1/Documents/deepseek-harness/default-workspace/snowluma-export-fpga/submission/attachments/AMD_poster_template.pptx',
  "Guide: C:/Users/REVO1/Downloads/全国大学生嵌入式芯片与系统设计竞赛'2026FPGA赛道选题指南-AMD.pdf; final PDF page 28 / printed page 25.",
  '',
  'Metric scope: vision service counter deltas over 179.773885 s (not isolated maximum FPS): YOLOX 1781, YuNet 1773, SFace 133 calls. LLM full RPC median 1.837 s and TTS full RPC median 0.718 s are 5 warm requests each, include network/admission/full response, and exclude speech capture/playback; no end-to-end acoustic-latency claim. Listening and following were paused during the benchmark. These data do not establish full-system endurance acceptance.',
  'Windows performs inference only. KV260 controls dialogue, validates reply_text/emotion/avatar_action, calls TTS independently, and commits assistant history only after a complete matching playback ACK. Visual perception and voice are independent. Custom RTL checks command admissibility before PWM; Windows does not drive the actuator directly.',
  'Reproduction used Ubuntu 20.04.4, Python 3.8.10, one CPU core: all 9 offline checks passed. Four RTL/XSim testbenches passed. Four firmware files were re-exported byte-identically from the original routed DCP; no fresh full synthesis/place-and-route run is claimed. Three reusable workflows: command_guard_validation, perception_freshness_benchmark, llm_voice_runtime_optimization.',
  'School, team members and adviser are intentionally blank per user. Prototype photo is reserved for a later real photograph. English first, Chinese second per teacher instruction. Photo replacement does not require changing the editable architecture or data table.',
].join('\n');
en.speakerNotes.text='English poster\n'+sources;
const cn=en.duplicate();
cn.moveTo(1);
for (const s of cn.shapes.items) {
  const entry=localized.get(s.name);
  if(entry) {
    s.text=s.name==='project-overview'?entry.chinese:entry.chinese.split('\n').map(run=>({runs:[run],spaceBefore:0,spaceAfter:0}));
    // Preserve the template Latin font; use an installed CJK family for Chinese.
    const hasCJK=/[\u3400-\u9fff]/u.test(entry.chinese);
    style(s,{...entry.opts,...(hasCJK?{font:'微软雅黑'}:{})});
  }
}
for (const t of cn.tables.items) {
  for(let r=0;r<6;r++)for(let c=0;c<2;c++) {
    const cell=t.getCell(r,c); cell.value=valuesCN[r][c];
    cell.text.style={fontSize:B,typeface:'微软雅黑',bold:r===0||c===1,color:r===0?'#FFFFFF':C.ink,verticalAlignment:'middle',alignment:c===1?'center':'left',insets:{left:8,right:6,top:4,bottom:4},autoFit:'none',wrap:'square'};
  }
}
// Translate the source's stacked section letters in place, keeping its strips.
const designIds=['TextBox 20','TextBox 21','TextBox 22','TextBox 23','TextBox 24','TextBox 25','TextBox 26','TextBox 27','TextBox 14','TextBox 15','TextBox 16','TextBox 17','TextBox 18','TextBox 19'];
for(let i=0;i<designIds.length;i++) {
  const s=cn.shapes.items.find(s=>s.name===designIds[i]);
  if(i<4){s.text=['创','新','设','计'][i];s.position=pos(818,272+i*52,31,42);style(s,{size:24,font:'微软雅黑',color:'#FFFFFF',align:'center',vertical:'middle'});} else s.text='';
}
for(let i=0;i<6;i++) {
  const s=cn.shapes.items.find(s=>s.name===`TextBox ${32+i}`);
  if(i<4){s.text=['测','试','结','果'][i];s.position=pos(897,230+i*38,32,40);style(s,{size:24,font:'微软雅黑',color:'#FFFFFF',align:'center',vertical:'middle'});} else s.text='';
}
cn.speakerNotes.text='中文海报\n'+sources;

await fs.writeFile(path.join(here,`poster-${revision}.inspection.ndjson`),(await p.inspect({kind:'slide,textbox,shape,image,table',maxChars:120000})).ndjson);
for (let i=0;i<p.slides.items.length;i++) {
  const s=p.slides.items[i];
  await fs.writeFile(path.join(here,`poster-${revision}-${i+1}.png`),new Uint8Array(await (await p.export({slide:s,format:'png',scale:1.5})).arrayBuffer()));
  await fs.writeFile(path.join(here,`poster-${revision}-${i+1}.layout.json`),new Uint8Array(await (await s.export({format:'layout'})).arrayBuffer()));
}
const candidatePath=path.join(here,`poster-${revision}.candidate.pptx`);
await (await PresentationFile.exportPptx(p)).save(candidatePath);
if(process.env.AUAR_FINALIZE==='1') {
  const {finalizePresentation}=await import(pathToFileURL(path.join(skillDir,'container_tools/artifact_tool_utils.mjs')).href);
  const finalPath=path.join(workspaceDir,'output','auar_amd_poster_en_cn.pptx');
  const receiptPath=path.join(here,`poster-${revision}.validation.json`);
  await finalizePresentation({explicitTotalSlideCount:2,workspaceDir,candidatePath,finalPath,pythonExecutable:python,
    integrityValidatorPath:path.join(skillDir,'container_tools/inspect_presentation_package_integrity.py'),
    layoutValidatorPath:path.join(skillDir,'container_tools/inspect_presentation_layout_geometry.py'),
    layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','1','--require-native-table-slide','2'],
    requiredNativeTableOwnerSlides:[1,2],fontPolicy,verifyArtifactToolImport:true,receiptPath});
  console.log(JSON.stringify({finalPath,receiptPath}));
} else console.log(JSON.stringify({candidatePath,slides:p.slides.items.length}));
