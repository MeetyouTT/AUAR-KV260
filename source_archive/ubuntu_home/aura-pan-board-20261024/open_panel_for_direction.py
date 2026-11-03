"""Open the existing manual panel without submitting a movement intent."""
import json,time,urllib.request
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def read():
 with op.open(base+'/api/state',timeout=3) as r:return json.load(r)
u=read();m=u['manual_pan'];b=m['readback'];assert u['phase']=='IDLE' and m['state']=='READY' and m['pulse_us']==1425 and b['flags']==0 and b['lease_left_ms']==0 and not m['automatic_following']
request=urllib.request.Request(base+'/api/command',data=json.dumps({'type':'pan_dialog'}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
with op.open(request,timeout=3) as r:assert json.load(r).get('ok')
time.sleep(.4);after=read()['manual_pan'];a=after['readback']
assert after['panel_open'] and after['state']=='READY' and all(a[k]==b[k] for k in ('flags','lease_left_ms','epoch','ack_seq','width_us'))
print(json.dumps({'panel_open':True,'state':after['state'],'pulse_us':after['pulse_us'],'left_sign':after['left_sign'],'flags':a['flags'],'lease_ms':a['lease_left_ms'],'movement_commands_sent':0}))
