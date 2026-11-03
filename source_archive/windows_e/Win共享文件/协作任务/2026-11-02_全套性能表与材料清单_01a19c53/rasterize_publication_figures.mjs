import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';
const root=path.dirname(fileURLToPath(import.meta.url));
const folder=path.join(root,'报告配图');
const names=['语音交互_两轮分段耗时','TTS_合成耗时与音频时长','系统资源_历史30秒CPU与DPU忙时','视觉质量_SFace误接收与误拒绝'];
for(const name of names){
  await sharp(await fs.readFile(path.join(folder,name+'.svg')),{density:144}).png().toFile(path.join(folder,name+'.png'));
}
console.log(JSON.stringify({png_figures_created:names.length,width:2000,height:1400}));
