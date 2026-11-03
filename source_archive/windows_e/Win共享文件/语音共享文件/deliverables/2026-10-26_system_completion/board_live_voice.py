"""Board's existing client over wire; no microphone, playback or movement."""
import base64,json,sys,wave
from pathlib import Path
HERE=Path(__file__).resolve().parent
AURA=HERE.parents[1]/'aura'
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
with wave.open(str(AURA/'models/asr/sherpa-onnx-paraformer-zh-2023-09-14/test_wavs/0.wav'),'rb') as f:
    pcm=f.readframes(f.getnframes())
script=r'''
import base64,hashlib,json,sys,threading,time,uuid,urllib.request
from pathlib import Path
sys.path.insert(0,'/home/root/aura-pan-current-20261024/16a07283/gui-manual-bound-v1/runtime/aura')
from board.runtime.audio.voice_channel import VoiceChannel
from board.runtime.audio.remote_frontend import RemoteSpeechGate
import numpy as np
pcm=base64.b64decode('PCM_PAYLOAD')
def state():
    with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as r:v=json.load(r)
    return {'handsfree_enabled':v['handsfree_dialogue']['enabled'],
            'microphone_open':v['handsfree_dialogue']['microphone_open'],
            'playing':v['playing'],'audio_output_state':v['audio_output_state']}
before=state();boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
frontend={}
def stream_frontend():
    gate=RemoteSpeechGate({'enabled':True,'host':'192.168.50.1','port':8795,'timeout_ms':180})
    frames=np.frombuffer(pcm,dtype='<i2').astype(np.float32)/32768
    times=[];lags=[];speech=0;start=time.perf_counter()
    try:
        for i in range(600):
            due=start+i*.02;pause=due-time.perf_counter()
            if pause>0:time.sleep(pause)
            lags.append(max(0,time.perf_counter()-due)*1000)
            at=(i*320)%(len(frames)//320*320)
            began=time.perf_counter();speech+=bool(gate(frames[at:at+320]));times.append((time.perf_counter()-began)*1000)
        frontend.update(status='PASS',frames=len(times),speech_frames=speech,
            rpc_p95_ms=round(float(np.percentile(times,95)),3),rpc_max_ms=round(max(times),3),
            over_20ms=sum(x>20 for x in times),capture_schedule_lag_max_ms=round(max(lags),3),
            wall_seconds=round(time.perf_counter()-start,3),concurrent_with_real_voice=True)
    except Exception as exc:frontend.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
    finally:gate.close()
t=threading.Thread(target=stream_frontend);t.start()
turns=[];session=uuid.uuid4().hex
try:
    for i in range(2):
        channel=VoiceChannel('192.168.50.1');audio=bytearray();first={};start=time.perf_counter()
        meta=dict(protocol='aura-asr-1',board_boot_id=boot,session_id=session,request_id=uuid.uuid4().hex,
                  generation=i+1,capture_id='public-board-automatic',sample_count=len(pcm)//2,
                  pcm_sha256=hashlib.sha256(pcm).hexdigest(),budget_ms=120000)
        def receive(h,p):
            first.setdefault(h['kind'],round((time.perf_counter()-start)*1000,3))
            if h['kind']=='audio':audio.extend(p)
        try:
            result=channel.exchange(meta,pcm,receive)
            assert result['network_complete'] and result['sample_count']>0
            assert hashlib.sha256(audio).hexdigest()==result['pcm_sha256']
            turns.append(dict(status='PASS',first_ms=first,samples=result['sample_count'],
                              pcm_sha256=result['pcm_sha256'],playback_ack_sent=False))
        finally:channel.close()
except Exception as exc:turns.append(dict(status='FAIL',error=type(exc).__name__+': '+str(exc)))
t.join(20)
assert not t.is_alive(),'Frontend thread did not finish'
after=state()
value=dict(status='PASS' if all(x['status']=='PASS' for x in turns) and len(turns)==2 and frontend.get('status')=='PASS' and before==after else 'FAIL',
    scope='real deployed board client, public PCM, Windows ASR/27B/OmniVoice and concurrent CPU frontend',
    turns=turns,frontend=frontend,ui_before=before,ui_after=after,
    boot_unchanged=boot==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    microphone_used=False,playback=False,physical_motion_commanded=False,production_files_changed=False)
print(json.dumps(value))
'''.replace('PCM_PAYLOAD',base64.b64encode(pcm).decode())
value=json.loads(ssh('python3 -B -',script,timeout=275))
(HERE/'board_live_voice.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(value))
raise SystemExit(0 if value['status']=='PASS' else 1)
