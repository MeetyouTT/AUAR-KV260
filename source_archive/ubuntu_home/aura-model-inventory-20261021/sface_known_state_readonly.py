import json,urllib.request
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(path):
 with op.open('http://127.0.0.1:8790'+path,timeout=3) as f:return json.load(f)
h=get('/health');v=get('/v1/ui/status')['modules']['identity'];i=h['identity']
out={'read_only':True,'camera_pid':h['pid'],'backend':i['backend'],'ready':i['ready'],'error':i['error'],
 'processed':i['processed'],'discarded':i['discarded'],'deferred':i['deferred'],
 'last_inference_ms':i['last_inference_ms'],'state':v.get('state'),'detail':v.get('detail') if v.get('state')!='KNOWN' else 'KNOWN',
 'face_count':v.get('face_count'),'source_frame_id':v.get('source_frame_id'),
 'has_current_target':bool(v.get('face_target')),'has_result_target':bool(v.get('target')),
 'people_count':len(v.get('people',[])),'feature_inference':i.get('feature_inference')}
print(json.dumps(out))
