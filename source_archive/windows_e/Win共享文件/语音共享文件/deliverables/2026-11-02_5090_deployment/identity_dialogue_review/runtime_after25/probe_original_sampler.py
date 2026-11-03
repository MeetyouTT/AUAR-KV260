import datetime,hashlib,http.client,json,sys,time
from pathlib import Path
root=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13');p=root/'startup/config.json';raw=p.read_bytes();startup_sha=hashlib.sha256(raw).hexdigest();s=json.loads(raw);a=Path(s['runtime'])/'aura';config=json.loads((a/'config/board_avatar_gtk.json').read_bytes())['board_business']
assert startup_sha=='092c2ccf0872cae2f6e13c81e2d8b8a2ffe3b0800ab701566128b5c7947159af'
paths=('board/runtime/board_dialogue_client.py','common/board_timeline_clock.py','common/model_inference_wire.py')
pins={k:hashlib.sha256((a/k).read_bytes()).hexdigest() for k in paths}
assert all(v==s['component_sha256'][k] for k,v in pins.items())
assert pins['board/runtime/board_dialogue_client.py']=='600e044dedfc90c70e319e0e91999b8b4b7f648e0a5ca98e2a1bc0ab09a076b2'
assert pins['common/board_timeline_clock.py']=='93b65ec3d9ca393b32499845297c78a2f1f71bc19e069b2ce3dc6f69e795af02'
sys.path.insert(0,str(a))
from board.runtime.board_dialogue_client import InferenceHttpClient
from common.board_timeline_clock import StableTimelineClock
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot=='903cfade-b93c-48fa-804e-379be1967313'
class ObservedOriginalClock(StableTimelineClock):
 def observe_http_date(self,sample,**kwargs):
  self.record.update(sent_monotonic=sample.sent_monotonic,received_monotonic=sample.received_monotonic,header_rtt_ms=(sample.received_monotonic-sample.sent_monotonic)*1000,age_at_observe_ms=(self.monotonic()-sample.received_monotonic)*1000)
  return super().observe_http_date(sample,**kwargs)
results=[]
for i in range(3):
 row={'index':i+1}
 c=http.client.HTTPConnection('192.168.50.1',config.get('model_port',8797),timeout=3.)
 sent=time.monotonic()
 try:
  c.connect();connected=time.monotonic();c.request('GET','/health',headers={'Accept':'application/json','Connection':'close'});r=c.getresponse();headers=time.monotonic();body=r.read(65537)
  row['plain_http']={'http_status':r.status,'connect_ms':(connected-sent)*1000,'header_rtt_ms':(headers-sent)*1000,'body_bytes':len(body),'total_ms':(time.monotonic()-sent)*1000}
 except (OSError,ValueError,http.client.HTTPException) as exc:row['plain_http']={'error_type':type(exc).__name__,'total_ms':(time.monotonic()-sent)*1000}
 finally:c.close()
 client=InferenceHttpClient('192.168.50.1',config.get('model_port',8797),clock=time.monotonic)
 clk=ObservedOriginalClock(boot,client.health_date_source_id(),client.validate_sample,utc_bounds=tuple(config['utc_bounds']),anchor_path=None,monotonic=time.monotonic)
 clk.record={};sent=time.monotonic()
 try:
  reading=client.sample_health_date(clk,deadline=time.monotonic()+3.)
  row['original_sampler']={'accepted':True,'quality':reading['quality'],'total_ms':(time.monotonic()-sent)*1000,**clk.record}
 except Exception as exc:
  code=str(exc) if type(exc).__name__=='ClockUnavailable' else None
  row['original_sampler']={'accepted':False,'error_type':type(exc).__name__,'clock_error_code':code,'total_ms':(time.monotonic()-sent)*1000,**clk.record}
 row['guard']={'max_rtt_seconds':clk.policy['max_rtt'],'max_sample_age_seconds':clk.policy['max_sample_age'],'anchor_path_is_none':clk.anchor_path is None}
 results.append(row)
print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'startup_sha256':startup_sha,'source_sha256':pins,'boot_id':boot,'utc_bounds':config['utc_bounds'],'endpoint':'http://192.168.50.1:'+str(config.get('model_port',8797))+'/health','source_package':str(a),'samples':results,'production_anchor_written':False,'database_opened':False,'inference_requested':False,'gui_or_motion_requested':False,'original_guard_preserved':True},sort_keys=True))
