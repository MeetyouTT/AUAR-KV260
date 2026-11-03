"use strict";
const audio=document.querySelector('#audio'),canvas=document.querySelector('#stage'),ctx=canvas.getContext('2d');
const play=document.querySelector('#play'),replay=document.querySelector('#replay'),seek=document.querySelector('#seek');
const label=document.querySelector('#label'),text=document.querySelector('#text'),load=document.querySelector('#load'),clock=document.querySelector('#clock'),error=document.querySelector('#error');
let timeline=null,sheets=[],lastFrame=-1,records=[],lastWall=null,lastAudio=null,pausedBaseline=null,lastDiagnostics=0;
const stateNames={IDLE:'待机',PRESENT:'来访待机',AWAKE:'唤醒',LISTENING:'聆听',THINKING:'思考',ACK_NOD:'点头',SPEAKING_NEUTRAL:'中性说话',SPEAKING:'兴奋说话',SPEAKING_LOW:'低落与安慰'};
function draw(){
  if(!timeline)return;
  const t=Math.min(audio.currentTime,timeline.duration),index=Math.min(timeline.samples.length-1,Math.floor(t*timeline.fps+1e-7));
  if(index!==lastFrame){
    const per=timeline.columns*timeline.rows,slot=index%per,img=sheets[Math.floor(index/per)];
    ctx.drawImage(img,(slot%timeline.columns)*timeline.width,Math.floor(slot/timeline.columns)*timeline.height,timeline.width,timeline.height,0,0,canvas.width,canvas.height);
    const row=timeline.samples[index],utterance=timeline.utterances.find(u=>t>=u.start&&t<u.end);
    label.textContent=utterance?.label||stateNames[row.display_state]||'准备中';
    const cancelled=timeline.utterances.find(u=>u.interrupted&&t>=u.end&&t<u.end+.65);
    text.textContent=utterance?.text||(cancelled?'语音已打断，正在平滑收口。':t>=timeline.duration-.1?'演出结束，可以重播或选择一个场景。':t===0&&audio.paused?'点击开始演示，或选择一个场景。':'');
    const now=performance.now();
    if(!audio.paused&&lastWall!==null&&t>=lastAudio){records.push({audioTime:t,frameTime:row.t,renderLagMs:(t-row.t)*1000,frameGapMs:now-lastWall,scene:row.scene,displayState:row.display_state,speechGain:row.speech_gain});if(records.length>10000)records.shift();}
    lastWall=now;lastAudio=t;lastFrame=index;
  }
  seek.value=String(t);clock.textContent=`${t.toFixed(1)} / ${timeline.duration.toFixed(1)} 秒`;
  canvas.dataset.frame=String(lastFrame);canvas.dataset.time=String(t);
  if(performance.now()-lastDiagnostics>500){document.querySelector('#diagnostics').textContent=JSON.stringify(window.auraDemoDiagnostics());lastDiagnostics=performance.now();}
}
function loop(){draw();requestAnimationFrame(loop);}
async function start(){try{await audio.play();}catch(e){error.textContent='未能播放，请检查音频输出后再点击开始。';}}
play.addEventListener('click',()=>audio.paused?start():audio.pause());
replay.addEventListener('click',()=>{audio.pause();audio.currentTime=0;lastFrame=-1;lastWall=null;records=[];draw();start();});
seek.addEventListener('input',()=>{audio.currentTime=Number(seek.value);lastWall=null;lastFrame=-1;draw();});
audio.addEventListener('play',()=>{play.textContent='暂停';lastWall=null;pausedBaseline=null;load.textContent='声音与画面同步播放中';});
audio.addEventListener('pause',()=>{play.textContent=audio.ended?'重新播放':'继续播放';pausedBaseline={audioTime:audio.currentTime,frame:lastFrame};lastWall=null;load.textContent=audio.ended?'演出完成':'已暂停，声音与画面停在同一时刻';});
audio.addEventListener('ended',()=>{lastFrame=-1;draw();play.textContent='重新播放';load.textContent='演出完成';});
audio.addEventListener('error',()=>{error.textContent='演出音频载入失败，请重新启动预览。';});
window.addEventListener('keydown',event=>{if(event.key==='F5'){event.preventDefault();replay.click();}});
// Read-only QA snapshot; no microphone, network telemetry or external upload.
window.auraDemoDiagnostics=()=>({ready:!!timeline&&sheets.length===timeline.sheets.length,audioTime:audio.currentTime,duration:audio.duration,paused:audio.paused,ended:audio.ended,audioError:audio.error?.code||null,currentFrame:lastFrame,pausedBaseline,records:records.slice()});
async function init(){
  const response=await fetch('timeline.json');if(!response.ok)throw Error('timeline');timeline=await response.json();
  canvas.width=timeline.width;canvas.height=timeline.height;seek.max=String(timeline.duration);
  let completed=0;sheets=await Promise.all(timeline.sheets.map(sheet=>new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>{completed++;load.textContent=`准备演出素材 ${completed} / ${timeline.sheets.length}`;resolve(img);};img.onerror=reject;img.src=sheet.file;})));
  audio.src=timeline.audio;audio.load();
  let chapter=0;
  timeline.utterances.forEach(u=>{const button=document.createElement('button');button.textContent=u.label;button.setAttribute('aria-label',`查看${u.label}`);button.addEventListener('click',()=>{audio.pause();audio.currentTime=Math.max(0,u.reply_at-.3);lastWall=null;lastFrame=-1;draw();start();});document.querySelector('.chapters').append(button);chapter++;});
  play.disabled=false;replay.disabled=false;seek.disabled=false;label.textContent='准备好了';text.textContent='点击开始演示，或选择一个场景。';load.textContent='演出素材已准备，播放会有声音。';draw();requestAnimationFrame(loop);
}
init().catch(e=>{error.textContent='素材准备失败，请重新启动预览。';load.textContent='载入失败';});
