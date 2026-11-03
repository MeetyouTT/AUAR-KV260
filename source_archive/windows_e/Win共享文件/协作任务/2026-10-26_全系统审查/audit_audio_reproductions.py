"""Fake TTS/health reproduction; no child process, model, socket or audio IO."""
import argparse
import io
import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.dont_write_bytecode=True
WORKSPACE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WORKSPACE/'语音共享文件/aura'))
from tools.voice_channel_source import channel_frames
from tools.board_model_host import ModelHandler
from common.voice_channel import read_frame
from board.runtime.audio.barge_verify import classify_interruption


def run():
    entered=threading.Event();release=threading.Event();packets=[];errors=[]
    class Voice:
        def generate(self,text):
            entered.set()
            release.wait(3.)  # Test is bounded even if the cleanup code changes.
            raise RuntimeError('Injected fake TTS release; no synthesis')
    class Stream:
        def __iter__(self):
            yield 'text','今天辛苦啦，我陪你聊聊。'
            yield 'speech_ready',None
            yield 'complete',{'reply_text':'今天辛苦啦，我陪你聊聊。','emotion':'friendly','avatar_action':''}
        def cancel(self): pass
    meta=dict(protocol='aura-asr-1',board_boot_id='test-boot',session_id='test-session',
        request_id='audit-timeout',generation=1,capture_id='test-capture',sample_count=3200,
        pcm_sha256='0'*64,budget_ms=5000)
    models=SimpleNamespace(histories={},voice=Voice(),latency_options={},lock=threading.Lock())
    budget=.2
    def consume():
        try:
            # Mirrors the outer HTTP handler's serialized model-operation owner.
            with models.lock:
                for packet in channel_frames(models,meta,'测试',budget,model='fixture',host='fixture',
                    stream_factory=lambda *a,**k:Stream()):
                    header,pcm=read_frame(io.BytesIO(packet));packets.append(header['kind'])
        except Exception as exc: errors.append(type(exc).__name__+': '+str(exc))
    started=time.monotonic();thread=threading.Thread(target=consume,daemon=True);thread.start()
    try:
        if not entered.wait(1.): raise RuntimeError('Fake TTS was not entered')
        time.sleep(.35)
        timeout={'scope':'real channel generator, fake blocked TTS, simulated HTTP owner lock',
            'channel_budget_ms':budget*1000,'observed_elapsed_ms':round((time.monotonic()-started)*1000,3),
            'request_thread_alive_after_budget':thread.is_alive(),'model_operation_lock_held':models.lock.locked(),
            'packet_kinds_before_release':list(packets)}
    finally:
        release.set();thread.join(2.)
    timeout.update(thread_exited_after_fake_tts_release=not thread.is_alive(),errors=errors)

    health=[];handler=ModelHandler.__new__(ModelHandler);handler.path='/health'
    fake=SimpleNamespace(lock=threading.Lock(),voice=SimpleNamespace(ready=False,error='injected unavailable'),
                         face_features=None,conversations=None)
    handler.server=SimpleNamespace(engine=SimpleNamespace(model_id='TEST_ONLY'),models=fake)
    handler.send=lambda status,value:health.append((status,value))
    handler.do_GET()
    return {'recorded_utc':datetime.now(timezone.utc).isoformat(),
        'board_accessed':False,'models_loaded':False,'worker_process_started':False,
        'channel_timeout_cleanup':timeout,
        'health_unready_injection':{'http_status':health[0][0],
            'injected_voice_ready':False,'reported_top_level_ready':health[0][1]['ready'],
            'scope':'handler stub, not a live service observation; initial startup warmup still exists'},
        'documented_echo_tradeoff':{'input':'停','playback_reference':'你可以随时说停，我会停下来。',
            'classification':classify_interruption('停','你可以随时说停，我会停下来。'),
            'interpretation':'text echo veto limitation, not proof of a new implementation regression'}}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists(): raise SystemExit('Output exists; choose a new file')
    result=run()
    with args.output.open('x',encoding='utf-8') as output: json.dump(result,output,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False,indent=2))
