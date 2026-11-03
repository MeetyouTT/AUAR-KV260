"""Owner-mediated temporary handsfree pause/resume for explicit speaker sampling."""
import json
import time
import urllib.request

ACTION='ACTION_PLACEHOLDER'
base='http://127.0.0.1:8783'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def state():
    with opener.open(base+'/api/state',timeout=3) as response:return json.load(response)
before=state();enabled=before.get('handsfree_dialogue',{}).get('enabled')
if type(enabled) is not bool:raise RuntimeError('No known handsfree owner')
desired=ACTION=='resume'
if ACTION not in ('pause','resume'):raise ValueError('Invalid action')
changed=False
if enabled!=desired:
    if desired and (before.get('playing') or before.get('phase')!='IDLE'):
        raise RuntimeError('Wait for playback before resuming the monitor')
    request=urllib.request.Request(base+'/api/command',data=json.dumps({'type':'conversation_toggle'}).encode(),
        headers={'Origin':base,'Content-Type':'application/json'})
    with opener.open(request,timeout=4) as response:result=json.load(response)
    if not result.get('ok'):raise RuntimeError(result)
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        current=state(); hf=current.get('handsfree_dialogue',{})
        if hf.get('enabled') is desired and (desired or hf.get('microphone_open') is False):
            changed=True;break
        time.sleep(.1)
    else:raise RuntimeError('Owner did not acknowledge requested state')
after=state().get('handsfree_dialogue',{})
print(json.dumps({'action':ACTION,'changed':changed,'before_enabled':enabled,
                  'after_enabled':after.get('enabled'),'microphone_open':after.get('microphone_open')}))
