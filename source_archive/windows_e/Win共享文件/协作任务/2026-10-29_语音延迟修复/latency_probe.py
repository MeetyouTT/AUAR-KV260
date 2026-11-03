import sys,json,time,hashlib,http.client,uuid,wave
from pathlib import Path
H=Path(__file__).resolve().parent
P=H.parents[1]/'语音共享文件'
sys.path.insert(0,str(P/'aura'))
sys.path.insert(0,str(P/'deliverables/2026-10-18_board_dialogue'))
def get(url):
 import urllib.request
 with urllib.request.urlopen(url,timeout=10) as r:return json.load(r)
def save(name,v):
 (H/(name+'.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(v,ensure_ascii=True),flush=True)
phase=sys.argv[1]
if phase in ('before','after'):
 from board_ssh import ssh
 source=(P/'deliverables/2026-10-28_timeline_summaries/capture_board.py').read_text(encoding='utf-8')
 ns={};exec(compile(source.split("value=json.loads(ssh(")[0],'<baseline>','exec'),{'__file__':str(P/'deliverables/2026-10-28_timeline_summaries/capture_board.py')},ns)
 board=json.loads(ssh('python3 -B -',ns['script'],timeout=30))
 v={'time_unix':time.time(),'board':board,'health':get('http://192.168.50.1:8792/health'),'residency':get('http://127.0.0.1:11435/api/ps')}
 save(phase,v)
 assert board['preflight_ready'] and not v['health']['busy'] and not v['health']['dependencies']['tts']['request_active']
elif phase.startswith('test_'):
 from board.runtime.audio.voice_channel import VoiceChannel
 wav=P/'aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14/test_wavs/0.wav'
 with wave.open(str(wav),'rb') as f:pcm=f.readframes(f.getnframes())
 results=[]
 for i in range(2):
  assert not get('http://192.168.50.1:8792/health')['busy']
  ch=VoiceChannel('192.168.50.1');start=time.monotonic();first={};end={};audio=bytearray()
  meta={'protocol':'aura-asr-1','board_boot_id':'latency-public-r1','session_id':uuid.uuid4().hex,'request_id':uuid.uuid4().hex,'generation':0,'capture_id':'official-fixed-wav','sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
  def receive(header,payload):
   kind=header['kind'];first.setdefault(kind,round((time.monotonic()-start)*1000,2))
   if kind=='end':end.update(header)
   if kind=='audio':audio.extend(payload)
  try:
   result=ch.exchange(meta,pcm,receive)
   results.append({'client_first_ms':first,'host_timing':end.get('timing',{}),'samples':result['sample_count'],'reply_text':result['reply_text'],'pcm_sha256':hashlib.sha256(audio).hexdigest(),'playback_ack_sent':False})
  finally:ch.close()
  time.sleep(.5)
 save(phase,{'wav_sha256':hashlib.sha256(wav.read_bytes()).hexdigest(),'context':'fresh independent anonymous session per request; no conversation/profile/ACK','runs':results,'residency':get('http://127.0.0.1:11435/api/ps')})
