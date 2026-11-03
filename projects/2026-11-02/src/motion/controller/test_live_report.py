import json,unittest
from live_report import bounded_live_report


class LiveReportTests(unittest.TestCase):
    def test_live_payload_stays_bounded_and_final_history_is_preserved(self):
        commands=[dict(source_frame_id=i,target_us=1450,mono_ms=1000+i) for i in range(128)]
        observations=[dict(source_frame_id=i,decision='EDGE_FOLLOW',source_age_ms=50) for i in range(512)]
        result=dict(state='FOLLOWING',commands_accepted=200,readback={'flags':15},
                    command_trace=commands,events=[{'reason':'EDGE_FOLLOW'} for i in range(48)])
        view=bounded_live_report({'status':'CONTINUOUS_FACE_ZONE_RUNNING'},result,observations,{'READY':600},{})
        self.assertEqual(view['result']['commands_accepted'],200)
        self.assertEqual(view['observation_trace'][0]['source_frame_id'],504)
        self.assertEqual(len(view['result']['command_trace']),8)
        self.assertEqual(len(view['result']['events']),8)
        self.assertEqual(len(result['command_trace']),128)
        self.assertEqual(len(observations),512)
        self.assertLess(len(json.dumps(view)),4000)
    def test_live_readback_and_fault_are_never_hidden_by_trace_trimming(self):
        result=dict(state='FAULT',fatal=True,readback={'flags':64,'lease_left_ms':0},
                    reason='SOURCE_LEASE_EXPIRED',command_trace=[],events=[])
        view=bounded_live_report({'status':'RUNNING'},result,[],{}, {})
        self.assertEqual(view['result']['readback'],result['readback'])
        self.assertTrue(view['result']['fatal'])
