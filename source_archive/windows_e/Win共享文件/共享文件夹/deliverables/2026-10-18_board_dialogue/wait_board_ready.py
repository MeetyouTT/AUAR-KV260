import json
from board_ssh import ssh,HERE

script=r'''
import http.client,json,time
deadline=time.monotonic()+150
last='not ready'
while time.monotonic()<deadline:
    connection=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
    try:
        connection.request('GET','/api/state');reply=connection.getresponse();state=json.loads(reply.read())
        if isinstance(state,dict) and state.get('dialogue_enabled'):
            print(json.dumps(state));break
        last='voice client not enabled'
    except Exception as exc:last=str(exc)
    finally:connection.close()
    time.sleep(1)
else:raise RuntimeError(last)
'''
result=ssh('python3 -',script,timeout=165)
(HERE/'board_voice_ready.json').write_text(result,encoding='utf-8')
state=json.loads(result)
print(json.dumps({'voice_enabled':state['dialogue_enabled'],'phase':state['phase'],
                  'service':state['local_transcription']['service'],'error':state['error']},ensure_ascii=True))
