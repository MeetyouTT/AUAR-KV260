import json
from pathlib import Path

T=Path(__file__).resolve().parent
expected=json.loads((T/'EXPECTED_AFTER.json').read_bytes())
ready=json.loads((T/'ready_read_1_RESULT.json').read_bytes())['board_result']
assert ready['ready'] and ready['all380_actual_bytes_match']
for key in ('gui_owner','gtk_owner','camera_owner'):expected[key]=ready[key]
with (T/'EXPECTED_FINAL.json').open('x',encoding='utf-8') as f:json.dump(expected,f,ensure_ascii=False,indent=2)
source=(T/'fresh_read_1.py').read_text(encoding='utf-8')
assert sum(s.startswith('E=') for s in source.splitlines())==1
source='\n'.join('E='+repr(expected) if line.startswith('E=') else line for line in source.splitlines())+'\n'
extra="""try:
 assert out['status']=='READONLY_RECONCILED' and not out['errors']
 current=out['current_state']
 assert current['pair_ready'] and current['runtime_fault_count']==0
 assert not any(current[k] for k in ('listening_enabled','microphone_open','playing','pending_job','speaker_busy','follow'))
 assert current['axis_readback']['flags']==0 and out['saved_listening_preference']=={'version':1,'enabled':False}
 assert not Path('/run/aura-dialogue-thinking-test.json').exists()
 c=http.client.HTTPConnection('192.168.50.1',8797,timeout=3)
 try:
  c.request('GET','/health');r=c.getresponse();health=json.loads(r.read(1048576));assert r.status==200
 finally:c.close()
 assert health['ok'] and not health['active'] and health['pending']==0
 assert health['backend']['context_limit']==4096 and health['backend']['tts_ready'] is True
 out.update(model_health=health,thinking_enabled=False,status='FIVE_TURN_FINAL_RUNTIME_VERIFIED')
except Exception as error:
 out['errors'].append(dict(error_class=type(error).__name__,line=traceback.extract_tb(error.__traceback__)[-1].lineno))
print(json.dumps(out))"""
assert source.count('print(json.dumps(out))')==1
source=source.replace('print(json.dumps(out))',extra)
compile(source,'final_read_1.py','exec')
with (T/'final_read_1.py').open('x',encoding='utf-8') as f:f.write(source)
print('final_read_prepared')
