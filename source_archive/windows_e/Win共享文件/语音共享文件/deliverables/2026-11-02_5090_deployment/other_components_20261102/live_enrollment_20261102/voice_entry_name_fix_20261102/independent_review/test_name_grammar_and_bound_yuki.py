"""Independent grammar/authority boundaries on truly instance-bound Yuki methods."""
import ast,hashlib,importlib.util,json,os
from pathlib import Path
import sys,threading
from types import SimpleNamespace
from unittest.mock import patch
import pytest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent;LIVE=ROOT.parent
MODE=os.environ.get('AURA_NAME_FIX_REVIEW_MODE','candidate');assert MODE in ('baseline','candidate')
RUNTIME=ROOT/(MODE+'_runtime')
LOADED={}
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec)
 raw=path.read_bytes();LOADED[str(path)]=hashlib.sha256(raw).hexdigest();sys.modules[name]=mod
 exec(compile(raw,str(path),'exec'),mod.__dict__);return mod
old=load('name_fix_old_blackbox_helpers',LIVE/'split_commands_20261102/independent_voice_review/test_split_entry_blackbox.py')
sys.path.insert(0,str(RUNTIME))
feature=load('common.feature_intents',RUNTIME/'common/feature_intents.py')
load('common.binding_intent',RUNTIME/'common/binding_intent.py')
jobs_mod=load('board.runtime.audio.board_dialogue_jobs',RUNTIME/'board/runtime/audio/board_dialogue_jobs.py')
business_mod=load('board.runtime.board_business',RUNTIME/'board/runtime/board_business.py')
yuki_business=load('tools.yuki_business_candidate',RUNTIME/'tools/yuki_business_candidate.py')
yuki_jobs=load('tools.yuki_jobs_candidate',RUNTIME/'tools/yuki_jobs_candidate.py')
formal=load('tools.formal_yuki',RUNTIME/'tools/formal_yuki.py')
from common.binding_intent import binding_intent
from common.voice_enrollment import valid_name

class Builder:
 system_prompt='synthetic paired prompt'
 def __call__(self,context,text,history=None):return context
class Commands:
 def __call__(self,*a,**kw):return None
class Sequence:
 board_boot_id='synthetic-boot';idle=True
 def __init__(self):
  self.store=SimpleNamespace(check_turn_current=lambda *a,**kw:None)
  self.context_builder=Builder();self.command_handler=Commands();self.asr=SimpleNamespace()
  self.records=[];self.replies=[]
 def prepare_local_sequence(self,text,producer,reply_sink,**kwargs):
  self.records.append(text)
  producer(lambda reply,**options:self.replies.append(reply.text))
  return SimpleNamespace(local_plan=True)

