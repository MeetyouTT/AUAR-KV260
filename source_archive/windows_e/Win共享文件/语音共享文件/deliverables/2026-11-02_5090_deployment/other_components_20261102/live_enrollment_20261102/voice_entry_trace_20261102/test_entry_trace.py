"""Fixed-metadata privacy and exact original dispatch tests; all local RAM."""
import ast,copy,hashlib,importlib.util,json,os
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
from unittest.mock import patch
import pytest

HERE=Path(__file__).resolve().parent
LIVE=HERE.parent
BASE=LIVE/'split_commands_20261102/actual_release/runtime'
MODE=os.environ.get('AURA_ENTRY_TRACE_MODE','candidate')
assert MODE in ('baseline','candidate')
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec)
 sys.modules[name]=mod;exec(compile(path.read_bytes(),str(path),'exec'),mod.__dict__);return mod
sys.path.insert(0,str(BASE))
blackbox=load('entry_trace_blackbox_fixtures',LIVE/'split_commands_20261102/independent_voice_review/test_split_entry_blackbox.py')
# The public fixtures do not construct models, private stores or devices.
load('common.binding_intent',BASE/'common/binding_intent.py')
jobs_mod=load('board.runtime.audio.board_dialogue_jobs',HERE/MODE/'board/runtime/audio/board_dialogue_jobs.py')
business_mod=load('board.runtime.board_business',HERE/MODE/'board/runtime/board_business.py')
blackbox.business_module=business_mod;blackbox.jobs_module=jobs_mod
from common.binding_intent import binding_intent
from board.runtime.board_dialogue import DIALOGUE_ROUTE

CANARY='PRIVATE_CANARY_NAME_TARGET_TRANSCRIPT_ae91'

def fixture():return blackbox.Fixture()
def entry(f):return f.handler.public()['entry_trace']

