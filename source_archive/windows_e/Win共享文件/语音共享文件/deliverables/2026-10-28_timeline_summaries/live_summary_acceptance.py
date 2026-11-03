"""Actual ARM voice client, cached VLM digest, isolated probe deletion and stale ACK.

No live microphone, audio playback, accepted playback receipt, or private text
is saved in shared evidence. Only the acceptance's own new frame is removed.
"""
import base64,hashlib,json,subprocess,sys,time,urllib.error,urllib.request,uuid,wave
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'));from board_ssh import ssh
baseline=json.loads((H/'board_baseline.json').read_text(encoding='utf-8'))
assert json.loads((H/'deployment.json').read_text(encoding='utf-8'))['status']=='COMMITTED'
assert not (H/'live_summary_acceptance.json').exists(),'Review the existing receipt and probe cleanup before a fresh acceptance'
def call(path,value=None,port=8812):
    request=urllib.request.Request('http://192.168.50.1:%d%s'%(port,path),data=json.dumps(value).encode() if value is not None else None,
                                  headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=4) as response:return json.load(response)
def events(summary=False):return call('/v1/memory/timeline',{'boot':baseline['boot'],'text':'回顾今天看到了什么' if summary else '今天看到了什么'})
def ps(args):
    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',*args],capture_output=True,timeout=30)
    if result.returncode:raise RuntimeError((result.stdout+result.stderr).decode('utf-8',errors='replace')[-500:])
    return result.stdout.decode('utf-8-sig',errors='replace')
report={'status':'RUNNING','scope':'one own camera probe, actual ARM synthetic question, actual 27B/TTS; no mic/playback/private text archive',
    'board_boot':baseline['boot'],'checks':[]}
