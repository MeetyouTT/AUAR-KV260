"""Open the native adjustment dialog; sends no pan movement commands."""
import json,time,urllib.request
base='http://127.0.0.1:8783'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
results=[]
for data in [{'type':'ui_page','page':'vision'},{'type':'pan_dialog'}]:
 request=urllib.request.Request(base+'/api/command',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':base})
 with opener.open(request,timeout=4) as response:value=json.load(response)
 assert value.get('ok'),value
 results.append(value)
time.sleep(.2)
with opener.open(base+'/api/state',timeout=1) as response:state=json.load(response)
assert state['ui_page']=='vision' and state['manual_pan']['state']=='READY'
assert state['manual_pan']['readback']['flags']==0 and state['manual_pan']['readback']['lease_left_ms']==0
print(json.dumps({'native_dialog_open_ack':results,'ui_page':state['ui_page'],'manual_pan':state['manual_pan'],'movement_commands_sent_by_helper':0}),flush=True)
