"""Existing camera -> VLM -> timeline -> hub restart -> same persisted event.

Images and observation text are not copied into shared evidence.
"""
import hashlib,json,subprocess,sys,time,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
baseline=json.loads((H/'runtime_current.json').read_text(encoding='utf-8'))
assert baseline['ready_for_readonly_completion'] and baseline['component_pins_unchanged'] and not baseline['hash_mismatches']
def http(path,value=None,port=8812):
    request=urllib.request.Request('http://192.168.50.1:%d%s'%(port,path),
        data=json.dumps(value).encode() if value is not None else None,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=3) as response:return json.load(response)
def ps(args):
    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass',*args],capture_output=True,timeout=30)
    if result.returncode:raise RuntimeError((result.stdout+result.stderr).decode('utf-8',errors='replace')[-500:])
    return result.stdout.decode('utf-8-sig')
def gate():
    script=r'''
import json,subprocess,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as response:s=json.load(response)
assert s['phase']=='IDLE' and not s['playing'] and s['audio_output_state']=='IDLE_READY'
assert s['handsfree_dialogue']['enabled'] is False and s['handsfree_dialogue']['microphone_open'] is False
assert s['manual_pan']['automatic_following'] is False and s['manual_pan']['pulse_us'] is None
assert subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True).strip()==CAMERA
print('IDLE_PAUSED')
'''.replace('BOOT',repr(baseline['boot'])).replace('CAMERA',repr(baseline['camera_service']['MainPID']))
    assert ssh('python3 -B -',script).strip()=='IDLE_PAUSED'
def recall():return http('/v1/memory/timeline',{'boot':baseline['boot'],'text':'今天看到了什么'})['events']
report={'scope':'one explicit current-frame observation; no microphone/playback/motion; no image or summary in shared evidence',
        'status':'RUNNING','board_boot':baseline['boot']}
def save():(H/'live_persistence.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
gate();voice=http('/health',port=8792);report['voice_fingerprint']=voice['source_fingerprint'];report['before_hub_pid']=http('/health')['pid'];save()
script=r'''
import base64,json,sys,urllib.request
sys.path.insert(0,AURA)
from board.runtime.visual_capture import current_frame
frame,jpeg=current_frame(BOOT)
raw=json.dumps({'frame':frame,'jpeg_base64':base64.b64encode(jpeg).decode()}).encode()
request=urllib.request.Request('http://192.168.50.1:8812/v1/observations',data=raw,headers={'Content-Type':'application/json'})
with urllib.request.urlopen(request,timeout=3) as response:result=json.load(response)
assert result['accepted']
print(json.dumps({'frame_id':frame['frame_id'],'epoch':frame['camera_epoch'],'bytes_in_ram':len(jpeg),'accepted':True}))
'''.replace('AURA',repr(baseline['actual_runtime']+'/aura')).replace('BOOT',repr(baseline['boot']))
report['submission']=json.loads(ssh('python3 -B -',script));save()
until=time.monotonic()+22;event=None
while time.monotonic()<until:
    rows=recall()
    event=next((r for r in rows if r['boot']==baseline['boot'] and r['camera_epoch']==report['submission']['epoch']
                and r['first_frame']<=report['submission']['frame_id']<=r['last_frame']),None)
    if event:break
    time.sleep(.4)
if event is None:raise RuntimeError('New observation not present: '+json.dumps(http('/health')))
report['stored']={'event_id':event['event_id'],'start_utc':event['start_utc'],'end_utc':event['end_utc'],
    'time_basis':event['time_basis'],'source':event['source'],'current':event['current'],
    'summary_sha256':hashlib.sha256(event['text'].encode()).hexdigest(),'summary_characters':len(event['text'])}
assert event['current'] is False and event['time_basis']=='host_received';save()
gate();report['stop']=json.loads(ps(['-File',str(H/'manage_owned.ps1'),'-Group','hub','-Stop']));save()
ps(['-File',str(H.parent/'2026-10-28_device_skills/start_devices.ps1')])
until=time.monotonic()+60
while time.monotonic()<until:
    try:
        health=http('/health')
        if health['speaker_ready']:break
    except (OSError,ValueError):pass
    time.sleep(.4)
else:raise TimeoutError('CPU hub restart failed; recover through start_devices.ps1')
restored=next((r for r in recall() if r['event_id']==event['event_id']),None)
assert restored and hashlib.sha256(restored['text'].encode()).hexdigest()==report['stored']['summary_sha256']
assert http('/health',port=8792)['source_fingerprint']==report['voice_fingerprint']
gate();report.update(status='PASS',after_hub_pid=health['pid'],event_survived_restart=True,
    actual_camera_owner_preserved=True,microphone_opened=False,images_persisted=False)
save();print(json.dumps(report))
