import {chromium} from 'file:///C:/Users/REVO1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';

const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const runtime=JSON.parse(await fs.readFile(path.join(root,'.build','runtime.json'),'utf8'));
const target=path.join(root,'output','video','AUAR_片头_字标居中淡出_3秒.mp4');
const ff=spawn(runtime.ffmpeg,['-y','-v','error','-f','image2pipe','-vcodec','png','-framerate','30','-i','pipe:0','-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-r','30','-c:a','aac','-b:a','192k','-t','3','-movflags','+faststart','-metadata','title=AUAR 字标居中淡出片头',target],{windowsHide:true,stdio:['pipe','ignore','pipe']});
let err='';ff.stderr.on('data',b=>err+=b.toString());
ff.stdin.on('error',e=>{err+=e.message;});
const closed=once(ff,'close');
const browser=await chromium.launch({channel:'msedge',headless:true,args:['--hide-scrollbars','--disable-extensions']});
try{
  const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
  await page.goto(pathToFileURL(path.join(root,'source','opening.html')).href);
  await page.waitForFunction(()=>window.__openingReady);
  const session=await page.context().newCDPSession(page);
  const states=[];
  for(let i=0;i<90;i++){
    const state=await page.evaluate(t=>window.renderOpening(t),i/30);
    const r=await session.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false,fromSurface:true,optimizeForSpeed:true});
    const bytes=Buffer.from(r.data,'base64');
    if([0,54,87].includes(i)){states.push(state);await fs.writeFile(path.join(root,'.build','qa',`opening-${i}.png`),bytes);}
    if(!ff.stdin.write(bytes))await once(ff.stdin,'drain');
  }
  ff.stdin.end();const [code]=await closed;
  if(code!==0)throw Error(err);
  if(states[0].opacity!==1||states[1].opacity>=1||states[2].opacity!==0)throw Error('Fade sequence failed.');
  await fs.writeFile(path.join(root,'.build','qa','opening-check.json'),JSON.stringify({file:target,duration:3,frames:90,center:[960,540],states,errors:err},null,2));
  console.log(JSON.stringify({file:target,duration:3,frames:90,states}));
}finally{await browser.close();}
