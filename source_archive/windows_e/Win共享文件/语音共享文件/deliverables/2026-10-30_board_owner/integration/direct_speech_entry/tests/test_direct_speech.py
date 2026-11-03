"""Fresh production entry/pair policy; only device/player/ASR delivery is fake."""
import ast
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[3]
sys.path.insert(0,str(PROJECT/'aura'))
import tools
PAIR_TOOLS=ROOT.parent/'production_business_overlay/candidate/aura/tools'
if str(PAIR_TOOLS) not in tools.__path__:tools.__path__.append(str(PAIR_TOOLS))
import common
common.__path__.insert(0,str(ROOT/'before/common'))
COMMON_FALLBACK=PAIR_TOOLS.parent/'common'
if str(COMMON_FALLBACK) not in common.__path__:common.__path__.append(str(COMMON_FALLBACK))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);sys.modules[name]=value;spec.loader.exec_module(value)
    return value

load('tools.board_recording',ROOT/'before/tools/board_recording.py')
load('tools.handsfree_recording',ROOT/'before/tools/handsfree_recording.py')
load('tools.barge_in_recording',ROOT/'before/tools/barge_in_recording.py')
voice=load('tools.voice_first_recording',ROOT/'after/tools/voice_first_recording.py')
production=load('tools.production_listening',ROOT/'after/tools/production_listening.py')
jobs=load('board.runtime.audio.board_dialogue_jobs',ROOT/'before/board/runtime/audio/board_dialogue_jobs.py')
policy_tree=ast.parse((ROOT/'before/board/runtime/board_business.py').read_text(encoding='utf-8'))
policy_node=next(node for node in policy_tree.body if isinstance(node,ast.FunctionDef) and node.name=='board_entry_policy')
policy_globals={}
exec(compile(ast.Module(body=[policy_node],type_ignores=[]),'<exact-production-entry-policy>','exec'),policy_globals)
policy=policy_globals['board_entry_policy']
paired_jobs=load('direct_entry_paired_jobs',ROOT/'before/tools/yuki_jobs_candidate.py')
from tools.yuki_business_candidate import CharacterSpeechPolicy,LocalRecordText
from tools.formal_yuki import paired_recording_type
from board.runtime.audio.capture import CapturedAudio,FORMAT
from host.model_service.protocol import AudioRef

GOOD=b'\xe8\x03'*3200


class Pair:
    def __init__(self):
        self.speech=CharacterSpeechPolicy();self.ready=True;self.invalidators=[]
    def ready_now(self):return self.ready
    def require_ready(self):
        if not self.ready:raise RuntimeError('Pair not ready')

class Controller:
    def __init__(self):
        self.last_error='';self.events=[];self.completions=[]
        self.state=dict(phase='IDLE',playing=False,paused=False,pending_job=None,audio_output_state='IDLE_READY')
    def public(self):return dict(self.state)
    def cancel(self):self.state.update(phase='IDLE',playing=False,paused=False,pending_job=None)
    def tick(self):pass
    def take_completion(self):return self.completions.pop(0) if self.completions else None
    def channel_event(self,header,pcm,owner,assets,requested_at):
        self.events.append(header)
        if header['kind']=='start':self.state['phase']='THINKING'
    def channel_complete(self,owner,result):pass

