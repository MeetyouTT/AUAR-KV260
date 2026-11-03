import json
import math
from pathlib import Path
import re
import subprocess
import wave

HERE=Path(__file__).resolve().parent
OUTPUT=HERE.parent/'output'
SOURCE=Path(r'C:\Users\REVO1\.codex\visualizations\2026\11\03\01a19fed-c7be-7720-a693-f09fa0eeefbd\aura-dialogue-continuous.html')
speech=json.loads((HERE/'speech.json').read_text(encoding='utf-8'))

def norm(s):
    return ''.join(c for c in s if c.isalnum())

def stamp(seconds):
    ms=round(seconds*1000)
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'

clips=[]
scenes=[]
subtitle=[]
cursor=0
fps=30
logical=[0,3,7,10.5,14,18,22,26,29]
target_samples=40*48000
prefix_samples=[round(.5*48000)]+[round(.08*48000)]*7
suffix_samples=[round(.18*48000)]*7+[round(.65*48000)]
clip_samples=[round(s['speech_duration']*48000) for s in speech['scenes']]
spare=target_samples-sum(prefix_samples)-sum(suffix_samples)-sum(clip_samples)
assert spare>0, 'Narration must fit with natural scene transitions.'
weights=[1.3,1,1.2,1,1.2,1.2,1,1.5]
extra=[int(spare*w/sum(weights)) for w in weights]
extra[-1]+=spare-sum(extra)
suffix_samples=[a+b for a,b in zip(suffix_samples,extra)]
for i,s in enumerate(speech['scenes']):
    prefix=prefix_samples[i]/48000
    suffix=suffix_samples[i]/48000
    with wave.open(s['clip'],'rb') as f:
        assert f.getframerate()==48000 and f.getnchannels()==1 and f.getsampwidth()==2
        pcm=f.readframes(f.getnframes())
    n0=round(prefix*48000)
    n1=round(suffix*48000)
    clips.append(b'\0'*(n0*2)+pcm+b'\0'*(n1*2))
    d=(n0+len(pcm)//2+n1)/48000
    words=[b for b in s['boundaries'] if b['type']=='WordBoundary']
    assert ''.join(norm(b['text']) for b in words)==norm(s['text']), f'voice text mismatch in scene {i+1}'
    char_times=[]
    for b in words:
        letters=norm(b['text'])
        a=prefix+b['offset']/1e7
        dur=b['duration']/1e7
        for k,c in enumerate(letters):
            char_times.append((a+dur*k/len(letters),a+dur*(k+1)/len(letters)))
    plain=norm(s['text'])
    def at(phrase,end=False):
        phrase=norm(phrase)
        p=plain.index(phrase)
        return char_times[p+len(phrase)-1][1] if end else char_times[p][0]
    def mapping(pairs):
        points=[[0,logical[i]]]+[[at(p,end),v] for p,v,end in pairs]+[[d,logical[i+1]-(0 if i==7 else .0001)]]
        assert all(points[j+1][0]>points[j][0] and points[j+1][1]>=points[j][1] for j in range(len(points)-1)), points
        return points
    if i==0:
        points=mapping([])
        camera_in=.55
        camera_out=min(at('图像处理')-.2,d-.72)
    elif i==1:
        points=mapping([('说完一句',6.04,False),('才提交',6.48,True)])
        camera_in=.12; camera_out=d-.72
    elif i==2:
        points=mapping([('把录音',8,False),('转成文本',9.05,True)])
        camera_in=.12;camera_out=d-.72
    elif i==3:
        points=mapping([('区分',10.65,False),('补充',11.5,False),('上下文',13.15,True)])
        camera_in=.12;camera_out=d-.72
    elif i==4:
        points=mapping([('调用',14.55,False),('取回',16.1,False),('校验',17.62,True)])
        camera_in=.12;camera_out=d-.72
    elif i==5:
        points=mapping([('独立调用',18.55,False),('收回',20,False),('音频',21.4,True)])
        camera_in=.12;camera_out=d-.72
    elif i==6:
        points=mapping([])
        camera_in=max(.12,at('声音')-.4);camera_out=d-.72
    else:
        points=mapping([('播放',26.45,False),('提交',27.25,False),('再恢复',28.35,False),('聆听',28.6,True)])
        camera_in=.12;camera_out=min(at('再恢复'),d-.72)
    caps=[]
    char_cursor=0
    for text in s['captions']:
        n=len(norm(text))
        assert plain[char_cursor:char_cursor+n]==norm(text),text
        a=cursor+char_times[char_cursor][0]-.06
        b=cursor+char_times[char_cursor+n-1][1]+.20
        caps.append({'text':text,'start':a,'end':b})
        char_cursor+=n
    assert char_cursor==len(plain)
    for j in range(len(caps)-1):
        caps[j]['end']=min(caps[j+1]['start']-.04,max(caps[j]['end'],caps[j+1]['start']-.12))
    subtitle.extend(caps)
    entry=.6 if i==0 else .5
    assert camera_out>camera_in+entry+.25
    scenes.append({'index':i,'title':s['title'],'short':s['short'],'text':s['text'],'start':cursor,'end':cursor+d,'duration':d,'prefix':prefix,'speech_duration':s['speech_duration'],'cameraIn':camera_in,'cameraOut':camera_out,'cameraEntry':entry,'cameraExit':.55,'visionAt':at('图像处理') if i==0 else None,'captionClose':caps[-1]['end'] if i==7 else None,'captions':caps,'map':points})
    cursor+=d

assert abs(cursor-40)<1e-6
frames=1200
duration=40.0
with wave.open(str(HERE/'narration-raw.wav'),'wb') as f:
    f.setnchannels(1);f.setsampwidth(2);f.setframerate(48000)
    for pcm in clips:f.writeframes(pcm)
    f.writeframes(b'\0'*(max(0,round((duration-cursor)*48000))*2))
subprocess.run([speech['ffmpeg'],'-y','-v','error','-i',str(HERE/'narration-raw.wav'),'-af','loudnorm=I=-17:TP=-1.5:LRA=9','-ar','48000','-c:a','pcm_s16le',str(HERE/'narration-master.wav')],check=True)

timeline={'duration':duration,'fps':fps,'frames':frames,'width':1920,'height':1080,'voice':speech['voice'],'voice_direction':'通用温柔女性播报风格','rate':speech['rate'],'pitch':speech['pitch'],'ffmpeg':speech['ffmpeg'],'scenes':scenes}
(HERE/'timeline.json').write_text(json.dumps(timeline,ensure_ascii=False,indent=2),encoding='utf-8')
(OUTPUT/'AUAR_雪妃_40秒版_字幕.srt').write_text('\n\n'.join(f'{i+1}\n{stamp(c["start"])} --> {stamp(c["end"])}\n{c["text"]}' for i,c in enumerate(subtitle))+'\n',encoding='utf-8-sig')
(OUTPUT/'AUAR_雪妃_40秒版_讲解稿.txt').write_text('\n\n'.join(f'{i+1:02d} {s["title"]}\n{s["text"]}' for i,s in enumerate(scenes))+'\n',encoding='utf-8-sig')

fragment=SOURCE.read_text(encoding='utf-8')
def replace_once(a,b):
    global fragment
    assert fragment.count(a)==1,(a,fragment.count(a))
    fragment=fragment.replace(a,b)
replace_once('let t=0,running=!reduced','let t=0,running=false')
replace_once("W=Math.max(300,root.querySelector('#ad-diagram').getBoundingClientRect().width);mobile=W<600;H=mobile?740:630;VH=mobile?650:540;buildCount++;",'W=1480;mobile=false;H=630;VH=1480*690/1792;buildCount++;')
replace_once('svg.style.height=`${VH}px`;','svg.style.height="690px";')
replace_once('const s=W<680, nw=s?128:142,rw=s?132:148;','const s=false, nw=190,rw=200;')
replace_once("s?82:94,'麦克风'","145,'麦克风'")
replace_once("s?100:112,'本地指令'","160,'本地指令'")
replace_once('function drawWave(id,amp,clock=t)','function drawWave(id,amp,clock=window.__videoTime)')
replace_once("const ww=tiny?8:Math.max(40,[...txt].reduce((n,c)=>n+(c.charCodeAt(0)>255?13:6.5),0)+14);","const ww=tiny?9:Math.max(48,[...txt].reduce((n,c)=>n+(c.charCodeAt(0)>255?18:9),0)+20);")
replace_once("y:tiny?-4:-11,width:ww,height:tiny?8:22","y:tiny?-4.5:-15,width:ww,height:tiny?9:30")
pattern=r'  function cameraAt\(\)\{[\s\S]*?\n  function packet'
camera='''  function cameraAt(){
    const i=index(),s=window.__timeline.scenes[i],local=window.__videoLocal,focus=focusViews[i];
    const a=s.cameraIn,b=s.cameraOut,entry=s.cameraEntry,exit=s.cameraExit;
    if(local<a)return {rect:globalView,mode:i===0?'全链路总览':'全链路定位',lens:.8};
    if(local<a+entry){const q=ease((local-a)/entry);return {rect:mix(globalView,focus,q),mode:'总览定位 · 连续推近',lens:(1-q)*.75};}
    if(local>b){const q=ease((local-b)/exit);return {rect:mix(focus,globalView,q),mode:i===7?'回到总览 · 完成闭环':i===0?'并行视觉 · 接续下一步':'拉回总览 · 接续下一步',lens:q*.5};}
    return {rect:focus,mode:'局部讲解 · 同一条数据流',lens:0};
  }
  function packet'''
fragment,n=re.subn(pattern,lambda m:camera,fragment)
assert n==1
replace_once("new ResizeObserver(()=>{const w=root.querySelector('#ad-diagram').getBoundingClientRect().width;if(Math.abs(w-W)>1)build();}).observe(root.querySelector('#ad-diagram'));",'/* Fixed 1920x1080 video world: geometry remains stable for the full film. */')
template=(HERE/'video-template.html').read_text(encoding='utf-8')
# The approved source contains scoped CSS; repeat the video stylesheet last so fixed export geometry wins.
css=re.search(r'<style>([\s\S]*?)</style>',template).group(0)
html=template.replace('TIMELINE_DATA',json.dumps(timeline,ensure_ascii=False,separators=(',',':'))).replace('<!-- APPROVED_ANIMATION -->',fragment+css)
(HERE/'video-source.html').write_text(html,encoding='utf-8')
print(json.dumps({'duration':duration,'frames':frames,'voice':speech['voice'],'scenes':[{'start':round(s['start'],3),'duration':round(s['duration'],3),'title':s['title']} for s in scenes]},ensure_ascii=False),flush=True)
