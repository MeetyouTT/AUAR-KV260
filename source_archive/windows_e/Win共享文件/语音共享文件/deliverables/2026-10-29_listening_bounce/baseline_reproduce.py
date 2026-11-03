"""Reproduce the former admission behavior using the exact r4 handler, fake inference only."""
import bootstrap
bootstrap.service_module()
import json,sys,threading,time,types
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
legacy=types.ModuleType('legacy_board_host');legacy.__file__=str(A/'tools/board_model_host.py')
exec(compile((H/'before/tools/board_model_host.py').read_text(encoding='utf-8'),'r4_handler','exec'),legacy.__dict__)
import test_handoff as t
t.ModelHandler=legacy.ModelHandler
entered=threading.Event();cleanup=threading.Event()
def serve(handler,context,*args,**kw):
 if context['request_id']=='first':
  handler.send_response(200);handler.send_header('Content-Length','0');handler.end_headers()
  entered.set();handler.connection.recv(1);cleanup.set();time.sleep(.2)
 else:handler.send(200,{'ok':True})
with t.fake_server(serve) as (server,model,calls):
 first=t.request(server,'first');first.getresponse().read();assert entered.wait(1);first.close();assert cleanup.wait(1)
 second=t.request(server,'second');response=second.getresponse();body=json.loads(response.read());second.close()
 report={'status':'REPRODUCED_R4_503_DURING_CANCEL_CLEANUP','http_status':response.status,'body':body,
         'inference_calls':len(calls),'fake_inference':True,'production_devices_used':False}
 assert response.status==503 and body['error']=='Voice host busy' and len(calls)==1
(H/'baseline_reproduction.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
