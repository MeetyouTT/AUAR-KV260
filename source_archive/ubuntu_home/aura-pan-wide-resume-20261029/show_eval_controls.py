import json,urllib.request
base='http://127.0.0.1:8783';op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get():
 with op.open(base+'/api/state',timeout=3) as f:return json.load(f)
def command(data):
 req=urllib.request.Request(base+'/api/command',data=json.dumps(data).encode(),headers={'Origin':base,'Content-Type':'application/json'})
 with op.open(req,timeout=4) as f:return json.load(f)
u=get();m=u['manual_pan'];assert [m['minimum_us'],m['maximum_us']]==[500,2500]
replies=[]
if m['state']=='READY' and not m['automatic_following']:
 replies.append(command({'type':'ui_page','page':'vision'}))
 replies.append(command({'type':'pan_dialog'}))
u=get();m=u['manual_pan']
print(json.dumps({'presentation_only':True,'replies':replies,'page':u['ui_page'],'panel_open':m['panel_open'],'state':m['state'],'range_us':[m['minimum_us'],m['maximum_us']],'pulse_us':m['pulse_us'],'automatic_following':m['automatic_following'],'motion_commands_sent':0}))
