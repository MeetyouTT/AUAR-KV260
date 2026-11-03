"""Upfront name/consent, automatic completion, and bounded camera transactions."""
import copy
import unittest
from unittest.mock import patch
from common import voice_enrollment as speech
from board.identity.voice_enrollment import VoiceEnrollment


def snapshot():
    key={'camera_epoch':'camera','track_id':1,'track_generation':1}
    return {'protocol_version':'aura-ui-1','board_boot_id':'boot','service_epoch':'service',
        'sequence':1,'observed_mono_ms':1000,'ttl_ms':2000,'source_kind':'actual',
        'context':{'session_id':'camera-session','request_id':'','generation':0},
        'modules':{'camera':{'state':'READY'},'vision':{'state':'READY','people_count':1},
            'target':{'state':'CONFIRMED','selected':key,'tracks':[{'key':key,'label':'face'}]},
            'identity':{'state':'UNKNOWN','people':[],'db_version':0,'enrollment_sampling':{
                'session_id':'','stage':'idle','counts':{'collect':0,'validate':0},
                'total':0,'total_required':15,'detail':'waiting','bound_target':None}}},
        'capabilities':{'identity_enroll':False,'identity_delete':False,
            'identity_sample_start':True,'identity_sample_cancel':False}}


class SimpleFlowTests(unittest.TestCase):
    def setUp(self):
        self.now=1.;self.commands=[];self.view=snapshot()
        self.flow=VoiceEnrollment('boot',lambda:copy.deepcopy(self.view),self.command,simple=True,
            now_ms=lambda:1000,clock=lambda:self.now)

    @property
    def sample(self):return self.view['modules']['identity']['enrollment_sampling']

    def say(self,text):return self.flow.handle(text,copy.deepcopy(self.view))

    def command(self,command):
        self.commands.append(copy.deepcopy(command));action=command['action']
        if action=='identity_sample_start':
            self.sample.update(session_id='sample1',stage='collect',bound_target=copy.deepcopy(command['params']['target']))
            self.view['capabilities']['identity_sample_start']=False
        elif action=='identity_sample_cancel':self.sample.update(session_id='',stage='idle')
        else:
            self.view['modules']['identity'].update(state='KNOWN',db_version=1,
                last_operation={'command_id':command['command_id'],'action':action,'state':'COMMITTED',
                                'db_version':1,'detail':'saved'})
        return {'accepted':True,'command_id':command['command_id']}

    def start(self,replacement=False):
        if replacement:self.view['modules']['identity']['people']=[{'person_id':'original','display_name':'小林'}]
        expected='prepare_update_name' if replacement else 'prepare_name'
        self.assertEqual(self.say('帮我登记身份，我叫小林'),speech.result(expected,'小林'))
        self.assertEqual(self.commands,[])
        self.assertEqual(self.say('确认更新登记' if replacement else '确认登记')['code'],'sample_auto')

    def ready(self):
        self.sample.update(stage='ready',counts={'collect':10,'validate':5},total=15)
        self.view['capabilities']['identity_enroll']=True

    def test_combined_request_requires_explicit_name_confirmation_before_collection(self):
        self.assertEqual(self.say('汐蓝，帮我登记身份，我叫小林')['code'],'prepare_name')
        for text in ('好的','是的','确认登记吗'):
            self.assertEqual(self.say(text)['code'],'retry_confirm')
        self.assertEqual(self.commands,[])
        self.assertEqual(self.say('确认登记')['code'],'sample_auto')
        self.assertEqual([c['action'] for c in self.commands],['identity_sample_start'])

    def test_success_is_automatic_without_second_confirmation_and_token_bound(self):
        self.start();self.ready();replies=[]
        self.flow.guide(lambda reply,final:replies.append((reply,final)))
        self.assertEqual(replies,[(speech.result('registered'),True)])
        saves=[c for c in self.commands if c['action']=='identity_enroll']
        self.assertEqual(len(saves),1);self.assertEqual(saves[0]['params']['sampling_session_id'],'sample1')
        self.assertTrue(saves[0]['params']['confirmed']);self.assertEqual(self.flow.stage,'idle')

    def test_existing_name_still_requires_explicit_update_before_sampling(self):
        self.view['modules']['identity']['people']=[{'person_id':'original','display_name':'小林'}]
        self.assertEqual(self.say('帮我登记身份我叫小林')['code'],'prepare_update_name')
        self.assertEqual(self.say('确认登记')['code'],'retry_update');self.assertEqual(self.commands,[])
        self.assertEqual(self.say('确认更新登记')['code'],'sample_auto');self.ready()
        replies=[];self.flow.guide(lambda r,f:replies.append(r))
        save=next(c for c in self.commands if c['action']=='identity_enroll')
        self.assertEqual(save['params']['replace_person_id'],'original');self.assertEqual(replies,[speech.result('registered')])

    def test_name_correction_repeats_consent_for_the_new_name(self):
        self.say('帮我登记身份我叫小林')
        self.assertEqual(self.say('不是我叫小明'),speech.result('prepare_name','小明'))
        self.assertEqual(self.commands,[]);self.say('确认登记');self.ready();self.flow.guide(lambda *_:None)
        self.assertEqual(next(c for c in self.commands if c['action']=='identity_enroll')['params']['display_name'],'小明')

    def test_original_two_request_turns_also_use_upfront_confirmation(self):
        self.assertEqual(self.say('帮我登记身份')['code'],'ask_name')
        self.assertEqual(self.say('我叫小林')['code'],'prepare_name');self.assertEqual(self.commands,[])

    def test_automatic_validation_cue_once_without_response_and_bad_frame_waits(self):
        self.start();self.sample['stage']='validate';replies=[];steps=[]
        def advance(_):
            steps.append(1)
            if len(steps)==1:
                self.ready();self.view['capabilities']['identity_enroll']=False
            else:
                self.assertFalse(any(c['action']=='identity_enroll' for c in self.commands))
                self.view['capabilities']['identity_enroll']=True
        with patch('board.identity.voice_enrollment.time.sleep',advance):
            self.flow.guide(lambda r,f:replies.append(r))
        self.assertEqual(replies,[speech.result('sample_validate'),speech.result('registered')]);self.assertEqual(len(steps),2)

    def test_rejected_write_waits_for_fresh_frame_without_another_spoken_confirmation(self):
        self.start();self.ready();original=self.flow.command;attempts=[]
        def reject_once(c):
            if c['action']=='identity_enroll':
                attempts.append(1)
                if len(attempts)==1:return {'accepted':False,'command_id':c['command_id']}
            return original(c)
        self.flow.command=reject_once;replies=[]
        with patch('board.identity.voice_enrollment.time.sleep',lambda _:None):self.flow.guide(lambda r,f:replies.append(r))
        self.assertEqual(len(attempts),2);self.assertEqual(replies,[speech.result('registered')])

    def test_cancel_or_stale_network_request_never_saves(self):
        self.start();self.ready();replies=[]
        self.flow.guide(lambda r,f:replies.append(r),is_current=lambda:False)
        self.assertEqual(replies,[]);self.assertFalse(any(c['action']=='identity_enroll' for c in self.commands))

    def test_changed_database_or_session_never_uses_upfront_consent(self):
        for mutation in (lambda:self.view['modules']['identity'].update(db_version=1),
                         lambda:self.sample.update(session_id='replaced')):
            self.setUp();self.start();self.ready();mutation();replies=[]
            self.flow.guide(lambda r,f:replies.append(r))
            self.assertEqual(replies,[speech.result('sample_failed')])
            self.assertFalse(any(c['action']=='identity_enroll' for c in self.commands))

    def test_ambiguous_write_response_never_reports_success_or_retries(self):
        self.start();self.ready();attempts=[]
        def disconnect(command):attempts.append(command);raise OSError('connection lost')
        self.flow.command=disconnect;self.flow._cancel_sample=lambda _:None;replies=[]
        self.flow.guide(lambda r,f:replies.append(r))
        self.assertEqual(len(attempts),1);self.assertNotIn(speech.result('registered'),replies)

    def test_only_explicit_combined_requests_route_away_from_chat(self):
        for text in ('帮我登记身份我叫小林','汐蓝，帮我登记身份，我叫小林'):
            self.assertTrue(speech.enrollment_requested(text));self.assertEqual(speech.requested_name(text),'小林')
        for text in ('他说帮我登记身份我叫小林','如果我要登记身份我叫小林','帮我登记身份我叫小林然后删除所有资料',
                     '不要帮我登记身份我叫小林','“帮我登记身份我叫小林”','我叫小林'):
            self.assertFalse(speech.enrollment_requested(text))


