"""Start the user-requested face trial with an independent 180s GUI STOP timer."""
import json,subprocess,time,urllib.request
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def command(kind):
 q=urllib.request.Request(base+'/api/command',data=json.dumps({'type':kind}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
 with op.open(q,timeout=3) as r:return json.load(r)
u=get(8783,'/api/state');m=u['manual_pan'];h=get(8790,'/health');s=h['dpu_schedule']
assert not s['owner_fenced'] and h['identity']['ready']
assert m.get('automatic_following') or m['state']=='READY' and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
stop_code="import json,urllib.request; b='http://127.0.0.1:8783'; q=urllib.request.Request(b+'/api/command',data=b'{\"type\":\"pan_stop\"}',headers={'Origin':b,'Content-Type':'application/json'}); o=urllib.request.build_opener(urllib.request.ProxyHandler({})); r=o.open(q,timeout=4); assert json.load(r).get('ok')"
unit='aura-face-pan-human-stop-'+str(time.monotonic_ns())
q=subprocess.run(['systemd-run','--quiet','--collect','--unit='+unit,'--on-active=180s','--timer-property=AccuracySec=1s','/usr/bin/python3','-B','-c',stop_code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=6)
assert q.returncode==0,q.stderr[-500:]
try:
 ack={'ok':True,'already_running':True} if m.get('automatic_following') else command('pan_face_follow')
 assert ack.get('ok'),ack
except BaseException:
 subprocess.run(['systemctl','stop',unit+'.timer'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 raise
time.sleep(.7);u=get(8783,'/api/state');face=get(8790,'/v1/motion/face/observation')
print(json.dumps({'status':'HUMAN_FACE_TEST_STARTED','stop_after_s':180,'stop_timer':unit+'.timer','ack':ack,
 'manual':u['manual_pan'],'face_state':face['state'],'face_box':face.get('target',{}).get('box') if face.get('target') else None,
 'preview':u['ui_runtime'].get('preview_metrics'),'camera_pid':h['pid'],'primary_before':s['primary_period_overruns'],
 'optional_before':{k:s['optional'][k]['overruns'] for k in ('yunet','sface')},'physical_human_acceptance':'PENDING_USER'}))
