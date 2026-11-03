"""Temporary public-PCM TCP round trip: board client, stock CPU SDK on PC.

This is a bounded transport experiment, not a production service or protocol.
One public sample, one expected board peer, one outstanding 20 ms frame.
"""
import base64,hashlib,json,socket,struct,sys,threading,time
from pathlib import Path
import numpy as np
import sherpa_onnx as s

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]
EXTERNAL=Path('D:/AIModels/audio-frontend-eval-20261021')
sys.path.insert(0,str(HERE));from benchmark import make_cases,pcm
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'));from board_ssh import ssh
config=s.OnlineSpeechDenoiserConfig(model=s.OfflineSpeechDenoiserModelConfig(
    gtcrn=s.OfflineSpeechDenoiserGtcrnModelConfig(model=str(EXTERNAL/'gtcrn_simple.onnx')),
    num_threads=1,provider='cpu'))
sd=s.OnlineSpeechDenoiser(config)
vc=s.VadModelConfig();vc.silero_vad.model=str(EXTERNAL/'silero_vad_v5.onnx')
vc.silero_vad.threshold=.5;vc.silero_vad.min_speech_duration=.18;vc.silero_vad.min_silence_duration=.7
vc.sample_rate=16000;vc.num_threads=1
vad=s.VoiceActivityDetector(vc,buffer_size_in_seconds=25)
for _ in range(16):
    out=sd(np.zeros(320,dtype=np.float32),16000)
    if len(out.samples):vad.accept_waveform(out.samples)
sd.reset();vad.reset()
cases,_=make_cases();samples=next(c['samples'] for c in cases if c['name']=='public_5_fan_like_snr0')
raw=pcm(samples);raw=raw[:len(raw)//640*640]
listener=socket.socket();listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
listener.bind(('0.0.0.0',0));listener.listen(1);listener.settimeout(25)
port=listener.getsockname()[1]
host_result={}


def exact(conn,count):
    parts=bytearray()
    while len(parts)<count:
        part=conn.recv(count-len(parts))
        if not part:raise RuntimeError('Truncated test frame')
        parts.extend(part)
    return bytes(parts)


def serve():
    try:
        with listener:
            connection,peer=listener.accept()
            with connection:
                assert peer[0]=='192.168.50.2'
                connection.settimeout(3);connection.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
                cpu_start=time.process_time();times=[];joined=bytearray();detected=0
                for sequence in range(len(raw)//640):
                    frame=exact(connection,640);joined.extend(frame)
                    began=time.perf_counter()
                    out=sd(np.frombuffer(frame,dtype='<i2').astype(np.float32)/32768,16000)
                    if len(out.samples):vad.accept_waveform(out.samples)
                    active=vad.is_speech_detected();detected+=bool(active)
                    while not vad.empty():vad.pop()
                    times.append((time.perf_counter()-began)*1000)
                    response=json.dumps({'sequence':sequence,'input_samples':(sequence+1)*320,
                                         'speech_active':active}).encode()
                    connection.sendall(struct.pack('!I',len(response))+response)
                assert bytes(joined)==raw
                host_result.update(status='PUBLIC_STREAM_ROUNDTRIP_PASSED',sdk=s.__version__,
                    received_sha256=hashlib.sha256(joined).hexdigest(),frames=len(times),
                    cpu_rtf=(time.process_time()-cpu_start)/(len(raw)/32000),
                    process_ms_p95=float(np.percentile(times,95)),speech_active_frames=detected)
    except Exception as exc:
        host_result.update(status='PUBLIC_STREAM_ROUNDTRIP_FAILED',error_type=type(exc).__name__,error=str(exc)[:500])


thread=threading.Thread(target=serve,daemon=True);thread.start()
remote=r'''
import base64,hashlib,json,socket,struct,time
raw=base64.b64decode(DATA)
def exact(connection,n):
 result=bytearray()
 while len(result)<n:
  part=connection.recv(n-len(result))
  if not part:raise RuntimeError('Truncated test response')
  result.extend(part)
 return bytes(result)
with socket.create_connection(('192.168.50.1',PORT),timeout=3) as connection:
 connection.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1);connection.settimeout(.5)
 rtt=[];began=time.monotonic();late=0;active=0
 for seq in range(len(raw)//640):
  next_at=began+seq*.02
  time.sleep(max(0,next_at-time.monotonic()))
  t=time.monotonic();connection.sendall(raw[seq*640:(seq+1)*640])
  size=struct.unpack('!I',exact(connection,4))[0];assert size<512
  response=json.loads(exact(connection,size));assert response['sequence']==seq
  assert response['input_samples']==(seq+1)*320
  elapsed=(time.monotonic()-t)*1000;rtt.append(elapsed);late+=elapsed>20;active+=bool(response['speech_active'])
 rtt.sort()
print(json.dumps({'frames':len(rtt),'rtt_ms_median':rtt[len(rtt)//2],
 'rtt_ms_p95':rtt[int((len(rtt)-1)*.95)],'rtt_ms_max':max(rtt),
 'roundtrips_over_20ms':late,'wall_seconds':time.monotonic()-began,
 'input_seconds':len(raw)/32000,'sha256':hashlib.sha256(raw).hexdigest(),
 'speech_active_frames':active,'microphone_opened':False,'playback_started':False}))
'''
try:
    remote='DATA='+repr(base64.b64encode(raw).decode())+'\nPORT='+str(port)+'\n'+remote
    board=json.loads(ssh('python3 -B -',remote,timeout=25))
finally:
    thread.join(6)
    listener.close()
assert not thread.is_alive()
result={'host':host_result,'board':board,'temporary_port_closed':True,
        'production_changed':False,'microphone_opened':False,'sample':'public_5_fan_like_snr0',
        'scope':'One paced public-audio stream; no live microphone, cancellation/ownership integration, or field acceptance.'}
(HERE/'stream_transport_probe.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
