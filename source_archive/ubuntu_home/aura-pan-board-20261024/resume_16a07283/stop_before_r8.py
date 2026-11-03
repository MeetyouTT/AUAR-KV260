import json,time,urllib.request
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def read():
 with o.open(base+'/api/state',timeout=3) as r:return json.load(r)['manual_pan']
before=read();assert before['automatic_following'] and 'continuous-v10r7/' in before['face_follow']['report']
request=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_stop"}',headers={'Origin':base,'Content-Type':'application/json'})
with o.open(request,timeout=3) as r:reply=json.load(r)
end=time.monotonic()+8
while time.monotonic()<end:
 after=read()
 if not after['automatic_following'] and after['state']=='READY':break
 time.sleep(.1)
assert after['state']=='READY' and not after['automatic_following'] and after['readback']['flags']==0 and after['readback']['lease_left_ms']==0,after
print(json.dumps({'status':'R7_STOPPED_FOR_R8','manual':after,'reply':reply}))