def save():(H/'live_summary_acceptance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
initial=events();report['original_event_ids']=[r['event_id'] for r in initial['events']];save()
script=r'''
import base64,json,sys,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as response:s=json.load(response)
assert s['phase']=='IDLE' and s['handsfree_dialogue']['enabled'] is False and s['handsfree_dialogue']['microphone_open'] is False
assert s['manual_pan']['automatic_following'] is False and s['manual_pan']['pulse_us']==PULSE
sys.path.insert(0,AURA)
from board.runtime.visual_capture import current_frame
frame,jpeg=current_frame(BOOT)
request=urllib.request.Request('http://192.168.50.1:8812/v1/observations',data=json.dumps({'frame':frame,'jpeg_base64':base64.b64encode(jpeg).decode()}).encode(),
    headers={'Content-Type':'application/json'})
with urllib.request.urlopen(request,timeout=4) as response:value=json.load(response)
assert value['accepted'];print(json.dumps({'frame_id':frame['frame_id'],'epoch':frame['camera_epoch'],'bytes_in_ram':len(jpeg)}))
'''.replace('BOOT',repr(baseline['boot'])).replace('PULSE',repr(baseline['pan']['pulse_us'])).replace('AURA',repr(baseline['actual_runtime']+'/aura'))
report['submission']=json.loads(ssh('python3 -B -',script,timeout=15));save()
until=time.monotonic()+25;probe=None
while time.monotonic()<until:
    rows=events()['events']
    probe=next((r for r in rows if r.get('boot')==baseline['boot'] and r.get('camera_epoch')==report['submission']['epoch']
        and r['first_frame']==r['last_frame']==report['submission']['frame_id']),None)
    if probe:break
    time.sleep(.4)
assert probe,'New isolated observation not found'
report['probe_event']={'event_id':probe['event_id'],'received':probe['start_utc'],'summary_sha256':hashlib.sha256(probe['text'].encode()).hexdigest()};save()
until=time.monotonic()+12;cached=None
while time.monotonic()<until:
    cached=events(True)
    if cached.get('background_digest_used') and any(r.get('source_count',0)>=len(report['original_event_ids'])+1 for r in cached['events']):break
    time.sleep(.4)
assert cached and cached.get('background_digest_used')
assert any(r.get('source_count',0)>=len(report['original_event_ids'])+1 for r in cached['events'])
report['checks'].append({'name':'actual_camera_background_day_digest','status':'PASS','sources':[r['source_count'] for r in cached['events']],
    'current_flags':[r['current'] for r in cached['events']]});save()
audio=H/'summary_question.wav'
ps(['-File',str(H/'synthesize_question.ps1'),'-Text','回顾今天看到了什么','-OutputPath',str(audio)])
with wave.open(str(audio),'rb') as source:
    assert (source.getframerate(),source.getnchannels(),source.getsampwidth())==(16000,1,2)
    pcm=source.readframes(source.getnframes())
meta={'protocol':'aura-asr-1','board_boot_id':baseline['boot'],'session_id':uuid.uuid4().hex,'request_id':uuid.uuid4().hex,'generation':1,
    'capture_id':'synthetic-summary-acceptance','sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
script=r'''
import base64,hashlib,json,sys,time
sys.path.insert(0,AURA)
from board.runtime.audio.voice_channel import VoiceChannel
pcm=base64.b64decode(PCM);meta=META;channel=VoiceChannel('192.168.50.1',visual_question=True)
started=time.monotonic();first_audio=None;transcript='';visual_requested=False;end={};kinds=set();digest=hashlib.sha256()
def receive(header,payload):
 global first_audio,transcript,visual_requested
 kinds.add(header['kind'])
 if header['kind']=='transcript':transcript=header['text'];visual_requested=bool(header.get('visual_request'))
 if header['kind']=='audio':
  digest.update(payload)
  if first_audio is None:first_audio=round((time.monotonic()-started)*1000,2)
 if header['kind']=='end':end.update(header)
try:
 result=channel.exchange(meta,pcm,receive)
 assert result['sample_count']>0 and digest.hexdigest()==result['pcm_sha256'] and not result['playback_verified']
 print(json.dumps({'first_pcm_ms':first_audio,'transcript':transcript,'reply_characters':len(result['reply_text']),
  'sample_count':result['sample_count'],'pcm_sha256':result['pcm_sha256'],'network_complete':result['network_complete'],
  'private_reply_sha256':hashlib.sha256(result['reply_text'].encode()).hexdigest(),
  'history_messages':end.get('timing',{}).get('history_messages'),'current_picture_requested':visual_requested,
  'playback_ack_sent':False}))
finally:channel.close()
'''.replace('AURA',repr(baseline['actual_runtime']+'/aura')).replace('PCM',repr(base64.b64encode(pcm).decode())).replace('META',repr(meta))
voice=json.loads(ssh('python3 -B -',script,timeout=135));assert not voice['current_picture_requested'] and '回顾' in voice['transcript']
assert voice['history_messages']>0
report['voice']=voice;report['context']=meta;report['checks'].append({'name':'actual_arm_cached_summary_voice','status':'PASS'});save()
# WMI gives the same real AppData view as the serving process.
python=r'C:\Users\35870\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
helper=H/'remove_probe.py'
command='"'+python+'" -B "'+str(helper)+'"'
launch="$setup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0};"+\
    "$p=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='"+command+"';ProcessStartupInformation=$setup};if($p.ReturnValue -ne 0){throw 'Probe cleanup launch failed'}"
ps(['-Command',launch]);until=time.monotonic()+15
while time.monotonic()<until and not (H/'probe_removed.json').exists():time.sleep(.2)
removed=json.loads((H/'probe_removed.json').read_text(encoding='utf-8'));assert removed['status']=='PASS',removed
after=events();ids=[r['event_id'] for r in after['events']]
assert probe['event_id'] not in ids and set(report['original_event_ids'])<=set(ids)
report['cleanup']=removed;report['checks'].append({'name':'only_probe_removed_original_sources_preserved','status':'PASS'});save()
ack={'context':meta,'voice_sample_count':voice['sample_count'],'pcm_sha256':voice['pcm_sha256']}
try:
    call('/v1/voice/channel/played',ack,port=8792)
    raise AssertionError('Stale visual-source ACK was accepted')
except urllib.error.HTTPError as exc:
    assert exc.code==400
    report['checks'].append({'name':'late_ack_rejected_after_source_forget','status':'PASS','http':400})
report.update(status='PASS',images_persisted=False,microphone_opened=False,physical_audio_played=False,successful_playback_ack=False)
save();print(json.dumps({'status':report['status'],'checks':report['checks'],'first_pcm_ms':voice['first_pcm_ms'],'probe_removed':True}))
