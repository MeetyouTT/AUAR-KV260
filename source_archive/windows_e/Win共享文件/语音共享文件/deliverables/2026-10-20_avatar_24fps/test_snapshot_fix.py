import copy,hashlib,json,tempfile,time,types,unittest
from pathlib import Path
from tools.board_avatar_worker import snapshot_copy
from tools.board_recording import RecordingController
from tools.render_performance import PerformanceRecorder
from board.runtime.audio.capture import CapturedAudio,FORMAT
from host.model_service.protocol import AudioRef

class SnapshotTests(unittest.TestCase):
    def test_detached_snapshot_preserves_values_and_fallback(self):
        source={'log':[{'actions':[{'a':'ack_nod'}],'values':(1,2)}],'data':{1,2}}
        result=snapshot_copy(source)
        self.assertEqual(result,copy.deepcopy(source))
        result['log'][0]['actions'][0]['a']='changed';result['data'].add(3)
        self.assertEqual(source['log'][0]['actions'][0]['a'],'ack_nod');self.assertEqual(source['data'],{1,2})

    def controller(self):
        c=RecordingController.__new__(RecordingController)
        c._collect=lambda:None;c.capture=None;c.utterance=None;c.closed=False
        c.recording_state='IDLE';c.recording_error='';c.transcription={'state':'IDLE'}
        c.auto_enabled=False;c.auto_state='STOPPED';c.auto_error='';c.auto_turns=0
        counts={'core':0,'service':0}
        def public():
            counts['core']+=1
            return dict(phase='IDLE',playing=False,paused=False,pending_job=None,audio_output_state='IDLE_READY')
        def service():counts['service']+=1;return dict(enabled=True,pending=False,streaming=True,feedback_ready=True)
        c.controller=types.SimpleNamespace(public=public)
        c.transcriber=types.SimpleNamespace(public=service,enabled=lambda:True)
        c._playback_active=lambda:(_ for _ in ()).throw(AssertionError('Duplicate output snapshot'))
        return c,counts

    def test_one_playback_and_service_snapshot_per_publication(self):
        c,counts=self.controller();state=c.public()
        self.assertEqual(counts,dict(core=1,service=1))
        self.assertTrue(state['automatic_conversation']['can_start'])
        self.assertTrue(state['local_recording']['can_start'])

    def test_completed_pcm_cache_is_detached_and_invalidates(self):
        c,counts=self.controller();pcm=b'\x01\x00'*3200
        c.utterance=CapturedAudio('one',AudioRef(1,0,3200,FORMAT),pcm,1,201)
        first=c.public()['local_recording']['result'];first['format']['rate_hz']=1
        self.assertEqual(c.public()['local_recording']['result']['format']['rate_hz'],16000)
        self.assertEqual(c._public_metadata['pcm_sha256'],hashlib.sha256(pcm).hexdigest())
        c.utterance=CapturedAudio('two',AudioRef(1,3200,3200,FORMAT),b'\x02\x00'*3200,201,401)
        result=c.public()['local_recording']['result']
        self.assertEqual(result['capture_id'],'two');self.assertNotEqual(result['pcm_sha256'],first['pcm_sha256'])
        c.utterance=None;self.assertIsNone(c.public()['local_recording']['result'])
        self.assertIsNone(c._public_utterance)

    def test_phase_log_uses_actual_intervals_without_cross_phase_attribution(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'performance.jsonl';p=PerformanceRecorder(path)
            for phase,state,at,seq in [('IDLE','IDLE',0,1),('IDLE','IDLE',.125,2),
                                       ('SPEAKING','ACK_NOD',1,3),('SPEAKING','ACK_NOD',1.3,4),
                                       ('IDLE','IDLE',5.1,5)]:
                p.observe(phase,state,at,seq,dict(total=20,public=2))
            p.close(5.2)
            rows=[json.loads(x) for x in path.read_text().splitlines()]
            self.assertEqual(len(rows),2)
            phases={r['phase']:r for r in rows[0]['phases']}
            self.assertAlmostEqual(phases['IDLE']['interval_ms']['p95'],125)
            self.assertAlmostEqual(phases['SPEAKING']['interval_ms']['p95'],300)
            self.assertEqual(phases['SPEAKING']['over_187_5ms'],1)
            self.assertNotIn('reply',path.read_text());self.assertEqual(p.status()['written'],2)

if __name__=='__main__':unittest.main()
