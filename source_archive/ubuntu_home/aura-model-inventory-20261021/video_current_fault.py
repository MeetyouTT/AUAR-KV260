import json,urllib.request
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=4) as r:h=json.load(r)
i=h['identity'];f=i['face_targets']
print(json.dumps({'pid':h['pid'],'detection_hz':h['detection_hz'],'schedule':h['dpu_schedule'],
 'identity_ready':i['ready'],'feature':i['feature_inference'],'face_backend':f['backend'],
 'worker_alive':f['worker_alive'],'fault_latched':f['fault_latched'],'gaps':f['freshness_metrics']['counters']['observed_gap_intervals']}))