class BoardSimpleFlowTests(unittest.TestCase):
    def setUp(self):
        from tests.framework.test_enrollment_sampling import IntegrationTests
        self.case=IntegrationTests();self.case.setUp();self.addCleanup(self.case.doCleanups)
        c=self.case.c
        self.flow=VoiceEnrollment('boot',c.state.snapshot,c.state.command,simple=True,
            now_ms=lambda:c.now,clock=lambda:c.now/1000)

    def say(self,text):return self.flow.handle(text,self.case.c.state.snapshot())

    def test_upfront_confirmation_then_camera_validation_commits_once(self):
        self.assertEqual(self.say('帮我登记身份我叫小林')['code'],'prepare_name')
        self.assertEqual(self.case.c.store.revision,0)
        self.assertEqual(self.say('确认登记')['code'],'sample_auto')
        self.case.ready();replies=[];self.flow.guide(lambda r,f:replies.append(r))
        self.assertEqual(replies,[speech.result('registered')]);self.assertEqual(self.case.c.store.revision,1)
        self.assertEqual(self.case.c.store.people()[0]['display_name'],'小林')

    def test_replaced_camera_token_refuses_previously_authorized_commit(self):
        self.say('帮我登记身份我叫小林');self.say('确认登记');self.case.ready()
        command=self.case.c.enrollment(cid='wrong-session');command['params']['sampling_session_id']='replaced'
        self.assertFalse(self.case.c.state.command(command)['accepted']);self.assertEqual(self.case.c.store.revision,0)
        self.case.c.service.sampling.session_id='replaced';replies=[];self.flow.guide(lambda r,f:replies.append(r))
        self.assertEqual(replies,[speech.result('sample_failed')]);self.assertEqual(self.case.c.store.revision,0)


if __name__=='__main__':unittest.main()
