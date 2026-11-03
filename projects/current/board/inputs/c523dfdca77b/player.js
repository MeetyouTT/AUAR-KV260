'use strict';
const $=id=>document.getElementById(id);
let lastState={},previousImage=null,connected=true;
async function command(data){
  $('error').textContent='';
  try{const response=await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const result=await response.json();if(!response.ok)throw Error(result.error||'操作失败');return result;}
  catch(error){$('error').textContent=error.message;}
}
$('speak').onclick=()=>command({type:'speak',text:$('text').value,emotion:$('emotion').value,action:$('action').value});
$('pause').onclick=()=>command({type:'pause'});
$('cancel').onclick=()=>command({type:'event',event:'cancel'});
document.querySelectorAll('[data-demo]').forEach(button=>button.onclick=()=>command({type:'demo',index:Number(button.dataset.demo)}));
document.querySelectorAll('[data-event]').forEach(button=>button.onclick=()=>command({type:'event',event:button.dataset.event}));
$('dialogue').onclick=()=>command({type:'dialogue',text:$('dialogueText').value});
async function update(){
  const began=performance.now();
  try{
    const [response,frame]=await Promise.all([fetch('/api/state'),fetch('/api/frame')]);
    if(!response.ok||!frame.ok)throw Error('本机演示窗口已断开');
    lastState=await response.json();connected=true;
    const blob=await frame.blob();const url=URL.createObjectURL(blob);
    await new Promise(resolve=>{const img=new Image();img.onload=()=>{$('avatar').src=url;if(previousImage)URL.revokeObjectURL(previousImage);previousImage=url;resolve();};img.onerror=()=>{URL.revokeObjectURL(url);resolve();};img.src=url;});
    $('status').textContent=lastState.status_text||'等你开口';$('reply').textContent=lastState.reply||'可以打个招呼，也可以输入你想让她说的话。';
    $('pause').textContent=lastState.paused?'继续播放':'暂停 / 继续';
    if(lastState.error)$('error').textContent=lastState.error;
    $('dialogueText').disabled=!lastState.dialogue_enabled;$('dialogue').disabled=!lastState.dialogue_enabled;
    $('modelStatus').textContent=lastState.dialogue_enabled?'对话服务已配置 · 发送时连接':'对话模型未连接 · 可在另一台电脑接入';
    $('diagnostics').textContent=JSON.stringify(lastState);
  }catch(error){connected=false;$('status').textContent='演示窗口未连接';$('error').textContent='请先启动共享文件夹中的实时演示台。';}
  setTimeout(update,connected?Math.max(0,33-(performance.now()-began)):1000);
}
update();
