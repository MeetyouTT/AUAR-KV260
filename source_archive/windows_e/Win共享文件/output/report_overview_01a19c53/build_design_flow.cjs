const fs = require('fs');
const path = require('path');
const sharp = require('C:/Users/REVO1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const out = 'E:/Win共享文件/output/report_overview_01a19c53';
const W=1800,H=950;
const nodes=[
 {n:'01',x:65,y:145,t:'需求与指标分析',s:'明确功能范围|制定测试指标'},
 {n:'02',x:505,y:145,t:'系统架构设计',s:'划分板端职责|定义主机接口'},
 {n:'03',x:945,y:145,t:'FPGA平台开发',s:'集成DPU|加入运动监督IP'},
 {n:'04',x:1385,y:145,t:'视觉模型部署',s:'模型适配与量化|验证板端推理'},
 {n:'05',x:1385,y:540,t:'语音与界面开发',s:'语音识别与回答|完成播放与显示'},
 {n:'06',x:945,y:540,t:'外设与转轴联调',s:'连接相机与显示|验证单轴跟随'},
 {n:'07',x:505,y:540,t:'性能测试与优化',s:'设置对照试验|测量并修正问题'},
 {n:'08',x:65,y:540,t:'版本整理与验收',s:'统一版本与材料|补齐整机验收'}
];
const bw=350,bh=250;
let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M 0 0 L 9 5 L 0 10 Z" fill="#39465a"/></marker></defs><rect width="100%" height="100%" fill="white"/><g font-family="Microsoft YaHei,SimHei,sans-serif"><text x="900" y="70" text-anchor="middle" font-size="46" font-weight="700" fill="#111827">AUAR·雪妃 作品设计流程</text>`;
const lines=[ [415,270,505,270],[855,270,945,270],[1295,270,1385,270],[1560,395,1560,540],[1385,665,1295,665],[945,665,855,665],[505,665,415,665] ];
for(const [x1,y1,x2,y2] of lines) svg+=`<path d="M ${x1} ${y1} L ${x2} ${y2}" fill="none" stroke="#39465a" stroke-width="3" marker-end="url(#arrow)"/>`;
for(const a of nodes){
 svg+=`<g transform="translate(${a.x} ${a.y})"><rect x="0" y="0" width="${bw}" height="${bh}" rx="12" fill="#f7f9fc" stroke="#52637c" stroke-width="2"/><text x="24" y="39" font-size="22" fill="#52637c">${a.n}</text><text x="175" y="105" text-anchor="middle" font-size="40" font-weight="700" fill="#111827">${a.t}</text><text x="175" y="168" text-anchor="middle" font-size="32" fill="#374151">${a.s.split("|")[0]}</text><text x="175" y="215" text-anchor="middle" font-size="32" fill="#374151">${a.s.split("|")[1]}</text></g>`;
}
svg+=`<text x="900" y="885" text-anchor="middle" font-size="28" fill="#374151">按研发步骤组织，具体实现与测试证据在后续章节展开</text></g></svg>`;
const svgPath=path.join(out,'overview_design_flow.svg');
fs.writeFileSync(svgPath,svg,'utf8');
sharp(Buffer.from(svg),{density:192}).resize({width:3600}).png().toFile(path.join(out,'overview_design_flow.png')).then(()=>{process.stdout.write(JSON.stringify({svg:svgPath,png:path.join(out,'overview_design_flow.png'),width:3600})+'\n');}).catch(e=>{process.stderr.write(String(e));process.exitCode=1;});