class Bound:
 def __init__(self):
  self.clock=old.voice.Clock();self.business=old.Business(self.clock);self.controller=Sequence();self.face_calls=0;self.source_reads=0
  def no_face(*args):self.face_calls+=1;raise AssertionError('Voice tried face command')
  def no_source():self.source_reads+=1;raise AssertionError('Voice tried visual provider')
  self.handler=business_mod.LocalIdentityReplies('synthetic-boot',no_source,no_face,clock=self.clock,
      now_ms=lambda:round(self.clock()*1000))
  self.handler.attach_speaker_business(self.business,old.Readback())
  self.jobs=jobs_mod.BoardDialogueJobs(self.controller,dict(enabled=True,host='127.0.0.1',port=8797,timeout_ms=120000),
      'synthetic-boot',scope_provider=lambda _:dict(kind='conversation',id='a'*32),clock=self.clock,start_worker=False,
      special_handlers=dict(identity_enrollment=self.handler,identity_query=self.handler,speaker_identity=self.handler))
  self.runtime=SimpleNamespace(started=False,closed=False,jobs=self.jobs,controller=self.controller,_foreground_idle=lambda:True)
  metadata=json.loads((ROOT/'yuki_pair.formal.public.json').read_text(encoding='utf-8'))
  from common.character_profile import selected_profile
  from tools.board_persona_candidate import BoardPersonaCandidate
  identity=metadata['identity'];profile=selected_profile()
  persona=BoardPersonaCandidate(identity['profile_version'],identity['display_name'],identity['persona_config_sha256'],
      identity['render_profile_id'],identity['render_source_profile_sha256'],profile.persona_full_prompt)
  self.pair=formal.CandidatePair(RUNTIME,metadata,persona)
  self.controller.context_builder.system_prompt=persona.system_prompt
  self.pair.attach_mailbox(SimpleNamespace(ready=True,lock=threading.RLock()))
  self.pair.observe_native_frame({'frames':1})
  yuki_business.bind_runtime_pair(self.runtime,self.pair)
  assert self.jobs._route.__func__ is yuki_jobs._route
  assert self.jobs._admit_text.__func__ is yuki_jobs._admit_text
  self.index=0
 def say(self,text):
  self.index+=1;raw=old.voice.pcm(self.index)
  clip=SimpleNamespace(capture_id='independent-'+str(self.index),pcm=raw,audio=SimpleNamespace(sample_count=len(raw)//2))
  self.jobs.submit(clip);job=self.jobs.waiting
  admitted=self.jobs._admit_text(job,text)
  with patch.dict(sys.modules,{'webrtcvad':SimpleNamespace(Vad=old.voice.VAD)}):result=self.jobs._route(job,admitted,reply_sink=lambda *a:None)
  self.jobs.waiting=None
  return result
 def row(self):return self.business.device.sessions[(self.jobs.boot_id,self.jobs.session_id)]

@pytest.mark.parametrize('phrase',[
 '我要请帮我登记一下我的声纹，我叫林小山',
 '我想给我录入声纹，名字是：林　小山',
 '登记声音。我的名字是：林 小 山',
 '雪妃，给我注册一下声纹，我叫林小山',
])
def test_natural_self_starts_use_actual_yuki_bound_route_without_visual(phrase):
 c=Bound();c.say(phrase)
 assert c.row()['stage']=='samples' and c.row()['name']=='林小山' and c.row()['vectors']==[]
 assert c.controller.records[-1]==phrase and c.business.routes==0 and c.face_calls==0 and c.source_reads==0

@pytest.mark.parametrize('name_text,expected',[
 ('我叫：林　小 山','林小山'),('我的名字是 : 林 小山。','林小山'),('名字是林小山','林小山'),
 ('我叫Abc-Def','Abc-Def'),('叫我林小山','林小山'),
])
def test_pending_name_normalization_is_only_formatting_and_keeps_raw_record(name_text,expected):
 c=Bound();c.say('登记声纹');before=c.handler._standalone_entry
 for _ in range(100):assert c.handler.public()['entry_name_pending']
 c.say(name_text)
 assert c.row()['name']==expected and valid_name(expected) and c.row()['vectors']==[]
 assert c.controller.records[-1]==name_text and c.handler._standalone_entry is before

@pytest.mark.parametrize('text',[
 '我叫：林小山？','我叫林小山呢','我叫林小山是不是','我叫不是林小山','我叫不要林小山',
 '我叫林\u00a0小山','我叫J ohn','我叫林-小山','我叫林小山:删除','我叫林小山，然后保存',
 '“我叫林小山”','我叫\n林小山','我是林小山','我叫A'+'b'*20,
])
def test_rejected_name_shapes_never_open_original_sampler_in_pending_mode(text):
 c=Bound();c.say('登记声纹')
 if '\n' in text:
  with pytest.raises(ValueError):c.say(text)
 else:c.say(text)
 assert c.business.device.sessions=={} and c.handler.public()['entry_name_pending']
 assert c.business.fixture.encoder.calls==0 and c.business.fixture.store.enrolls==[]

@pytest.mark.parametrize('text',[
 '请不要帮我登记一下声纹','我并不想登记我的声音','如果我要录入声纹，我叫林小山',
 '你能给我注册声纹吗','能不能登记声纹，我叫林小山','我想问一下如何登记声纹',
 '他说“我想录入声纹，我叫林小山”','请复述登记声纹我叫林小山',
])
def test_unarmed_negation_quotes_and_questions_never_open_or_arm_voice(text):
 c=Bound();c.say(text)
 assert c.business.device.sessions=={} and c.handler.public()['entry_mode'] is None
 assert not c.handler.public()['entry_name_pending'] and c.business.fixture.store.enrolls==[]

@pytest.mark.parametrize('question',['声纹登记成功了吗','我叫什么名字','你现在能识别我的声音吗'])
def test_pending_queries_do_not_become_name_or_sample(question):
 c=Bound();c.say('登记声纹');c.say(question)
 assert c.business.device.sessions=={} and c.handler.public()['entry_name_pending']
 assert c.business.fixture.encoder.calls==0

def test_unarmed_strict_name_cannot_start_voice_or_grant():
 c=Bound();c.say('名字是：林 小山')
 assert c.business.device.sessions=={} and c.handler.public()['entry_mode'] is None
 assert c.business.fixture.store.enrolls==[]

@pytest.mark.parametrize('question',['声纹登记成功了吗','查询我的声纹','你现在能识别我的声音吗'])
def test_original_recognized_voice_query_does_not_consume_active_sample(question):
 c=Bound();c.say('登记声纹，我叫林小山');c.say(question)
 assert c.row()['vectors']==[] and c.business.fixture.encoder.calls==0 and c.business.fixture.store.enrolls==[]

def test_actual_yuki_full_three_sample_save_needs_original_final_confirmation():
 c=Bound();c.say('我想给我登记一下声纹');c.say('雪妃，我叫：林 小山')
 for text in ('独立合成第一段','独立合成第二段','独立合成第三段'):c.say(text)
 assert c.row()['stage']=='confirm' and len(c.row()['vectors'])==3
 c.say('确认保存身份关联');c.say('确认登记');assert c.business.fixture.store.enrolls==[]
 c.say('确认保存声纹')
 assert len(c.business.fixture.store.enrolls)==1 and c.handler.public()['entry_mode'] is None
 assert c.business.routes==0 and c.face_calls==0 and c.source_reads==0

def test_old_vocative_remains_refused_by_actual_current_pair_route():
 c=Bound();c.say('汐蓝，登记声纹，我叫林小山')
 assert c.business.device.sessions=={} and c.controller.records==[]

def test_yuki_admit_unchanged_and_route_only_two_kind_tuple_additions():
 oldtree=ast.parse((ROOT/'baseline_runtime/tools/yuki_jobs_candidate.py').read_text(encoding='utf-8'))
 newtree=ast.parse((ROOT/'candidate_runtime/tools/yuki_jobs_candidate.py').read_text(encoding='utf-8'))
 count=0
 for node in ast.walk(newtree):
  if isinstance(node,ast.Tuple) and any(isinstance(e,ast.Constant) and e.value=='face_only' for e in node.elts):
   node.elts=[e for e in node.elts if not (isinstance(e,ast.Constant) and e.value in ('face_only','voice_only'))];count+=1
 assert count==2 and ast.dump(oldtree,include_attributes=False)==ast.dump(newtree,include_attributes=False)

def test_other_business_methods_clock_epochs_permissions_and_name_validator_unchanged():
 def methods(path):
  result={};tree=ast.parse(path.read_text(encoding='utf-8'))
  for cls in tree.body:
   if isinstance(cls,ast.ClassDef):
    for node in cls.body:
     if isinstance(node,ast.FunctionDef):result[(cls.name,node.name)]=ast.dump(node,include_attributes=False)
  return result
 a=methods(ROOT/'baseline_runtime/board/runtime/board_business.py')
 b=methods(ROOT/'candidate_runtime/board/runtime/board_business.py')
 assert {name for name in a if a[name]!=b[name]}=={('LocalIdentityReplies','__call__')}
 assert (ROOT/'baseline_runtime/common/voice_enrollment.py').read_bytes()==(ROOT/'candidate_runtime/common/voice_enrollment.py').read_bytes()
 assert (ROOT/'baseline_runtime/common/binding_intent.py').read_bytes()==(ROOT/'candidate_runtime/common/binding_intent.py').read_bytes()

def test_record_compiled_source_fingerprints():
 (HERE/(MODE.upper()+'_LOADED.json')).write_text(json.dumps(LOADED,indent=2)+'\n',encoding='utf-8')
