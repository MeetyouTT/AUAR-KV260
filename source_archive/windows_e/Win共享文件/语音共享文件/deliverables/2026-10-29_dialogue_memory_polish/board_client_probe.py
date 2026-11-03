"""Existing ARM client over Ethernet; public PCM in RAM, no mic or playback."""
import base64,hashlib,json,subprocess,sys,time,uuid,wave
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'));from board_ssh import ssh
assert not (H/'board_probe.json').exists()
b=json.loads((H/'board_baseline.json').read_text(encoding='utf-8'))
report={'status':'RUNNING','started_unix':time.time(),'conversation_id':uuid.uuid4().hex,'session_id':uuid.uuid4().hex,'turns':[],'mic':False,'playback':False}
def save():(H/'board_probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
try:
    for index,(label,name) in enumerate([('set','fixed_fact_setup.wav'),('query','fixed_fact_question.wav')],1):
        with wave.open(str(H/name),'rb') as f:pcm=f.readframes(f.getnframes())
        meta={'protocol':'aura-asr-1','board_boot_id':b['boot'],'session_id':report['session_id'],'request_id':uuid.uuid4().hex,'generation':index,
          'capture_id':'public-ethernet-memory','sample_count':len(pcm)//2,'pcm_sha256':hashlib.sha256(pcm).hexdigest(),'budget_ms':120000}
        row={'label':label,'context':meta};report['turns'].append(row);save()
        script=r'''
import base64,hashlib,json,sys,time,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as response:s=json.load(response)
assert s['phase']=='IDLE' and not s['playing'] and s['audio_output_state']=='IDLE_READY'
assert s['handsfree_dialogue']['enabled'] is False and s['handsfree_dialogue']['microphone_open'] is False and s['manual_pan']['automatic_following'] is False
sys.path.insert(0,AURA)
from board.runtime.audio.voice_channel import VoiceChannel
pcm=base64.b64decode(PCM);meta=META;channel=VoiceChannel('192.168.50.1')
began=time.monotonic();first=None;digest=hashlib.sha256();end={}
def receive(header,payload):
 global first
 if header['kind']=='audio':
  digest.update(payload)
  if first is None:first=round((time.monotonic()-began)*1000,2)
 if header['kind']=='end':end.update(header)
try:
 value=channel.exchange(meta,pcm,receive,conversation=CID)
 assert value['network_complete'] and value['pcm_sha256']==digest.hexdigest() and not value['playback_verified']
 print(json.dumps({'first_pcm_ms':first,'reply':value['reply_text'],'sample_count':value['sample_count'],'backend':end.get('timing',{}).get('llm',{}).get('backend'),'playback_ack_sent':False}))
finally:channel.close()
'''.replace('BOOT',repr(b['boot'])).replace('AURA',repr(b['actual_runtime']+'/aura')).replace('PCM',repr(base64.b64encode(pcm).decode())).replace('META',repr(meta)).replace('CID',repr(report['conversation_id']))
        result=json.loads(ssh('python3 -B -',script,timeout=135));row.update(result);row['status']='PASS'
        if label=='query':assert '绿色' in result['reply'] and result['backend']=='conversation_memory_command'
        save()
    report['status']='PASS'
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
finally:
    save()
    python=r'C:\Users\35870\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    command='"'+python+'" -B "'+str(H/'cleanup_public_probe.py')+'" --report board_probe.json'
    launch="$s=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0};"+"$p=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='"+command+"';ProcessStartupInformation=$s};if($p.ReturnValue -ne 0){throw 'Board public cleanup launch failed'}"
    try:
        subprocess.run(['powershell.exe','-NoProfile','-Command',launch],check=True,capture_output=True,timeout=15)
        until=time.monotonic()+20
        while not (H/'board_probe_cleanup.json').exists() and time.monotonic()<until:time.sleep(.1)
        value=json.loads((H/'board_probe_cleanup.json').read_text(encoding='utf-8'));assert value['status']=='PASS',value
        report['cleanup']=value
    except Exception as exc:report.update(status='FAIL',cleanup_error=str(exc))
    save()
print(json.dumps({'status':report['status'],'first_pcm_ms':[r.get('first_pcm_ms') for r in report['turns']],'cleanup':report.get('cleanup')},ensure_ascii=True))
raise SystemExit(0 if report['status']=='PASS' else 1)

