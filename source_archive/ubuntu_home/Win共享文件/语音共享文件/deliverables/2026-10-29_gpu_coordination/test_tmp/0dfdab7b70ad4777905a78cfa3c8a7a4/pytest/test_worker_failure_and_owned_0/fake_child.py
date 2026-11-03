
import json,sys
for line in sys.stdin:
 request=json.loads(line)
 if request.get('text')=='exit':sys.exit(2)
 print('RESULT '+json.dumps({'ok':True,'request_id':request['request_id'],
  'result':{'echo':request.get('text','warmup'),'cache_hit':False,'cuda_idle_cache':{'available':True}}}),flush=True)
