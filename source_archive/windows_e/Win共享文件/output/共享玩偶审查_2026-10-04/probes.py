import json
import random
import sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('E:/项目/共享文件夹/aura')
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
sys.stdout.reconfigure(encoding='utf-8')
from tools import demo_stage as ds
from board.interaction import avatar_timing as at, avatar_assets as aa
from board.runtime.events import EventType as E
from board.runtime.fsm import RuntimeState
from board.runtime.audio.tts import TtsPlayer,TtsConfig

core=ds.StageCore(rng=random.Random(1234)); core.idle_gain=0
core.reply_text='同样的长句用于取帧对比'*8
entries=[]; sequences=[]
for i in range(4):
    core.reset_playback()
    first=core.frame_at('SPEAKING_NEUTRAL',100.0)
    sequences.append([core.frame_at('SPEAKING_NEUTRAL',100.0+k/30)['index'] for k in range(300)])
    entries.append({'phase':first['phase'],'first_index':first['index']})
phase={'entries':entries,'sequences_identical':all(s==sequences[0] for s in sequences[1:])}
core.reset_playback()
core.frame_at('ACK_NOD',0.0)
bursts=[]
for t in (1.0,1.1,1.2):
    core.frame_at('ACK_NOD',t)
    bursts.append(core.take_burst_finished())

class Value:
    def __init__(self,v=''): self.v=v
    def get(self): return self.v
    def set(self,v): self.v=v
class FakeTts:
    def __init__(self): self.calls=[];self.config=type('Config',(),{'engine':'mock','voice':'none'})()
    def speak_async(self,text,style=None): self.calls.append(('speak',text))
    def stop(self): self.calls.append(('stop',))
def app_in(state):
    a=ds.StageApp.__new__(ds.StageApp)
    a.core=core;core.fsm.reset(state)
    a.busy=False;a.entry=Value('请告诉我现在的状态')
    a._reply_var=Value();a.tts=FakeTts();a.messages=[];a._log=a.messages.append
    return a
class FakeThread:
    def __init__(self,*a,**kw):pass
    def start(self):pass
original=ds.threading.Thread
ds.threading.Thread=FakeThread
a=app_in(RuntimeState.LISTENING)
a._send_llm()
voice={'after_send_llm':core.fsm.state.name,'busy':a.busy}
ds.threading.Thread=original
a=app_in(RuntimeState.SPEAKING_NEUTRAL)
a._send_event('AUDIO_CANCEL_REQUESTED')
cancel={'state':core.fsm.state.name,'tts_calls':a.tts.calls[:]}
a=app_in(RuntimeState.THINKING)
a._send_event('AUDIO_CANCEL_REQUESTED')
a._on_response({'reply_text':'这是取消后才到达的旧回复','emotion':'neutral','avatar_action':''},None,1.0)
late={'state':core.fsm.state.name,'tts_calls':a.tts.calls[:],'display':a._reply_var.v}

rows=[]
for name in ['idle_normal','talking_neutral']:
    d=aa.asset_dir(name);diffs=aa.read_motion(d);n=len(aa.list_frames(d));f=aa.frames_fps(d)
    idx=[at.frame_index(at.warp_time(i/f,diffs,f,slowdown=1.5),n,f,False) for i in range(int(n*1.5)*3)]
    rows.append({'asset':name,'frames':n,'max_index_warp':max(idx),'missing_indices':sorted(set(range(n))-set(idx)),'repeated_pairs':sum(a==b for a,b in zip(idx,idx[1:])),'pairs':len(idx)-1})
facts=json.loads((OUT/'audit.json').read_text(encoding='utf-8'))
summary={'phase_not_applied':phase,'burst_repeated_completion':bursts,'voice_listening_not_advanced':voice,'cancel_does_not_stop_tts':cancel,'late_response_after_cancel':late,'warp_skips_last_frame':rows,'total_png_frames':sum(a['frames'] for a in facts['assets']),'total_png_mib':round(sum(a['png_mib'] for a in facts['assets']),2),'hash_mismatch_count':sum(len(a['bad_hash']) for a in facts['assets'])}
(OUT/'probes.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
