"""Metric semantics and attribution guards, no models or native devices."""
import importlib.util
import copy
import json
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('dashboard',Path(__file__).with_name('model_runtime_dashboard.py'))
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)


class CounterSemantics(unittest.TestCase):
    def test_cpu_one_core_on_twelve_core_machine(self):
        self.assertAlmostEqual(d.percent_delta(3,5,2,12),100/12)

    def test_all_core_capacity_is_one_hundred(self):
        self.assertEqual(d.percent_delta(0,24,2,12),100)

    def test_missing_or_reset_cpu_is_unknown(self):
        for old,new,elapsed,cpus in [(None,2,2,12),(4,2,2,12),(0,1,0,12),(0,1,2,0)]:
            self.assertIsNone(d.percent_delta(old,new,elapsed,cpus))

    def test_nonfinite_gpu_metadata_is_unknown(self):
        for value in ('N/A','[N/A]',float('inf'),float('nan'),None):
            self.assertIsNone(d.finite(value))

    def test_exclusive_process_groups_prevent_host_double_count(self):
        processes={1:{'ppid':0},2:{'ppid':1},3:{'ppid':2},4:{'ppid':1},5:{'ppid':4},6:{'ppid':1}}
        groups=d.exclusive_groups(dict(llm={2},tts={4},host={1}),processes)
        self.assertEqual(groups['llm'],{2,3});self.assertEqual(groups['tts'],{4,5})
        self.assertEqual(groups['host'],{1,6})
        self.assertEqual(sum(map(len,groups.values())),6)

    def test_parent_cycle_is_bounded(self):
        self.assertEqual(d.descendants({1},{1:{'ppid':2},2:{'ppid':1}}),{1,2})

    def test_dead_root_does_not_adopt_reused_parent_id(self):
        self.assertEqual(d.descendants({1},{2:{'ppid':1}}),set())

    def test_gpu_uses_busiest_engine_not_sum_of_different_engines(self):
        values={'pid_1_luid_a_phys_0_eng_0_engtype_3D':30,
            'pid_2_luid_a_phys_0_eng_0_engtype_3D':20,
            'pid_1_luid_a_phys_0_eng_1_engtype_Compute':40,
            'pid_9_luid_a_phys_0_eng_0_engtype_3D':90}
        self.assertEqual(d.engine_usage(values,{1,2}),50)

    def test_gpu_duplicate_instance_suffix_shares_physical_engine(self):
        values={'pid_1_luid_a_phys_0_eng_0_engtype_3D':10,
            'pid_1_luid_a_phys_0_eng_0_engtype_3D#1':20}
        self.assertEqual(d.engine_usage(values,{1}),30)

    def test_gpu_empty_healthy_counter_is_zero_not_unknown(self):
        self.assertEqual(d.engine_usage({},set()),0)

    def test_gpu_rejects_unselected_processes(self):
        self.assertEqual(d.engine_usage({'pid_19_luid_a_eng_1':90},{1}),0)

    def test_local_get_cannot_target_board_or_inference_route(self):
        for address,path in [('192.168.50.2','/health'),('example.com','/health'),
                             ('127.0.0.1','/v1/inference/llm'),('127.0.0.1','/api/generate')]:
            with self.assertRaises(ValueError):d.local_json(address,11435,path)

    def test_missing_metric_is_not_formatted_as_zero(self):
        self.assertEqual(d.fmt(None,'%'),'—');self.assertEqual(d.memory_text(None),'—')
        self.assertEqual(d.fmt(0,'%'),'0.0%')


