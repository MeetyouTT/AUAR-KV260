"""Validate real 20-second auto-stop and retain a clean pending recording."""
import glob
import json
import subprocess
import time
import urllib.request


def api(data=None):
    base='http://127.0.0.1:8783'
    request=base+'/api/state' if data is None else urllib.request.Request(base+'/api/command',
        data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':base})
    with urllib.request.urlopen(request,timeout=4) as r:return json.load(r)


assert api()['local_recording']['can_start']
request=api({'type':'service_action','action':'record_start'})
deadline=time.monotonic()+25
observed=False
samples=[]
while time.monotonic()<deadline:
    state=api();recording=state['local_recording']
    samples.append({'at':time.monotonic(),'state':recording['state'],'sample_count':recording['sample_count']})
    if recording['state']=='RECORDING':observed=True
    if observed and recording['state']=='READY':break
    if recording['state']=='ERROR':raise AssertionError(recording)
    time.sleep(.2)
assert observed and recording['state']=='READY',recording
assert recording['result']['sample_count']==320000 and recording['result']['duration_seconds']==20
owners=subprocess.run(['fuser']+glob.glob('/dev/snd/pcm*'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=3)
assert owners.returncode==1,owners.stdout
assert recording['can_start'] and not recording['can_stop']
print(json.dumps({'status':'PASS_REAL_20_SECOND_AUTO_STOP','request':request,'samples':samples,
    'recording':recording,'no_audio_owner_after':True,'settings':state['ui_settings'],
    'addresses':subprocess.check_output(['ip','-j','address'],text=True)},ensure_ascii=False))
