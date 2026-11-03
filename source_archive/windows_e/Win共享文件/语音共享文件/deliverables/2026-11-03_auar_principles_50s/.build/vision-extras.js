window.createVisualExtras=(svg)=>{
  const ns='http://www.w3.org/2000/svg';
  const e=(tag,attrs={},text)=>{const n=document.createElementNS(ns,tag);for(const [k,v]of Object.entries(attrs))n.setAttribute(k,v);if(text!==undefined)n.textContent=text;return n;};
  const label=(parent,text,x,y,strong=false)=>{const n=e('text',{x,y,class:strong?'av-strong':'av-note'},text);parent.append(n);return n;};
  const vision=e('g',{'data-extra':'vision',opacity:0});
  const axis=e('g',{'data-extra':'axis',opacity:0});
  svg.append(vision,axis);
  label(vision,'相机视野',237,645);
  vision.append(e('rect',{x:55,y:662,width:365,height:139,rx:6,class:'av-screen'}));
  const detection=e('g');
  detection.append(e('rect',{x:-31,y:-44,width:62,height:88,rx:3,class:'av-target'}),e('circle',{cx:0,cy:0,r:4,fill:'#77a7bc'}));
  label(detection,'目标',0,60);
  vision.append(detection);
  vision.append(e('path',{d:'M 424 730 H 544',class:'av-line','marker-end':'url(#ad-arrow)'}));
  label(vision,'目标框',484,706);
  label(vision,'CPU 跟踪位置',710,660);
  vision.append(e('path',{d:'M 568 730 H 852',class:'av-line'}));
  const track=e('path',{class:'av-trace'}),dot=e('circle',{cx:620,cy:730,r:6,fill:'#77a7bc'});
  vision.append(track,dot);
  const position=label(vision,'目标位置',710,778,true);
  label(vision,'图像 → 检测框 → 位置',470,820);

  label(axis,'画面中的目标位置',790,650);
  axis.append(e('rect',{x:640,y:674,width:300,height:132,rx:6,class:'av-screen'}));
  axis.append(e('path',{d:'M 775 680 V 772',class:'av-control','stroke-dasharray':'4 4'}));
  label(axis,'期望位置',842,691);
  const movingTarget=e('g');
  movingTarget.append(e('rect',{x:-21,y:-33,width:42,height:66,rx:3,class:'av-target'}),e('circle',{r:4,fill:'#77a7bc'}));
  axis.append(movingTarget);
  const status=label(axis,'目标偏移',790,790);
  label(axis,'控制脉冲 PWM',1066,650);
  const pulse=e('path',{class:'av-control'});axis.append(pulse);
  label(axis,'单轴转动',1306,650);
  axis.append(e('circle',{cx:1306,cy:747,r:25,class:'av-line'}),e('circle',{cx:1306,cy:747,r:4,fill:'#eab04f'}));
  const rotor=e('g');rotor.append(e('path',{d:'M 0 18 V -60',class:'av-control','stroke-width':'4'}),e('rect',{x:-20,y:-68,width:40,height:17,rx:3,fill:'#fff0d3',stroke:'#eab04f'}));
  axis.append(rotor);
  const axisState=label(axis,'等待控制',1306,792);
  axis.append(e('path',{d:'M 1343 759 H 1400 V 831 H 790 V 807',class:'av-line','marker-end':'url(#ad-arrow)'}));
  label(axis,'回看目标位置 · 到位后停止',1090,851);
  const ease=q=>{q=Math.max(0,Math.min(1,q));return q*q*(3-2*q);};
  return {
    update(scene,local,opacity){
      vision.setAttribute('opacity',scene.kind==='vision'?opacity:0);
      axis.setAttribute('opacity',scene.kind==='axis'?opacity:0);
      if(scene.kind==='vision'){
        const q=ease((local-.7)/(scene.duration-1.7)),x=.28+.4*q;
        detection.setAttribute('transform',`translate(${55+365*x},721)`);
        const px=568+284*x;dot.setAttribute('cx',px);
        track.setAttribute('d',`M ${568+284*.28} 730 H ${px}`);
        position.textContent=`位置 x = ${x.toFixed(2)}`;
      }
      if(scene.kind==='axis'){
        const cues=scene.axisCues;
        const q=ease((local-cues.move)/(cues.stop-cues.move-.15));
        const controlled=local>=cues.control,stopped=q>=.999;
        movingTarget.setAttribute('transform',`translate(${694+81*q},729)`);
        status.textContent=stopped?'到位':'目标偏移';
        status.setAttribute('fill',stopped?'#ad7b29':'#56738d');
        rotor.setAttribute('transform',`translate(1306,747) rotate(${28*(1-q)})`);
        axisState.textContent=stopped?'停止':local>=cues.move?'跟随中':'等待控制';
        let d='M 968 744';
        const width=6+5*q;
        for(let n=0;n<7;n++){const x=968+n*27;d+=` H ${x} V 716 H ${x+width} V 744 H ${x+27}`;}
        pulse.setAttribute('d',d);pulse.setAttribute('opacity',controlled?1:.16);
        axis.dataset.motion=stopped?'stopped':local>=cues.move?'following':'waiting';
        axis.dataset.targetPosition=(.18+.27*q).toFixed(4);
        axis.dataset.angle=(28*(1-q)).toFixed(4);
      }
    }
  };
};
