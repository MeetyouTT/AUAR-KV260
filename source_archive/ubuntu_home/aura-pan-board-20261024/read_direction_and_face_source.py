"""Read only completed manual movements and anonymous face motion metadata."""
import json,time,urllib.request
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
u=get(8783,'/api/state');m=u['manual_pan'];h=get(8790,'/health');v=get(8790,'/v1/ui/status');identity=v.get('modules',{}).get('identity',{});a=identity.get('face_attention') or {}
hist=[{k:r.get(k) for k in ('direction','initial_us','target_us','final_us','commands_accepted','stopped_early','completion','failure','duration_ms')} for r in m.get('history',[])[-2:]]
stamp=a.get('captured_mono_ms')
print(json.dumps({'manual_state':m['state'],'left_sign':m['left_sign'],'pulse_us':m['pulse_us'],'readback':m.get('readback'),
 'last_two_moves':hist,'face_backend':h['identity']['face_targets'].get('backend'),
 'face_source_age_ms':h['identity']['face_targets'].get('source_age_ms'),
 'face_attention_fields':sorted(a),'head_yaw_ratio':a.get('yaw_ratio'),'head_roll_degrees':a.get('roll_degrees'),
 'attention_age_ms':int(time.monotonic()*1000)-stamp if type(stamp) is int else None,
 'face_count':identity.get('face_count'),'sface_ready':h['identity']['ready'],'identity_payload_exported':False},sort_keys=True))
