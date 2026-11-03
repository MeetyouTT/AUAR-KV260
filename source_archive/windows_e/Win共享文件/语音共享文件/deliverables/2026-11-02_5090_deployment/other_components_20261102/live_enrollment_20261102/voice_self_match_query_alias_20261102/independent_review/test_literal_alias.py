"""Independent two-regex-parser literal check and actual Yuki alias path."""
import ast,copy,hashlib,json,sys
from pathlib import Path
import pytest
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from composition import c,RELEASE
from common.feature_intents import speaker_query_requested,speaker_text
from board.runtime.board_speaker_business import BoardSpeakerBusiness

TARGETS=('你可以根据我的声音辨别我是谁吗','辨别我的声音')

@pytest.mark.parametrize('file,allowed',[
 ('common/feature_intents.py','speaker_text'),
 ('board/runtime/board_speaker_business.py','_explicit_self_match'),
])
def test_only_four_query_regex_literals_change_and_every_other_ast_node_is_identical(file,allowed):
 before=ast.parse((ROOT/'baseline_runtime'/file).read_text(encoding='utf-8'))
 after=ast.parse((ROOT/'candidate_runtime'/file).read_text(encoding='utf-8'))
 changed=[]
 class Undo(ast.NodeTransformer):
  function=None
  def visit_FunctionDef(self,node):
   previous=self.function;self.function=node.name;self.generic_visit(node);self.function=previous;return node
  def visit_Constant(self,node):
   if isinstance(node.value,str) and '辨别' in node.value:
    assert self.function==allowed and '|辨别' in node.value
    assert node.value.count('|辨别')==1
    node.value=node.value.replace('|辨别','');changed.append(self.function)
   return node
 Undo().visit(after)
 assert len(changed)==4 and ast.dump(before,include_attributes=False)==ast.dump(after,include_attributes=False)
 assert (ROOT/'candidate_runtime'/file).stat().st_size-(ROOT/'baseline_runtime'/file).stat().st_size==28

@pytest.mark.parametrize('text',TARGETS)
def test_new_alias_is_readonly_speaker_query_and_exact_self_match(text):
 assert speaker_text(text)=='查询我的声纹' and speaker_query_requested(text)
 assert BoardSpeakerBusiness._explicit_self_match(text) is True

@pytest.mark.parametrize('text',[
 '不要辨别我的声音','我不想让你辨别我的声音','如果你可以辨别我的声音会怎样',
 '请重复“辨别我的声音”','你刚才说辨别我的声音','“你可以根据我的声音辨别我是谁吗”',
])
def test_negative_quoted_and_hypothetical_text_does_not_trigger_probe(text):
 assert not speaker_query_requested(text) and not BoardSpeakerBusiness._explicit_self_match(text)

def saved(c):
 c.say('登记声纹，我叫合成词项复验')
 for t in ('合成登记独立第一段','合成登记独立第二段','合成登记独立第三段'):c.say(t)
 c.say('确认保存声纹');assert c.voice_count()==1;c.encoder.calls=0

@pytest.mark.parametrize('text',TARGETS)
def test_actual_bound_yuki_alias_reaches_original_three_match_probe_without_extra_encode(c,text):
 saved(c)
 from tools import yuki_jobs_candidate
 assert c.runtime.jobs._route.__func__ is yuki_jobs_candidate._route
 assert c.runtime.identity_handler.business is c.business
 for index in range(1,4):
  latency,errors=c.say(text)
  assert errors==[] and latency['error_class']=='none'
  assert c.encoder.calls==index
  assert c.business.public()['self_match_probe']['distinct_captures']==index
 value=c.business.public()['self_match_probe']
 assert value['phase']=='CANDIDATE' and value['candidate_completed']==1
 assert value['field_calibrated'] is False and value['identity_verified'] is False and value['personal_memory_allowed'] is False
 assert '合成词项复验' in c.last_reply
 assert c.business.turn(copy.deepcopy(c.last_meta),text,c.last_raw)==c.last_reply and c.encoder.calls==3
 assert c.business.hub.binding.registry.health()['active_people']==0
 assert c.business.health()['profile_grants_issued'] is False

@pytest.mark.parametrize('text',TARGETS)
def test_alias_query_during_original_registration_does_not_consume_sample(c,text):
 c.say('登记声纹，我叫合成词项复验');c.say(text)
 assert c.row()['stage']=='samples' and c.row()['vectors']==[] and c.encoder.calls==0
 assert c.business.public()['self_match_probe']['phase']=='IDLE' and c.voice_count()==0

def test_record_current_compiled_source_hashes():
 names=('common/feature_intents.py','board/runtime/board_speaker_business.py')
 (HERE/'REVIEWED_SOURCE_SHA.json').write_text(json.dumps({n:hashlib.sha256((RELEASE/n).read_bytes()).hexdigest() for n in names},indent=2)+'\n',encoding='utf-8')
