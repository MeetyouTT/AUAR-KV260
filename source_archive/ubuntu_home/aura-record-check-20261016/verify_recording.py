"""Rebuild UART responses and independently verify the actual PCM sample."""
import array
import base64
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sys
import wave

work=Path(__file__).resolve().parent
folder=sorted((work/'evidence').glob('*-record-check'))[-1]
result=json.loads((folder/'result.json').read_text())
assert result['complete'] and result['console_echo_restored']
raw=(folder/'serial.raw').read_bytes().decode('utf-8','replace')
begins=re.findall(r'\bBEGIN (MEDIA\d+) (\d+) (\d+)\r?$',raw,re.M)
assert len(begins)==len(result['commands'])
for row,(marker,code,size) in zip(result['commands'],begins):
    parts=re.findall(r'^DATA '+marker+r' (\d+) ([A-Za-z0-9+/=]+)\r?$',raw,re.M)
    assert [int(i) for i,_ in parts]==list(range(len(parts)))
    data=gzip.decompress(base64.b64decode(''.join(value for _,value in parts),validate=True))
    sha=hashlib.sha256(data).hexdigest()
    assert int(code)==row['exit_code']==0 and int(size)==row['bytes']==len(data)
    assert sha==row['sha256'] and re.findall(r'^END '+marker+r' ([0-9a-f]{64})\r?$',raw,re.M)==[sha]
    assert data==(folder/(row['name']+'.output')).read_bytes()

original=json.loads((folder/'response.output').read_bytes())
record=json.loads((folder/'response.json').read_text())
assert record['status']=='PASS_RECORDING_WITH_SIGNAL'
artifact=original['artifacts']['microphone-5s.wav']
data=(folder/'microphone-5s.wav').read_bytes()
assert data==base64.b64decode(artifact['base64'],validate=True)
assert len(data)==artifact['bytes']==160044 and hashlib.sha256(data).hexdigest()==artifact['sha256']
with wave.open(io.BytesIO(data),'rb') as wav:
    assert (wav.getnchannels(),wav.getsampwidth(),wav.getframerate(),wav.getnframes())==(1,2,16000,80000)
    pcm=wav.readframes(wav.getnframes())
assert hashlib.sha256(pcm).hexdigest()==record['independent_capture']['pcm_sha256']
samples=array.array('h',pcm)
if sys.byteorder!='little':samples.byteswap()
peak=max(abs(x) for x in samples)
rms=math.sqrt(sum(x*x for x in samples)/len(samples))
assert peak==record['signal']['peak'] and abs(rms-record['signal']['rms'])<.001
assert sum(x!=0 for x in samples)==record['signal']['nonzero_samples']>0
assert sum(abs(x)>=32767 for x in samples)==record['signal']['clipped_samples']==0
assert record['gui_stop_cancel_passed'] and record['gui_recording']['sample_count']>=48000
final=record['final']
assert final['local_recording']['can_start'] and final['local_recording']['result'] is None
assert final['local_recording']['state']=='CANCELLED' and not final['error']
assert record['camera_before']['pid']==record['camera_after']['pid']
summary={'status':'PASS','verified_uart_responses':len(begins),'wav_sha256':artifact['sha256'],
         'wav_bytes':len(data),'sample_rate_hz':16000,'channels':1,'sample_count':80000,'seconds':5,
         'gui_seconds':record['gui_recording']['duration_seconds'],'signal':record['signal'],
         'gui_stop_cancel_passed':True,'final_page':final['ui_page'],'volume':final['ui_settings']['volume'],
         'physical_finger_touch_tested':False,'asr_tested':False,'speech_intelligibility_assessed':False}
(work/'validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False))
