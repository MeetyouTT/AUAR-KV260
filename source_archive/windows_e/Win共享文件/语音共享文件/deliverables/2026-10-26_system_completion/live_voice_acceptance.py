"""Use official bundled test WAV only; receive audio without any playback/ACK."""
import hashlib
import http.client
import json
from pathlib import Path
import sys
import time
import uuid
import wave

HERE=Path(__file__).resolve().parent
AURA=HERE.parents[1]/'aura'
sys.path.insert(0,str(AURA))
from board.runtime.audio.voice_channel import VoiceChannel
from board.runtime.audio.remote_frontend import RemoteSpeechGate
import numpy as np

report={'scope':'public prerecorded input; no microphone, playback or durable conversation',
        'started_unix':time.time(),'checks':[]}
def save():
    (HERE/'live_voice_acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def health(port):
    c=http.client.HTTPConnection('192.168.50.1',port,timeout=3)
    try:
        c.request('GET','/health');r=c.getresponse();return {'http':r.status,'body':json.loads(r.read(32768))}
    finally:c.close()
def check(name,fn):
    began=time.monotonic();row={'name':name}
    try:row.update(status='PASS',result=fn())
    except Exception as exc:row.update(status='FAIL',error=type(exc).__name__+': '+str(exc)[:350])
    row['seconds']=round(time.monotonic()-began,3);report['checks'].append(row);save()
    print(json.dumps(row,ensure_ascii=True),flush=True)

source=AURA/'models/asr/sherpa-onnx-paraformer-zh-2023-09-14/test_wavs/0.wav'
with wave.open(str(source),'rb') as f:
    assert (f.getnchannels(),f.getsampwidth(),f.getframerate())==(1,2,16000)
    pcm=f.readframes(f.getnframes())
report['public_sample']={'path':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                         'samples':len(pcm)//2}
session=uuid.uuid4().hex
def turn(cancel=False):
    ch=VoiceChannel('192.168.50.1');began=time.monotonic();audio=bytearray();kinds={};first={};end={}
    meta={'protocol':'aura-asr-1','board_boot_id':'automatic-public-test','session_id':session,
          'request_id':uuid.uuid4().hex,'generation':len(report['checks']),
          'capture_id':'official-asr-test-wav','sample_count':len(pcm)//2,
          'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
    def receive(header,payload):
        kind=header['kind'];kinds[kind]=kinds.get(kind,0)+1
        first.setdefault(kind,round((time.monotonic()-began)*1000,2))
        if kind=='audio':audio.extend(payload)
        if kind=='end':end.update(header)
        if cancel and kind=='text':ch.cancel()
    try:
        result=ch.exchange(meta,pcm,receive)
        assert not cancel,'Cancelled turn unexpectedly completed'
        assert result['network_complete'] and not result['playback_verified']
        assert result['sample_count']>0
        assert hashlib.sha256(audio).hexdigest()==result['pcm_sha256']
        return {'frames':kinds,'first_ms':first,'samples':result['sample_count'],
                'pcm_sha256':result['pcm_sha256'],'reply_characters':len(result['reply_text']),
                'host_timing':end.get('timing',{}),'playback_ack_sent':False}
    except InterruptedError:
        if not cancel:raise
        assert kinds.get('text'), 'Cancelled before text'
        return {'cancelled':True,'frames':kinds,'first_ms':first,'playback_ack_sent':False}
    finally:ch.close()
def ready():
    rows={str(p):health(p) for p in (8791,8792)}
    assert all(x['http']==200 and x['body'].get('ready') for x in rows.values())
    return rows
def wait_unbusy():
    until=time.monotonic()+8
    while time.monotonic()<until:
        h=health(8792)
        if not h['body'].get('busy'):return h
        time.sleep(.1)
    raise TimeoutError('Model lock still busy after cancellation')
def frontend():
    gate=RemoteSpeechGate({'enabled':True,'host':'192.168.50.1','port':8795,'timeout_ms':180})
    times=[];speech=0
    values=np.frombuffer(pcm,dtype='<i2').astype(np.float32)/32768
    values=np.concatenate([values,np.zeros(16000,dtype=np.float32)])
    try:
        deadline=time.monotonic()
        for offset in range(0,len(values)-319,320):
            pause=deadline-time.monotonic()
            if pause>0:time.sleep(pause)
            before=time.monotonic();speech+=bool(gate(values[offset:offset+320]));times.append((time.monotonic()-before)*1000)
            deadline+=.02
        return {'frames':len(times),'speech_frames':speech,'rpc_p95_ms':round(float(np.percentile(times,95)),3),
                'rpc_max_ms':round(max(times),3),'over_20ms':sum(x>20 for x in times),
                'real_time_wall_seconds':round(time.monotonic()-(deadline-len(times)*.02),3)}
    finally:gate.close()

check('initial_health',ready)
check('actual_public_asr_llm_tts_receive',turn)
check('cancel_after_first_text',lambda:turn(cancel=True))
check('model_lock_released',wait_unbusy)
check('actual_recovery_next_turn',turn)
check('paced_frontend_public_audio',frontend)
check('final_health',ready)
report['finished_unix']=time.time()
report['status']='PASS' if all(x['status']=='PASS' for x in report['checks']) else 'FAIL'
save()
raise SystemExit(0 if report['status']=='PASS' else 1)
