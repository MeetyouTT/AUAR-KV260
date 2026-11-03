"""Candidate controller/jobs with fake inference, public PCM and memory hooks."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import threading
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
AURA=ROOT.parents[4]/'aura'
sys.path.insert(0,str(AURA))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module

dialogue=load('board.runtime.board_dialogue',ROOT/'after/board/runtime/board_dialogue.py')
jobs_module=load('board.runtime.audio.board_dialogue_jobs',ROOT/'after/board/runtime/audio/board_dialogue_jobs.py')
from common.model_inference_wire import Owner,audio_payload,make_response


class Clock:
    def __init__(self):self.now=10.
    def __call__(self):return self.now

class Store:
    def __init__(self):self.rows={};self.events=[];self.valid=True
    def preempt_compaction(self):self.events.append('preempt')
    def begin_turn(self,scope,turn_id,text,*,generation,metadata):
        self.rows[turn_id]=dict(status='generating',generation=generation,user=text)
        self.events.append('begin');return dict(user_event_id='public-user-event')
    def context(self,scope,**kwargs):self.events.append('context');return dict(messages=[],facts=[])
    def generated(self,turn_id,text,*,generation,**kwargs):
        self.rows[turn_id].update(status='awaiting_playback',assistant=text);self.events.append('generated')
    def check_prepared_turn_current(self,turn_id,*,generation):
        self.events.append('durable')
        if not self.valid or self.rows[turn_id]['status']!='awaiting_playback':raise PermissionError('revoked fixture')
        return True
    def bind_audio_receipt(self,turn_id,**receipt):
        self.rows[turn_id]['receipt']=receipt;self.events.append('bound')
    def ack_played(self,turn_id,**receipt):
        self.rows[turn_id]['status']='played' if receipt['complete'] else 'interrupted'
        self.events.append('heard' if receipt['complete'] else 'interrupted')
        return dict(status=self.rows[turn_id]['status'])
    def interrupt(self,turn_id,**kwargs):self.rows[turn_id]['status']='interrupted';self.events.append('interrupt')

class Models:
    def __init__(self,clock,reply='公开第一句。公开第二句！',rate=24000):
        self.clock,self.reply,self.rate=clock,reply,rate;self.calls=[];self.hook=None;self.cancelled=[]
    def request(self,kind,payload,**kwargs):
        self.calls.append((kind,payload,kwargs));self.clock.now+=.1
        if self.hook:self.hook(kind,payload)
        result=(dict(text=json.dumps(dict(reply_text=self.reply,emotion='friendly',avatar_action=''),ensure_ascii=False))
                if kind=='llm' else dict(audio=audio_payload(b'\x01\x00'*160,self.rate)))
        return make_response(Owner.from_dict(payload),result=result)
    def cancel(self,owner):self.cancelled.append(owner)

class Asr:
    model_sha256='a'*64
    def __init__(self,clock,text='公开的问题'):self.clock,self.text=clock,text;self.calls=0
    def transcribe(self,pcm,**kwargs):self.calls+=1;self.clock.now+=.01;return self.text

def setup(reply='公开第一句。公开第二句！',rate=24000):
    clock=Clock();store=Store();models=Models(clock,reply,rate)
    controller=dialogue.BoardDialogueController(store,models,board_boot_id='public-boot',
        system_prompt='公开测试人格',clock=clock)
    return controller,store,models,clock

def prepare(controller,**kwargs):
    return controller.prepare_text('公开的问题',scope=dict(kind='conversation',id='a'*32),
        session_id='public-session',generation=1,budget_ms=10000,**kwargs)

def clip():
    pcm=struct.pack('<h',1000)*3200
    return SimpleNamespace(capture_id='public-capture',pcm=pcm,audio=SimpleNamespace(sample_count=3200))


class ControllerTests(unittest.TestCase):
    def test_first_sentence_emits_before_second_tts_with_same_complete_receipt(self):
        controller,store,models,clock=setup();emitted=[]
        def sink(chunk,reply,start,token):
            emitted.append((chunk,reply,start,token,len(models.calls)))
            self.assertNotIn('bound',store.events)
            self.assertEqual(store.rows[next(iter(store.rows))]['status'],'awaiting_playback')
        plan=prepare(controller,chunk_sink=sink)
        self.assertEqual([e[4] for e in emitted],[2,3])
        self.assertEqual([e[2] for e in emitted],[0,160])
        self.assertTrue(all(e[3]==plan.playback_token for e in emitted))
        self.assertEqual(tuple(e[0] for e in emitted),plan.chunks)
        self.assertEqual(plan.sha256,hashlib.sha256(plan.pcm).hexdigest())
        self.assertEqual(plan.samples,320)
        self.assertEqual(store.events.count('durable'),4)
        self.assertNotIn('heard',store.events)
        self.assertEqual(controller.acknowledge(plan,playback_token=plan.playback_token,
            sha256=plan.sha256,samples=plan.samples,complete=True)['status'],'played')

    def test_no_sink_preserves_buffering_non24k_and_original_tts_order(self):
        controller,store,models,_=setup(rate=48000)
        plan=prepare(controller)
        self.assertEqual([kind for kind,_,_ in models.calls],['llm','tts','tts'])
        self.assertEqual(plan.sample_rate,48000)
        self.assertEqual(store.events.count('durable'),0)
        self.assertFalse(controller.last_prepare_metrics['streaming_enabled'])

    def test_long_reply_rejected_before_tts_and_before_any_chunk(self):
        controller,store,models,_=setup('公开。'+'词'*238)
        emitted=[]
        with self.assertRaises(dialogue.ReplyRejected):prepare(controller,chunk_sink=lambda *args:emitted.append(args))
        self.assertEqual([kind for kind,_,_ in models.calls],['llm'])
        self.assertEqual(emitted,[])
        self.assertNotIn('generated',store.events)

    def test_all_sentence_boundaries_preflight_before_first_valid_sentence_plays(self):
        controller,store,models,_=setup('先说。'+'词'*221)
        emitted=[]
        with self.assertRaises(dialogue.ReplyRejected):prepare(controller,chunk_sink=lambda *args:emitted.append(args))
        self.assertEqual([kind for kind,_,_ in models.calls],['llm'])
        self.assertEqual(emitted,[])

    def test_missing_durable_api_has_no_streaming_fallback(self):
        controller,store,models,_=setup();store.check_prepared_turn_current=None
        with self.assertRaisesRegex(RuntimeError,'guard is unavailable'):prepare(controller,chunk_sink=lambda *args:None)
        self.assertEqual([kind for kind,_,_ in models.calls],['llm'])
        self.assertNotIn('generated',store.events)

    def test_forget_during_tts_blocks_the_unheard_chunk(self):
        controller,store,models,_=setup();emitted=[]
        models.hook=lambda kind,payload:setattr(store,'valid',False) if kind=='tts' else None
        with self.assertRaises(PermissionError):prepare(controller,chunk_sink=lambda *args:emitted.append(args))
        self.assertEqual(emitted,[])
        self.assertNotIn('bound',store.events)
        self.assertNotIn('heard',store.events)

    def test_cancel_after_first_sentence_prevents_later_synthesis_and_final_receipt(self):
        controller,store,models,_=setup();cancelled=threading.Event();emitted=[]
        def sink(*args):emitted.append(args);cancelled.set()
        with self.assertRaises(dialogue.StaleGeneration):prepare(controller,chunk_sink=sink,cancel_event=cancelled)
        self.assertEqual(len(emitted),1)
        self.assertEqual([kind for kind,_,_ in models.calls],['llm','tts'])
        self.assertNotIn('bound',store.events)
        self.assertNotIn('heard',store.events)

    def test_second_tts_failure_cannot_commit_a_partial_reply(self):
        controller,store,models,_=setup();emitted=[]
        def hook(kind,payload):
            if kind=='tts' and sum(k=='tts' for k,_,_ in models.calls)==2:raise RuntimeError('public synthetic failure')
        models.hook=hook
        with self.assertRaises(RuntimeError):prepare(controller,chunk_sink=lambda *args:emitted.append(args))
        self.assertEqual(len(emitted),1)
        self.assertNotIn('bound',store.events)
        self.assertNotIn('heard',store.events)

    def test_non24k_stream_rejected_before_audio_and_default_bridge_unchanged(self):
        controller,store,models,_=setup(rate=48000);emitted=[]
        with self.assertRaises(dialogue.ReplyRejected):prepare(controller,chunk_sink=lambda *args:emitted.append(args))
        self.assertEqual(emitted,[])
        self.assertNotIn('bound',store.events)


class JobsTests(unittest.TestCase):
    def make(self,rate=24000,audio_converter=None):
        controller,store,models,clock=setup(rate=rate);asr=Asr(clock)
        jobs=jobs_module.BoardDialogueJobs(controller,dict(enabled=True,host='192.168.50.1',port=8797,timeout_ms=10000),
            'public-boot',asr=asr,scope_provider=lambda meta:dict(kind='conversation',id='a'*32),
            audio_converter=audio_converter,clock=clock,start_worker=False)
        self.addCleanup(jobs.close)
        return jobs,controller,store,models,asr,clock
    def collect(self,jobs):
        values=[]
        while True:
            item=jobs.poll()
            if item is None:return values
            values.append(item)

    def test_real_jobs_stream_and_metadata_measure_queue_not_speaker(self):
        jobs,controller,store,models,asr,clock=self.make();seen=[]
        def hook(kind,payload):
            if kind=='tts' and sum(k=='tts' for k,_,_ in models.calls)==2:
                seen.append(any(item.get('channel_event',{}).get('kind')=='audio' for item in jobs.progress))
        models.hook=hook
        jobs.submit(clip());self.assertTrue(jobs.run_next());values=self.collect(jobs)
        self.assertEqual(seen,[True]);self.assertEqual(asr.calls,1)
        self.assertEqual(sum(v.get('channel_event',{}).get('kind')=='end' for v in values),1)
        self.assertTrue(any('network_complete' in v for v in values))
        metrics=jobs.public()['latency']
        self.assertTrue(metrics['complete']);self.assertEqual(metrics['asr_calls'],1)
        self.assertEqual(metrics['prepare']['tts_calls'],2)
        self.assertEqual(metrics['prepare']['streamed_chunks'],2)
        self.assertLess(metrics['first_audio_queued_ms'],metrics['worker_total_ms'])
        self.assertFalse(metrics['speaker_first_audio_measured'])
        encoded=json.dumps(metrics)
        for private in ('公开的问题','公开第一句','public-capture','request_id','pcm','playback_token'):
            self.assertNotIn(private,encoded)

    def test_error_removes_queued_partial_audio_and_preserves_no_heard(self):
        jobs,controller,store,models,asr,clock=self.make()
        def hook(kind,payload):
            if kind=='tts' and sum(k=='tts' for k,_,_ in models.calls)==2:raise RuntimeError('public fixture failure')
        models.hook=hook;jobs.submit(clip());jobs.run_next();values=self.collect(jobs)
        self.assertEqual(len(values),1);self.assertIn('error',values[0])
        self.assertNotIn('heard',store.events);self.assertNotIn('bound',store.events)

    def test_explicit_native_rate_converter_keeps_original_buffered_path(self):
        converter=lambda plan:jobs_module.PlaybackPayload(b'\x01\x00'*160,converter_id='public-explicit-converter')
        jobs,controller,store,models,asr,clock=self.make(rate=48000,audio_converter=converter)
        jobs.submit(clip());jobs.run_next();values=self.collect(jobs)
        self.assertTrue(any('network_complete' in v for v in values))
        self.assertFalse(controller.last_prepare_metrics['streaming_enabled'])
        self.assertEqual(controller.last_prepare_metrics['streamed_chunks'],0)

    def test_wake_only_asr_once_and_no_llm_tts(self):
        jobs,controller,store,models,asr,clock=self.make();asr.text='雪妃'
        jobs.mark_wake_entry('public-capture');jobs.submit(clip());jobs.run_next();values=self.collect(jobs)
        self.assertEqual(asr.calls,1);self.assertEqual(models.calls,[])
        self.assertTrue(values[0]['wake_only']);self.assertTrue(jobs.public()['latency']['wake_only'])

    def test_candidate_sources_are_python39_and_original_queue_bounds_remain(self):
        for path in (ROOT/'after').rglob('*.py'):ast.parse(path.read_text(encoding='utf-8'),feature_version=(3,9))
        text=(ROOT/'after/board/runtime/audio/board_dialogue_jobs.py').read_text(encoding='utf-8')
        self.assertIn('while len(self.progress) >= 128:',text)
        self.assertIn('queue.Queue(maxsize=16)',text)


if __name__=='__main__':unittest.main()
