"""Health-only validation, including binary frontend/portrait protocols."""
import concurrent.futures,datetime,json,socket,urllib.request
from recovery_common import H,A,read,save
from common import frontend_wire,portrait_wire
from common.voice_service_capabilities import require_current_voice
baseline=read('baseline.json')
def http(port,host='192.168.50.1',path='/health'):
 with urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=5) as response:return json.load(response)
def binary(port,wire,timeout):
 with socket.create_connection(('192.168.50.1',port),timeout=3) as connection:
  wire.send(connection,{'protocol':wire.PROTOCOL,'kind':'health'})
  value,payload=wire.receive(connection,timeout)
 assert not payload and value['ready'] and value['protocol']==wire.PROTOCOL
 return value
jobs={'asr':lambda:http(8791),'voice':lambda:http(8792),'visual':lambda:http(8810,'127.0.0.1'),
 'memory':lambda:http(8812,'127.0.0.1'),'frontend':lambda:binary(8795,frontend_wire,2),
 'portrait':lambda:binary(8796,portrait_wire,0),'ollama':lambda:http(11435,'127.0.0.1','/api/ps')}
report={'status':'CHECKING','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'services':{}}
with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
 tasks={key:pool.submit(job) for key,job in jobs.items()}
 for key,task in tasks.items():
  try:report['services'][key]={'reachable':True,'health':task.result()}
  except Exception as exc:report['services'][key]={'reachable':False,'error':type(exc).__name__+': '+str(exc)}
try:
 assert all(row['reachable'] for row in report['services'].values())
 values={key:row['health'] for key,row in report['services'].items()}
 assert values['asr']['ready'] and values['asr']['protocol']=='aura-asr-1'
 config=json.loads((A/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
 require_current_voice(values['voice'],config['model'],baseline['fingerprint']);assert not values['voice']['busy']
 assert values['visual']['status']=='ok'
 assert values['memory']['revision']=='device-timeline-v2' and values['memory']['speaker_ready']
 expected=json.loads((H.parent/'2026-10-27_windows_portrait/snapshot_verification.json').read_text(encoding='utf-8'))['revision']
 assert values['portrait']['revision']==expected
 assert values['voice']['latency_options']['compact_grammar'] is False
 report['status']='PASS'
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
save('endpoints.json',report)
print(json.dumps({'status':report['status'],'reachable':{key:row['reachable'] for key,row in report['services'].items()},
 'revision':report['services'].get('voice',{}).get('health',{}).get('service_revision'),'error':report.get('error')},ensure_ascii=True))
raise SystemExit(0 if report['status']=='PASS' else 1)
