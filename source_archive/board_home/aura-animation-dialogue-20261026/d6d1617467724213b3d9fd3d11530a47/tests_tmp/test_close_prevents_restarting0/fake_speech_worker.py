
import json,sys,time
for line in sys.stdin:
    request=json.loads(line);kind=request.get('text','ok');token=request['request_id']
    if kind=='hang':time.sleep(30)
    if kind=='partial':sys.stdout.write('RESULT {');sys.stdout.flush();time.sleep(30)
    if kind=='exit':sys.exit(3)
    if kind=='mismatch':token='obsolete-request'
    if kind=='slow':time.sleep(.5)
    print('RESULT '+json.dumps({'request_id':token,'ok':True,'result':{'echo':kind}}),flush=True)
