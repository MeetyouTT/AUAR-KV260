"""Inspect one public channel's timing contract without assuming context count."""
import hashlib,json,sys,time,uuid,wave
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';sys.path.insert(0,str(A))
from board.runtime.audio.voice_channel import VoiceChannel
with wave.open(str(H/'public_warmup.wav'),'rb') as f:pcm=f.readframes(f.getnframes())
meta={'protocol':'aura-asr-1','board_boot_id':'public-latency-benchmark','session_id':uuid.uuid4().hex,'request_id':uuid.uuid4().hex,
 'generation':1,'capture_id':'public-context-probe','sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
end={};digest=hashlib.sha256();transcript=''
def receive(h,p):
 global transcript
 if h['kind']=='end':end.update(h)
 if h['kind']=='audio':digest.update(p)
 if h['kind']=='transcript':transcript=h['text']
c=VoiceChannel('192.168.50.1')
try:result=c.exchange(meta,pcm,receive)
finally:c.close()
value={'network_complete':result['network_complete'],'playback_verified':result['playback_verified'],'sample_count':result['sample_count'],
 'hash_match':result['pcm_sha256']==digest.hexdigest(),'public_transcript':transcript,'timing':end.get('timing'),'end_keys':list(end)}
(H/'context_diagnostic.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(value,ensure_ascii=True))