class Capture:
    def __init__(self,*args,**kwargs):self.state='IDLE';self.counter=0;self.result=None;self.on_speech_start=None
    def start(self):self.counter+=1;self.state='RECORDING';self.result=None;return 'public-cap-'+str(self.counter)
    def snapshot(self):return dict(state=self.state,error='',sample_count=0 if self.result is None else self.result.audio.sample_count,
        speech_active=False,input_ready=self.state=='RECORDING',has_result=self.result is not None)
    def finish(self,pcm=GOOD):
        self.on_speech_start()
        self.result=CapturedAudio('public-cap-'+str(self.counter),AudioRef(1,0,len(pcm)//2,FORMAT),pcm,1000,1200)
        self.state='READY'
    def take(self):
        assert self.result is not None
        value=self.result;self.result=None;self.state='IDLE';return value
    def cancel(self):self.state='CANCELLED';self.result=None
    def close(self):self.cancel()

class Transcriber:
    feedback_assets={}
    def __init__(self,pair,boot,text,camera):
        self.character_pair=pair;self.boot=boot;self.text=text;self.live=True;self.held=False
        self.pending=False;self.results=[];self.submitted=[];self.admitted=[];self.marked=[];self.generation=0
        self.last_ack=None;self.visual_entry_handler=policy('voice_first',boot,camera,now_ms=lambda:1000)
        self.work=None;self._entry_error=jobs.BoardDialogueJobs._entry_error
    def _current(self,job):return self.live
    def enabled(self):return True
    def public(self):return dict(enabled=True,streaming=True,feedback_ready=True,pending=self.pending,last_playback_ack=self.last_ack)
    def select_conversation(self,*,resume):pass
    def capture_started(self,cid):pass
    def mark_visual_entry(self,cid):self.marked.append(('visual',cid))
    def mark_wake_entry(self,cid):self.marked.append(('wake',cid))
    def submit(self,clip):
        self.submitted.append(clip);self.generation+=1;self.pending=True
        meta=dict(protocol='aura-asr-1',board_boot_id=self.boot,session_id='public-session',request_id='public-req-'+str(self.generation),
            generation=self.generation,capture_id=clip.capture_id,sample_count=clip.audio.sample_count,
            pcm_sha256=hashlib.sha256(clip.pcm).hexdigest(),budget_ms=10000)
        entry=self.marked[-1][0] if self.marked and self.marked[-1][1]==clip.capture_id else None
        self.work=SimpleNamespace(meta=meta,entry=entry,pcm=clip.pcm,capture_snapshot=None,
            scope=dict(kind='conversation',id='a'*32),cancelled=threading.Event())
        if not self.held:self.deliver()
        return meta
    def deliver(self):
        job=self.work
        try:raw=paired_jobs._admit_text(self,job,self.text)
        except ValueError as exc:
            if not getattr(exc,'entry_rejected',False):raise
            self.results.append(dict(entry_rejected=True,context=job.meta));self.pending=False;return
        self.admitted.append(raw)
        if raw is None:
            self.results.append(dict(wake_detected=True,wake_only=True,context=job.meta));self.pending=False
        else:
            for kind in ('start','transcript'):
                self.results.append(dict(channel_event=dict(kind=kind,text=raw),pcm=b'',context=job.meta))
    def poll(self):return self.results.pop(0) if self.results else None
    def cancel(self):self.pending=False;self.results.clear()
    def close(self):self.cancel()


class EntryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.now=[10.];self.camera_calls=0
    def make(self,text='今天心情不错',*,production_mode=True,barge_enabled=False):
        pair=Pair()
        def camera():self.camera_calls+=1;raise AssertionError('Ordinary speech cannot query camera')
        tx=Transcriber(pair,'public-boot',text,camera);inner=Controller()
        options=dict(transcriber=tx,boot_id='public-boot',attention_provider=camera,clock=lambda:self.now[0],
            auto_capture_factory=Capture,barge_capture_factory=lambda:self.fail('Unexpected barge capture'),
            barge_enabled=barge_enabled,device_observer=False,visual_social=False,early_listen=False)
        if production_mode:
            settings=production.ProductionMonitorChoice(Path(self.temp.name).resolve())
            kind=paired_recording_type(voice.VoiceFirstRecordingController,pair)
            owner=kind(inner,monitor_settings=settings,**options)
            business=SimpleNamespace(recording=owner,character_pair=pair,
                runtime=SimpleNamespace(started=True,closed=False,config=SimpleNamespace(data_origin='board')))
            production.bind_automatic_listening(owner,business,pair)
        else:owner=voice.VoiceFirstRecordingController(inner,**options)
        self.addCleanup(owner.close)
        owner.tick()
        return owner,tx,inner,pair

    def test_non_vocative_first_turn_passes_actual_pair_admission_and_only_then_enters(self):
        owner,tx,inner,pair=self.make();tx.held=True
        self.assertFalse(owner.wake_word_required)
        owner.capture.finish();owner.tick()
        self.assertFalse(owner.monitor_entered);self.assertFalse(owner.auto_enabled)
        self.assertEqual(tx.marked[0][0],'visual')
        tx.deliver();owner.tick()
        self.assertTrue(owner.monitor_entered);self.assertTrue(owner.auto_enabled)
        self.assertEqual(tx.admitted,['今天心情不错'])
        self.assertEqual(self.camera_calls,0)
        status=owner.public()['handsfree_dialogue']
        self.assertEqual(status['entry_mode'],'direct_speech');self.assertEqual(status['wake_words'],[])
        self.assertFalse(status['visual_required'])

    def test_optional_name_prefix_remains_verbatim_for_memory_while_intent_may_strip(self):
        text='雪妃，今天心情不错';owner,tx,inner,pair=self.make(text)
        owner.capture.finish();owner.tick()
        self.assertEqual(tx.admitted,[text])
        local=LocalRecordText.capture(tx.work,tx.admitted[0],pair.speech)
        self.assertEqual(local.raw_record_text,text)
        self.assertNotEqual(local.intent_text,text)
        self.assertEqual(self.camera_calls,0)

    def test_silent_and_noise_text_entry_rejected_without_entering_or_camera(self):
        for text,pcm in (('今天心情不错',b'\0\0'*3200),('音乐',GOOD),('哈哈',GOOD)):
            with self.subTest(text=text):
                owner,tx,inner,pair=self.make(text)
                owner.capture.finish(pcm);owner.tick()
                self.assertFalse(owner.monitor_entered);self.assertFalse(owner.auto_enabled)
                self.assertEqual(tx.admitted,[]);self.assertEqual(inner.events,[])
                self.assertGreater(owner.monitor_stats['entry_rejected'],0)
                owner.close()
        self.assertEqual(self.camera_calls,0)

    def test_wrong_speech_proof_and_wrong_boot_cannot_enter(self):
        owner,tx,inner,pair=self.make()
        owner.capture.finish();owner.speech_proof=('foreign-capture',owner.monitor_key);owner.tick()
        self.assertEqual(tx.submitted,[]);self.assertFalse(owner.monitor_entered)
        job=SimpleNamespace(entry='visual',pcm=GOOD,meta=dict(board_boot_id='wrong-boot'),capture_snapshot=None)
        with self.assertRaises(ValueError):paired_jobs._admit_text(tx,job,'今天心情不错')
        job.meta['board_boot_id']='public-boot';tx.live=False
        with self.assertRaises(ValueError):paired_jobs._admit_text(tx,job,'今天心情不错')

    def test_old_generation_transcript_after_pause_or_cancel_does_not_reenter(self):
        owner,tx,inner,pair=self.make();tx.held=True
        owner.capture.finish();owner.tick();old=dict(tx.work.meta)
        owner.handsfree_toggle()
        tx.results.append(dict(channel_event=dict(kind='start'),pcm=b'',context=old))
        owner.tick()
        self.assertFalse(owner.monitor_enabled);self.assertFalse(owner.monitor_entered)
        owner.handsfree_toggle();self.now[0]+=1;owner.tick()
        owner.cancel()
        tx.results.append(dict(channel_event=dict(kind='start'),pcm=b'',context=old))
        owner.tick()
        self.assertFalse(owner.monitor_entered)

    def test_direct_capture_never_starts_while_playback_is_active(self):
        owner,tx,inner,pair=self.make();owner.cancel()
        inner.state.update(phase='SPEAKING',playing=True)
        previous=owner.capture.counter;self.now[0]+=1;owner.tick()
        self.assertEqual(owner.capture.counter,previous)
        self.assertFalse(owner._recording())
        inner.cancel();owner.tick();self.assertEqual(owner.capture.counter,previous+1)

    def test_pause_preference_cancel_rearm_and_resume_remain_owned(self):
        owner,tx,inner,pair=self.make();previous=owner.capture.counter
        owner.handsfree_toggle();self.now[0]+=30;owner.tick()
        self.assertFalse(owner.monitor_enabled);self.assertFalse(owner.monitor_settings.read())
        self.assertEqual(owner.capture.counter,previous)
        owner.handsfree_toggle();self.now[0]+=1;owner.tick()
        self.assertTrue(owner.monitor_settings.read());self.assertEqual(owner.capture.counter,previous+1)
        owner.cancel();self.now[0]+=1;owner.tick()
        self.assertTrue(owner.monitor_enabled);self.assertEqual(owner.capture.counter,previous+2)
        self.assertFalse(owner.wake_word_required)

    def test_next_capture_waits_for_matching_complete_ack_and_tail(self):
        owner,tx,inner,pair=self.make();owner.capture.finish();owner.tick()
        previous=owner.capture.counter
        owner.transcription['state']='ANSWERED';tx.pending=False;inner.cancel()
        owner.rearm_at=self.now[0]+.5;owner.ack_deadline=self.now[0]+7
        owner.tick();self.assertEqual(owner.capture.counter,previous)
        tx.last_ack=dict(request_id=owner.transcription['request_id'],committed=True)
        self.now[0]+=.4;owner.tick();self.assertEqual(owner.capture.counter,previous)
        self.now[0]+=.2;owner.tick();self.assertEqual(owner.capture.counter,previous+1)

    def test_default_legacy_mode_still_requires_wake_and_accepts_wake_only(self):
        owner,tx,inner,pair=self.make(production_mode=False)
        self.assertTrue(owner.wake_word_required);owner.capture.finish();owner.tick()
        self.assertEqual(tx.marked[0][0],'wake');self.assertFalse(owner.monitor_entered)
        tx.text='雪妃';owner.capture.finish();owner.tick()
        self.assertTrue(owner.monitor_entered);self.assertTrue(owner.auto_enabled)
        self.assertEqual(tx.admitted,[None])

if __name__=='__main__':unittest.main()
