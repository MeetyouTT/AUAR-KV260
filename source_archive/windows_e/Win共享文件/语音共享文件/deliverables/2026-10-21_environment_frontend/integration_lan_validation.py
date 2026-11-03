"""Paced public PCM through the final service and real board client; no mic."""
import base64,json,sys,threading,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[1]
sys.path.insert(0,str(PROJECT/'aura'));sys.path.insert(0,str(HERE))
from tools.audio_frontend_host import Pipeline,FrontendServer
from benchmark import make_cases,pcm
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
candidate=json.loads((HERE/'integration_candidate.json').read_text())
server=FrontendServer(('192.168.50.1',0),[Pipeline('D:/AIModels/audio-frontend-eval-20261021') for _ in range(2)])
thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);thread.start()
cases,_=make_cases();case=next(c for c in cases if c['name']=='public_5_fan_like_snr0');raw=pcm(case['samples'])
remote=r"""
import base64,json,sys,time
import numpy as np
sys.path.insert(0,ROOT+'/aura')
from board.runtime.audio.remote_frontend import RemoteSpeechGate,health
from board.runtime.audio.automatic_capture import SpeechEndpoint
config={'enabled':True,'host':'192.168.50.1','port':PORT,'timeout_ms':180}
raw=base64.b64decode(DATA);rows=[]
for onset in (180,240):
 gate=RemoteSpeechGate(config);endpoint=SpeechEndpoint(frame_classifier=gate,pre_roll_ms=500)
 endpoint.vad.config.min_speech_ms=onset;endpoint.start_frames=onset//20
 endpoint.ring=__import__('collections').deque(maxlen=endpoint.pre_frames+endpoint.start_frames)
 began=time.monotonic();rtt=[];started=[];result=None
 try:
  for offset in range(0,len(raw)-639,640):
   time.sleep(max(0,began+offset/32000-time.monotonic()))
   active=endpoint.active;t=time.monotonic();result=endpoint.feed(raw[offset:offset+640]);rtt.append((time.monotonic()-t)*1000)
   if endpoint.active and not active:started.append((offset+640)/32000)
   if result is not None:
    assert raw[offset+640-len(result):offset+640]==result;break
  assert result is not None and len(started)==1
  rows.append({'onset_ms':onset,'frames':len(rtt),'speech_starts':started,'original_pcm_exact':True,
   'roundtrip_ms_p95':float(np.percentile(rtt,95)),'roundtrip_ms_max':max(rtt),'over_20ms':sum(x>20 for x in rtt),
   'wall_seconds':time.monotonic()-began,'frontend':gate.public()})
 finally:gate.close()
 time.sleep(.1)
print(json.dumps({'rows':rows,'health_after':health(config),'microphone_opened':False,'playback_started':False}))
"""
remote='ROOT='+repr(candidate['runtime'])+'\nPORT='+str(server.server_address[1])+'\nDATA='+repr(base64.b64encode(raw).decode())+'\n'+remote
began_cpu=time.process_time()
try:result=json.loads(ssh('python3 -B -',remote,timeout=45))
finally:server.shutdown();server.server_close();thread.join(2)
result.update(host_cpu_seconds=time.process_time()-began_cpu,temporary_server_closed=True,sample=case['name'],scope='Final native service/client, paced public stream; no live field acceptance.')
(HERE/'integration_lan_validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
