"""Maintenance-only real selected-voice echo check; keep microphone PCM in RAM."""
import audioop,json,sys,time
import numpy as np
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'aura'))
from tools.gstreamer_audio import GStreamerAudioOutput
from tools.barge_in_capture import BargeInCapture
from board.runtime.audio.automatic_capture import SpeechEndpoint
from board.runtime.audio.echo_cancel import SpeexEcho
from tools.selected_voice_service import VoiceWorker
from board.runtime.character import DEMO_LINES
voice=VoiceWorker(root/'deliverables/2026-10-06_xilan_live',cached_only=True)
clip=voice.generate(DEMO_LINES[0]['text']);voice.close()
metrics={'input_rms':[],'clean_rms':[],'speech_starts':0,'baseline_speech_starts':0};echoes=[]
phase=['baseline'];last_hot=[time.monotonic()];ref_frames=[];mic_frames=[];levels=[]
class Echo(SpeexEcho):
 def __init__(self):super().__init__();echoes.append(self);self.diag_rate=None
 def reference(self,raw,at,sequence):
  pcm,self.diag_rate=audioop.ratecv(raw,2,1,24000,16000,self.diag_rate)
  ref_frames.append((at,np.frombuffer(pcm,dtype='<i2').copy()))
  super().reference(raw,at,sequence)
 def process(self,raw):
  clean=super().process(raw)
  metrics['input_rms'].append(audioop.rms(raw,2));metrics['clean_rms'].append(audioop.rms(clean,2))
  if phase[0]=='playback':
   mic_frames.append((time.monotonic(),np.frombuffer(raw,dtype='<i2').copy()))
   levels.append((time.monotonic(),audioop.rms(raw,2),audioop.rms(clean,2)))
  return clean
class ProbeCapture(BargeInCapture):
 def _read_pcm(self,process):
  endpoint=self.endpoint
  try:
   while not self._cancelled:
    raw=process.stdout.read(640)
    if len(raw)!=640:
     if self._cancelled:return b''
     raise RuntimeError('Probe microphone ended')
    clean=self.echo.process(raw)
    if not self.echo.healthy():last_hot[0]=time.monotonic();continue
    if audioop.rms(clean,2)>=328:last_hot[0]=time.monotonic()
    active=endpoint.active;result=endpoint.feed(clean)
    if endpoint.active and not active:
     key='speech_starts' if phase[0]=='playback' else 'baseline_speech_starts'
     metrics[key]+=1
    if result is not None:self._new_endpoint();endpoint=self.endpoint
   return b''
  finally:self._release_echo()
output=capture=None
try:
 output=GStreamerAudioOutput(device='hw:CARD=MCP01,DEV=0',persistent=True,echo_reference=True)
 capture=ProbeCapture(output,echo_factory=Echo);capture.start()
 deadline=time.monotonic()+20
 while time.monotonic()-last_hot[0]<1.:
  if time.monotonic()>=deadline:raise RuntimeError('No quiet baseline before playback; no echo conclusion')
  if capture.snapshot()['state']=='ERROR':raise RuntimeError(capture.snapshot()['error'])
  time.sleep(.02)
 trigger_at=None
 if len(sys.argv)>2:
  control=Path(sys.argv[2]);control.with_suffix('.ready').write_text(json.dumps({'ready':True,'pid':__import__('os').getpid()}))
  deadline=time.monotonic()+180
  while not control.with_suffix('.go').exists():
   if time.monotonic()>=deadline:raise RuntimeError('Controlled test start timed out')
   time.sleep(.02)
  trigger_at=time.monotonic()
 phase[0]='playback';test_start=time.monotonic();end=test_start+9.;plays=0
 while time.monotonic()<end:
  if capture.snapshot()['state']=='ERROR':raise RuntimeError(capture.snapshot()['error'])
  if not output.active or output.finished():output.play(clip['path'],sha256=clip['sha256']);plays+=1
  time.sleep(.02)
 echo=echoes[0]
 correlation=[]
 if mic_frames and ref_frames:
  mic=np.concatenate([r[1] for r in mic_frames]).astype(float)
  ref=np.concatenate([r[1] for r in ref_frames]).astype(float)
  offset=round((mic_frames[0][0]-ref_frames[0][0])*16000)
  for lag in range(-250,251,10):
   shift=offset-round(lag*16);lo=max(0,-shift);hi=min(len(mic),len(ref)-shift)
   if hi-lo<1600:continue
   a=mic[lo:hi];b=ref[lo+shift:hi+shift]
   correlation.append({'delay_ms':lag,'correlation':round(float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-8)),4)})
 blocks=[]
 for second in range(9):
  block=[r for r in levels if second<=r[0]-test_start<second+1]
  blocks.append({'second':second,'input_mean':round(float(np.mean([r[1] for r in block])),2) if block else None,
   'clean_mean':round(float(np.mean([r[2] for r in block])),2) if block else None})
 def stats(values):
  values=sorted(values);return {'frames':len(values),'mean':round(sum(values)/len(values),2) if values else 0,
   'p95':values[min(len(values)-1,int(len(values)*.95))] if values else 0,'max':max(values) if values else 0}
 result={'passed':metrics['speech_starts']==0 and echo.capture_frames>=200 and echo.reference_frames>=200
  and echo.healthy(),'speech_starts':metrics['speech_starts'],'plays':plays,
  'baseline_speech_starts':metrics['baseline_speech_starts'],
  'input':stats(metrics['input_rms']),'clean':stats(metrics['clean_rms']),
  'reference_frames':echo.reference_frames,'reference_gaps':echo.reference_gaps,'healthy':echo.healthy(),
  'prewarmed_start_control':trigger_at is not None,
  'trigger_to_playback_loop_ms':round((test_start-trigger_at)*1000) if trigger_at is not None else None,
  'playback_loop_seconds':round(time.monotonic()-test_start,2),
  'strongest_reference_lags':sorted(correlation,key=lambda r:abs(r['correlation']),reverse=True)[:5],'blocks':blocks,
  'microphone_audio_saved':False,'actual_asr_or_model_called':False,
  'scope':'Real selected-voice loudspeaker echo only; no human interruption acceptance'}
 print('PROBE '+json.dumps(result),flush=True)
finally:
 if capture:capture.close()
 if output:output.close()
