"use strict";
const $=id=>document.getElementById(id),audio=$('audio'),canvas=$('stage'),ctx=canvas.getContext('2d');
let timeline,assets,sheets=[],mouthSheet,eyes={},mode='idle',lastFrame=-1,live=null,jobId=null,requestGeneration=0;
let boot=performance.now(),visualPausedAt=null,pausedTotal=0,freezeBlink=false,closing=null,records=[],lastRecord=0,lastDiagnostics=0;
let extensionSeed=20261007;
const eyeWork=document.createElement('canvas');eyeWork.width=99;eyeWork.height=38;
const mouthWork=document.createElement('canvas');mouthWork.width=464;mouthWork.height=480;
const names={IDLE:'待机',PRESENT:'来访待机',AWAKE:'唤醒',LISTENING:'聆听',THINKING:'思考',ACK_NOD:'点头',SPEAKING_NEUTRAL:'中性说话',SPEAKING:'兴奋说话',SPEAKING_LOW:'低落与安慰'};
const image=url=>new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>resolve(img);img.onerror=reject;img.src=url;});
function value(values,time,hop=.01){const p=Math.max(0,time/hop),i=Math.floor(p);if(i>=values.length)return 0;return values[i]+((values[i+1]??0)-values[i])*(p-i);}
function visualTime(){return ((visualPausedAt??performance.now())-boot-pausedTotal)/1000;}
function setVisualPause(paused){if(paused&&visualPausedAt===null)visualPausedAt=performance.now();if(!paused&&visualPausedAt!==null){pausedTotal+=performance.now()-visualPausedAt;visualPausedAt=null;}}
function drawKey(asset,slot,alpha=1){ctx.globalAlpha=alpha;ctx.drawImage(mouthSheet,slot%assets.columns*464,Math.floor(slot/assets.columns)*480,464,480,0,0,464,480);ctx.globalAlpha=1;}
function blink(asset,t){const b=assets.blink,name=b.aliases[asset]||asset,frames=eyes[name];if(!frames)return null;while(b.starts[b.starts.length-1]<=t){extensionSeed=(Math.imul(extensionSeed,1664525)+1013904223)>>>0;b.starts.push(b.starts[b.starts.length-1]+3.2+2.6*extensionSeed/4294967296);}let low=0,high=b.starts.length;while(low<high){const mid=(low+high)>>>1;if(b.starts[mid]<=t)low=mid+1;else high=mid;}const index=low-1;if(index<0)return null;const phase=t-b.starts[index];if(phase<0||phase>=b.duration)return null;let left=0;while(left+1<b.times.length&&b.times[left+1]<=phase)left++;const right=Math.min(left+1,b.times.length-1),fraction=left===right?0:(phase-b.times[left])/(b.times[right]-b.times[left]);const x=eyeWork.getContext('2d');x.clearRect(0,0,eyeWork.width,eyeWork.height);x.globalCompositeOperation='source-over';x.globalAlpha=1-fraction;x.drawImage(frames[left],0,0);x.globalCompositeOperation='lighter';x.globalAlpha=fraction;x.drawImage(frames[right],0,0);x.globalAlpha=1;x.globalCompositeOperation='source-over';ctx.drawImage(eyeWork,b.bounds[0],b.bounds[1]);return phase;}
function mouth(asset,level,gain){const keys=assets.mouths[asset];drawKey(asset,keys[0].slot);let right=keys.findIndex(k=>k.level>=level);if(right<0)right=keys.length-1;const left=Math.max(0,right-1),span=keys[right].level-keys[left].level,f=span?(level-keys[left].level)/span:0;if(gain>0){const x=mouthWork.getContext('2d');x.clearRect(0,0,464,480);for(const [key,a] of [[keys[left],1],[keys[right],f]]){x.globalAlpha=a;x.drawImage(mouthSheet,key.slot%assets.columns*464,Math.floor(key.slot/assets.columns)*480,464,480,0,0,464,480);}x.globalAlpha=1;ctx.globalAlpha=gain;ctx.drawImage(mouthWork,0,0);ctx.globalAlpha=1;}}
let currentState={};
function draw(){
  if(!assets||!timeline)return;
  const now=performance.now(),time=audio.currentTime;
  ctx.clearRect(0,0,464,480);let gain=0,level=0,asset='talking_calm_reuse_v1',blinkPhase=null,state='IDLE';
  if(mode==='script'){
    const index=Math.min(timeline.samples.length-1,Math.floor(Math.min(time,timeline.duration)*timeline.fps+1e-7)),per=timeline.columns*timeline.rows,slot=index%per,row=timeline.samples[index];
    ctx.drawImage(sheets[Math.floor(index/per)],slot%timeline.columns*timeline.width,Math.floor(slot/timeline.columns)*timeline.height,timeline.width,timeline.height,0,0,464,480);
    asset=row.asset;state=row.display_state;gain=row.speech_gain;level=row.mouth_level;blinkPhase=row.blink_phase;lastFrame=index;
    const u=timeline.utterances.find(u=>time>=u.start&&time<u.end);$('label').textContent=u?.label||names[state]||'待机';$('text').textContent=u?.text||(time>=timeline.duration-.1?'演出完成，可以输入新台词。':'');
  }else{
    if(live){asset=live.emotion==='happy'?'talking_high_reuse_v1':live.emotion==='sad'?'talking_low_reuse_v1':'talking_calm_reuse_v1';if(mode==='live'&&!audio.ended){gain=value(live.result.envelope.gains,time);level=value(live.result.envelope.levels,time);state=gain>.01?'SPEAKING':'IDLE';}}
    if(closing){const u=(now-closing.started)/180;gain=closing.gain*Math.max(0,1-u*u*(3-2*u));level=closing.level;asset=closing.asset;if(u>=1){closing=null;gain=0;level=0;}}
    mouth(asset,level,gain);blinkPhase=blink(asset,visualTime());lastFrame=-1;
  }
  currentState={mode,audioTime:time,paused:audio.paused,ended:audio.ended,audioError:audio.error?.code||null,frame:lastFrame,asset,speechGain:gain,mouthLevel:level,blinkPhase,visualTime:visualTime(),jobId};
  if(now-lastRecord>30){records.push({...currentState,wall:now});if(records.length>2000)records.shift();lastRecord=now;}
  if(now-lastDiagnostics>300){$('diagnostics').textContent=JSON.stringify({...currentState,records:records.slice()});lastDiagnostics=now;}
  $('seek').value=String(time);$('clock').textContent=`${time.toFixed(1)} / ${(Number.isFinite(audio.duration)?audio.duration:0).toFixed(1)} 秒`;
  requestAnimationFrame(draw);
}
async function play(){try{await audio.play();$('pause').disabled=false;$('cancel').disabled=false;}catch(e){$('error').textContent='未能播放，请检查音频输出后重试。';}}
function stopCurrent(){audio.pause();setVisualPause(false);freezeBlink=false;if(currentState.speechGain>0)closing={started:performance.now(),gain:currentState.speechGain,level:currentState.mouthLevel,asset:currentState.asset};mode='idle';}
async function cancelPending(){requestGeneration++;if(jobId){const id=jobId;jobId=null;try{await fetch('/api/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});}catch(e){}}}
async function scriptAt(time=0){await cancelPending();stopCurrent();live=null;closing=null;mode='script';audio.src='audio/script.wav';audio.currentTime=time;$('seek').max=String(timeline.duration);$('speechStatus').textContent='播放完整演示';records=[];play();}
$('script').onclick=()=>scriptAt();
$('pause').onclick=()=>{if(audio.paused){freezeBlink=false;setVisualPause(false);play();}else{freezeBlink=true;setVisualPause(true);audio.pause();}};
$('seek').oninput=()=>{audio.currentTime=Number($('seek').value);closing=null;};
$('cancel').onclick=async()=>{await cancelPending();stopCurrent();$('label').textContent='已打断';$('text').textContent='声音停止，嘴部平滑收起。';$('speechStatus').textContent='可输入下一句。正在生成的旧请求不会自动播放。';$('speak').disabled=false;};
audio.onplay=()=>{$('pause').textContent='暂停';$('load').textContent='声音与口型同步播放中';};
audio.onpause=()=>{$('pause').textContent='继续';};
audio.onended=()=>{mode='idle';closing=null;setVisualPause(false);freezeBlink=false;$('pause').disabled=true;$('pause').textContent='暂停';$('label').textContent='朗读结束';$('text').textContent='可以重播，或输入另一句。';$('load').textContent='已结束，眨眼继续独立运行';$('speechStatus').textContent='朗读完成，可以重播或输入新台词。';};
audio.onerror=()=>{$('error').textContent='音频载入失败，请重试。';};
$('replay').onclick=()=>{if(live){mode='live';$('label').textContent='柔亮俏皮 · 新台词';$('text').textContent=live.text;}else{mode='script';}closing=null;audio.currentTime=0;setVisualPause(false);freezeBlink=false;records=[];play();};
$('speak').onclick=async()=>{
  await cancelPending();stopCurrent();const generation=requestGeneration;
  const text=$('speechText').value.trim(),emotion=$('emotion').value;
  if(!text){$('error').textContent='请先输入一句台词。';return;}
  $('error').textContent='';$('speak').disabled=true;$('cancel').disabled=false;$('label').textContent='正在准备声音';$('text').textContent=text;$('speechStatus').textContent='本机正在准备同一声线，眨眼继续独立运行…';
  try{
    const response=await fetch('/api/speech',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,emotion})});let job=await response.json();if(!response.ok)throw Error(job.error||'生成失败');
    if(generation!==requestGeneration){await fetch('/api/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:job.id})});return;}jobId=job.id;
    while(['QUEUED','GENERATING'].includes(job.status)){
      if(generation!==requestGeneration)return;
      await new Promise(resolve=>setTimeout(resolve,600));job=await(await fetch(`/api/job/${job.id}`)).json();
    }
    if(generation!==requestGeneration||job.status==='CANCELLED')return;
    if(job.status!=='COMPLETE')throw Error(job.error||'生成失败');
    jobId=null;live=job;mode='live';closing=null;audio.src=job.result.audio;audio.currentTime=0;$('seek').max=String(job.result.duration_seconds);
    $('label').textContent='柔亮俏皮 · 新台词';$('text').textContent=job.text;$('speechStatus').textContent=job.result.cache_hit?'复用已生成的同声线缓存。':'同声线已生成，正在朗读。';records=[];await play();
  }catch(e){if(generation===requestGeneration){$('error').textContent=e.message;$('label').textContent='声音准备未完成';}}
  finally{if(generation===requestGeneration)$('speak').disabled=false;}
};
async function init(){
  [timeline,assets]=await Promise.all([fetch('timeline.json').then(r=>r.json()),fetch('live_assets.json').then(r=>r.json())]);
  let count=0;sheets=await Promise.all(timeline.sheets.map(s=>image(s.file).then(img=>{count++;$('load').textContent=`准备演出素材 ${count} / ${timeline.sheets.length}`;return img;})));
  mouthSheet=await image(assets.mouth_sheet);
  await Promise.all(Object.entries(assets.blink.targets).map(async([name,data])=>{eyes[name]=await Promise.all(data.layers.map(r=>image(r.file)));}));
  timeline.utterances.forEach(u=>{const button=document.createElement('button');button.textContent=u.label;button.onclick=()=>scriptAt(Math.max(0,u.reply_at-.3));document.querySelector('.chapters').append(button);});
  $('script').disabled=false;$('replay').disabled=false;$('speak').disabled=false;$('seek').disabled=false;$('label').textContent='准备好了';$('text').textContent='眨眼独立运行。可以播放全剧，或试一句新台词。';$('load').textContent='已准备好';audio.src='audio/script.wav';audio.load();draw();
}
init().catch(e=>{$('error').textContent='素材准备失败，请重新启动预览。';});
