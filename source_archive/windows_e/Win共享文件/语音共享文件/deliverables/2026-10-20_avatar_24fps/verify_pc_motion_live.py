"""Real ASR/27B/TTS, existing archived input, no capture/playback/memory ACK."""
import hashlib,http.client,json,sys,time,uuid,wave
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from common.asr_wire import encode_context
from common.voice_channel import ChannelState,read_frame
with wave.open(str(ROOT/'deliverables/2026-10-18_stream_playback/chat_input.wav'),'rb') as audio:
    assert (audio.getframerate(),audio.getnchannels(),audio.getsampwidth())==(16000,1,2)
    pcm=audio.readframes(audio.getnframes())
meta=dict(protocol='aura-asr-1',board_boot_id='motion-diagnosis',session_id=uuid.uuid4().hex,
          request_id=uuid.uuid4().hex,capture_id='existing-archived-input',generation=1,
          sample_count=len(pcm)//2,pcm_sha256=hashlib.sha256(pcm).hexdigest(),budget_ms=120000)
conn=http.client.HTTPConnection('192.168.50.1',8792,timeout=125)
state=ChannelState(meta);started=time.monotonic();controls=[];first_audio=None;start=None
try:
    conn.request('POST','/v1/voice/channel',pcm,{'Content-Type':'application/octet-stream',
                 'X-Aura-Asr':encode_context(meta),'X-Aura-Motion':'speech-v1'})
    response=conn.getresponse();assert response.status==200,response.read(1024)
    while not state.ended:
        h,raw=read_frame(response);state.accept(h,raw)
        if h['kind']=='error':raise RuntimeError(h['error'])
        if h['kind']=='start':start=h
        if h['kind']=='control':controls.append(dict(seq=h['seq'],emotion=h['emotion'],action=h['action'],at_sample=h['at_sample']))
        if h['kind']=='audio' and first_audio is None:first_audio=dict(seq=h['seq'],elapsed_ms=(time.monotonic()-started)*1000)
    assert start['speech_motion']=='v1','Production host did not activate motion'
    assert first_audio and controls and controls[0]['seq']<first_audio['seq'] and controls[0]['at_sample']==0
    report=dict(passed=True,actual_asr_llm_tts=True,playback=False,capture=False,playback_ack=False,
                durable_conversation_requested=False,sample_count=state.samples,controls=controls,
                first_pcm_ms=first_audio['elapsed_ms'],reply_sha256=hashlib.sha256(state.text.encode()).hexdigest(),
                source_model=start['llm_model'],num_step=start['num_step'])
    (HERE/'pc_motion_live.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
finally:conn.close()
