const fs=require('fs');
const path=require('path');
const sharp=require('C:/Users/REVO1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root='E:/Win共享文件/协作任务/2026-11-02_作品概述_AMD实跑_01a19c53';
const figures=path.join(root,'report_figures');
fs.copyFileSync(path.join(root,'gui/actual_block_design.svg'),path.join(figures,'03_vivado_block_design.svg'));
fs.copyFileSync(path.join(root,'gui/xsim_wave_panel.png'),path.join(figures,'05_xsim_native_wave_panel.png'));
fs.copyFileSync(path.join(root,'gui/vivado_block_design_native.png'),path.join(figures,'03_vivado_block_design_native.png'));
(async()=>{
 for(const file of fs.readdirSync(figures).filter(n=>n.endsWith('.svg'))){
  if(file==='06_design_workflow.svg')continue;
  const width=file.startsWith('03_')?4800:3000;
  const output=path.join(figures,file.replace(/\.svg$/,'.png'));
  await sharp(path.join(figures,file),{density:180,limitInputPixels:100000000}).resize({width}).png().toFile(output);
  process.stdout.write(JSON.stringify({file:path.basename(output),width})+'\n');
 }
})().catch(e=>{process.stderr.write(String(e));process.exitCode=1;});
