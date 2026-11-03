'use strict';
let micSession=null,micHeld=false,micEpoch=0;
const micButton=document.getElementById('microphone');
async function beginMicrophone(){
  if(micHeld)return;
  micHeld=true;const epoch=++micEpoch;
  micButton.textContent='正在打开麦克风…';
  try{
    await command({type:'event',event:'cancel'});
    const stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
    if(!micHeld||epoch!==micEpoch){stream.getTracks().forEach(t=>t.stop());return;}
    const context=new AudioContext();await context.resume();
    const source=context.createMediaStreamSource(stream),processor=context.createScriptProcessor(4096,1,1);
    const session={stream,context,source,processor,chunks:[],size:0,rate:context.sampleRate,epoch};micSession=session;
    processor.onaudioprocess=e=>{
      if(micSession!==session)return;
      const input=e.inputBuffer.getChannelData(0);session.chunks.push(new Float32Array(input));session.size+=input.length;
      if(session.size>=session.rate*20)endMicrophone(true);
    };
    source.connect(processor);processor.connect(context.destination);
    micButton.textContent='正在听 · 松开发送';micButton.setAttribute('aria-pressed','true');
  }catch(error){micHeld=false;micButton.textContent='按住说话';$('error').textContent='麦克风未能打开：'+error.message;}
}
async function endMicrophone(send){
  micHeld=false;const session=micSession;micSession=null;
  micButton.textContent='按住说话';micButton.setAttribute('aria-pressed','false');
  if(!session)return;
  session.processor.disconnect();session.source.disconnect();session.stream.getTracks().forEach(t=>t.stop());await session.context.close();
  if(!send)return;
  if(session.size/session.rate<.2){$('error').textContent='录音太短，请按住说完一句再松开。';return;}
  const input=new Float32Array(session.size);let offset=0;
  for(const chunk of session.chunks){input.set(chunk,offset);offset+=chunk.length;}
  const size=Math.min(320000,Math.floor(input.length*16000/session.rate)),raw=new Uint8Array(size*2),view=new DataView(raw.buffer);
  for(let i=0;i<size;i++){
    const start=Math.floor(i*session.rate/16000),end=Math.max(start+1,Math.floor((i+1)*session.rate/16000));
    let sum=0;for(let j=start;j<end&&j<input.length;j++)sum+=input[j];
    const value=Math.max(-1,Math.min(1,sum/(end-start)));view.setInt16(i*2,Math.round(value*(value<0?32768:32767)),true);
  }
  let binary='';for(let i=0;i<raw.length;i+=8192)binary+=String.fromCharCode(...raw.subarray(i,i+8192));
  $('heard').textContent='正在识别…';await command({type:'microphone',pcm:btoa(binary)});
}
micButton.addEventListener('pointerdown',e=>{e.preventDefault();micButton.setPointerCapture(e.pointerId);beginMicrophone();});
micButton.addEventListener('pointerup',()=>endMicrophone(true));
micButton.addEventListener('pointercancel',()=>endMicrophone(false));
micButton.addEventListener('keydown',e=>{if(e.code==='Space'&&!e.repeat){e.preventDefault();beginMicrophone();}});
micButton.addEventListener('keyup',e=>{if(e.code==='Space'){e.preventDefault();endMicrophone(true);}});
window.addEventListener('blur',()=>endMicrophone(false));
document.getElementById('cancel').addEventListener('click',()=>{++micEpoch;endMicrophone(false);});
setInterval(()=>{
  micButton.disabled=!lastState.microphone_ready||!lastState.voice_ready||!lastState.dialogue_enabled;
  $('ready').textContent=lastState.microphone_ready&&lastState.voice_ready?'声音与识别已就绪，可以开聊':'正在加载声音与识别，请稍等…';
  if(lastState.dialogue_input)$('heard').textContent='你说：'+lastState.dialogue_input;
},300);
