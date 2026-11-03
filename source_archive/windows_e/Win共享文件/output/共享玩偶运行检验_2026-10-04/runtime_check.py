import hashlib
import json
from pathlib import Path
import random
import sys
import time
sys.dont_write_bytecode=True
ROOT=Path('E:/项目/共享文件夹/aura')
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image,ImageDraw
from tools.demo_stage import StageCore
from board.runtime.fsm import RuntimeState
from board.runtime.events import EventType as E
from board.runtime.audio.tts import TtsPlayer,TtsConfig
from board.runtime.dialogue_client import MockDialogueAdapter
from board.runtime.dialogue_client.adapter import DialogueRequest
from board.interaction import avatar_assets as aa,avatar_fsm as af

result={'environment':'PC; actual StageCore and FSM; mock dialogue and scripted TTS; no microphone/board/real LLM', 'states':[], 'scenarios':[]}
labels={'IDLE':'待机','PRESENT':'有人','LISTENING':'聆听','THINKING':'思考','SPEAKING':'高情绪播报','SPEAKING_NEUTRAL':'中性播报','SPEAKING_LOW':'低落播报','AWAKE':'唤醒','PUZZLED':'困惑','ACK_NOD':'点头','DENY_SHAKE':'摇头','CAMERA_LOST':'相机丢失','NETWORK_LOST':'断网','CANCELLED':'取消','ERROR':'错误'}
preview_states={'IDLE','LISTENING','THINKING','SPEAKING','SPEAKING_NEUTRAL','ACK_NOD','DENY_SHAKE'}
contact=Image.new('RGB',(5*180,15*205),(252,252,243))
times=[0,.35,.9,2,4]
for row,state in enumerate(RuntimeState):
    core=StageCore(rng=random.Random(11));core.reply_text='这是一段用于验证当前播放核心行为的较长回复。'*3
    seq=core.sequence(state.name)
    metas=[core.frame_at(state.name,100+t) for t in times]
    indexes=[core.frame_at(state.name,100+i/30)['index'] for i in range(180)]
    info={'state':state.name,'label':labels[state.name],'asset':seq[3] if seq else None,'frames':len(seq[0]) if seq else 0,'fps':seq[1] if seq else 0,'burst':seq[2] if seq else None,'sample_indices':[m['index'] if m else None for m in metas],'unique_frames_in_6s':len(set(indexes)),'qt_label':af.avatar_spec(state.name).label,'load_ok':all(m is not None for m in metas)}
    result['states'].append(info)
    for col,m in enumerate(metas):
        img=m['image'].copy();img.thumbnail((178,178))
        contact.paste(img,(col*180+(180-img.width)//2,row*205+178-img.height),img)
        ImageDraw.Draw(contact).text((col*180+4,row*205+181),f'{state.name} t={times[col]} f={m["index"]}',fill=(25,35,50))
    if state.name in preview_states:
        core.reset_playback();frames=[]
        for i in range(90):
            m=core.frame_at(state.name,100+i/15)
            img=m['image'].copy();img.thumbnail((240,248))
            canvas=Image.new('RGB',(256,284),(252,252,243))
            canvas.paste(img,((256-img.width)//2,250-img.height),img)
            ImageDraw.Draw(canvas).text((8,260),f'{state.name} frame={m["index"]}',fill=(25,35,50))
            frames.append(canvas)
        frames[0].save(OUT/(state.name+'.webp'),save_all=True,append_images=frames[1:],duration=67,loop=0,quality=78,method=3)
    print('STATE',state.name,info['sample_indices'],flush=True)
contact.save(OUT/'runtime_states.png')

def scenario(name,events):
    c=StageCore();trace=[]
    for kind,payload in events:
        rejected=c.fsm.rejected_count
        c.send(kind,payload)
        m=c.frame_at(c.fsm.state.name,time.monotonic())
        trace.append({'event':kind,'state':c.fsm.state.name,'asset':m['asset'],'rejected':c.fsm.rejected_count>rejected})
    result['scenarios'].append({'name':name,'trace':trace})
scenario('single_utterance_kws',[(E.SCENE_PERSON_ENTER,{}),(E.AUDIO_KWS_DETECTED,{}),(E.AUDIO_VAD_END,{}),(E.DIALOGUE_RESPONSE_RECEIVED,{'emotion':'neutral','reply_text':'收到'}),(E.AUDIO_PLAYBACK_STOP,{})])
scenario('button_dialogue',[(E.BOARD_KEY_PRESSED,{}),(E.AUDIO_VAD_END,{}),(E.DIALOGUE_RESPONSE_RECEIVED,{'emotion':'neutral','reply_text':'收到'}),(E.AUDIO_PLAYBACK_STOP,{})])
scenario('high_emotion',[(E.BOARD_KEY_PRESSED,{}),(E.AUDIO_VAD_END,{}),(E.DIALOGUE_RESPONSE_RECEIVED,{'emotion':'happy','reply_text':'好呀'}),(E.AUDIO_PLAYBACK_STOP,{})])
scenario('low_emotion',[(E.BOARD_KEY_PRESSED,{}),(E.AUDIO_VAD_END,{}),(E.DIALOGUE_RESPONSE_RECEIVED,{'emotion':'sad','reply_text':'抱歉'}),(E.AUDIO_PLAYBACK_STOP,{})])
scenario('camera_recovery',[(E.CAMERA_LOST,{}),(E.CAMERA_RECOVERED,{})])
scenario('network_recovery',[(E.DIALOGUE_NETWORK_LOST,{}),(E.DIALOGUE_NETWORK_RESTORED,{})])
scenario('wake_completion',[(E.AUDIO_KWS_DETECTED,{}),(E.AUDIO_PLAYBACK_STOP,{})])
scenario('cancel_with_presence',[(E.SCENE_PERSON_ENTER,{}),(E.BOARD_KEY_PRESSED,{}),(E.AUDIO_VAD_END,{}),(E.AUDIO_CANCEL_REQUESTED,{})])

# Poll an actual TtsPlayer clock backend with the same burst-continuation protocol.
c=StageCore();c.send(E.BOARD_KEY_PRESSED);c.send(E.AUDIO_VAD_END)
adapter=MockDialogueAdapter();adapter.connect()
resp=adapter.send_request(DialogueRequest(request_id='runtime-check',audio_generation_id=1,scene_state={'schema_version':'1.0','scene_seq':1,'camera_state':'online','people_count':1,'current_target':{'track_id':1,'position':'left'}})).to_dict()
c.apply_response(resp)
player=TtsPlayer(TtsConfig(engine='scripted'));player.speak_async(resp['reply_text'])
trace=[];last=None;start=time.monotonic()
while time.monotonic()-start < 8:
    if player.poll():c.send(E.AUDIO_PLAYBACK_STOP)
    state=c.fsm.state.name
    c.frame_at(state,time.monotonic())
    if c.take_burst_finished() and player.is_busy():c.send(E.AUDIO_PLAYBACK_START,{'emotion':c.emotion})
    if c.fsm.state.name!=last:
        last=c.fsm.state.name;trace.append({'seconds':round(time.monotonic()-start,3),'state':last})
    if last=='IDLE':break
    time.sleep(.033)
result['timed_mock_dialogue']={'response':resp,'timeline':trace,'audio_backend':'scripted, no sound'}

for name in ['IDLE','LISTENING','THINKING','SPEAKING_NEUTRAL']:
    c=StageCore();c.idle_gain=0;c.reply_text='同一条较长回复用于重复性验证。'*4
    entries=[];seqs=[]
    for i in range(3):
        c.reset_playback();m=c.frame_at(name,0);entries.append({'phase':m['phase'],'first':m['index']})
        seqs.append([c.frame_at(name,j/30)['index'] for j in range(900)])
    result.setdefault('repeatability',[]).append({'state':name,'entries':entries,'same_30s_frame_sequence':all(x==seqs[0] for x in seqs[1:])})
result['source_fingerprints']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'tools/demo_stage.py',ROOT/'board/runtime/fsm.py',ROOT/'board/interaction/avatar_timing.py',ROOT/'board/interaction/avatar_assets.py']}
(OUT/'runtime_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
cards=''.join(f'<article><h2>{labels[s]} · {s}</h2><img src="{s}.webp"><p>当前 StageCore 取帧，6 秒样本，预览采样 15fps。一次性动作只播到末帧；浏览器随后重播样本。</p></article>' for s in ['IDLE','LISTENING','THINKING','SPEAKING','SPEAKING_NEUTRAL','ACK_NOD','DENY_SHAKE'])
html='<!doctype html><html lang="zh"><meta charset="utf-8"><title>玩偶当前播放器样本</title><style>body{font:16px system-ui;background:#eef0f3;color:#18202b;margin:32px}main{display:flex;flex-wrap:wrap;gap:20px}article{background:white;padding:18px;border-radius:12px;width:290px}h2{font-size:17px}img{width:256px}p{line-height:1.6;font-size:14px}</style><h1>玩偶当前播放器样本</h1><p>直接调用项目的实际 StageCore；原素材和代码未修改。此页用于观察当前取帧效果，并非 KV260、音频或状态切换通过证据。</p><main>'+cards+'</main></html>'
(OUT/'index.html').write_text(html,encoding='utf-8')
print(json.dumps({'states_ok':sum(s['load_ok'] for s in result['states']),'timed_dialogue':result['timed_mock_dialogue']['timeline'],'scenarios':result['scenarios']},ensure_ascii=False,indent=2),flush=True)
