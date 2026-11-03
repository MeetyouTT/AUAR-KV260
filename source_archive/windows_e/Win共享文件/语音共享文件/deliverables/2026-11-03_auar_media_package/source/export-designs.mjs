import {chromium} from 'file:///C:/Users/REVO1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';

const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const browser=await chromium.launch({channel:'msedge',headless:true,args:['--hide-scrollbars','--disable-extensions']});
const errors=[],bounds=[];
const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:2});
page.on('pageerror',e=>errors.push(e.message));
const covers=[['cover-main.svg','AUAR_视频总封面.png'],['cover-01-photo.svg','01_实物照片_章节封面.png'],['cover-02-principle.svg','02_原理讲解_章节封面.png'],['cover-03-demo.svg','03_实机效果_章节封面.png']];
async function inspect(page,w,h,name){
  const issues=await page.evaluate(({w,h})=>[...document.querySelectorAll('text')].map(n=>({text:n.textContent,b:n.getBoundingClientRect().toJSON()})).filter(({b})=>b.x<0||b.y<0||b.right>w+.5||b.bottom>h+.5),{w,h});
  bounds.push({file:name,issues});
}
for(const [input,output]of covers){
  await page.goto(pathToFileURL(path.join(root,'source',input)).href);
  await page.evaluate(()=>document.fonts.ready);
  await inspect(page,1920,1080,input);
  await page.screenshot({path:path.join(root,'output','covers',output)});
}
const small=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
for(const [input]of covers){
  await small.goto(pathToFileURL(path.join(root,'source',input)).href);
  await small.evaluate(()=>document.fonts.ready);
  await small.screenshot({path:path.join(root,'.build','qa',input.replace('.svg','-1080.png'))});
}
const poster=await browser.newPage({viewport:{width:1400,height:1980},deviceScaleFactor:3508/1400});
poster.on('pageerror',e=>errors.push(e.message));
await poster.goto(pathToFileURL(path.join(root,'source','poster-a3.svg')).href);
await poster.evaluate(()=>document.fonts.ready);
await inspect(poster,1400,1980,'poster-a3.svg');
await poster.screenshot({path:path.join(root,'output','poster','AUAR_项目海报_A3_300dpi.png')});
const preview=await browser.newPage({viewport:{width:1400,height:1980},deviceScaleFactor:1});
await preview.goto(pathToFileURL(path.join(root,'source','poster-a3.svg')).href);
await preview.evaluate(()=>document.fonts.ready);
await preview.screenshot({path:path.join(root,'.build','qa','poster-preview.png')});
const contact=await browser.newPage({viewport:{width:1920,height:1200},deviceScaleFactor:1});
const sourceLinks=covers.map(([,name])=>pathToFileURL(path.join(root,'output','covers',name)).href);
const contactHtml=`<html><head><meta charset="UTF-8"><style>html,body{margin:0;background:#eef4fb;font-family:'Microsoft YaHei UI',sans-serif}h1{margin:0;position:absolute;left:64px;top:30px;font-size:32px;font-weight:500;color:#25435f}.grid{position:absolute;left:64px;top:108px;display:grid;grid-template-columns:864px 864px;gap:44px 64px}img{width:864px;height:486px;display:block;border:1px solid #d4e2ef;box-sizing:border-box}</style></head><body><h1>AUAR · 封面与章节视觉</h1><div class="grid">${sourceLinks.map(url=>`<img src="${url}">`).join('')}</div></body></html>`;
const contactPath=path.join(root,'.build','qa','contact.html');
await fs.writeFile(contactPath,contactHtml);await contact.goto(pathToFileURL(contactPath).href);
await contact.evaluate(()=>Promise.all([...document.images].map(i=>i.decode())));
await contact.screenshot({path:path.join(root,'output','covers','AUAR_四款封面一览.png')});
await browser.close();
const report={errors,bounds,cover_pixels:[3840,2160],poster_pixels:[3508,4961]};
await fs.writeFile(path.join(root,'.build','qa','design-check.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));
if(errors.length||bounds.some(b=>b.issues.length))process.exitCode=1;
