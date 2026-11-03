"""Stop the finite controller and close its panel without restarting services."""
import json,time,urllib.request
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get():
 with o.open(base+'/api/state',timeout=3) as r:return json.load(r)
before=get();responses=[]
for typ in ('pan_stop','pan_close'):
 q=urllib.request.Request(base+'/api/command',data=json.dumps({'type':typ}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(q,timeout=3) as r:responses.append(json.load(r))
 time.sleep(.3)
rows=[]
for _ in range(12):
 u=get();v=u['ui_runtime'];m=u['manual_pan'];rows.append({'page':u.get('ui_page'),'preview':v.get('preview_metrics'),'link':v.get('link'),
 'pan':{k:m.get(k) for k in ('state','readback','automatic_following','panel_open')}});time.sleep(.2)
print(json.dumps({'responses':responses,'samples':rows,'video_restore_user_confirmation':'PENDING'}))
