"""Public synthetic enrollment state; actual router/hub, no DB, model or device."""
from collections import OrderedDict
import copy
import hashlib
import json
from types import SimpleNamespace as NS
import unittest

from common.asr_wire import context
from common.identity_links import _guard,validate_resolution
from common.speaker_visual import unavailable,validate_visual
from common.voice_enrollment import identity_query_requested
from tools.unified_identity_binding import UnifiedBindingRouter
from tools.binding_hub_runtime import BindingHubRuntime

PCM=b'\x01\x00'*4800
def capture(number=1):
    return context(dict(protocol='aura-asr-1',board_boot_id='public-boot',session_id='public-session',
        request_id='query-'+str(number),capture_id='capture-'+str(number),generation=number,
        sample_count=len(PCM)//2,pcm_sha256=hashlib.sha256(PCM).hexdigest(),budget_ms=120000),PCM)

def visual(meta):
    target=dict(camera_epoch='public-camera',track_id=1,track_generation=1)
    return validate_visual(dict(version=1,context=meta,source_kind='actual',state='FACE_AT_CAPTURE_BOUNDARIES',
        reason='NOT_ACTIVE_SPEAKER_PROOF',evidence=dict(service_epoch='public-service',camera_epoch='public-camera',
        target=target,gallery_revision=2,face_identity_id='public-face',boundary_start_ms=1000,
        boundary_end_ms=1100,checked_ms=1200,source_start_ms=990,source_end_ms=1090,frame_start=10,frame_end=11)),meta)

class Registry:
    def __init__(self,meta,scene,state='SAMPLING_VOICE'):
        self.clock=lambda:10.
        self.row={'state':state,'face_guard':json.dumps(_guard(scene,meta)),
            'face_receipt':json.dumps({'revision_after':2,'identity_id':'public-face'}),'name':'小林'}
        self.confirm_calls=0;self.resolve_calls=0
        self.resolution='UNKNOWN'
    def attempt(self,attempt,meta):return copy.deepcopy(self.row)
    def confirm(self,*args):self.confirm_calls+=1;return False
    def resolve(self,meta,proofs,anonymous=None):
        self.resolve_calls+=1
        state=self.resolution
        return validate_resolution(dict(version=1,context=meta,state=state,
            reason='MODALITY_IDENTITIES_DISAGREE' if state=='CONFLICT' else 'NO_LINKED_EVIDENCE',
            person_id='b'*32 if state=='MATCH_CANDIDATE' else None,name='小林' if state=='MATCH_CANDIDATE' else None,
            modalities=['face','voice'] if state=='CONFLICT' else ['face'] if state=='MATCH_CANDIDATE' else [],
            claim_scope='visible_person' if state=='MATCH_CANDIDATE' else 'none',provisional=False,
            field_calibrated=False,identity_verified=False,personal_memory_allowed=False,single_speaker_verified=False),meta)

class Speaker:
    def __init__(self,meta):
        actor=meta['board_boot_id'],meta['session_id']
        self.calls=[];self.sessions={actor:{'stage':'sample1'}}
        self.device=NS(state=lambda meta:{'active':True},sessions=self.sessions,
            key=lambda meta:(meta['board_boot_id'],meta['session_id']))
    def turn(self,meta,text,pcm):
        self.calls.append((copy.deepcopy(meta),text,pcm))
        self.sessions[(meta['board_boot_id'],meta['session_id'])]['stage']='sample2'
        return '已收到一段，请继续下一段。',None
    def take_alias(self,meta):return None

def router_fixture(state='SAMPLING_VOICE'):
    meta=capture();scene=visual(meta);registry=Registry(meta,scene,state);speaker=Speaker(meta)
    router=UnifiedBindingRouter(registry,speaker,voice_gallery=lambda:None,face_gallery=lambda:None)
    router.active[router.actor(meta)]='a'*32
    return meta,scene,registry,speaker,router

def hub_fixture(state='UNKNOWN'):
    meta,scene,registry,speaker,router=router_fixture()
    registry.resolution=state
    hub=object.__new__(BindingHubRuntime)
    hub.router=router;hub.registry=registry;hub.speaker=speaker
    hub.clock=lambda:10.;hub.latest=OrderedDict();hub.routes=OrderedDict()
    hub._trim=lambda:None;hub.reconcile_voice=lambda:None;hub._gallery_for=lambda meta,digest:None
    hub._face_reference=lambda meta,scene,reference:None
    hub.face_naming_proof=lambda meta,scene:None
    hub.voice_reference=lambda unused:{'store_id':'public-voice-store'}
    hub.evidence=[];hub._control_evidence=lambda *args,**kw:hub.evidence.append(copy.deepcopy(kw))
    hub.anonymous=NS(evidence=lambda meta:None)
    hub.analysis_calls=[]
    def analyze(meta,pcm):hub.analysis_calls.append(meta['request_id']);return {'state':'UNAVAILABLE'},None
    hub.hub=NS(progressive_speaker=NS(analyze=analyze,provisional=NS(proof=lambda *args,**kwargs:None)))
    return meta,scene,registry,speaker,hub

class QueryIsolationTests(unittest.TestCase):
    def test_face_question_cannot_become_next_voice_enrollment_sample(self):
        meta,scene,registry,speaker,router=router_fixture()
        before=copy.deepcopy((registry.row,router.active,speaker.sessions))
        result=router.route(meta,'我是谁',PCM,visual=scene)
        self.assertEqual(result['route'],'ordinary')
        self.assertEqual(speaker.calls,[])
        self.assertEqual((registry.row,router.active,speaker.sessions),before)
        self.assertFalse(result['personal_memory_allowed'])

    def test_current_supported_natural_identity_questions_are_all_read_only(self):
        for question in ('我是谁','雪妃，我是谁呀？','你还认识我吗','我叫什么名字','我以前登记过人脸'):
            with self.subTest(question=question):
                meta,scene,registry,speaker,router=router_fixture()
                self.assertTrue(identity_query_requested(question))
                self.assertEqual(router.route(meta,question,PCM,visual=scene)['route'],'ordinary')
                self.assertFalse(speaker.calls)

    def test_query_without_a_face_does_not_advance_or_cancel_voice_enrollment(self):
        meta,scene,registry,speaker,router=router_fixture()
        before=copy.deepcopy(router.active)
        self.assertEqual(router.route(meta,'我是谁',PCM,visual=unavailable(meta))['route'],'ordinary')
        self.assertEqual(router.active,before);self.assertFalse(speaker.calls)

    def test_actual_sample_still_uses_original_voice_workflow(self):
        meta,scene,registry,speaker,router=router_fixture()
        result=router.route(meta,'今天的阳光很好',PCM,visual=scene)
        self.assertEqual(result['route'],'device_reply');self.assertEqual(len(speaker.calls),1)
        self.assertEqual(speaker.calls[0][1:],('今天的阳光很好',PCM))
        self.assertEqual(speaker.sessions[router.actor(meta)]['stage'],'sample2')

    def test_quoted_negated_compound_and_assistant_questions_keep_original_sampling_semantics(self):
        for text in ('你是谁','不要回答我是谁','他说我是谁','“我是谁”','我是谁然后保存身份'):
            with self.subTest(text=text):
                meta,scene,registry,speaker,router=router_fixture()
                self.assertFalse(identity_query_requested(text))
                self.assertEqual(router.route(meta,text,PCM,visual=scene)['route'],'device_reply')
                self.assertEqual(len(speaker.calls),1)

    def test_face_confirmation_stage_keeps_original_flow(self):
        meta,scene,registry,speaker,router=router_fixture('AWAIT_CONFIRMATION')
        result=router.route(meta,'我是谁',PCM,visual=scene)
        self.assertEqual(result['route'],'face_exchange');self.assertEqual(result['board_text'],'我是谁')
        self.assertEqual(registry.confirm_calls,1);self.assertFalse(speaker.calls)

class ProductionHubQueryTests(unittest.TestCase):
    def test_existing_hub_identity_query_runs_instead_of_sample(self):
        meta,scene,registry,speaker,hub=hub_fixture()
        result=hub.route(meta,'我是谁',PCM,visual=scene)
        self.assertEqual(result['decision']['route'],'device_reply')
        self.assertEqual(result['decision']['reason'],'EXPLICIT_IDENTITY_QUERY')
        self.assertIn('访客',result['decision']['reply'])
        self.assertEqual(registry.resolve_calls,1);self.assertEqual(hub.analysis_calls,[meta['request_id']])
        self.assertFalse(speaker.calls);self.assertFalse(result['decision']['personal_memory_allowed'])

    def test_cross_modality_conflict_still_cannot_name_a_person(self):
        meta,scene,registry,speaker,hub=hub_fixture('CONFLICT')
        result=hub.route(meta,'你还认识我吗',PCM,visual=scene)
        self.assertIn('不一致',result['decision']['reply']);self.assertNotIn('小林',result['decision']['reply'])
        self.assertFalse(speaker.calls);self.assertFalse(result['decision']['personal_memory_allowed'])

    def test_visible_face_candidate_remains_scoped_and_does_not_grant_private_memory(self):
        meta,scene,registry,speaker,hub=hub_fixture('MATCH_CANDIDATE')
        result=hub.route(meta,'我叫什么名字',PCM,visual=scene)
        self.assertIn('当前画面',result['decision']['reply']);self.assertIn('小林',result['decision']['reply'])
        self.assertIn('不代表',result['decision']['reply']);self.assertFalse(speaker.calls)
        self.assertFalse(result['decision']['personal_memory_allowed'])

    def test_same_request_is_cached_without_a_second_sample_or_analysis(self):
        meta,scene,registry,speaker,hub=hub_fixture()
        first=hub.route(meta,'我是谁',PCM,visual=scene)
        self.assertEqual(hub.route(meta,'我是谁',PCM,visual=scene),first)
        self.assertEqual(registry.resolve_calls,1);self.assertEqual(len(hub.analysis_calls),1);self.assertFalse(speaker.calls)

    def test_reused_request_with_changed_text_is_rejected_before_more_work(self):
        meta,scene,registry,speaker,hub=hub_fixture()
        hub.route(meta,'我是谁',PCM,visual=scene)
        with self.assertRaises(ValueError):hub.route(meta,'你还认识我吗',PCM,visual=scene)
        self.assertEqual(registry.resolve_calls,1);self.assertFalse(speaker.calls)

if __name__=='__main__':unittest.main()
