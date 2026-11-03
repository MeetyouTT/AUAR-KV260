import { chromium } from 'file:///C:/Users/REVO1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import fs from 'node:fs/promises';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const here=path.dirname(fileURLToPath(import.meta.url));
const data=JSON.parse(await fs.readFile(path.join(here,'timeline.json'),'utf8'));
const qa=path.join(here,'qa');await fs.mkdir(qa,{recursive:true});
const browser=await chromium.launch({channel:'msedge',headless:true,args:['--hide-scrollbars','--disable-extensions']});
const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto(pathToFileURL(path.join(here,'video-source.html')).href);
await page.waitForFunction(()=>window.__videoReady===true);
const samples=[];
for(const [i,s]of data.scenes.entries()){
  for(const [label,local] of [['wide',.1],['focus',Math.min(s.cameraIn+2,s.cameraOut-.2)]]){
    const time=s.start+local;
    const info=await page.evaluate(t=>window.renderVideoFrame(t),time);
    const measured=await page.evaluate(()=>{
      const root=document.getElementById('aura-dialogue-dataflow'),svg=root.querySelector('#ad-svg');
      const frame=svg.getBoundingClientRect(),state=root.__animation.get();
      const overflow=[];
      for(const id of state.focus){
        const n=root.querySelector(`[data-node="${id}"] > rect`),r=n.getBoundingClientRect();
        if(r.left<frame.left-.5||r.right>frame.right+.5||r.top<frame.top-.5||r.bottom>frame.bottom+.5)overflow.push(id);
      }
      const textOverflow=[];
      for(const n of root.querySelectorAll('.ad-node')){
        const r=n.querySelector('rect').getBBox();
        for(const text of n.querySelectorAll('text')){
          const b=text.getBBox();
          if(b.width>r.width-10)textOverflow.push({node:n.dataset.node,text:text.textContent,width:b.width,available:r.width});
        }
      }
      const caption=document.getElementById('video-caption').getBoundingClientRect();
      return {root:[root.offsetWidth,root.offsetHeight],svg:[frame.x,frame.y,frame.width,frame.height],overflow,textOverflow,captionHeight:caption.height,bodyOverflow:document.documentElement.scrollWidth>1920||document.documentElement.scrollHeight>1080};
    });
    await page.screenshot({path:path.join(qa,`${i+1}-${label}.png`)});
    samples.push({time,label,info,measured});
  }
}
await page.evaluate(()=>window.renderVideoFrame(window.__timeline.duration-.01));
await page.screenshot({path:path.join(qa,'end.png')});
const start=performance.now();
const session=await page.context().newCDPSession(page);
let bytes=0;
for(let i=0;i<20;i++){
  await page.evaluate(t=>window.renderVideoFrame(t),86+i/30);
  const r=await session.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false,fromSurface:true,optimizeForSpeed:true});
  bytes+=Buffer.byteLength(r.data,'base64');
}
const speed={frames:20,seconds:(performance.now()-start)/1000,bytes};
await browser.close();
const result={errors,speed,samples};
await fs.writeFile(path.join(qa,'visual-check.json'),JSON.stringify(result,null,2));
console.log(JSON.stringify({errors,speed,issues:samples.filter(s=>s.measured.overflow.length||s.measured.textOverflow.length||s.measured.bodyOverflow),duration:data.duration},null,2));
if(errors.length||samples.some(s=>s.measured.overflow.length||s.measured.textOverflow.length||s.measured.bodyOverflow))process.exitCode=1;