def jobs_fixture(text='今天普通闲聊',handlers=None):
    clock=blackbox.voice.Clock()
    class ASR:
        def transcribe(self,pcm,**kw):return text
    asr=ASR();ctl=SimpleNamespace(board_boot_id='synthetic-boot',asr=asr,store=SimpleNamespace(preempt_compaction=lambda:None),
        command_handler=None,context_builder=None)
    jobs=jobs_mod.BoardDialogueJobs(ctl,dict(enabled=True,host='127.0.0.1',port=8797,timeout_ms=30000),'synthetic-boot',
        scope_provider=lambda _:dict(kind='conversation',id='a'*32),clock=clock,start_worker=False,special_handlers=handlers)
    raw=blackbox.voice.pcm(3)
    clip=SimpleNamespace(capture_id='synthetic-clip',audio=SimpleNamespace(sample_count=len(raw)//2),pcm=raw)
    jobs.submit(clip);job=jobs.waiting
    return jobs,job,ctl,clock

def route(jobs,job,text):
    if MODE=='candidate':
        t=jobs_mod._entry_route_trace();jobs_mod._entry_asr_trace(t,text);job.entry_route_trace=t
        jobs.last_voice_route=dict(generation=job.meta['generation'],entry_trace=copy.deepcopy(t))
    return jobs._route(job,text)

def trace(jobs):return jobs.public()['last_voice_route']['entry_trace']

def no_text(value):
    if isinstance(value,dict):
        assert all(type(k) is str for k in value)
        for v in value.values():no_text(v)
    elif type(value) is str:
        assert value in {'not_evaluated','ordinary','remember_self','name_hint','invalid_name','face_only','voice_only','other',
            'not_selected','ordinary_dialogue','explicit_memory_commands','identity_enrollment','identity_query',
            'speaker_identity','history_delete_preview','structured_visual_query','reasoning_dialogue',
            'not_called','calling','none','returned','reply','error','started','rejected','complete',
            'face','voice','entered','producer','business_turn','finished','BoardCapabilityNotReady','StaleGeneration',
            'TimeoutError','PermissionError','ValueError','RuntimeError','OSError','ConnectionError','ModelRequestError',
            'ReplyRejected','ScopeDenied','StaleTurn','InterruptedError','MemoryError'}
    else:assert type(value) in (int,bool) and (type(value) is bool or 0<=value<=4097)

@pytest.mark.skipif(MODE=='baseline',reason='New metadata projection only')
def test_real_loaded_parser_flags_are_code_constants_not_disk_version():
    flags=jobs_mod._entry_parser_flags(binding_intent)
    assert flags==dict(parser_code_known=True,parser_face_only_const=True,parser_voice_only_const=True)
    def old_parser(text):return {'kind':'ordinary','name':None}
    assert jobs_mod._entry_parser_flags(old_parser)==dict(parser_code_known=True,parser_face_only_const=False,parser_voice_only_const=False)
    assert jobs_mod._entry_parser_flags(object())==dict(parser_code_known=False,parser_face_only_const=False,parser_voice_only_const=False)

@pytest.mark.skipif(MODE=='baseline',reason='New metadata projection only')
def test_jobs_recognized_voice_handler_dispatch_and_missing_handler_are_fixed():
    calls=[]
    class Handler:
        def public(self):return {'active':False}
        def __call__(self,text,**kw):calls.append(text);return 'synthetic-plan'
    h=Handler();j,job,_,_=jobs_fixture(handlers={'speaker_identity':h})
    assert route(j,job,'登记声纹，我叫合成姓名')==('synthetic-plan',None)
    t=trace(j)
    assert t['binding_kind']=='voice_only' and t['capability']=='speaker_identity'
    assert t['speaker_requested'] and t['handler_called'] and t['handler_available'] and t['handler_result']=='returned'
    assert len(calls)==1;no_text(t)
    j,job,_,_=jobs_fixture()
    with pytest.raises(jobs_mod.BoardCapabilityNotReady):route(j,job,'登记声纹')
    t=trace(j);assert t['capability']=='speaker_identity' and not t['handler_available'] and not t['handler_called']

@pytest.mark.skipif(MODE=='baseline',reason='New metadata projection only')
def test_asr_keyword_flags_distinguish_fixed_near_words_without_text():
    j,job,_,_=jobs_fixture();raw='登记 等级 声纹 升温 声音 人脸 我叫'+CANARY
    route(j,job,raw);t=trace(j)
    assert t['asr_characters']==len(raw) and all(t[k] for k in ('has_register','has_level','has_voiceprint','has_warming','has_voice','has_face','has_my_name'))
    assert CANARY not in json.dumps(t,ensure_ascii=False);no_text(t)
    j,job,_,_=jobs_fixture();route(j,job,'今天天气晴朗');t=trace(j)
    assert not any(t[k] for k in ('has_register','has_level','has_voiceprint','has_warming','has_voice','has_face','has_my_name'))

@pytest.mark.skipif(MODE=='baseline',reason='New metadata projection only')
def test_natural_prefix_flags_are_observations_and_do_not_expand_authorization_grammar():
    j,job,_,_=jobs_fixture();raw='我要我想登记一下声文声纹身份名字，我叫'+CANARY
    route(j,job,raw);t=trace(j)
    assert all(t[k] for k in ('has_i_want','has_i_would_like','has_a_bit','has_voice_word','has_identity','has_name_word'))
    assert t['binding_kind']=='ordinary' and not t['speaker_requested'] and not t['handler_called']
    assert CANARY not in json.dumps(t);no_text(t)

@pytest.mark.skipif(MODE=='baseline',reason='New metadata projection only')
def test_jobs_trace_resets_for_next_turn_and_failure_rethrows_same_exception():
    error=RuntimeError(CANARY)
    class Handler:
        def public(self):return {'active':False}
        def __call__(self,*a,**kw):raise error
    j,job,_,_=jobs_fixture(handlers={'speaker_identity':Handler()})
    with pytest.raises(RuntimeError) as e:route(j,job,'登记声纹')
    assert e.value is error and trace(j)['handler_result']=='error' and trace(j)['error_class']=='RuntimeError'
    raw=blackbox.voice.pcm(7);clip=SimpleNamespace(capture_id='next-clip',audio=SimpleNamespace(sample_count=len(raw)//2),pcm=raw)
    j.submit(clip);nextjob=j.waiting;route(j,nextjob,'普通话题')
    t=nextjob.entry_route_trace
    assert t['binding_kind']=='ordinary' and not t['handler_called'] and t['handler_result']=='not_called' and t['error_class']=='none'
    assert CANARY not in json.dumps(trace(j))

@pytest.mark.skipif(MODE=='baseline',reason='New metadata projection only')
def test_short_circuit_query_does_not_add_original_enrollment_state_calls():
    class Handler:
        def __call__(self,*a,**kw):return None
    j,job,_,_=jobs_fixture(handlers={'speaker_identity':Handler()})
    j._enrollment_state=lambda: (_ for _ in ()).throw(AssertionError('Original query short circuit was changed'))
    assert route(j,job,'声纹保存了吗')==(None,None)
    assert j.last_voice_route['entry_trace']['enrollment_checked'] is False

@pytest.mark.skipif(MODE=='baseline',reason='New metadata projection only')
def test_no_speech_new_job_does_not_keep_old_handler_or_parser_flags():
    j,job,_,_=jobs_fixture('')
    j.last_voice_route=dict(generation=0,entry_trace={'handler_called':True,'binding_kind':'voice_only'})
    assert j.run_next()
    t=trace(j)
    assert t['outcome']=='rejected' and t['asr_result_seen'] and t['asr_characters']==0
    assert not t['handler_called'] and t['binding_kind']=='not_evaluated' and not t['parser_code_known']

@pytest.mark.skipif(MODE=='baseline',reason='New metadata projection only')
def test_cancelled_older_trace_cannot_overwrite_a_newer_processed_generation():
    j,job,_,_=jobs_fixture();route(j,job,'普通聊天')
    older=job.entry_route_trace
    j.last_voice_route=dict(generation=job.meta['generation']+1,entry_trace={'sentinel':True})
    j._publish_entry_route_trace(job,older)
    assert j.last_voice_route['entry_trace']=={'sentinel':True}

@pytest.mark.skipif(MODE=='baseline',reason='New metadata projection only')
def test_lir_voice_turn_present_and_parser_metadata_no_face_text_ids_or_extra_turn():
    f=fixture();f.forbid_source=True;f.say('登记声纹，我叫合成姓名')
    t=entry(f)
    assert t['input_mode']=='none' and t['resolved_mode']=='voice' and t['binding_kind']=='voice_only'
    assert t['parser_code_known'] and t['parser_face_only_const'] and t['parser_voice_only_const']
    assert t['business_turn_calls']==1 and t['business_turn_result']=='reply'
    assert t['speaker_state_known'] and t['speaker_present_after'] and t['speaker_active_after']
    assert not t['face_active_before'] and not t['face_active_after']
    assert f.source_reads==0 and len(f.business.turns)==1;no_text(t)

@pytest.mark.skipif(MODE=='baseline',reason='New metadata projection only')
def test_lir_none_and_exception_class_whitelist_preserve_original_results():
    f=fixture();f.say('普通聊天'+CANARY)
    t=entry(f);assert t['business_turn_result']=='none' and t['business_turn_calls']==1 and CANARY not in json.dumps(t)
    class CustomerNameException(Exception):pass
    error=CustomerNameException(CANARY)
    def fail(*a,**kw):raise error
    f.business.turn=fail
    with pytest.raises(CustomerNameException) as e:f.say('登记声纹，我叫合成姓名')
    assert e.value is error and entry(f)['error_class']=='other' and entry(f)['business_turn_result']=='error'
    assert CANARY not in json.dumps(entry(f)) and 'CustomerNameException' not in json.dumps(entry(f));no_text(entry(f))

@pytest.mark.skipif(MODE=='baseline',reason='New metadata projection only')
def test_lir_face_no_voice_turn_and_reset_does_not_erase_last_failure_metadata():
    f=fixture();f.say('登记人脸，我叫合成姓名');t=entry(f)
    assert t['resolved_mode']=='face' and t['face_active_after'] and t['business_turn_calls']==0
    f.handler.reset();after=entry(f)
    assert after['reset_since_trace'] and after['binding_kind']=='face_only' and after['business_turn_calls']==0
    f.say('普通话题');t=entry(f)
    assert not t['reset_since_trace'] and t['binding_kind']=='ordinary' and t['error_class']=='none'

@pytest.mark.skipif(MODE=='baseline',reason='New metadata projection only')
def test_lir_metadata_is_independent_copy_and_does_not_clear_pending_entry():
    f=fixture();f.forbid_source=True;f.say('登记声纹')
    before=f.handler._standalone_entry
    for _ in range(200):assert f.handler.public()['entry_name_pending']
    t=entry(f);t['business_turn_calls']=999
    assert entry(f)['business_turn_calls']==1 and f.handler._standalone_entry is before

@pytest.mark.skipif(MODE=='baseline',reason='New metadata projection only')
def test_original_clock_and_split_guard_methods_unchanged_ast():
    def methods(path,cls):
        tree=ast.parse(path.read_text(encoding='utf-8'));c=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
        return {n.name:ast.dump(n,include_attributes=False) for n in c.body if isinstance(n,ast.FunctionDef)}
    old=methods(HERE/'baseline/board/runtime/board_business.py','BoardBusinessRuntime')
    new=methods(HERE/'candidate/board/runtime/board_business.py','BoardBusinessRuntime')
    assert old==new
    old=methods(HERE/'baseline/board/runtime/board_business.py','LocalIdentityReplies')
    new=methods(HERE/'candidate/board/runtime/board_business.py','LocalIdentityReplies')
    for name in ('_entry_for','_new_entry','attach_speaker_business','_visual','_gallery'):assert old[name]==new[name]
    assert {name for name in old if old[name]!=new[name]}=={'__init__','reset','public','__call__'}
    old=methods(HERE/'baseline/board/runtime/audio/board_dialogue_jobs.py','BoardDialogueJobs')
    new=methods(HERE/'candidate/board/runtime/audio/board_dialogue_jobs.py','BoardDialogueJobs')
    assert {name for name in old if old[name]!=new[name]}=={'_route','_execute'}

@pytest.mark.parametrize('action',['face','voice','bare-name','cross-mode','cancel','expiry'])
def test_baseline_candidate_same_original_enrollment_outcomes(action):
    f=fixture()
    if action=='face':
        f.say('登记人脸，我叫合成姓名');assert f.handler.flow.stage=='authorize' and f.business.turns==[]
    elif action=='voice':
        f.forbid_source=True;f.say('登记声纹，我叫合成姓名')
        for s in ('样本一','样本二','样本三'):f.say(s)
        f.say('确认保存声纹');assert len(f.business.fixture.store.enrolls)==1 and f.commands==[]
    elif action=='bare-name':
        f.forbid_source=True;f.say('登记声纹');f.poll();f.say('我叫合成姓名');assert f.business.public()['active']
    elif action=='cross-mode':
        f.say('登记人脸，我叫合成姓名');epoch=f.handler.flow.epoch;f.say('登记声纹，我叫合成姓名')
        assert f.handler.flow.epoch==epoch and f.business.turns==[]
    elif action=='cancel':
        f.say('登记声纹');f.say('取消声纹登记');assert f.say('我叫合成姓名') is DIALOGUE_ROUTE
    elif action=='expiry':
        f.say('登记声纹');f.clock.now+=120.001;assert f.say('我叫合成姓名') is DIALOGUE_ROUTE
