import { chromium } from 'file:///C:/Users/REVO1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath,pathToFileURL } from 'node:url';

const here=path.dirname(fileURLToPath(import.meta.url));
const data=JSON.parse(await fs.readFile(path.join(here,'timeline.json'),'utf8'));
const destination=path.join(here,'rendered.mp4');
const start=performance.now();
const args=['-y','-v','error','-nostats','-f','image2pipe','-vcodec','png','-framerate',String(data.fps),'-i','pipe:0','-i',path.join(here,'narration-master.wav'),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-r',String(data.fps),'-c:a','aac','-b:a','192k','-ac','2','-ar','48000','-t',String(data.duration),'-movflags','+faststart','-metadata','title=AUAR·雪妃｜一轮对话的数据流','-metadata','comment=16:9 原理动画；通用合成女性解说；演示时序不代表实测耗时',destination];
const ff=spawn(data.ffmpeg,args,{windowsHide:true,stdio:['pipe','ignore','pipe']});
let ffError='';let inputError=null;
ff.stderr.on('data',b=>ffError+=b.toString());
ff.stdin.on('error',e=>{inputError=e;});
const exited=once(ff,'close');
let browser;
try{
  browser=await chromium.launch({channel:'msedge',headless:true,args:['--hide-scrollbars','--disable-extensions']});
  const page=await browser.newPage({viewport:{width:data.width,height:data.height},deviceScaleFactor:1});
  const jsErrors=[];page.on('pageerror',e=>jsErrors.push(e.message));
  await page.goto(pathToFileURL(path.join(here,'video-source.html')).href);
  await page.waitForFunction(()=>window.__videoReady===true);
  const session=await page.context().newCDPSession(page);
  for(let frame=0;frame<data.frames;frame++){
    if(inputError)throw inputError;
    await page.evaluate(t=>window.renderVideoFrame(t),frame/data.fps);
    const capture=await session.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false,fromSurface:true,optimizeForSpeed:true});
    if(!ff.stdin.write(Buffer.from(capture.data,'base64')))await once(ff.stdin,'drain');
    if(frame%300===0){
      const elapsed=(performance.now()-start)/1000;
      console.log(JSON.stringify({frame,total:data.frames,percent:Math.round(frame/data.frames*100),videoSeconds:Math.round(frame/data.fps),elapsedSeconds:Math.round(elapsed)}));
      await fs.writeFile(path.join(here,'render-progress.json'),JSON.stringify({frame,total:data.frames,elapsedSeconds:elapsed}));
    }
  }
  ff.stdin.end();
  const [code]=await exited;
  if(code!==0)throw Error(`ffmpeg exited ${code}: ${ffError}`);
  if(jsErrors.length)throw Error(jsErrors.join('\n'));
  const stat=await fs.stat(destination);
  const receipt={file:destination,bytes:stat.size,frames:data.frames,fps:data.fps,duration:data.duration,width:data.width,height:data.height,renderSeconds:(performance.now()-start)/1000,jsErrors,ffmpegError:ffError};
  await fs.writeFile(path.join(here,'render-result.json'),JSON.stringify(receipt,null,2));
  console.log(JSON.stringify(receipt,null,2));
}catch(error){
  ff.stdin.destroy();ff.kill();
  console.error(error);console.error(ffError);process.exitCode=1;
}finally{
  if(browser)await browser.close();
}