class HostTelemetry(unittest.TestCase):
    def response(self):
        return dict(ok=True,data=dict(ok=True,protocol_version=1,role='model_inference_only',
            active=False,pending=0,counts={},backend=dict(tts_ready=True,
                gpu_coordination=dict(active={'llm':0,'tts':0},queued=0,last_wait_ms=12.5))))

    def test_known_empty_counter_means_zero(self):
        value=d.health_metadata(self.response())
        self.assertTrue(value['available']);self.assertEqual(value['counters']['completed'],0)
        self.assertEqual(value['counters']['accepted_llm'],0)

    def test_missing_or_denied_health_is_unknown_not_zero(self):
        for response in (None,{},dict(ok=False,status=403),dict(ok=True,data={})):
            with self.subTest(response=response):
                value=d.health_metadata(response)
                self.assertFalse(value['available']);self.assertNotIn('completed',value['counters'])
                self.assertIsNone(value['pending']);self.assertIsNone(value['active'])

    def test_wrong_role_closed_host_or_bool_protocol_is_not_trusted(self):
        for key,bad in [('role','other-service'),('ok',False),('protocol_version',True)]:
            response=self.response();response['data'][key]=bad
            self.assertFalse(d.health_metadata(response)['available'])

    def test_counter_invalid_values_cannot_invent_completions(self):
        for bad in (True,False,-1,float('nan'),float('inf'),0.0,'12',1<<60):
            response=self.response();response['data']['counts']['completed']=bad
            with self.subTest(value=bad):
                self.assertNotIn('completed',d.health_metadata(response)['counters'])

    def test_missing_counter_object_stays_unknown(self):
        for bad in (None,[],True,''):
            response=self.response();response['data']['counts']=bad
            self.assertEqual(d.health_metadata(response)['counters'],{})

    def test_gpu_phase_requires_bounded_nonnegative_integer(self):
        for bad in (True,False,-1,float('nan'),float('inf'),1.0,'1',4097):
            response=self.response();response['data']['backend']['gpu_coordination']['active']['llm']=bad
            with self.subTest(value=bad):
                value=d.health_metadata(response)
                self.assertIsNone(value['gpu_active']['llm'])
                self.assertEqual(d.task_phase_state('llm',value,('模型已驻留','ready')),('模型已驻留','ready'))

    def test_pending_and_gpu_queue_reject_bool(self):
        response=self.response();response['data']['pending']=True
        response['data']['backend']['gpu_coordination']['queued']=False
        value=d.health_metadata(response)
        self.assertIsNone(value['pending']);self.assertIsNone(value['gpu_queued'])

    def test_wait_rejects_bool_nonfinite_negative_string_and_overflow(self):
        for bad in (True,False,float('nan'),float('inf'),-1,'12.5',1<<10000):
            response=self.response();response['data']['backend']['gpu_coordination']['last_wait_ms']=bad
            with self.subTest(kind=type(bad).__name__):
                self.assertIsNone(d.health_metadata(response)['gpu_last_wait_ms'])
        response=self.response();response['data']['backend']['gpu_coordination']['last_wait_ms']=0
        self.assertEqual(d.health_metadata(response)['gpu_last_wait_ms'],0.0)

    def test_residency_and_ready_do_not_prove_inference(self):
        value=d.health_metadata(self.response())
        self.assertEqual(d.task_phase_state('llm',value,('模型已驻留','ready')),('模型已驻留','ready'))
        self.assertEqual(d.task_phase_state('tts',value,('模型就绪','ready')),('模型就绪','ready'))
        self.assertEqual(d.phase_summary(value),('当前待机','ready'))

    def test_llm_lease_marks_only_llm_phase_and_host_busy(self):
        response=self.response();response['data']['active']=True
        response['data']['backend']['gpu_coordination']['active']['llm']=1
        value=d.health_metadata(response)
        self.assertEqual(d.task_phase_state('llm',value,('模型已驻留','ready')),('LLM 推理中','busy'))
        self.assertEqual(d.task_phase_state('tts',value,('模型就绪','ready')),('模型就绪','ready'))
        self.assertEqual(d.task_phase_state('host',value,('监听中','online')),('LLM 推理中','busy'))

    def test_tts_lease_marks_tts_without_guessing_llm_request_kind(self):
        response=self.response();response['data']['active']=True
        response['data']['backend']['gpu_coordination']['active']['tts']=1
        value=d.health_metadata(response)
        self.assertEqual(d.task_phase_state('tts',value,('模型就绪','ready')),('TTS 合成中','busy'))
        self.assertEqual(d.task_phase_state('llm',value,('模型已驻留','ready')),('模型已驻留','ready'))
        self.assertEqual(d.phase_summary(value),('TTS 合成中','busy'))

    def test_host_active_without_lease_is_processing_or_waiting(self):
        response=self.response();response['data']['active']=True
        for active in ({'llm':0,'tts':0},{},{'llm':None,'tts':None}):
            response['data']['backend']['gpu_coordination']['active']=active
            self.assertEqual(d.phase_summary(d.health_metadata(response)),('处理 / 等待资源','busy'))

    def test_malformed_host_active_does_not_look_idle(self):
        response=self.response();response['data']['active']='false'
        value=d.health_metadata(response)
        self.assertIsNone(value['active']);self.assertEqual(d.phase_summary(value),('任务遥测未提供','online'))

    def test_scalar_projection_drops_private_ids_and_arbitrary_keys(self):
        response=self.response();response['data']['private_request']='PRIVATE_REQUEST_TOKEN'
        gpu=response['data']['backend']['gpu_coordination']
        gpu['lease_id']='PRIVATE_LEASE_TOKEN';gpu['active']['raw_payload']='PRIVATE_PAYLOAD'
        response['data']['counts']['secret']='PRIVATE_COUNT'
        before=copy.deepcopy(response);value=d.health_metadata(response)
        self.assertNotIn('PRIVATE_',json.dumps(value));self.assertEqual(response,before)
        self.assertEqual(value['gpu_queued'],0);self.assertEqual(value['gpu_last_wait_ms'],12.5)


if __name__=='__main__':unittest.main()
