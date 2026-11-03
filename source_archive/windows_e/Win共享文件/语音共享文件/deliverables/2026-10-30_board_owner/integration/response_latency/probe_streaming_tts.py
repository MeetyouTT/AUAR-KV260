"""Compare old and candidate delivery using identical public text and real RAM TTS."""
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE=r'''
import base64,hashlib,http.client,importlib.util,json,pathlib,subprocess,sys,tempfile,time,types,uuid
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
raw=(root/'startup/config.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==EXPECTED
pins=json.loads(raw)['component_sha256']
assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
sys.path.insert(0,str(root/'runtime/aura'))
def get(host,port,path):
 c=http.client.HTTPConnection(host,port,timeout=3)
 try:
  c.request('GET',path);r=c.getresponse();raw=r.read(1048577);assert r.status==200 and len(raw)<=1048576
  return json.loads(raw)
 finally:c.close()
unit=dict(x.split('=',1) for x in subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState'],text=True).splitlines() if '=' in x)
assert unit==dict(MainPID='0',ActiveState='inactive')
journal=json.loads((root.parent/'control-production-v1/state.json').read_bytes())
assert journal['phase']=='NORMAL_CLOSED' and journal['guard_removed'] is False
health=get('192.168.50.1',8797,'/health')
assert health['active'] is False and health['pending']==0
assert health['backend']['tts']=='omnivoice' and health['backend']['num_step']==16 and health['backend']['tts_ready'] is True
assert health['backend']['gpu_coordination']['enforcing'] is True
for rel in ('board/runtime/board_dialogue.py','common/board_memory.py','board/runtime/board_dialogue_client.py'):
 assert hashlib.sha256((root/'runtime/aura'/rel).read_bytes()).hexdigest()==pins[rel]
from board.runtime.board_dialogue import BoardDialogueController as OldController
from common.board_memory import BoardMemoryStore as OldStore
from board.runtime.board_dialogue_client import InferenceHttpClient
from common.model_inference_wire import make_response
def load(name,item):
 raw=base64.b64decode(item['base64']);assert hashlib.sha256(raw).hexdigest()==item['sha256']
 module=types.ModuleType(name);module.__file__='<reviewed-source-only-candidate>';module.__package__=name.rpartition('.')[0];sys.modules[name]=module
 exec(compile(raw,module.__file__,'exec'),module.__dict__)
 return module
new_controller=load('_latency_controller_candidate',SOURCES['controller']).BoardDialogueController
new_store=load('common._latency_store_candidate',SOURCES['store']).BoardMemoryStore
reply=json.dumps(dict(reply_text='先确认目的地。再准备需要的物品。最后核对出发时间。',emotion='neutral',avatar_action=''),ensure_ascii=False)
class Client:
 def __init__(self):self.inner=InferenceHttpClient('192.168.50.1',8797);self.seconds=[]
 def request(self,kind,payload,**kwargs):
  if kind=='llm':return make_response(payload,result=dict(text=reply))
  assert kind=='tts';began=time.monotonic();out=self.inner.request(kind,payload,**kwargs)
  self.seconds.append(time.monotonic()-began);return out
 def cancel(self,owner):return self.inner.cancel(owner)
results=[]
for name,Controller,Store,stream in [('before',OldController,OldStore,False),('after',new_controller,new_store,True)]:
 with tempfile.TemporaryDirectory(prefix='aura-public-tts-latency-',dir='/tmp') as directory:
  store=Store(pathlib.Path(directory)/'public-only.sqlite3',data_origin='synthetic')
  client=Client();controller=Controller(store,client,board_boot_id=BOOT,system_prompt='公开测试固定三句回复。')
  session='public-tts-'+uuid.uuid4().hex;scope=dict(kind='conversation',id=session)
  chunks=[];began=time.monotonic()
  def sink(chunk,answer,start_sample,token):
   assert chunk.sample_rate==24000
   chunks.append(dict(at_ms=(time.monotonic()-began)*1000,start_sample=start_sample,samples=len(chunk.pcm)//2))
  options=dict(chunk_sink=sink) if stream else {}
  plan=controller.prepare_text('请说出三个准备步骤。',scope=scope,session_id=session,generation=1,budget_ms=60000,**options)
  total=(time.monotonic()-began)*1000
  assert plan.sample_rate==24000 and len(plan.chunks)==3 and len(plan.pcm)==plan.samples*2
  assert hashlib.sha256(plan.pcm).hexdigest()==plan.sha256
  first=chunks[0]['at_ms'] if stream else total
  assert not stream or len(chunks)==3 and first<chunks[-1]['at_ms'] and first<total
  assert controller.cancel(session,generation=1) is True and controller.idle
  assert not any(row['role']=='assistant' for row in store.context(scope)['messages'])
  results.append(dict(mode=name,first_deliverable_pcm_ms=round(first,2),total_synthesis_ms=round(total,2),
   tts_request_ms=[round(x*1000,2) for x in client.seconds],sentence_count=3,
   first_chunk_preceded_remaining_synthesis=bool(stream and first<chunks[-1]['at_ms']),
   unplayed_plan_cancelled=True,assistant_not_recorded_as_heard=True))
  del plan,controller,client,store
after=get('192.168.50.1',8797,'/health')
assert after['active'] is False and after['pending']==0
assert after['counts'].get('accepted_tts',0)-health['counts'].get('accepted_tts',0)==6
print(json.dumps(dict(status='PUBLIC_THREE_SENTENCE_TTS_DELIVERY_CHECK',cases=results,
 first_pcm_reduction_ms=round(results[0]['first_deliverable_pcm_ms']-results[1]['first_deliverable_pcm_ms'],2),
 actual_llm_called=False,reply_fixture_identical=True,actual_omnivoice_16=True,actual_asr_called=False,
 real_user_store_accessed=False,audio_played=False,raw_audio_archived=False,
 audible_first_sound_measured=False,synthetic_store_removed=True,production_source_changed=False)))
'''

if __name__=='__main__':
    candidates={
        'controller':HERE/'streaming_candidate/after/board/runtime/board_dialogue.py',
        'store':HERE/'memory_candidate/after/common/board_memory.py',
    }
    sources={key:dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),base64=base64.b64encode(path.read_bytes()).decode()) for key,path in candidates.items()}
    baseline=json.loads((HERE/'board_baseline.json').read_text(encoding='utf-8'))
    remote='EXPECTED='+repr(baseline['startup_sha256'])+'\nBOOT='+repr(baseline['board_boot_id'])+'\nSOURCES='+repr(sources)+'\n'+REMOTE
    result=json.loads(ssh('python3 -B -',remote,timeout=90))
    result['candidate_hashes']={key:item['sha256'] for key,item in sources.items()}
    (HERE/'public_tts_comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
