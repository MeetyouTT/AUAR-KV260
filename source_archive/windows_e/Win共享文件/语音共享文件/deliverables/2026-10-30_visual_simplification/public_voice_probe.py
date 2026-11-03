"""One existing public WAV through ASR/27B/TTS, RAM receive only, no CID or ACK."""
import hashlib,json,sys,time,uuid,wave
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';sys.path.insert(0,str(A))
from board.runtime.audio.voice_channel import VoiceChannel
source=A/'models/asr/sherpa-onnx-paraformer-zh-2023-09-14/test_wavs/0.wav'
with wave.open(str(source),'rb') as wav:
    assert (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())==(1,2,16000)
    pcm=wav.readframes(wav.getnframes())
token=uuid.uuid4().hex
meta=dict(protocol='aura-asr-1',board_boot_id='public-retirement-probe',session_id=token,
          request_id=token,generation=1,capture_id=token,sample_count=len(pcm)//2,
          pcm_sha256=hashlib.sha256(pcm).hexdigest(),budget_ms=90000)
channel=VoiceChannel('192.168.50.1',visual_question=True)
started=time.monotonic();events=[];first=None
def frame(header,payload):
    global first
    events.append(header['kind'])
    assert not header.get('visual_request'),'Retired generic image request appeared'
    if payload and first is None:first=time.monotonic()-started
try:
    result=channel.exchange(meta,pcm,frame)
    assert result['network_complete'] and result['sample_count']>0 and result['reply_text']
    report=dict(status='PASS',source='existing_upstream_public_wav',input_sha256=meta['pcm_sha256'],
                first_pcm_seconds=first,elapsed_seconds=time.monotonic()-started,
                sample_count=result['sample_count'],pcm_sha256=result['pcm_sha256'],events=events,
                reply_characters=len(result['reply_text']),reply_sha256=hashlib.sha256(result['reply_text'].encode()).hexdigest(),
                microphone_opened=False,physical_playback=False,playback_ack_sent=False,durable_conversation_created=False)
finally:channel.close()
(H/'public_voice_probe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ('status','first_pcm_seconds','sample_count','microphone_opened','playback_ack_sent')}))
